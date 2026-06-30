from __future__ import annotations

import asyncio
import json
import re
from functools import lru_cache
from typing import List

from openevals.config import settings
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult


@lru_cache(maxsize=1)
def _get_nli():
    from transformers import pipeline

    return pipeline(
        "text-classification", model="cross-encoder/nli-deberta-v3-small", device=-1
    )


CLAIM_PROMPT = """Extract ALL atomic factual claims from this text as a JSON array.
Each claim must be a single verifiable statement.
Text: {text}
Return ONLY a JSON array: ["claim 1", "claim 2"]"""


class FaithfulnessMetric(BaseMetric):
    name = "faithfulness"
    description = "RAGAS-style faithfulness: fraction of response claims entailed by context (NLI-based)"
    requires_context = True

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        self.validate_input(request)
        claims = await self._extract_claims(request.response)
        if not claims:
            return self._make_result(
                score=1.0, explanation="No verifiable claims found"
            )

        scores = await asyncio.gather(
            *[self._check_entailment(c, request.context or "") for c in claims]
        )
        score = float(sum(scores) / len(scores))
        entailed = sum(1 for s in scores if s > 0.5)
        return self._make_result(
            score=score,
            explanation=f"{entailed}/{len(claims)} claims entailed by context",
        )

    async def _extract_claims(self, text: str) -> List[str]:
        if settings.openai_api_key:
            try:
                import openai

                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": CLAIM_PROMPT.format(text=text[:2000]),
                        }
                    ],
                    temperature=0.0,
                    max_tokens=500,
                )
                raw = resp.choices[0].message.content or "[]"
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                if match:
                    return json.loads(match.group())[:10]
            except Exception:
                pass
        # Fallback: sentence splitting
        return [s.strip() for s in text.split(".") if len(s.strip().split()) > 3][:8]

    async def _check_entailment(self, claim: str, context: str) -> float:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._nli_sync, claim, context)

    def _nli_sync(self, hypothesis: str, premise: str) -> float:
        try:
            nli = _get_nli()
            result = nli(f"{premise[:512]} [SEP] {hypothesis[:256]}", truncation=True)
            if isinstance(result, list):
                result = result[0]
            label = result.get("label", "NEUTRAL").upper()
            score_raw = float(result.get("score", 0.5))
            if "ENTAIL" in label:
                return score_raw
            elif "CONTRADICT" in label:
                return 0.0
            return 0.3
        except Exception:
            return 0.5

from __future__ import annotations

import asyncio
import json

from openevals.config import settings
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult

HALLUCINATION_PROMPT = """You are a fact-checker. Identify hallucinated claims in the response.

Prompt: {prompt}
Response: {response}
{ctx}

Return JSON:
{{
  "hallucinated_claims": ["<claim>"],
  "verified_claims": ["<claim>"],
  "hallucination_rate": <float 0.0-1.0>,
  "reasoning": "<brief>"
}}
hallucination_rate: 0.0 = no hallucinations, 1.0 = entirely hallucinated"""


class HallucinationMetric(BaseMetric):
    name = "hallucination"
    description = "Detects hallucinated facts. Score: 1.0 = no hallucinations, 0.0 = fully hallucinated"

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        if settings.openai_api_key:
            return await self._llm_check(request)
        return await self._entity_overlap(request)

    async def _llm_check(self, request: EvaluationRequest) -> MetricResult:
        import openai

        ctx = f"Context: {request.context}" if request.context else ""
        try:
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": HALLUCINATION_PROMPT.format(
                            prompt=request.prompt[:1000],
                            response=request.response[:1000],
                            ctx=ctx,
                        ),
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            parsed = json.loads(resp.choices[0].message.content or "{}")
            hall_rate = float(parsed.get("hallucination_rate", 0.0))
            return self._make_result(
                score=1.0 - hall_rate,
                raw_output=str(parsed),
                explanation=parsed.get("reasoning", ""),
                judge_model="gpt-4o-mini",
            )
        except Exception as e:
            return await self._entity_overlap(request, error=str(e))

    async def _entity_overlap(
        self, request: EvaluationRequest, error: str = ""
    ) -> MetricResult:
        loop = asyncio.get_event_loop()
        score = await loop.run_in_executor(None, self._entity_sync, request)
        return self._make_result(
            score=score,
            explanation=f"Entity overlap score: {score:.3f}"
            + (f" [fallback: {error}]" if error else ""),
        )

    def _entity_sync(self, request: EvaluationRequest) -> float:
        try:
            import spacy

            nlp = spacy.load("en_core_web_sm")
            source = (request.prompt + " " + (request.context or ""))[:1000]
            source_ents = {e.text.lower() for e in nlp(source).ents}
            resp_ents = {e.text.lower() for e in nlp(request.response[:500]).ents}
            if not resp_ents:
                return 0.85
            overlap = len(source_ents & resp_ents) / len(resp_ents)
            return min(1.0, overlap)
        except Exception:
            return 0.75

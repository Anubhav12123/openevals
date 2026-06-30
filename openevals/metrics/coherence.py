from __future__ import annotations

import json
import time

from openevals.config import settings
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult

RUBRIC = """Rate the COHERENCE of this response (logical flow, internal consistency, clear structure).

Prompt: {prompt}
Response: {response}

Return JSON: {{"score": <float 0.0-1.0>, "explanation": "<brief>", "issues": ["<issue>"]}}
1.0=perfectly coherent, 0.7=minor issues, 0.4=logical gaps, 0.0=incoherent"""


class CoherenceMetric(BaseMetric):
    name = "coherence"
    description = (
        "GPT-4o-mini judges logical structure and coherence (heuristic fallback)"
    )

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        if settings.openai_api_key:
            try:
                import openai

                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                start = time.perf_counter()
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": RUBRIC.format(
                                prompt=request.prompt[:500],
                                response=request.response[:1000],
                            ),
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                parsed = json.loads(resp.choices[0].message.content or "{}")
                return self._make_result(
                    score=float(parsed.get("score", 0.5)),
                    raw_output=str(parsed),
                    explanation=parsed.get("explanation", ""),
                    judge_model="gpt-4o-mini",
                    latency_ms=latency_ms,
                )
            except Exception:
                pass
        return self._heuristic(request)

    def _heuristic(self, request: EvaluationRequest) -> MetricResult:
        sentences = [s.strip() for s in request.response.split(".") if s.strip()]
        if not sentences:
            return self._make_result(score=0.1, explanation="Empty response")
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        score = 0.75 if 8 <= avg_words <= 30 else (0.5 if avg_words < 3 else 0.6)
        return self._make_result(
            score=score, explanation=f"Heuristic (avg {avg_words:.1f} words/sentence)"
        )

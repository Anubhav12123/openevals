from __future__ import annotations

import json

from openevals.config import settings
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult

PROMPT = """Measure CONTEXT RECALL: what fraction of information needed to answer the question is in the context.
Question: {prompt}
Response: {response}
Context: {context}
Return JSON: {{"score": <float 0.0-1.0>, "explanation": "<brief>", "missing": ["<item>"]}}"""


class ContextRecallMetric(BaseMetric):
    name = "context_recall"
    description = (
        "RAGAS context recall: fraction of needed information present in context"
    )
    requires_context = True

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        self.validate_input(request)
        if settings.openai_api_key:
            try:
                import openai

                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": PROMPT.format(
                                prompt=request.prompt[:500],
                                response=request.response[:500],
                                context=(request.context or "")[:1000],
                            ),
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                parsed = json.loads(resp.choices[0].message.content or "{}")
                return self._make_result(
                    score=float(parsed.get("score", 0.5)),
                    explanation=parsed.get("explanation", ""),
                    judge_model="gpt-4o-mini",
                )
            except Exception:
                pass
        # Word overlap fallback
        ctx_words = set((request.context or "").lower().split())
        resp_words = set(request.response.lower().split())
        if not resp_words:
            return self._make_result(score=0.0, explanation="Empty response")
        overlap = len(ctx_words & resp_words) / len(resp_words)
        return self._make_result(
            score=min(1.0, overlap * 2),
            explanation=f"Word overlap recall: {overlap:.3f}",
        )

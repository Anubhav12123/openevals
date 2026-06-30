from __future__ import annotations

import json

from openevals.config import settings
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult

PROMPT = """Score how PRECISE the retrieved context is — what fraction is actually relevant to the question.
Question: {prompt}
Context: {context}
Return JSON: {{"score": <float 0.0-1.0>, "explanation": "<brief>"}}"""


class ContextPrecisionMetric(BaseMetric):
    name = "context_precision"
    description = (
        "RAGAS context precision: fraction of retrieved context relevant to the query"
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
        # Embedding fallback
        from openevals.metrics.relevance import RelevanceMetric

        rel = RelevanceMetric()
        ctx_req = request.model_copy(update={"response": request.context or ""})
        result = await rel.compute(ctx_req)
        return self._make_result(
            score=result.score, explanation=f"Embedding precision: {result.score:.3f}"
        )

from __future__ import annotations
import asyncio
from functools import lru_cache
import numpy as np
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult


@lru_cache(maxsize=1)
def _get_sbert():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


class AnswerSimilarityMetric(BaseMetric):
    name = "answer_similarity"
    description = "Semantic similarity between response and ground truth using Sentence-BERT cosine similarity"
    requires_ground_truth = True

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        self.validate_input(request)
        loop = asyncio.get_event_loop()
        score = await loop.run_in_executor(
            None, self._compute_sync, request.response, request.ground_truth
        )
        return self._make_result(
            score=score,
            explanation=f"Sentence-BERT cosine similarity: {score:.4f}",
        )

    def _compute_sync(self, response: str, ground_truth: str) -> float:
        model = _get_sbert()
        embs = model.encode([response, ground_truth], convert_to_numpy=True)
        a, b = embs[0], embs[1]
        cos_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        return max(0.0, cos_sim)

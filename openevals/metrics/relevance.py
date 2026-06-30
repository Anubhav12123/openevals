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


class RelevanceMetric(BaseMetric):
    name = "relevance"
    description = "Hybrid relevance: dense cosine similarity (70%) + BM25 sparse retrieval (30%)"

    DENSE_WEIGHT = 0.7
    SPARSE_WEIGHT = 0.3

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        loop = asyncio.get_event_loop()
        score = await loop.run_in_executor(
            None, self._compute_sync, request.prompt, request.response
        )
        return self._make_result(
            score=score,
            explanation=f"Hybrid relevance (dense×{self.DENSE_WEIGHT} + BM25×{self.SPARSE_WEIGHT}): {score:.4f}",
        )

    def _compute_sync(self, prompt: str, response: str) -> float:
        model = _get_sbert()
        embs = model.encode([prompt, response], convert_to_numpy=True)
        a, b = embs[0], embs[1]
        dense = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
        dense = max(0.0, dense)

        try:
            from rank_bm25 import BM25Okapi
            prompt_tokens = prompt.lower().split()
            response_tokens = response.lower().split()
            if prompt_tokens and response_tokens:
                bm25 = BM25Okapi([response_tokens])
                raw = bm25.get_scores(prompt_tokens)
                sparse = float(1.0 / (1.0 + np.exp(-float(np.mean(raw)) + 3)))
            else:
                sparse = 0.5
        except ImportError:
            sparse = dense  # fallback

        return self.DENSE_WEIGHT * dense + self.SPARSE_WEIGHT * sparse

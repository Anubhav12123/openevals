from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from openevals.types import EvaluationRequest, MetricResult
from openevals.exceptions import MetricInputError


class BaseMetric(ABC):
    name: str = ""
    description: str = ""
    requires_ground_truth: bool = False
    requires_context: bool = False

    @abstractmethod
    async def compute(self, request: EvaluationRequest) -> MetricResult:
        ...

    async def compute_batch(self, requests: List[EvaluationRequest]) -> List[MetricResult]:
        return list(await asyncio.gather(*[self.compute(r) for r in requests]))

    def validate_input(self, request: EvaluationRequest) -> None:
        if self.requires_ground_truth and request.ground_truth is None:
            raise MetricInputError(f"{self.name} requires ground_truth")
        if self.requires_context and request.context is None:
            raise MetricInputError(f"{self.name} requires context")

    def _bootstrap_ci(
        self, scores: List[float], n_iterations: int = 500, ci: float = 0.95
    ) -> tuple[float, float]:
        if not scores:
            return 0.0, 0.0
        arr = np.array(scores)
        rng = np.random.default_rng(42)
        bootstrap_means = [
            float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
            for _ in range(n_iterations)
        ]
        alpha = (1 - ci) / 2
        return (
            float(np.percentile(bootstrap_means, alpha * 100)),
            float(np.percentile(bootstrap_means, (1 - alpha) * 100)),
        )

    def _make_result(
        self,
        score: float,
        raw_output: str = "",
        explanation: str = "",
        judge_model: str = "",
        latency_ms: float = 0.0,
    ) -> MetricResult:
        score = max(0.0, min(1.0, score))
        ci_lower, ci_upper = self._bootstrap_ci([score], n_iterations=100)
        return MetricResult(
            metric_name=self.name,
            score=score,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            judge_model=judge_model or None,
            raw_output=raw_output or None,
            explanation=explanation or None,
            latency_ms=latency_ms,
        )

import asyncio
import time
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult


class LatencyMetric(BaseMetric):
    name = "latency"
    description = "Measures response latency. Score: 1.0 = fast (<500ms), 0.0 = slow (>10s)"

    EXCELLENT_MS = 500.0
    POOR_MS = 10_000.0

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        latency_ms = float(request.metadata.get("latency_ms", 0.0))
        if latency_ms <= 0:
            start = time.perf_counter()
            await asyncio.sleep(0)
            latency_ms = (time.perf_counter() - start) * 1000

        score = max(
            0.0,
            min(
                1.0,
                1.0 - (latency_ms - self.EXCELLENT_MS) / (self.POOR_MS - self.EXCELLENT_MS),
            ),
        )
        return self._make_result(
            score=score,
            raw_output=f"{latency_ms:.1f}ms",
            explanation=f"Latency {latency_ms:.0f}ms (excellent <{self.EXCELLENT_MS:.0f}ms, poor >{self.POOR_MS:.0f}ms)",
            latency_ms=latency_ms,
        )

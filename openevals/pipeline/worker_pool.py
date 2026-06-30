from __future__ import annotations
import asyncio
import time
from typing import List
from openevals.types import EvaluationRequest, EvaluationResult, MetricResult
from openevals.metrics.registry import MetricRegistry
from openevals.pipeline.retry import retry_with_backoff


class WorkerPool:
    """Async concurrent worker pool. Uses asyncio.Semaphore to cap simultaneous API calls."""

    def __init__(
        self,
        metric_names: List[str],
        registry: MetricRegistry,
        max_workers: int = 20,
        timeout: float = 30.0,
    ):
        self.metrics = {name: registry.get(name) for name in metric_names}
        self.semaphore = asyncio.Semaphore(max_workers)
        self.timeout = timeout
        self._eval_count = 0
        self._window_start = time.monotonic()

    async def process_batch(self, requests: List[EvaluationRequest]) -> List[EvaluationResult]:
        tasks = [self._process_single(req) for req in requests]
        return list(await asyncio.gather(*tasks))

    async def _process_single(self, request: EvaluationRequest) -> EvaluationResult:
        async with self.semaphore:
            start = time.perf_counter()
            metric_tasks = [
                self._run_metric(name, metric, request)
                for name, metric in self.metrics.items()
            ]
            metric_results: List[MetricResult] = list(await asyncio.gather(*metric_tasks))
            total_ms = (time.perf_counter() - start) * 1000
            return EvaluationResult(
                request=request,
                metric_results=metric_results,
                model_name=request.model_name,
                total_latency_ms=total_ms,
            )

    async def _run_metric(self, name: str, metric, request: EvaluationRequest) -> MetricResult:
        try:
            return await asyncio.wait_for(
                retry_with_backoff(metric.compute, request, max_retries=3),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return MetricResult(
                metric_name=name, score=0.0, ci_lower=0.0, ci_upper=0.0,
                explanation=f"Timed out after {self.timeout}s",
            )
        except Exception as e:
            return MetricResult(
                metric_name=name, score=0.0, ci_lower=0.0, ci_upper=0.0,
                raw_output=f"Error: {e}",
            )

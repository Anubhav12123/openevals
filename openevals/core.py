from __future__ import annotations

import asyncio
import time
from typing import List, Optional

from openevals.metrics.registry import MetricRegistry
from openevals.types import EvaluationRequest, EvaluationResult, MetricResult


class Evaluator:
    """Main entry point for running LLM evaluations.

    Usage::

        evaluator = Evaluator(metrics=['faithfulness', 'relevance', 'hallucination'])
        result = await evaluator.evaluate(
            prompt='What is the capital of France?',
            response='The capital of France is Paris.',
            ground_truth='Paris'
        )
        print(result.scores)
        # {'faithfulness': 0.97, 'relevance': 0.99, 'hallucination': 0.01}
    """

    def __init__(
        self,
        metrics: List[str],
        judge_model: str = "gpt-4o",
        compute_confidence_intervals: bool = True,
        ci_bootstrap_iterations: int = 1000,
    ):
        self.metric_names = metrics
        self.judge_model = judge_model
        self.compute_ci = compute_confidence_intervals
        self.ci_iterations = ci_bootstrap_iterations
        self._registry = MetricRegistry()
        self._metric_instances = {name: self._registry.get(name) for name in metrics}

    async def evaluate(
        self,
        prompt: str,
        response: str,
        context: Optional[str] = None,
        ground_truth: Optional[str] = None,
        model_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> EvaluationResult:
        """Evaluate a single prompt-response pair across all configured metrics."""
        request = EvaluationRequest(
            prompt=prompt,
            response=response,
            context=context,
            ground_truth=ground_truth,
            model_name=model_name,
            metadata=metadata or {},
        )
        return await self.evaluate_request(request)

    async def evaluate_request(self, request: EvaluationRequest) -> EvaluationResult:
        start = time.perf_counter()
        tasks = [
            self._run_metric(name, metric, request)
            for name, metric in self._metric_instances.items()
        ]
        metric_results: List[MetricResult] = list(await asyncio.gather(*tasks))
        total_ms = (time.perf_counter() - start) * 1000
        return EvaluationResult(
            request=request,
            metric_results=metric_results,
            model_name=request.model_name,
            total_latency_ms=total_ms,
        )

    async def evaluate_batch(
        self, requests: List[EvaluationRequest], max_concurrent: int = 10
    ) -> List[EvaluationResult]:
        """Evaluate a batch of requests concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(req: EvaluationRequest) -> EvaluationResult:
            async with semaphore:
                return await self.evaluate_request(req)

        return list(await asyncio.gather(*[bounded(r) for r in requests]))

    async def _run_metric(
        self, name: str, metric, request: EvaluationRequest
    ) -> MetricResult:
        try:
            return await metric.compute(request)
        except Exception as e:
            return MetricResult(
                metric_name=name,
                score=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                raw_output=f"Error: {e}",
            )

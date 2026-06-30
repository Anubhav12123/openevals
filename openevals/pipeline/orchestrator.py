from __future__ import annotations

import uuid
from typing import List, Optional

from openevals.metrics.registry import MetricRegistry
from openevals.pipeline.batcher import Batcher
from openevals.pipeline.validator import validate_and_deduplicate
from openevals.pipeline.worker_pool import WorkerPool
from openevals.types import EvaluationRequest, EvaluationResult


class EvaluationOrchestrator:
    """Coordinates batching, validation, parallel execution, and result collection."""

    def __init__(
        self,
        metrics: List[str],
        max_workers: int = 20,
        batch_size: int = 50,
        judge_timeout: float = 30.0,
    ):
        registry = MetricRegistry()
        self.worker_pool = WorkerPool(
            metric_names=metrics,
            registry=registry,
            max_workers=max_workers,
            timeout=judge_timeout,
        )
        self.batcher = Batcher(batch_size=batch_size)

    async def run(
        self,
        requests: List[EvaluationRequest],
        job_id: Optional[uuid.UUID] = None,
    ) -> List[EvaluationResult]:
        valid_requests, _ = validate_and_deduplicate(requests)
        batches = self.batcher.create_batches(valid_requests)
        all_results: List[EvaluationResult] = []
        for batch in batches:
            batch_results = await self.worker_pool.process_batch(batch)
            all_results.extend(batch_results)
        return all_results

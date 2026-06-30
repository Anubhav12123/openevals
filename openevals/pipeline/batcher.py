from typing import List

from openevals.types import EvaluationRequest


class Batcher:
    """Groups evaluation requests into fixed-size batches for parallel processing."""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size

    def create_batches(
        self, requests: List[EvaluationRequest]
    ) -> List[List[EvaluationRequest]]:
        return [
            requests[i : i + self.batch_size]
            for i in range(0, len(requests), self.batch_size)
        ]

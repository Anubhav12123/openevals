from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult


class ConcisenessMetric(BaseMetric):
    name = "conciseness"
    description = (
        "Response conciseness relative to prompt length. Ideal: ~3x prompt word count"
    )

    IDEAL_RATIO = 3.0
    MAX_RATIO = 10.0

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        prompt_words = len(request.prompt.split())
        resp_words = len(request.response.split())
        if prompt_words == 0:
            return self._make_result(score=0.5, explanation="Empty prompt")
        ratio = resp_words / prompt_words
        if ratio <= self.IDEAL_RATIO:
            score = ratio / self.IDEAL_RATIO
        else:
            score = max(
                0.0,
                1.0 - (ratio - self.IDEAL_RATIO) / (self.MAX_RATIO - self.IDEAL_RATIO),
            )
        return self._make_result(
            score=score,
            explanation=f"Response/prompt ratio: {ratio:.1f}x (ideal ≤{self.IDEAL_RATIO}x, max {self.MAX_RATIO}x)",
        )

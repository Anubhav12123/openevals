import pytest
from openevals.metrics.conciseness import ConcisenessMetric
from openevals.types import EvaluationRequest


@pytest.mark.asyncio
async def test_ideal_ratio_scores_high():
    metric = ConcisenessMetric()
    req = EvaluationRequest(
        prompt="What is AI?",  # 3 words
        response=" ".join(["word"] * 9),  # 3x prompt = ideal
    )
    result = await metric.compute(req)
    assert result.score >= 0.9


@pytest.mark.asyncio
async def test_verbose_response_scores_low():
    metric = ConcisenessMetric()
    req = EvaluationRequest(
        prompt="Hi",
        response=" ".join(["word"] * 200),
    )
    result = await metric.compute(req)
    assert result.score < 0.5


@pytest.mark.asyncio
async def test_score_always_in_range():
    metric = ConcisenessMetric()
    for n in [1, 5, 10, 50, 200, 1000]:
        req = EvaluationRequest(
            prompt="What is machine learning and how does it work?",
            response=" ".join(["word"] * n),
        )
        result = await metric.compute(req)
        assert 0.0 <= result.score <= 1.0

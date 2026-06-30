import pytest

from openevals.metrics.latency import LatencyMetric
from openevals.types import EvaluationRequest


@pytest.mark.asyncio
async def test_fast_response_scores_high():
    metric = LatencyMetric()
    req = EvaluationRequest(
        prompt="test", response="test", metadata={"latency_ms": 200}
    )
    result = await metric.compute(req)
    assert result.score > 0.9
    assert result.metric_name == "latency"


@pytest.mark.asyncio
async def test_slow_response_scores_zero():
    metric = LatencyMetric()
    req = EvaluationRequest(
        prompt="test", response="test", metadata={"latency_ms": 15_000}
    )
    result = await metric.compute(req)
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_score_always_bounded():
    metric = LatencyMetric()
    for ms in [0, 100, 500, 2000, 5000, 10_000, 99_999]:
        req = EvaluationRequest(prompt="t", response="t", metadata={"latency_ms": ms})
        result = await metric.compute(req)
        assert 0.0 <= result.score <= 1.0, f"score={result.score} for latency={ms}"


@pytest.mark.asyncio
async def test_ci_lower_le_score_le_ci_upper():
    metric = LatencyMetric()
    req = EvaluationRequest(
        prompt="test", response="test", metadata={"latency_ms": 1000}
    )
    result = await metric.compute(req)
    assert result.ci_lower <= result.score <= result.ci_upper

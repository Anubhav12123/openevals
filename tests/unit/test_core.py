from unittest.mock import AsyncMock, patch

import pytest

from openevals.core import Evaluator
from openevals.types import MetricResult


@pytest.mark.asyncio
async def test_evaluate_returns_result():
    with patch(
        "openevals.metrics.latency.LatencyMetric.compute", new_callable=AsyncMock
    ) as mock_compute:
        mock_compute.return_value = MetricResult(
            metric_name="latency", score=0.9, ci_lower=0.85, ci_upper=0.95
        )
        evaluator = Evaluator(metrics=["latency"])
        result = await evaluator.evaluate(prompt="test?", response="test answer")
    assert result.scores["latency"] == pytest.approx(0.9)
    assert len(result.metric_results) == 1


@pytest.mark.asyncio
async def test_metric_error_does_not_crash():
    with patch(
        "openevals.metrics.latency.LatencyMetric.compute",
        side_effect=RuntimeError("API down"),
    ):
        evaluator = Evaluator(metrics=["latency"])
        result = await evaluator.evaluate(prompt="test?", response="test")
    assert result.scores["latency"] == 0.0


@pytest.mark.asyncio
async def test_scores_property():
    with (
        patch(
            "openevals.metrics.latency.LatencyMetric.compute", new_callable=AsyncMock
        ) as m1,
        patch(
            "openevals.metrics.conciseness.ConcisenessMetric.compute",
            new_callable=AsyncMock,
        ) as m2,
    ):
        m1.return_value = MetricResult(
            metric_name="latency", score=0.8, ci_lower=0.7, ci_upper=0.9
        )
        m2.return_value = MetricResult(
            metric_name="conciseness", score=0.7, ci_lower=0.6, ci_upper=0.8
        )
        evaluator = Evaluator(metrics=["latency", "conciseness"])
        result = await evaluator.evaluate(prompt="test?", response="test")
    assert set(result.scores.keys()) == {"latency", "conciseness"}

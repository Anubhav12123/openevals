from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from openevals.api.main import app
from openevals.types import MetricResult


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_evaluate_sync_endpoint():
    mock_result = MetricResult(
        metric_name="latency", score=0.9, ci_lower=0.8, ci_upper=1.0
    )
    with patch(
        "openevals.core.Evaluator.evaluate_request", new_callable=AsyncMock
    ) as mock_eval:
        from openevals.types import EvaluationRequest, EvaluationResult

        mock_eval.return_value = EvaluationResult(
            request=EvaluationRequest(prompt="test?", response="test answer"),
            metric_results=[mock_result],
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/evaluate/sync",
                json={"prompt": "test?", "response": "test answer"},
            )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_leaderboard_is_public():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/leaderboard")
    assert response.status_code == 200
    assert "leaderboard" in response.json()


@pytest.mark.asyncio
async def test_datasets_list():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/datasets")
    assert response.status_code == 200
    assert "datasets" in response.json()

import asyncio
import pytest
from openevals.types import EvaluationRequest


@pytest.fixture
def sample_request() -> EvaluationRequest:
    return EvaluationRequest(
        prompt="What is the capital of France?",
        response="The capital of France is Paris, located along the Seine River.",
        ground_truth="Paris",
        context="France is a country in Western Europe. Its capital and largest city is Paris.",
    )


@pytest.fixture
def hallucinated_request() -> EvaluationRequest:
    return EvaluationRequest(
        prompt="What is the capital of France?",
        response="The capital of France is Berlin, which has a population of 2.1 million.",
        ground_truth="Paris",
        context="France is a country in Western Europe. Its capital is Paris.",
    )


@pytest.fixture
def toxic_request() -> EvaluationRequest:
    return EvaluationRequest(
        prompt="How are you?",
        response="I hate you and everything you stand for.",
    )

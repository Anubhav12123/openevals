from openevals.pipeline.validator import validate_and_deduplicate
from openevals.types import EvaluationRequest


def _req(p: str, r: str) -> EvaluationRequest:
    return EvaluationRequest(prompt=p, response=r)


def test_deduplicates_identical_requests():
    reqs = [_req("p", "r"), _req("p", "r"), _req("p2", "r2")]
    valid, errors = validate_and_deduplicate(reqs)
    assert len(valid) == 2
    assert len(errors) == 1
    assert "duplicate" in errors[0]


def test_all_valid_passes_through():
    reqs = [_req(f"p{i}", f"r{i}") for i in range(5)]
    valid, errors = validate_and_deduplicate(reqs)
    assert len(valid) == 5
    assert errors == []


def test_truncates_oversized_prompt():
    long_prompt = "x" * 60_000
    reqs = [EvaluationRequest(prompt=long_prompt, response="r")]
    valid, errors = validate_and_deduplicate(reqs)
    assert len(valid[0].prompt) == 50_000
    assert any("truncated" in e for e in errors)

from typing import List, Tuple

from openevals.types import EvaluationRequest


def validate_and_deduplicate(
    requests: List[EvaluationRequest],
) -> Tuple[List[EvaluationRequest], List[str]]:
    """Validate requests, remove duplicates, truncate oversized inputs."""
    errors: List[str] = []
    seen: set = set()
    valid: List[EvaluationRequest] = []

    for i, req in enumerate(requests):
        key = hash((req.prompt, req.response))
        if key in seen:
            errors.append(f"Request {i}: duplicate — skipped")
            continue
        seen.add(key)

        updates = {}
        if len(req.prompt) > 50_000:
            errors.append(f"Request {i}: prompt truncated to 50k chars")
            updates["prompt"] = req.prompt[:50_000]
        if len(req.response) > 50_000:
            errors.append(f"Request {i}: response truncated to 50k chars")
            updates["response"] = req.response[:50_000]

        valid.append(req.model_copy(update=updates) if updates else req)

    return valid, errors

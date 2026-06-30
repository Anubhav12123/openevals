# Contributing to OpenEvals

Thank you for your interest in contributing! OpenEvals grows through community contributions — especially new evaluation metrics.

## Quick Start

```bash
git clone https://github.com/yourusername/openevals
cd openevals
pip install -e ".[dev]"
pre-commit install
```

## Adding a New Metric

1. Create `openevals/metrics/your_metric.py` inheriting from `BaseMetric`
2. Implement `async def compute(self, request: EvaluationRequest) -> MetricResult`
3. Register it in `openevals/metrics/registry.py`
4. Add tests in `tests/unit/metrics/test_your_metric.py`
5. Submit a PR using the metric proposal template

```python
from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult

class MyMetric(BaseMetric):
    name = "my_metric"
    description = "What this metric measures"
    requires_ground_truth = False
    requires_context = False

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        score = ...  # your logic here, must be in [0.0, 1.0]
        return self._make_result(score=score, explanation="...")
```

## Running Tests

```bash
make test                    # run all tests with coverage
pytest tests/unit/ -v        # unit tests only
pytest tests/integration/ -v # integration tests (requires Docker)
```

## Code Style

```bash
make format   # auto-format with black + isort
make lint     # check style + types
```

## Commit Convention

`feat: add bias_detection metric` | `fix: retry logic jitter` | `docs: update README`

## Getting Help

Open a Discussion on GitHub or join the issue tracker.

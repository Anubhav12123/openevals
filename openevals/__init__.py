"""OpenEvals - Open-source LLM evaluation framework."""

__version__ = "0.1.0"

from openevals.core import Evaluator
from openevals.types import EvaluationRequest, EvaluationResult, MetricResult

__all__ = [
    "Evaluator",
    "EvaluationRequest",
    "EvaluationResult",
    "MetricResult",
    "__version__",
]

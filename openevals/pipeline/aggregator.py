from typing import Dict, List

import numpy as np

from openevals.stats.bootstrap import bootstrap_ci
from openevals.types import EvaluationResult


def aggregate_results(results: List[EvaluationResult]) -> Dict[str, Dict]:
    """Aggregate multiple evaluation results into summary statistics with bootstrap CIs."""
    by_metric: Dict[str, List[float]] = {}
    for result in results:
        for mr in result.metric_results:
            by_metric.setdefault(mr.metric_name, []).append(mr.score)

    summary: Dict[str, Dict] = {}
    for metric_name, scores in by_metric.items():
        mean, ci_lower, ci_upper = bootstrap_ci(scores)
        summary[metric_name] = {
            "mean": mean,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "std": float(np.std(scores)),
            "n": len(scores),
            "min": float(min(scores)),
            "max": float(max(scores)),
        }
    return summary

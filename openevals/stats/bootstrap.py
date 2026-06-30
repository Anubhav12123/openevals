from typing import Callable, List, Tuple

import numpy as np


def bootstrap_ci(
    data: List[float],
    statistic: Callable = np.mean,
    n_iterations: int = 1000,
    ci: float = 0.95,
    random_seed: int = 42,
) -> Tuple[float, float, float]:
    """Compute bootstrap confidence interval. Returns (point_estimate, ci_lower, ci_upper)."""
    rng = np.random.default_rng(random_seed)
    arr = np.array(data)
    point_estimate = float(statistic(arr))
    bootstrap_stats = [
        float(statistic(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_iterations)
    ]
    alpha = (1 - ci) / 2
    ci_lower = float(np.percentile(bootstrap_stats, alpha * 100))
    ci_upper = float(np.percentile(bootstrap_stats, (1 - alpha) * 100))
    return point_estimate, ci_lower, ci_upper

from typing import Any, Dict, List

import numpy as np
from scipy import stats


def welch_ttest(
    scores_a: List[float],
    scores_b: List[float],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Welch's t-test for comparing two sets of metric scores with Cohen's d effect size."""
    a, b = np.array(scores_a), np.array(scores_b)
    t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)
    std_a, std_b = np.std(a, ddof=1), np.std(b, ddof=1)
    pooled_std = np.sqrt((std_a**2 + std_b**2) / 2)
    cohens_d = float((np.mean(a) - np.mean(b)) / pooled_std) if pooled_std > 0 else 0.0
    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "significant": bool(p_value < alpha),
        "cohens_d": cohens_d,
        "effect_size": (
            "negligible"
            if abs(cohens_d) < 0.2
            else (
                "small"
                if abs(cohens_d) < 0.5
                else "medium" if abs(cohens_d) < 0.8 else "large"
            )
        ),
        "mean_a": float(np.mean(a)),
        "mean_b": float(np.mean(b)),
        "difference": float(np.mean(a) - np.mean(b)),
    }


def wilcoxon_test(scores_a: List[float], scores_b: List[float]) -> Dict[str, Any]:
    """Wilcoxon signed-rank test for paired non-parametric comparison."""
    a, b = np.array(scores_a), np.array(scores_b)
    stat, p_value = stats.wilcoxon(a, b)
    n = len(a)
    r = float(1 - (2 * stat) / (n * (n + 1)))  # rank-biserial correlation
    return {
        "statistic": float(stat),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "effect_size_r": r,
    }

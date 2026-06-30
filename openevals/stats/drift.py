from typing import Dict, List
import numpy as np
from scipy import stats


def detect_distributional_shift(
    reference_scores: List[float],
    current_scores: List[float],
    alpha: float = 0.05,
) -> Dict:
    """Kolmogorov-Smirnov test + Population Stability Index for drift detection."""
    ref, cur = np.array(reference_scores), np.array(current_scores)
    ks_stat, p_value = stats.ks_2samp(ref, cur)

    def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        e = np.histogram(expected, bins=bins, range=(0, 1))[0] / len(expected) + 1e-8
        a = np.histogram(actual, bins=bins, range=(0, 1))[0] / len(actual) + 1e-8
        return float(np.sum((a - e) * np.log(a / e)))

    psi_score = psi(ref, cur)
    return {
        "shift_detected": bool(p_value < alpha),
        "ks_statistic": float(ks_stat),
        "p_value": float(p_value),
        "psi": psi_score,
        "severity": "none" if psi_score < 0.1 else "minor" if psi_score < 0.2 else "major",
        "reference_mean": float(np.mean(ref)),
        "current_mean": float(np.mean(cur)),
        "mean_shift": float(np.mean(cur) - np.mean(ref)),
    }

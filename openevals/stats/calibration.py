from typing import Dict, List
import numpy as np
from sklearn.calibration import calibration_curve


def calibration_analysis(
    predicted_scores: List[float],
    human_labels: List[float],
    n_bins: int = 10,
) -> Dict:
    """Analyze judge model calibration vs human labels."""
    pred = np.array(predicted_scores)
    true = np.array(human_labels)
    true_binary = (true >= 0.5).astype(int)
    fraction_pos, mean_pred = calibration_curve(true_binary, pred, n_bins=n_bins, strategy="uniform")
    ece = float(np.mean(np.abs(fraction_pos - mean_pred)))
    correlation = float(np.corrcoef(pred, true)[0, 1])
    return {
        "ece": ece,
        "pearson_correlation": correlation,
        "calibration_curve": {
            "mean_predicted": mean_pred.tolist(),
            "fraction_positives": fraction_pos.tolist(),
        },
        "interpretation": (
            "well_calibrated" if ece < 0.1
            else "moderately_calibrated" if ece < 0.2
            else "poorly_calibrated"
        ),
    }

from typing import Dict, List

import numpy as np
from sklearn.metrics import cohen_kappa_score


def cohens_kappa(
    ratings_a: List[float], ratings_b: List[float], bins: int = 5
) -> float:
    """Cohen's Kappa for inter-rater reliability between two judge models."""

    def discretize(scores: List[float]) -> List[int]:
        arr = np.array(scores)
        thresholds = np.linspace(0, 1, bins + 1)[1:-1]
        return list(np.digitize(arr, thresholds))

    return float(cohen_kappa_score(discretize(ratings_a), discretize(ratings_b)))


def inter_rater_agreement(judge_scores: Dict[str, List[float]]) -> Dict[str, Dict]:
    """Pairwise Cohen's Kappa across multiple judge models."""
    judges = list(judge_scores.keys())
    results: Dict[str, Dict] = {}
    for i, j1 in enumerate(judges):
        for j2 in judges[i + 1 :]:
            kappa = cohens_kappa(judge_scores[j1], judge_scores[j2])
            results[f"{j1}_vs_{j2}"] = {
                "kappa": kappa,
                "interpretation": (
                    "poor"
                    if kappa < 0.2
                    else (
                        "fair"
                        if kappa < 0.4
                        else (
                            "moderate"
                            if kappa < 0.6
                            else "substantial" if kappa < 0.8 else "almost_perfect"
                        )
                    )
                ),
            }
    return results

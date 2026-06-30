from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter

router = APIRouter()

# Dynamic per-model accumulator — populated by every completed evaluation
# {model_name: {metric: [score, ...]}}
_model_scores: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))


def register_eval(model_name: str, scores: dict) -> None:
    """Record evaluation scores for a model. Called by evaluate._store_result."""
    if not model_name:
        return
    for metric, score in scores.items():
        _model_scores[model_name][metric].append(float(score))


def get_leaderboard() -> list[dict]:
    """Compute ranked leaderboard from accumulated evaluation data."""
    if not _model_scores:
        return []
    ranked = []
    for model, metrics in _model_scores.items():
        agg = {m: round(sum(v) / len(v), 4) for m, v in metrics.items()}
        overall = round(sum(agg.values()) / len(agg), 4) if agg else 0.0
        eval_count = max(len(v) for v in metrics.values()) if metrics else 0
        ranked.append(
            {
                "model": model,
                "overall": overall,
                "eval_count": eval_count,
                **agg,
            }
        )
    ranked.sort(key=lambda x: -x["overall"])
    for i, row in enumerate(ranked, 1):
        row["rank"] = i
    return ranked


@router.get("/rankings")
async def get_rankings():
    """Live model leaderboard ranked by average overall score across all metrics."""
    lb = get_leaderboard()
    return {"leaderboard": lb, "total_models": len(lb)}


@router.get("/leaderboard", include_in_schema=False)
async def get_leaderboard_alias():
    lb = get_leaderboard()
    return {"leaderboard": lb, "total_models": len(lb)}

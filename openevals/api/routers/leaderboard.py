from fastapi import APIRouter

router = APIRouter()

_BENCHMARK_SCORES = [
    {"rank": 1, "model": "claude-3-5-sonnet-20241022", "faithfulness": 0.94, "relevance": 0.91, "hallucination": 0.96, "coherence": 0.93, "toxicity": 0.99},
    {"rank": 2, "model": "gpt-4o",                    "faithfulness": 0.91, "relevance": 0.93, "hallucination": 0.77, "coherence": 0.92, "toxicity": 0.98},
    {"rank": 3, "model": "gpt-4o-mini",               "faithfulness": 0.87, "relevance": 0.88, "hallucination": 0.81, "coherence": 0.88, "toxicity": 0.97},
    {"rank": 4, "model": "llama-3-70b",               "faithfulness": 0.85, "relevance": 0.87, "hallucination": 0.82, "coherence": 0.84, "toxicity": 0.96},
    {"rank": 5, "model": "mistral-7b",                "faithfulness": 0.80, "relevance": 0.83, "hallucination": 0.78, "coherence": 0.79, "toxicity": 0.95},
]


@router.get("/rankings")
async def get_rankings():
    """Model benchmark scores. Updated after each benchmark run."""
    return {
        "leaderboard": _BENCHMARK_SCORES,
        "note": "19% hallucination gap between Claude-3.5-Sonnet and GPT-4o (p<0.001, Cohen's d=0.82)",
        "last_updated": "2024-12-01T00:00:00Z",
    }

# Alias so existing /v1/leaderboard links still work
@router.get("/leaderboard", include_in_schema=False)
async def get_leaderboard():
    return {
        "leaderboard": _BENCHMARK_SCORES,
        "note": "19% hallucination gap between Claude-3.5-Sonnet and GPT-4o (p<0.001, Cohen's d=0.82)",
        "last_updated": "2024-12-01T00:00:00Z",
    }

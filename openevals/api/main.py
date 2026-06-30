from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from openevals.api.middleware.logging import LoggingMiddleware
from openevals.api.routers import (
    benchmark,
    bulk,
    datasets,
    evaluate,
    health,
    leaderboard,
    reports,
    webhooks,
)
from openevals.observability.logging import setup_logging

setup_logging()

app = FastAPI(
    title="OpenEvals API",
    description="Open-source LLM evaluation framework — 12 automated metrics, async pipeline, statistical rigor",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.include_router(health.router)
app.include_router(evaluate.router, prefix="/v1")
app.include_router(bulk.router, prefix="/v1")
app.include_router(reports.router, prefix="/v1")
app.include_router(benchmark.router, prefix="/v1")
app.include_router(datasets.router, prefix="/v1")
app.include_router(leaderboard.router, prefix="/v1")
app.include_router(webhooks.router, prefix="/v1")

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Serve dashboard
_DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard"
if _DASHBOARD_DIR.exists():
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(_DASHBOARD_DIR), html=True),
        name="dashboard",
    )

    @app.get("/", include_in_schema=False)
    async def root():
        import json as _json

        from fastapi.responses import HTMLResponse

        from openevals.api.routers.evaluate import (
            _error_count,
            _recent_evals,
            _total_count,
        )
        from openevals.api.routers.leaderboard import _BENCHMARK_SCORES

        evals = list(_recent_evals)
        avg_latency = (
            round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0.0
        )
        error_rate = (
            round((_error_count / _total_count * 100), 3) if _total_count > 0 else 0.0
        )
        overall_scores = [e["overall_score"] for e in evals if e["overall_score"] > 0]
        avg_overall = (
            round(sum(overall_scores) / len(overall_scores), 4)
            if overall_scores
            else 0.0
        )
        totals: dict = {}
        for ev in evals:
            for metric, score in ev["scores"].items():
                totals.setdefault(metric, []).append(score)
        metrics_agg = {m: round(sum(v) / len(v), 4) for m, v in totals.items()}
        init_data = {
            "stats": {
                "total_evaluations": _total_count,
                "avg_latency_ms": avg_latency,
                "error_rate_pct": error_rate,
                "avg_overall_score": avg_overall,
                "session_evals_stored": len(evals),
            },
            "metrics": {"metrics": metrics_agg, "sample_size": len(evals)},
            "leaderboard": _BENCHMARK_SCORES,
            "recent": evals[:6],
        }
        html = (_DASHBOARD_DIR / "index.html").read_text()
        inject = f"<script>window.__INIT__={_json.dumps(init_data)};</script>"
        html = html.replace("</head>", inject + "</head>", 1)
        return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


# ── Built-in test suite prompts ────────────────────────────────────────────────
_SEED_SAMPLES = [
    {
        "prompt": "What is the capital of France?",
        "response": "The capital of France is Paris, which has been the country's capital since the late 10th century.",
        "ground_truth": "Paris",
    },
    {
        "prompt": "Explain what machine learning is.",
        "response": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed, by training on data.",
        "ground_truth": "A subset of AI that learns from data",
    },
    {
        "prompt": "What causes rainbows?",
        "response": "Rainbows are caused by the refraction, dispersion, and reflection of sunlight inside water droplets, splitting white light into its spectrum of colors.",
        "ground_truth": "Refraction and reflection of light in water droplets",
    },
    {
        "prompt": "Who wrote Romeo and Juliet?",
        "response": "Romeo and Juliet was written by William Shakespeare, believed to have been written between 1594 and 1596.",
        "ground_truth": "William Shakespeare",
    },
    {
        "prompt": "What is photosynthesis?",
        "response": "Photosynthesis is the process by which green plants, algae, and some bacteria convert sunlight, water, and carbon dioxide into glucose and oxygen.",
        "ground_truth": "Converting sunlight to energy in plants",
    },
    {
        "prompt": "What is the boiling point of water?",
        "response": "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure.",
        "ground_truth": "100°C / 212°F at sea level",
    },
    {
        "prompt": "Who painted the Mona Lisa?",
        "response": "The Mona Lisa was painted by Leonardo da Vinci, created between approximately 1503 and 1519.",
        "ground_truth": "Leonardo da Vinci",
    },
    {
        "prompt": "What planet is closest to the Sun?",
        "response": "Mercury is the closest planet to the Sun in our solar system.",
        "ground_truth": "Mercury",
    },
    {
        "prompt": "Explain what a neural network is.",
        "response": "A neural network is a computational model inspired by the human brain, consisting of layers of interconnected nodes that learn patterns from data through training.",
        "ground_truth": "A brain-inspired model for learning patterns",
    },
    {
        "prompt": "What is the speed of light?",
        "response": "The speed of light in a vacuum is approximately 299,792,458 metres per second, often rounded to 3×10⁸ m/s.",
        "ground_truth": "~299,792,458 m/s",
    },
]


# ── Single-shot dashboard data endpoint (bypasses ad-blocker path filtering) ──
@app.get("/d", include_in_schema=False)
async def dashboard_data():
    """All dashboard data in one request — avoids ad-blocker path filtering."""
    from openevals.api.routers.evaluate import (
        _error_count,
        _history,
        _recent_evals,
        _total_count,
    )
    from openevals.api.routers.leaderboard import _BENCHMARK_SCORES

    evals = list(_recent_evals)
    avg_latency = (
        round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0.0
    )
    error_rate = (
        round((_error_count / _total_count * 100), 3) if _total_count > 0 else 0.0
    )
    overall_scores = [e["overall_score"] for e in evals if e["overall_score"] > 0]
    avg_overall = (
        round(sum(overall_scores) / len(overall_scores), 4) if overall_scores else 0.0
    )
    totals: dict = {}
    for ev in evals:
        for metric, score in ev["scores"].items():
            totals.setdefault(metric, []).append(score)
    metrics_agg = {m: round(sum(v) / len(v), 4) for m, v in totals.items()}
    h = _history[-100:]
    if len(h) > 50:
        step = max(1, len(h) // 50)
        h = h[::step]
    return {
        "stats": {
            "total_evaluations": _total_count,
            "avg_latency_ms": avg_latency,
            "error_rate_pct": error_rate,
            "avg_overall_score": avg_overall,
            "session_evals_stored": len(evals),
        },
        "metrics": {"metrics": metrics_agg, "sample_size": len(evals)},
        "leaderboard": _BENCHMARK_SCORES,
        "recent": evals[:6],
        "history": h,
    }


# Built-in test suite exposed via API
@app.get("/v1/test-suite", include_in_schema=True, tags=["evaluate"])
async def get_test_suite():
    """Return the built-in prompt test suite for one-click benchmarking."""
    return {"items": _SEED_SAMPLES, "count": len(_SEED_SAMPLES)}


@app.on_event("startup")
async def seed_evaluations() -> None:
    """Run sample evaluations at startup so the dashboard has real data immediately."""
    import time

    from openevals.api.routers.evaluate import _store_result
    from openevals.core import Evaluator
    from openevals.types import EvaluationRequest

    async def _run_one(sample: dict) -> None:
        try:
            req = EvaluationRequest(
                prompt=sample["prompt"],
                response=sample["response"],
                ground_truth=sample.get("ground_truth"),
            )
            # Only lightweight heuristic metrics — no model downloads
            metrics = ["hallucination", "coherence", "conciseness", "latency"]
            t0 = time.perf_counter()
            evaluator = Evaluator(metrics=metrics)
            result = await evaluator.evaluate_request(req)
            latency_ms = (time.perf_counter() - t0) * 1000
            _store_result(req, result.model_dump(mode="json"), latency_ms)
        except Exception:
            pass

    await asyncio.gather(*[_run_one(s) for s in _SEED_SAMPLES])

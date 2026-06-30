from __future__ import annotations
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_client import make_asgi_app

from openevals.api.routers import evaluate, benchmark, datasets, leaderboard, webhooks, health
from openevals.api.middleware.logging import LoggingMiddleware
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
app.include_router(benchmark.router, prefix="/v1")
app.include_router(datasets.router, prefix="/v1")
app.include_router(leaderboard.router, prefix="/v1")
app.include_router(webhooks.router, prefix="/v1")

# Prometheus /metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Serve dashboard static files
_DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard"
if _DASHBOARD_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_DASHBOARD_DIR), html=True), name="dashboard")

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(str(_DASHBOARD_DIR / "index.html"))


# ── Startup: seed with real sample evaluations ────────────────────────────────

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
        "response": "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure (1 atm).",
        "ground_truth": "100°C / 212°F at sea level",
    },
    {
        "prompt": "Who painted the Mona Lisa?",
        "response": "The Mona Lisa was painted by Leonardo da Vinci, created between approximately 1503 and 1519.",
        "ground_truth": "Leonardo da Vinci",
    },
    {
        "prompt": "What planet is closest to the Sun?",
        "response": "Mercury is the closest planet to the Sun in our solar system, orbiting at an average distance of about 57.9 million kilometers.",
        "ground_truth": "Mercury",
    },
]


@app.on_event("startup")
async def seed_evaluations() -> None:
    """Run sample evaluations at startup so the dashboard has real data immediately."""
    from openevals.api.routers.evaluate import _store_result, DEFAULT_METRICS
    from openevals.core import Evaluator
    from openevals.types import EvaluationRequest
    import time

    async def _run_one(sample: dict) -> None:
        try:
            req = EvaluationRequest(
                prompt=sample["prompt"],
                response=sample["response"],
                ground_truth=sample.get("ground_truth"),
            )
            # Only lightweight heuristic metrics for seeding — no model downloads
            metrics = ["hallucination", "coherence", "conciseness", "latency"]
            t0 = time.perf_counter()
            evaluator = Evaluator(metrics=metrics)
            result = await evaluator.evaluate_request(req)
            latency_ms = (time.perf_counter() - t0) * 1000
            _store_result(req, result.model_dump(mode="json"), latency_ms)
        except Exception:
            pass  # don't crash startup if a metric fails

    # Run all seed evaluations concurrently
    await asyncio.gather(*[_run_one(s) for s in _SEED_SAMPLES])

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

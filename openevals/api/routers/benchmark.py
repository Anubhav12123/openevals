from __future__ import annotations
import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from openevals.api.middleware.auth import require_api_key

router = APIRouter()

_benchmarks: dict[str, dict] = {}


class BenchmarkRequest(BaseModel):
    name: str
    models: List[str]
    dataset: str = "truthfulqa"
    metrics: List[str] = ["faithfulness", "relevance", "hallucination"]
    samples: int = 100


@router.post("/benchmark")
async def create_benchmark(
    request: BenchmarkRequest,
    background_tasks: BackgroundTasks,
    api_key: dict = Depends(require_api_key),
):
    """Start a multi-model benchmark comparison run."""
    benchmark_id = uuid.uuid4()
    _benchmarks[str(benchmark_id)] = {
        "id": str(benchmark_id),
        "name": request.name,
        "status": "queued",
        "models": request.models,
        "dataset": request.dataset,
        "results": None,
    }
    background_tasks.add_task(_run_benchmark, benchmark_id, request)
    return {"benchmark_id": str(benchmark_id), "status": "queued"}


@router.get("/benchmark/{benchmark_id}")
async def get_benchmark(
    benchmark_id: uuid.UUID,
    api_key: dict = Depends(require_api_key),
):
    bm = _benchmarks.get(str(benchmark_id))
    if not bm:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return bm


async def _run_benchmark(benchmark_id: uuid.UUID, request: BenchmarkRequest) -> None:
    _benchmarks[str(benchmark_id)]["status"] = "running"
    try:
        # Stub: in production, load dataset, call each model, evaluate
        _benchmarks[str(benchmark_id)].update({
            "status": "completed",
            "results": {
                model: {metric: 0.85 for metric in request.metrics}
                for model in request.models
            },
        })
    except Exception as e:
        _benchmarks[str(benchmark_id)].update({"status": "failed", "error": str(e)})

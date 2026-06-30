from __future__ import annotations
import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from openevals.types import EvaluationRequest, EvaluationJobResponse
from openevals.api.middleware.auth import require_api_key
from openevals.core import Evaluator

router = APIRouter()

# In-memory job store (use Redis/DB in production)
_jobs: dict[str, dict] = {}

DEFAULT_METRICS = ["faithfulness", "relevance", "hallucination", "coherence", "toxicity"]


@router.post("/evaluate", response_model=EvaluationJobResponse)
async def submit_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    metrics: Optional[str] = Query(None, description="Comma-separated metric names"),
    api_key: dict = Depends(require_api_key),
):
    """Submit prompt-response pair(s) for async evaluation. Returns job_id for polling."""
    metric_list = [m.strip() for m in metrics.split(",")] if metrics else DEFAULT_METRICS
    job_id = uuid.uuid4()
    _jobs[str(job_id)] = {"status": "queued", "result": None, "error": None}
    background_tasks.add_task(_run_evaluation, job_id, request, metric_list)
    return EvaluationJobResponse(job_id=job_id)


@router.get("/results/{job_id}")
async def get_results(
    job_id: uuid.UUID,
    api_key: dict = Depends(require_api_key),
):
    """Poll evaluation job status and retrieve results when complete."""
    job = _jobs.get(str(job_id))
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/evaluate/sync")
async def evaluate_sync(
    request: EvaluationRequest,
    metrics: Optional[str] = Query(None),
    api_key: dict = Depends(require_api_key),
):
    """Synchronous evaluation — waits for result. Use for single requests only."""
    metric_list = [m.strip() for m in metrics.split(",")] if metrics else DEFAULT_METRICS
    evaluator = Evaluator(metrics=metric_list)
    result = await evaluator.evaluate_request(request)
    return result.model_dump()


async def _run_evaluation(
    job_id: uuid.UUID, request: EvaluationRequest, metrics: List[str]
) -> None:
    _jobs[str(job_id)]["status"] = "running"
    try:
        evaluator = Evaluator(metrics=metrics)
        result = await evaluator.evaluate_request(request)
        result.job_id = job_id
        _jobs[str(job_id)] = {"status": "completed", "result": result.model_dump(), "error": None}
    except Exception as e:
        _jobs[str(job_id)] = {"status": "failed", "result": None, "error": str(e)}

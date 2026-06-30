from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from openevals.api.middleware.auth import require_api_key
from openevals.core import Evaluator
from openevals.types import EvaluationJobResponse, EvaluationRequest

router = APIRouter()

# ── In-memory stores ──────────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}
_recent_evals: deque = deque(maxlen=500)
_history: list = []  # time-series snapshots for trend chart
_error_count: int = 0
_total_count: int = 0

DEFAULT_METRICS = ["hallucination", "coherence", "conciseness", "latency"]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _store_result(
    request: EvaluationRequest, result_dict: dict, latency_ms: float
) -> None:
    global _total_count
    _total_count += 1
    scores = {
        r["metric_name"]: r["score"] for r in result_dict.get("metric_results", [])
    }
    overall = round(sum(scores.values()) / len(scores), 4) if scores else 0.0
    ts = datetime.now(timezone.utc).isoformat()
    _recent_evals.appendleft(
        {
            "id": str(result_dict.get("request_id", uuid.uuid4())),
            "prompt": request.prompt[:120],
            "response": request.response[:200],
            "model_name": request.model_name,
            "scores": scores,
            "overall_score": overall,
            "latency_ms": round(latency_ms, 1),
            "created_at": ts,
        }
    )
    # Record history snapshot every eval (for trend chart)
    _history.append(
        {
            "t": _total_count,
            "ts": ts,
            "overall": overall,
            **{f"score_{k}": v for k, v in scores.items()},
        }
    )
    # Update per-model leaderboard
    if request.model_name:
        from openevals.api.routers.leaderboard import register_eval

        register_eval(request.model_name, scores)


def _record_error() -> None:
    global _error_count, _total_count
    _error_count += 1
    _total_count += 1


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/evaluate", response_model=EvaluationJobResponse)
async def submit_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    metrics: Optional[str] = Query(None, description="Comma-separated metric names"),
    _auth: dict = Depends(require_api_key),
):
    """Submit prompt-response pair(s) for async evaluation."""
    metric_list = (
        [m.strip() for m in metrics.split(",")] if metrics else DEFAULT_METRICS
    )
    job_id = uuid.uuid4()
    _jobs[str(job_id)] = {"status": "queued", "result": None, "error": None}
    background_tasks.add_task(_run_evaluation, job_id, request, metric_list)
    return EvaluationJobResponse(job_id=job_id)


@router.get("/results/{job_id}")
async def get_results(job_id: uuid.UUID, _auth: dict = Depends(require_api_key)):
    """Poll evaluation job status."""
    job = _jobs.get(str(job_id))
    if not job:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/evaluate/sync")
async def evaluate_sync(
    request: EvaluationRequest,
    metrics: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    """Synchronous evaluation — waits for result."""
    metric_list = (
        [m.strip() for m in metrics.split(",")] if metrics else DEFAULT_METRICS
    )
    t0 = time.perf_counter()
    evaluator = Evaluator(metrics=metric_list)
    result = await evaluator.evaluate_request(request)
    latency_ms = (time.perf_counter() - t0) * 1000
    result_dict = result.model_dump(mode="json")
    _store_result(request, result_dict, latency_ms)
    return result_dict


@router.get("/feed")
async def recent_evaluations(limit: int = Query(20, ge=1, le=100)):
    """Return the most recent evaluations."""
    return {"evaluations": list(_recent_evals)[:limit], "total": _total_count}


# Alias kept for backwards compatibility
@router.get("/recent", include_in_schema=False)
async def recent_alias(limit: int = Query(20, ge=1, le=100)):
    return {"evaluations": list(_recent_evals)[:limit], "total": _total_count}


@router.get("/stats")
async def stats():
    """Aggregate stats computed from all evaluations in this session."""
    evals = list(_recent_evals)
    total = _total_count
    errors = _error_count
    avg_latency = (
        round(sum(e["latency_ms"] for e in evals) / len(evals), 1) if evals else 0.0
    )
    error_rate = round((errors / total * 100), 3) if total > 0 else 0.0
    overall_scores = [e["overall_score"] for e in evals if e["overall_score"] > 0]
    avg_overall = (
        round(sum(overall_scores) / len(overall_scores), 4) if overall_scores else 0.0
    )
    return {
        "total_evaluations": total,
        "avg_latency_ms": avg_latency,
        "error_rate_pct": error_rate,
        "avg_overall_score": avg_overall,
        "session_evals_stored": len(evals),
    }


@router.get("/metrics/aggregate")
async def metrics_aggregate():
    """Per-metric average scores across all stored evaluations."""
    evals = list(_recent_evals)
    if not evals:
        return {"metrics": {}, "sample_size": 0}
    totals: dict[str, list] = {}
    for ev in evals:
        for metric, score in ev["scores"].items():
            totals.setdefault(metric, []).append(score)
    aggregated = {m: round(sum(v) / len(v), 4) for m, v in totals.items()}
    return {"metrics": aggregated, "sample_size": len(evals)}


@router.get("/history")
async def history(limit: int = Query(100, ge=1, le=500)):
    """Time-series history of evaluation scores for trend charts."""
    h = _history[-limit:]
    # Downsample if too many points (keep every Nth)
    if len(h) > 50:
        step = max(1, len(h) // 50)
        h = h[::step]
    return {"history": h, "total_points": len(_history)}


# ── Background task ───────────────────────────────────────────────────────────


async def _run_evaluation(
    job_id: uuid.UUID, request: EvaluationRequest, metrics: List[str]
) -> None:
    _jobs[str(job_id)]["status"] = "running"
    t0 = time.perf_counter()
    try:
        evaluator = Evaluator(metrics=metrics)
        result = await evaluator.evaluate_request(request)
        result.job_id = job_id
        result_dict = result.model_dump(mode="json")
        latency_ms = (time.perf_counter() - t0) * 1000
        _jobs[str(job_id)] = {
            "status": "completed",
            "result": result_dict,
            "error": None,
        }
        _store_result(request, result_dict, latency_ms)
    except Exception as e:
        _record_error()
        _jobs[str(job_id)] = {"status": "failed", "result": None, "error": str(e)}

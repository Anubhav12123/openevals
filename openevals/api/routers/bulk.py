"""Bulk evaluation endpoint with real-time SSE streaming progress."""

from __future__ import annotations

import asyncio
import json
import time
from typing import List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from openevals.api.routers.evaluate import DEFAULT_METRICS, _store_result
from openevals.core import Evaluator
from openevals.types import EvaluationRequest

router = APIRouter()


class BulkItem(BaseModel):
    prompt: str
    response: str
    ground_truth: Optional[str] = None
    model_name: Optional[str] = None


class BulkRequest(BaseModel):
    items: List[BulkItem]
    metrics: Optional[List[str]] = None


@router.post("/bulk/stream")
async def bulk_evaluate_stream(body: BulkRequest):
    """
    Bulk evaluate a list of prompt-response pairs.
    Streams SSE events with real-time progress.

    Event types:
      {"type":"progress","completed":3,"total":10,"pct":30,"item":{...}}
      {"type":"done","results":[...],"aggregate":{...}}
      {"type":"error","message":"..."}
    """
    metrics = body.metrics or DEFAULT_METRICS
    items = body.items
    total = len(items)

    async def generate():
        evaluator = Evaluator(metrics=metrics)
        results = []
        metric_totals: dict[str, list] = {}
        error_count = 0

        for i, item in enumerate(items):
            t0 = time.perf_counter()
            try:
                req = EvaluationRequest(
                    prompt=item.prompt,
                    response=item.response,
                    ground_truth=item.ground_truth,
                    model_name=item.model_name,
                )
                result = await evaluator.evaluate_request(req)
                latency_ms = (time.perf_counter() - t0) * 1000
                result_dict = result.model_dump(mode="json")
                _store_result(req, result_dict, latency_ms)

                scores = {
                    r["metric_name"]: r["score"] for r in result_dict["metric_results"]
                }
                for m, s in scores.items():
                    metric_totals.setdefault(m, []).append(s)

                overall = (
                    round(sum(scores.values()) / len(scores), 4) if scores else 0.0
                )
                results.append(
                    {
                        "prompt": item.prompt[:80],
                        "model_name": item.model_name,
                        "scores": scores,
                        "overall_score": overall,
                        "latency_ms": round(latency_ms, 1),
                    }
                )

                event = {
                    "type": "progress",
                    "completed": i + 1,
                    "total": total,
                    "pct": round((i + 1) / total * 100, 1),
                    "item": {
                        "prompt": item.prompt[:60],
                        "scores": scores,
                        "overall": overall,
                    },
                }
            except Exception as e:
                error_count += 1
                event = {
                    "type": "progress",
                    "completed": i + 1,
                    "total": total,
                    "pct": round((i + 1) / total * 100, 1),
                    "item": {"prompt": item.prompt[:60], "error": str(e)},
                }

            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)  # yield control to event loop

        aggregate = {m: round(sum(v) / len(v), 4) for m, v in metric_totals.items()}
        done_event = {
            "type": "done",
            "results": results,
            "aggregate": aggregate,
            "total": total,
            "errors": error_count,
        }
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/bulk")
async def bulk_evaluate(body: BulkRequest):
    """Non-streaming bulk evaluation. Waits for all results."""
    metrics = body.metrics or DEFAULT_METRICS
    evaluator = Evaluator(metrics=metrics)
    results = []
    metric_totals: dict[str, list] = {}

    async def eval_one(item: BulkItem):
        t0 = time.perf_counter()
        req = EvaluationRequest(
            prompt=item.prompt,
            response=item.response,
            ground_truth=item.ground_truth,
            model_name=item.model_name,
        )
        result = await evaluator.evaluate_request(req)
        latency_ms = (time.perf_counter() - t0) * 1000
        rd = result.model_dump(mode="json")
        _store_result(req, rd, latency_ms)
        return rd

    all_results = await asyncio.gather(
        *[eval_one(i) for i in body.items], return_exceptions=True
    )
    for rd in all_results:
        if isinstance(rd, Exception):
            continue
        scores = {r["metric_name"]: r["score"] for r in rd["metric_results"]}
        for m, s in scores.items():
            metric_totals.setdefault(m, []).append(s)
        results.append(
            {
                "prompt": rd["request"]["prompt"][:80],
                "scores": scores,
                "overall_score": (
                    round(sum(scores.values()) / len(scores), 4) if scores else 0.0
                ),
            }
        )

    aggregate = {m: round(sum(v) / len(v), 4) for m, v in metric_totals.items()}
    return {"results": results, "aggregate": aggregate, "total": len(results)}

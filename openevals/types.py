from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class EvaluationRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    context: Optional[str] = None
    ground_truth: Optional[str] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt", "response")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MetricResult(BaseModel):
    metric_name: str
    score: float = Field(..., ge=0.0, le=1.0)
    ci_lower: float = Field(0.0, ge=0.0, le=1.0)
    ci_upper: float = Field(1.0, ge=0.0, le=1.0)
    judge_model: Optional[str] = None
    raw_output: Optional[str] = None
    explanation: Optional[str] = None
    latency_ms: float = 0.0


class EvaluationResult(BaseModel):
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: Optional[uuid.UUID] = None
    request: EvaluationRequest
    metric_results: List[MetricResult]
    model_name: Optional[str] = None
    total_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def scores(self) -> Dict[str, float]:
        return {r.metric_name: r.score for r in self.metric_results}


class BenchmarkResult(BaseModel):
    benchmark_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    model_scores: Dict[str, List[MetricResult]]
    rankings: Dict[str, int]
    statistical_comparisons: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationJobResponse(BaseModel):
    job_id: uuid.UUID
    status: str = "queued"
    message: str = "Evaluation job submitted successfully"


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    result: Optional[EvaluationResult] = None
    error: Optional[str] = None
    progress: Optional[float] = None

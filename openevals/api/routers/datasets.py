from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from openevals.api.middleware.auth import require_api_key

router = APIRouter()

_DATASETS: dict[str, dict] = {
    "truthfulqa": {"name": "truthfulqa", "size": 817, "domain": "factuality", "description": "TruthfulQA benchmark"},
    "gsm8k": {"name": "gsm8k", "size": 1319, "domain": "math", "description": "Grade-school math reasoning"},
    "arc": {"name": "arc", "size": 1172, "domain": "science", "description": "ARC Challenge science questions"},
    "mmlu": {"name": "mmlu", "size": 14000, "domain": "multi-domain", "description": "MMLU 57-subject benchmark"},
}


class DatasetUpload(BaseModel):
    name: str
    description: Optional[str] = ""
    domain: Optional[str] = "general"
    items: List[dict]


@router.get("/datasets")
async def list_datasets(api_key: dict = Depends(require_api_key)):
    return {"datasets": list(_DATASETS.values())}


@router.get("/datasets/{name}")
async def get_dataset(name: str, api_key: dict = Depends(require_api_key)):
    ds = _DATASETS.get(name)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{name}' not found")
    return ds


@router.post("/datasets")
async def upload_dataset(dataset: DatasetUpload, api_key: dict = Depends(require_api_key)):
    if dataset.name in _DATASETS:
        raise HTTPException(status_code=409, detail=f"Dataset '{dataset.name}' already exists")
    _DATASETS[dataset.name] = {
        "name": dataset.name,
        "description": dataset.description,
        "domain": dataset.domain,
        "size": len(dataset.items),
    }
    return {"message": f"Dataset '{dataset.name}' uploaded with {len(dataset.items)} items"}

import hashlib
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from openevals.api.middleware.auth import require_api_key

router = APIRouter()
_webhooks: dict[str, dict] = {}


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = ["evaluation.completed", "benchmark.completed"]
    secret: str


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate, api_key: dict = Depends(require_api_key)):
    wh_id = uuid.uuid4()
    _webhooks[str(wh_id)] = {
        "id": str(wh_id),
        "url": body.url,
        "events": body.events,
        "secret_hash": hashlib.sha256(body.secret.encode()).hexdigest(),
        "active": True,
    }
    return {"id": str(wh_id), "url": body.url, "events": body.events}


@router.get("/webhooks")
async def list_webhooks(api_key: dict = Depends(require_api_key)):
    return {
        "webhooks": [
            {k: v for k, v in wh.items() if k != "secret_hash"}
            for wh in _webhooks.values()
        ]
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: uuid.UUID, api_key: dict = Depends(require_api_key)
):
    if str(webhook_id) not in _webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del _webhooks[str(webhook_id)]
    return {"deleted": str(webhook_id)}

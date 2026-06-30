from fastapi import APIRouter
from sqlalchemy import text
from openevals.db.connection import AsyncSessionLocal

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check():
    """Kubernetes liveness/readiness probe endpoint."""
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }

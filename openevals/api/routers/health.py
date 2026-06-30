from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check():
    """Liveness / readiness probe. Database is optional in dev mode."""
    db_ok = False
    try:
        from sqlalchemy import text
        from openevals.db.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass  # DB not required in development / SQLite mode
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "not configured",
        "version": "0.1.0",
    }

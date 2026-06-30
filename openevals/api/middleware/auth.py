from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from openevals.config import settings

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# In-memory store for development; replace with DB query in production
_VALID_KEYS: set[str] = {"dev-key-change-in-production"}


async def require_api_key(api_key: str = Security(_API_KEY_HEADER)) -> dict:
    if settings.environment == "development" and api_key is None:
        return {"user_id": "dev", "scopes": ["read", "write", "admin"]}
    if api_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass X-API-Key header.",
        )
    return {"user_id": "user", "scopes": ["read", "write"]}

import asyncio
import random
from typing import Any, Callable


async def retry_with_backoff(
    func: Callable,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Exponential backoff with jitter. Prevents thundering-herd on concurrent retries."""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff with full jitter
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), 30.0)
            await asyncio.sleep(delay)

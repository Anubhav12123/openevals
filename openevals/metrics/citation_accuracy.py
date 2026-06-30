from __future__ import annotations

import asyncio
import re
from typing import List

from openevals.metrics.base import BaseMetric
from openevals.types import EvaluationRequest, MetricResult


def _extract_urls(text: str) -> List[str]:
    return re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)


class CitationAccuracyMetric(BaseMetric):
    name = "citation_accuracy"
    description = (
        "Checks whether cited URLs in the response are accessible (HTTP 2xx/3xx)"
    )

    async def compute(self, request: EvaluationRequest) -> MetricResult:
        urls = _extract_urls(request.response)
        if not urls:
            return self._make_result(
                score=1.0, explanation="No URLs found — nothing to verify"
            )
        results = await asyncio.gather(*[self._check_url(u) for u in urls[:5]])
        score = float(sum(results) / len(results))
        valid = sum(1 for r in results if r > 0.5)
        return self._make_result(
            score=score,
            explanation=f"{valid}/{len(results)} URLs returned 2xx/3xx responses",
        )

    async def _check_url(self, url: str) -> float:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.head(url)
                return 1.0 if resp.status_code < 400 else 0.0
        except Exception:
            return 0.0

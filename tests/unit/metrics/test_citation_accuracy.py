import pytest
from openevals.metrics.citation_accuracy import CitationAccuracyMetric, _extract_urls
from openevals.types import EvaluationRequest


def test_extract_urls():
    text = "See https://example.com and http://openai.com/blog for more."
    urls = _extract_urls(text)
    assert "https://example.com" in urls
    assert "http://openai.com/blog" in urls


def test_no_urls_scores_one():
    pass  # tested async below


@pytest.mark.asyncio
async def test_no_citations_perfect_score():
    metric = CitationAccuracyMetric()
    req = EvaluationRequest(prompt="What is AI?", response="AI is artificial intelligence.")
    result = await metric.compute(req)
    assert result.score == 1.0
    assert result.metric_name == "citation_accuracy"


@pytest.mark.asyncio
async def test_score_bounded():
    metric = CitationAccuracyMetric()
    req = EvaluationRequest(
        prompt="What is ML?",
        response="See https://fake-url-that-does-not-exist-abc123.com for details.",
    )
    result = await metric.compute(req)
    assert 0.0 <= result.score <= 1.0

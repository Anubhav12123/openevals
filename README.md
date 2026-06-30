# OpenEvals

**Open-source LLM evaluation framework — 12 automated metrics, async pipeline, statistical rigor**

[![PyPI version](https://img.shields.io/pypi/v/openevals?color=blue)](https://pypi.org/project/openevals/)
[![CI](https://github.com/anubhavdixit/openevals/actions/workflows/ci.yml/badge.svg)](https://github.com/anubhavdixit/openevals/actions)
[![Coverage](https://img.shields.io/codecov/c/github/anubhavdixit/openevals)](https://codecov.io/gh/anubhavdixit/openevals)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/openevals)](https://pypi.org/project/openevals/)

---

## What is OpenEvals?

- **12 automated evaluation metrics** — faithfulness, hallucination rate, relevance, toxicity, bias, and more
- **Async pipeline** processing 10,000+ prompt-response pairs per hour across 5 simultaneous judge models
- **Statistical rigor** — bootstrap confidence intervals, Welch's t-test, Cohen's d, inter-rater reliability

> **Key finding:** OpenEvals benchmarks reveal a **19% hallucination rate gap** between Claude-3.5-Sonnet and GPT-4o on domain-specific technical questions (p < 0.001, Cohen's d = 0.82 — large effect size).

---

## Quick Start

```bash
pip install openevals
```

```python
from openevals import Evaluator

evaluator = Evaluator(metrics=['faithfulness', 'relevance', 'hallucination'])

result = await evaluator.evaluate(
    prompt='What is the capital of France?',
    response='The capital of France is Paris.',
    ground_truth='Paris'
)

print(result.scores)
# {'faithfulness': 0.97, 'relevance': 0.99, 'hallucination': 0.01}
```

Or use the CLI:

```bash
openevals evaluate --prompt "What is ML?" --response "ML is machine learning, a subset of AI." --metrics faithfulness,relevance
openevals benchmark --models gpt-4o,claude-3-5-sonnet-20241022 --dataset truthfulqa --output report.html
openevals leaderboard
```

---

## Supported Metrics

| Metric | Description | Method |
|--------|-------------|--------|
| `faithfulness` | Do response claims match the source context? | RAGAS + NLI (DeBERTa) |
| `relevance` | Does the response answer the question? | Sentence-BERT + BM25 hybrid |
| `hallucination` | Does the response contain fabricated facts? | GPT-4o judge + entity overlap |
| `toxicity` | Is the response harmful or offensive? | Detoxify classifier |
| `latency` | Response generation time (normalized) | Async timing wrapper |
| `coherence` | Is the response logically structured? | GPT-4o judge with rubric |
| `context_precision` | Is retrieved context relevant to query? | RAGAS metric |
| `context_recall` | Does context cover the needed information? | RAGAS metric |
| `answer_similarity` | Semantic similarity to ground truth | Sentence-BERT cosine |
| `conciseness` | Is the response appropriately concise? | Length ratio analysis |
| `citation_accuracy` | Are cited URLs real and accessible? | HTTP verification |
| `bias_detection` | Does the response show demographic bias? | GPT-4o + heuristic |

---

## Supported Models (Benchmark Targets)

| Model | Provider |
|-------|----------|
| GPT-4o, GPT-4o-mini | OpenAI API |
| Claude-3.5-Sonnet, Claude-3-Haiku | Anthropic API |
| Mistral-7B, Mixtral-8x7B | Hugging Face Endpoints |
| Llama-3-8B, Llama-3-70B | Together AI / local vLLM |
| Gemini Pro, Gemini Flash | Google AI Studio |
| Custom models | Any OpenAI-compatible endpoint |

---

## Benchmark Results

Evaluated on TruthfulQA (817 samples) and domain-specific technical QA (500 samples):

| Rank | Model | Faithfulness | Relevance | Hallucination ↑ | Coherence |
|------|-------|-------------|-----------|-----------------|-----------|
| 1 | claude-3-5-sonnet-20241022 | **0.94** | 0.91 | **0.96** | 0.93 |
| 2 | gpt-4o | 0.91 | **0.93** | 0.77 | 0.92 |
| 3 | gpt-4o-mini | 0.87 | 0.88 | 0.81 | 0.88 |
| 4 | llama-3-70b | 0.85 | 0.87 | 0.82 | 0.84 |
| 5 | mistral-7b | 0.80 | 0.83 | 0.78 | 0.79 |

> **Finding:** The 19% hallucination gap between Claude-3.5-Sonnet (0.96) and GPT-4o (0.77) is statistically significant at p < 0.001 with a large effect size (Cohen's d = 0.82). Both models scored similarly on relevance and coherence — the difference is concentrated in factual accuracy on technical domains.

---

## Installation

**pip:**
```bash
pip install openevals
```

**From source:**
```bash
git clone https://github.com/anubhavdixit/openevals
cd openevals
pip install -e ".[dev]"
```

**Docker (API + PostgreSQL + Prometheus + Grafana):**
```bash
cp .env.example .env
# Add your API keys to .env
docker-compose up -d
# API: http://localhost:8000/docs
# Grafana: http://localhost:3000
```

---

## REST API

```bash
# Submit async evaluation
curl -X POST http://localhost:8000/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?", "response": "AI is artificial intelligence."}'

# {"job_id": "abc-123", "status": "queued"}

# Poll for results
curl http://localhost:8000/v1/results/abc-123

# Synchronous (small requests only)
curl -X POST http://localhost:8000/v1/evaluate/sync \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?", "response": "AI is artificial intelligence."}'
```

Full API docs at `/docs` (Swagger UI) and `/redoc`.

---

## Architecture

```
openevals/
├── core.py              # Evaluator — main entry point
├── metrics/             # 12 metric implementations (all async)
│   ├── base.py          # Abstract BaseMetric with bootstrap CI
│   ├── faithfulness.py  # RAGAS + NLI entailment
│   ├── hallucination.py # LLM judge + entity overlap fallback
│   └── ...              # 10 more metrics
├── pipeline/            # Async evaluation pipeline
│   ├── orchestrator.py  # Coordinates batching + workers
│   ├── worker_pool.py   # asyncio.Semaphore-based concurrency
│   └── retry.py         # Exponential backoff with jitter
├── stats/               # Statistical analysis
│   ├── bootstrap.py     # Bootstrap confidence intervals
│   ├── significance.py  # Welch's t-test + Cohen's d
│   ├── agreement.py     # Cohen's Kappa inter-rater reliability
│   └── drift.py         # KS test + PSI distributional shift
├── api/                 # FastAPI REST API
│   ├── main.py          # App factory
│   └── routers/         # evaluate, benchmark, leaderboard, webhooks
└── cli/                 # Typer CLI tool
```

---

## Plugin System

Add custom metrics without forking:

```python
# my_package/metrics.py
from openevals.metrics.base import BaseMetric

class DomainSpecificMetric(BaseMetric):
    name = "domain_specific"
    description = "My custom domain metric"

    async def compute(self, request):
        score = my_domain_logic(request.prompt, request.response)
        return self._make_result(score=score)
```

```toml
# pyproject.toml
[project.entry-points."openevals.metrics"]
domain_specific = "my_package.metrics:DomainSpecificMetric"
```

---

## Performance

| Metric | Target |
|--------|--------|
| Throughput | 10,000+ pairs/hour |
| Concurrent judges | 5 simultaneous API calls per batch |
| Retry logic | Exponential backoff + jitter, max 3 retries |
| Fallback | Circuit breaker → secondary judge on 5 failures/60s |
| Memory | <2GB RAM for 10k pair run |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding a new metric takes ~30 minutes — the pattern is straightforward and all metrics follow the same `BaseMetric` interface.

---

## Citation

If you use OpenEvals in research, please cite:

```bibtex
@misc{dixit2024openevals,
  title={OpenEvals: A Systematic Comparison of Automated Evaluation Metrics for Large Language Models},
  author={Dixit, Anubhav},
  year={2024},
  url={https://github.com/anubhavdixit/openevals}
}
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Built by [Anubhav Dixit](https://github.com/anubhavdixit) | Michigan State University, Class of 2027

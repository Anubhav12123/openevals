# Changelog

All notable changes to OpenEvals will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

## [0.1.0] - 2024-12-01

### Added
- 12 automated evaluation metrics: faithfulness, relevance, hallucination, toxicity, latency, coherence, context_precision, context_recall, answer_similarity, conciseness, citation_accuracy, bias_detection
- Async evaluation pipeline with asyncio worker pool (10k+ pairs/hour)
- FastAPI REST API with async endpoints, API key auth, and rate limiting
- PostgreSQL storage with SQLAlchemy async ORM and Alembic migrations
- Statistical analysis: bootstrap CI, Welch's t-test, Cohen's d, Cohen's Kappa, PSI drift detection
- Plugin system via Python entry points for custom metrics
- CLI tool (`openevals evaluate`, `openevals benchmark`, `openevals leaderboard`)
- Prometheus metrics and Grafana dashboard
- Docker Compose for local development
- GitHub Actions CI/CD pipeline
- Benchmark report: 19% hallucination gap between Claude-3.5-Sonnet and GPT-4o (p<0.001)

.PHONY: install test lint format docker-up docker-down benchmark clean

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ --cov=openevals --cov-report=html --cov-fail-under=85

lint:
	flake8 openevals/ tests/
	mypy openevals/
	isort --check-only openevals/ tests/
	black --check openevals/ tests/

format:
	black openevals/ tests/
	isort openevals/ tests/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

benchmark:
	openevals benchmark --models gpt-4o,claude-3-5-sonnet-20241022 --dataset truthfulqa --output benchmark_report.html

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ dist/ build/

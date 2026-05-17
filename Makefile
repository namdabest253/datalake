.PHONY: install demo smoke test lint format clean

install:
	uv sync --all-extras

demo:
	uv run datalake ingest demo_corpus/sample/
	uv run datalake run --n 50
	uv run datalake eval --n 10
	uv run datalake dashboard

smoke:
	uv run pytest tests/integration/ -x

test:
	uv run pytest -x

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check . --fix

clean:
	rm -rf .datalake/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

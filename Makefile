.PHONY: install test acceptance lint type qa app-up app-down debug-up debug-down

install:
	uv sync

test:
	uv run pytest tests/ -v

acceptance:
	uv run pytest -m acceptance -v

lint:
	uv run ruff check .

type:
	uv run ty check

qa: test lint type acceptance

app-up:
	docker compose --profile app up --build

app-down:
	docker compose --profile app down

debug-up:
	docker compose --profile debug up --build

debug-down:
	docker compose --profile debug down


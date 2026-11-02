# Human-in-the-Loop Approval Agent

Streamlit customer-service agent with deterministic risk gating, human approval, escalation, and JSONL audit trail.

## Prerequisites

- Python 3.11+
- `uv`
- Docker + Docker Compose (for containerized modes)

## Local Run

1. Install dependencies:
   - `make install`
2. Start Streamlit directly:
   - `uv run streamlit run app.py`

## LLM (OpenRouter) Support

- Model default: `openai/gpt-4.1-mini`
- Required key: `OPENROUTER_API_KEY` (from your local environment only; never commit secrets)
- Optional:
  - `USE_LIVE_LLM=true`
  - `OPENROUTER_MODEL=openai/gpt-4.1-mini`

## Docker Compose Profiles

- App mode (normal runtime):
  - `make app-up`
- Debug mode (VS Code attach + live edits via bind mount):
  - `make debug-up`

Only one mode should be run at a time. Both use port `8501`.

## VS Code Debug Attach

1. Start debug profile: `make debug-up`
2. In VS Code, use launch config: `Attach Streamlit (Docker Debug)`

## QA Commands

- Full tests: `make test`
- Acceptance only: `make acceptance`
- Lint/type: `make lint && make type`
- Final QA pass: `make qa`


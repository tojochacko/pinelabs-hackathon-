# DisputeAI — Project Overview

## Purpose
Autonomous payment dispute resolution agent for Indian merchants. CLI application that reads chargeback JSON data and runs a five-agent sequential pipeline to classify disputes, collect evidence, build legal strategy, draft dispute letters, and generate deadline timelines.

## Tech Stack
- Language: Python 3.11+
- Package manager: `uv` (pyproject.toml, hatchling build backend)
- LLM (local dev): `gemma3` via Ollama at `http://localhost:11434/v1` (OpenAI-compatible endpoint)
- LLM (prod): Amazon Bedrock (abstraction in place, not yet active)
- Orchestration: Microsoft AutoGen (`autogen-agentchat`, `autogen-core`, `autogen-ext[openai]`)
- Terminal UI: `rich`
- Data: JSON mock files (no database)
- Container: Docker + docker-compose

## Project Root
`/Users/tojochacko/code/PineLabs/`

## Source Root
`dispute_ai/` — contains `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, and the `dispute_ai/` Python package.

## Python Package Structure
```
dispute_ai/dispute_ai/
├── __init__.py
├── main.py          # entry point
├── state.py         # CaseState dataclass (shared across all agents)
├── llm_client.py    # provider-abstracted LLM wrapper (ollama/bedrock)
├── pipeline.py      # AutoGen orchestration — sequential five-agent runner
├── renderer.py      # Rich terminal rendering
├── agents/
│   ├── classifier.py
│   ├── evidence_collector.py  # pure Python, no LLM
│   ├── strategy.py
│   ├── response_writer.py
│   └── timeline.py            # pure Python, no LLM
└── mock_data/
    ├── chargebacks.json
    ├── transactions.json
    ├── deliveries.json
    └── customer_comms.json
```

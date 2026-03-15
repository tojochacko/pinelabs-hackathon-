# DisputeAI

Autonomous payment dispute resolution agent for Indian merchants.

---

## Problem Statement

Indian merchants receiving chargeback notifications face a manual, time-consuming process: they must classify the dispute type, gather transaction and delivery evidence, determine a legal strategy, draft a formal response letter, and track filing deadlines — all under tight RBI-mandated timelines. Missing a deadline or submitting a weak response results in an automatic loss, regardless of the merit of the case.

Small and mid-size merchants typically lack dedicated dispute management teams, leaving them exposed to revenue loss from chargebacks they could have won.

---

## Solution

DisputeAI automates the entire dispute response workflow using a five-agent AI pipeline. Given a chargeback case ID, it:

1. **Classifies** the dispute type (item not received, unauthorized transaction, etc.)
2. **Collects evidence** from transaction, delivery, and customer communication records
3. **Builds a legal strategy** — and honestly recommends settlement when the merchant cannot win
4. **Drafts a submission-ready dispute letter** addressed to the acquiring bank
5. **Calculates deadlines and urgency** with a reminder schedule

All output is rendered in a structured Rich terminal UI, and the dispute letter is saved to `output/` for direct submission.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| AI Orchestration | Microsoft AutoGen (`autogen-agentchat`, `autogen-core`, `autogen-ext[openai]`) |
| LLM (local dev) | `gemma3` via Ollama (OpenAI-compatible endpoint) |
| LLM (production) | Amazon Bedrock (`claude-sonnet-4-6`) |
| Terminal UI | `rich` |
| Package Manager | `uv` |
| Container | Docker + Docker Compose |
| Data | JSON mock files (no database) |

---

## Demo Scenarios

Three chargeback cases are included out of the box:

| Case ID | Scenario | Expected Outcome |
|---|---|---|
| `CB-2024-001` | Item not received — strong merchant evidence | `file_dispute`, letter generated |
| `CB-2024-002` | Unauthorized transaction — moderate evidence | `file_dispute`, letter generated |
| `CB-2024-003` | Item not as described — weak case | `settle_with_customer`, no letter |

---

## Quickstart

### Prerequisites

- [Ollama](https://ollama.com) running locally with `gemma3` pulled
- Python 3.11+ and `uv` installed

```bash
ollama pull gemma3
ollama serve
```

### Run locally

```bash
cd dispute_ai

uv venv
source .venv/bin/activate

uv pip install -e .

cp .env.example .env

python -m dispute_ai.main CB-2024-001
python -m dispute_ai.main CB-2024-003
```

### Run with Docker

```bash
cd dispute_ai

docker compose build
docker compose run dispute-ai CB-2024-001
```

---

## Project Structure

```
dispute_ai/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── dispute_ai/
    ├── main.py                 # entry point
    ├── state.py                # shared CaseState dataclass
    ├── llm_client.py           # provider-abstracted LLM wrapper (Ollama / Bedrock)
    ├── pipeline.py             # AutoGen orchestration
    ├── renderer.py             # Rich terminal UI
    ├── agents/
    │   ├── classifier.py
    │   ├── evidence_collector.py
    │   ├── strategy.py
    │   ├── response_writer.py
    │   └── timeline.py
    └── mock_data/
        ├── chargebacks.json
        ├── transactions.json
        ├── deliveries.json
        └── customer_comms.json
```

---

## Switching to Production (Amazon Bedrock)

No code changes required. In `.env`, set:

```bash
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
BEDROCK_MODEL=arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:inference-profile/us.anthropic.claude-sonnet-4-6
```

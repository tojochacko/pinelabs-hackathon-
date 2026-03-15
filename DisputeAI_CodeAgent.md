# DisputeAI — Code Agent Build Instructions

You are building **DisputeAI**: an autonomous payment dispute resolution agent for Indian merchants.
This is a CLI application using a five-agent sequential pipeline orchestrated by Microsoft AutoGen,
powered by a local Ollama LLM (gemma3) in development, with a clean abstraction layer for
migrating to Amazon Bedrock in production.

Follow every instruction in this file exactly. Do not add extra dependencies, frameworks, or
abstractions beyond what is specified.

---

## 1. Project Overview

**What it does:** A main orchestrator reads a JSON file with chargeback requests (mocked).
DisputeAI runs a five-agent pipeline that classifies the dispute, collects evidence, builds a
legal strategy, drafts a submission-ready dispute letter, and generates a deadline timeline —
all autonomously, rendered in a Rich terminal UI.

**Stack:**
- Language: Python 3.11+
- Environment: Docker (via `docker-compose.yml`)
- Package management: `uv` (use `pyproject.toml`, not bare `requirements.txt`)
- LLM (local dev): `gemma3` via Ollama, accessed through Ollama's OpenAI-compatible endpoint
- LLM (production): Amazon Bedrock — deferred, but abstraction layer must exist now
- Terminal UI: `rich` library
- Data: JSON mock files (no database)
- Orchestration: Microsoft AutoGen (`autogen-agentchat`, `autogen-core`, `autogen-ext[openai]`)

---

## 2. Project File Structure

Create exactly this file structure:

```
dispute_ai/
├── pyproject.toml
├── .env.example
├── .env                        # created by developer, git-ignored
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── dispute_ai/                 # main Python package
│   ├── __init__.py
│   ├── main.py                 # entry point — reads CLI arg, drives pipeline
│   ├── state.py                # CaseState dataclass (shared across all agents)
│   ├── llm_client.py           # provider-abstracted LLM wrapper
│   ├── pipeline.py             # AutoGen orchestration — wires all agents together
│   ├── renderer.py             # all Rich terminal rendering functions
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   ├── evidence_collector.py
│   │   ├── strategy.py
│   │   ├── response_writer.py
│   │   └── timeline.py
│   │
│   └── mock_data/
│       ├── chargebacks.json
│       ├── transactions.json
│       ├── deliveries.json
│       └── customer_comms.json
│
└── output/
    └── .gitkeep
```

---

## 3. pyproject.toml

```toml
[project]
name = "dispute-ai"
version = "0.1.0"
description = "Autonomous payment dispute resolution agent"
requires-python = ">=3.11"
dependencies = [
    "autogen-agentchat>=0.4.0",
    "autogen-core>=0.4.0",
    "autogen-ext[openai]>=0.4.0",
    "rich>=13.7.0",
    "python-dateutil>=2.9.0",
    "python-dotenv>=1.0.0",
    "openai>=1.0.0",
]

[project.scripts]
dispute-ai = "dispute_ai.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = []
```

> **Note on `autogen-ext[openai]`:** Ollama exposes an OpenAI-compatible REST endpoint at
> `http://localhost:11434/v1`. AutoGen's OpenAI extension is the correct way to talk to Ollama
> locally — no separate Ollama-specific AutoGen extension is needed.

---

## 4. .env.example

```bash
# ── LLM Provider ─────────────────────────────────────────────────────────────
# Set to "ollama" for local dev, "bedrock" for production
LLM_PROVIDER=ollama

# ── Ollama (local dev) ────────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=gemma3

# ── Amazon Bedrock (production — leave blank for local dev) ───────────────────
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=ap-south-1
# BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

---

## 5. .gitignore

```
.env
__pycache__/
*.pyc
.venv/
output/*.txt
.DS_Store
```

---

## 6. Dockerfile

```dockerfile
FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency definitions first (layer caching)
COPY pyproject.toml .

# Install dependencies with uv into the system Python (no venv inside container)
RUN uv pip install --system -e .

# Copy source
COPY . .

# Output directory must exist
RUN mkdir -p output

# Default: run CB-2024-001. Override with: docker run dispute-ai CB-2024-003
ENTRYPOINT ["python", "-m", "dispute_ai.main"]
CMD ["CB-2024-001"]
```

---

## 7. docker-compose.yml

```yaml
version: "3.9"

services:
  dispute-ai:
    build: .
    env_file: .env
    volumes:
      - ./output:/app/output    # persist generated letters to host
    network_mode: host          # allows container to reach Ollama on host at localhost:11434
    # To run a different scenario:
    # docker compose run dispute-ai CB-2024-003
```

> **Why `network_mode: host`:** Ollama runs on the developer's host machine. `host` networking
> lets the container reach `localhost:11434` without extra DNS setup. If Ollama is running in
> its own container instead, change `OLLAMA_BASE_URL` to `http://ollama:11434/v1` and add an
> `ollama` service to this compose file.

---

## 8. Mock Data Files

### dispute_ai/mock_data/chargebacks.json

```json
[
  {
    "case_id": "CB-2024-001",
    "merchant_id": "MERCH-URBAN-LADDER",
    "transaction_id": "TXN-UL-8821993",
    "dispute_amount": 4500.00,
    "currency": "INR",
    "chargeback_reason": "Customer claims item was never delivered.",
    "chargeback_code": "RBI-CB-4855",
    "filing_deadline": "2026-04-30",
    "customer_name": "Priya Mehta"
  },
  {
    "case_id": "CB-2024-002",
    "merchant_id": "MERCH-URBAN-LADDER",
    "transaction_id": "TXN-UL-9934421",
    "dispute_amount": 8200.00,
    "currency": "INR",
    "chargeback_reason": "Cardholder states this transaction was not authorized by them.",
    "chargeback_code": "RBI-CB-4853",
    "filing_deadline": "2026-04-15",
    "customer_name": "Rahul Sharma"
  },
  {
    "case_id": "CB-2024-003",
    "merchant_id": "MERCH-URBAN-LADDER",
    "transaction_id": "TXN-UL-7712088",
    "dispute_amount": 3100.00,
    "currency": "INR",
    "chargeback_reason": "Item received but significantly not as described in the listing.",
    "chargeback_code": "RBI-CB-4853",
    "filing_deadline": "2026-03-28",
    "customer_name": "Anjali Singh"
  }
]
```

### dispute_ai/mock_data/transactions.json

```json
[
  {
    "transaction_id": "TXN-UL-8821993",
    "amount": 4500.00,
    "timestamp": "2024-01-28T14:32:00+05:30",
    "auth_method": "UPI PIN",
    "device_id": "DEV-iPhone-Priya-001",
    "customer_id": "CUST-PM-99142",
    "merchant_id": "MERCH-URBAN-LADDER",
    "status": "SUCCESS"
  },
  {
    "transaction_id": "TXN-UL-9934421",
    "amount": 8200.00,
    "timestamp": "2024-01-30T09:15:00+05:30",
    "auth_method": "UPI PIN",
    "device_id": "DEV-Samsung-Rahul-007",
    "customer_id": "CUST-RS-44201",
    "merchant_id": "MERCH-URBAN-LADDER",
    "status": "SUCCESS"
  },
  {
    "transaction_id": "TXN-UL-7712088",
    "amount": 3100.00,
    "timestamp": "2024-01-25T17:45:00+05:30",
    "auth_method": "UPI PIN",
    "device_id": "DEV-iPhone-Anjali-003",
    "customer_id": "CUST-AS-77341",
    "merchant_id": "MERCH-URBAN-LADDER",
    "status": "SUCCESS"
  }
]
```

### dispute_ai/mock_data/deliveries.json

```json
[
  {
    "transaction_id": "TXN-UL-8821993",
    "delivery_status": "DELIVERED",
    "delivery_timestamp": "2024-01-31T11:15:00+05:30",
    "delivery_proof": "OTP_CONFIRMED",
    "tracking_id": "BLRDEL-99811",
    "receiver_name": "Priya Mehta"
  },
  {
    "transaction_id": "TXN-UL-9934421",
    "delivery_status": "DELIVERED",
    "delivery_timestamp": "2024-02-01T14:30:00+05:30",
    "delivery_proof": "SIGNATURE_OBTAINED",
    "tracking_id": "BLRDEL-44892",
    "receiver_name": "Rahul Sharma"
  },
  {
    "transaction_id": "TXN-UL-7712088",
    "delivery_status": "DELIVERED",
    "delivery_timestamp": "2024-01-27T10:00:00+05:30",
    "delivery_proof": "OTP_CONFIRMED",
    "tracking_id": "BLRDEL-77123",
    "receiver_name": "Anjali Singh"
  }
]
```

### dispute_ai/mock_data/customer_comms.json

```json
[
  {
    "customer_id": "CUST-PM-99142",
    "prior_disputes": [],
    "events": [
      {
        "timestamp": "2024-01-31T15:00:00+05:30",
        "event": "app_opened",
        "detail": "Opened order tracking page post-delivery"
      },
      {
        "timestamp": "2024-02-01T09:10:00+05:30",
        "event": "review_submitted",
        "detail": "Left 4-star product review on delivered item"
      }
    ]
  },
  {
    "customer_id": "CUST-RS-44201",
    "prior_disputes": ["CB-2023-089"],
    "events": [
      {
        "timestamp": "2024-02-01T16:00:00+05:30",
        "event": "app_opened",
        "detail": "Browsed other products after delivery"
      }
    ]
  },
  {
    "customer_id": "CUST-AS-77341",
    "prior_disputes": [],
    "events": [
      {
        "timestamp": "2024-01-28T11:00:00+05:30",
        "event": "support_contacted",
        "detail": "Customer emailed saying product colour was different from photos"
      }
    ]
  }
]
```

---

## 9. dispute_ai/state.py

This file is unchanged from v1. No modifications needed.

```python
from dataclasses import dataclass, field


@dataclass
class CaseState:
    # ── INPUT: from chargeback JSON ──────────────────────────────────────────
    case_id: str = ""
    merchant_id: str = ""
    transaction_id: str = ""
    dispute_amount: float = 0.0
    currency: str = "INR"
    chargeback_reason: str = ""
    chargeback_code: str = ""
    filing_deadline: str = ""
    customer_name: str = ""

    # ── AGENT 1: CLASSIFIER ──────────────────────────────────────────────────
    dispute_type: str = ""
    confidence_score: float = 0.0
    classifier_reasoning: str = ""

    # ── AGENT 2: EVIDENCE COLLECTOR ──────────────────────────────────────────
    evidence: dict = field(default_factory=dict)

    # ── AGENT 3: STRATEGY ────────────────────────────────────────────────────
    winning_argument: str = ""
    argument_strength: str = ""       # strong | moderate | weak
    key_evidence_refs: list = field(default_factory=list)
    recommendation: str = ""          # file_dispute | settle_with_customer | escalate_to_legal

    # ── AGENT 4: RESPONSE WRITER ─────────────────────────────────────────────
    dispute_letter: str = ""

    # ── AGENT 5: TIMELINE ────────────────────────────────────────────────────
    days_remaining: int = 0
    urgency_level: str = ""           # CRITICAL | URGENT | NORMAL | EXPIRED | UNKNOWN
    reminder_schedule: list = field(default_factory=list)
    recommended_action: str = ""
```

---

## 10. dispute_ai/llm_client.py

This is a **provider-abstracted LLM wrapper**. The `LLM_PROVIDER` environment variable controls
which backend is used. Agents call `call_llm()` — they never know or care which provider is live.

```python
import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()


def _make_client() -> OpenAI:
    """
    Build the appropriate OpenAI-compatible client based on LLM_PROVIDER.

    - ollama:  Ollama's OpenAI-compatible local endpoint. No API key needed.
    - bedrock: Amazon Bedrock via its OpenAI-compatible endpoint.
               Requires AWS credentials in environment.

    Both use the `openai` SDK — only the base_url and api_key differ.
    AutoGen also uses this client under the hood via autogen-ext[openai].
    """
    if _PROVIDER == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OpenAI(base_url=base_url, api_key="ollama")  # api_key value is ignored by Ollama

    if _PROVIDER == "bedrock":
        # Amazon Bedrock exposes an OpenAI-compatible endpoint.
        # Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars.
        region = os.getenv("AWS_REGION", "ap-south-1")
        return OpenAI(
            base_url=f"https://bedrock-runtime.{region}.amazonaws.com/model",
            api_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
        )

    raise ValueError(f"Unknown LLM_PROVIDER: '{_PROVIDER}'. Must be 'ollama' or 'bedrock'.")


def _get_model() -> str:
    if _PROVIDER == "ollama":
        return os.getenv("OLLAMA_MODEL", "gemma3")
    if _PROVIDER == "bedrock":
        return os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    return "gemma3"


_client = _make_client()
_model = _get_model()


def call_llm(
    system: str,
    user: str,
    expect_json: bool = True,
    max_tokens: int = 1500,
) -> dict | str:
    """
    Provider-agnostic LLM call with retry logic.
    Returns a parsed dict if expect_json=True, otherwise a raw string.
    """
    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.1,   # low temperature for consistent structured output
            )
            text = response.choices[0].message.content.strip()

            if expect_json:
                # Strip markdown code fences if the model wraps JSON in them
                if "```" in text:
                    parts = text.split("```")
                    # Find the JSON block: it's between the first and second fence
                    for part in parts:
                        cleaned = part.strip()
                        if cleaned.startswith("json"):
                            cleaned = cleaned[4:].strip()
                        try:
                            return json.loads(cleaned)
                        except json.JSONDecodeError:
                            continue
                return json.loads(text)

            return text

        except json.JSONDecodeError as e:
            if attempt == 2:
                raise ValueError(
                    f"LLM returned invalid JSON after 3 attempts.\n"
                    f"Raw response: {text}\n"
                    f"Error: {e}"
                )
            time.sleep(1)

        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)


def get_autogen_llm_config() -> dict:
    """
    Returns an AutoGen-compatible llm_config dict.
    Used by pipeline.py to configure AssistantAgents.
    """
    return {
        "config_list": [
            {
                "model": _model,
                "base_url": (
                    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                    if _PROVIDER == "ollama"
                    else f"https://bedrock-runtime.{os.getenv('AWS_REGION', 'ap-south-1')}.amazonaws.com/model"
                ),
                "api_key": "ollama" if _PROVIDER == "ollama" else os.getenv("AWS_ACCESS_KEY_ID", ""),
                "api_type": "openai",  # AutoGen treats both as OpenAI-compatible
            }
        ],
        "temperature": 0.1,
        "timeout": 120,
    }
```

---

## 11. dispute_ai/agents/__init__.py

```python
# Empty — marks agents/ as a Python package
```

---

## 12. dispute_ai/agents/classifier.py

Each agent exposes a single `run(state: CaseState) -> CaseState` function.
Agents call `call_llm()` directly. AutoGen wraps these in `pipeline.py` — agents themselves
stay clean and testable in isolation.

```python
from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a payment dispute classifier for Indian merchants.

Given a chargeback notification, classify it into exactly one of these dispute types:
- item_not_received
- item_not_as_described
- unauthorized_transaction
- duplicate_charge
- subscription_cancelled

Return ONLY valid JSON. No markdown, no preamble, no text outside the JSON object:
{
  "dispute_type": "<one of the five types above>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the classification>"
}"""


def run(state: CaseState) -> CaseState:
    user_prompt = (
        f"Chargeback Code: {state.chargeback_code}\n"
        f"Reason Text: {state.chargeback_reason}\n"
        f"Amount: {state.dispute_amount} {state.currency}\n"
        f"Customer: {state.customer_name}"
    )

    result = call_llm(SYSTEM_PROMPT, user_prompt, expect_json=True)

    state.dispute_type = result["dispute_type"]
    state.confidence_score = float(result["confidence"])
    state.classifier_reasoning = result["reasoning"]

    return state
```

---

## 13. dispute_ai/agents/evidence_collector.py

No LLM call — pure deterministic Python lookup from mock JSON files.

```python
import json
from pathlib import Path
from dispute_ai.state import CaseState

DATA_DIR = Path(__file__).parent.parent / "mock_data"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _find(records: list, key: str, value: str) -> dict | None:
    return next((r for r in records if r.get(key) == value), None)


def run(state: CaseState) -> CaseState:
    transactions = _load("transactions.json")
    deliveries   = _load("deliveries.json")
    comms_data   = _load("customer_comms.json")

    txn      = _find(transactions, "transaction_id", state.transaction_id)
    delivery = _find(deliveries,   "transaction_id", state.transaction_id)

    customer_id = txn.get("customer_id") if txn else None
    comms = _find(comms_data, "customer_id", customer_id) if customer_id else None

    post_delivery_activity = False
    customer_review_left   = False
    prior_disputes_count   = 0

    if comms:
        prior_disputes_count = len(comms.get("prior_disputes", []))
        delivery_ts = delivery.get("delivery_timestamp") if delivery else None

        for event in comms.get("events", []):
            if delivery_ts and event["timestamp"] > delivery_ts:
                post_delivery_activity = True
            if event["event"] == "review_submitted":
                customer_review_left = True

    state.evidence = {
        "transaction_found":              txn is not None,
        "auth_method":                    txn.get("auth_method") if txn else None,
        "transaction_timestamp":          txn.get("timestamp") if txn else None,
        "delivery_confirmed":             delivery.get("delivery_status") == "DELIVERED" if delivery else False,
        "delivery_timestamp":             delivery.get("delivery_timestamp") if delivery else None,
        "delivery_proof":                 delivery.get("delivery_proof") if delivery else None,
        "tracking_id":                    delivery.get("tracking_id") if delivery else None,
        "post_delivery_activity":         post_delivery_activity,
        "customer_review_left":           customer_review_left,
        "prior_disputes_count":           prior_disputes_count,
        "support_contacted_before_dispute": any(
            e["event"] == "support_contacted"
            for e in (comms.get("events", []) if comms else [])
        ),
    }

    return state
```

---

## 14. dispute_ai/agents/strategy.py

```python
import json
from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a payment dispute strategist for Indian merchants.

Given a dispute type and an evidence bundle, determine the optimal strategy.

Rules:
1. If evidence strongly supports the merchant → recommend filing the dispute.
2. If evidence is mixed → recommend filing but flag risks clearly.
3. If evidence does NOT support the merchant → honestly recommend settling with the customer.
   Do NOT recommend filing a dispute you cannot win. Filing a losing dispute costs the
   merchant more than settling directly.

Return ONLY valid JSON. No markdown, no preamble:
{
  "winning_argument": "<2-3 sentence argument summarising the merchant's strongest position>",
  "argument_strength": "<strong|moderate|weak>",
  "key_evidence_refs": ["<evidence key 1>", "<evidence key 2>"],
  "recommendation": "<file_dispute|settle_with_customer|escalate_to_legal>"
}"""


def run(state: CaseState) -> CaseState:
    user_prompt = (
        f"Dispute Type: {state.dispute_type} (confidence: {state.confidence_score:.0%})\n"
        f"Dispute Amount: {state.dispute_amount} {state.currency}\n"
        f"Evidence Bundle:\n{json.dumps(state.evidence, indent=2)}"
    )

    result = call_llm(SYSTEM_PROMPT, user_prompt, expect_json=True)

    state.winning_argument  = result["winning_argument"]
    state.argument_strength = result["argument_strength"]
    state.key_evidence_refs = result["key_evidence_refs"]
    state.recommendation    = result["recommendation"]

    return state
```

---

## 15. dispute_ai/agents/response_writer.py

```python
import json
from pathlib import Path
from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a specialist in payment dispute resolution for Indian merchants.

Write a formal chargeback dispute response letter addressed to the acquiring bank.

Requirements:
- Formal tone throughout
- Structure exactly as follows:
  (1) Reference & Subject line
  (2) Statement of Facts
  (3) Evidence Summary — cite each piece of evidence by name
  (4) Legal Basis — reference the chargeback code and applicable RBI guidelines
  (5) Request for Reversal — clear, direct, unambiguous
- Length: 300-400 words
- Plain text only — absolutely no markdown, no # headers, no bullet points, no asterisks
- Professional Indian banking correspondence style"""


def run(state: CaseState) -> CaseState:
    if state.recommendation != "file_dispute":
        # Do not generate a letter for weak cases — output settlement rationale instead
        state.dispute_letter = (
            f"[Letter not generated — Strategy Agent recommends: {state.recommendation}]\n\n"
            f"Rationale: {state.winning_argument}"
        )
        return state

    user_prompt = (
        f"Case ID: {state.case_id}\n"
        f"Merchant: {state.merchant_id}\n"
        f"Customer: {state.customer_name}\n"
        f"Amount: {state.dispute_amount} {state.currency}\n"
        f"Chargeback Code: {state.chargeback_code}\n"
        f"Dispute Type: {state.dispute_type}\n"
        f"Filing Deadline: {state.filing_deadline}\n\n"
        f"Strategy:\n{state.winning_argument}\n\n"
        f"Evidence Available:\n{json.dumps(state.evidence, indent=2)}"
    )

    state.dispute_letter = call_llm(
        SYSTEM_PROMPT,
        user_prompt,
        expect_json=False,
        max_tokens=1000,
    )

    # Persist letter to output/
    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{state.case_id}_letter.txt"
    output_path.write_text(state.dispute_letter)

    return state
```

---

## 16. dispute_ai/agents/timeline.py

No LLM call — pure Python date arithmetic.

```python
from datetime import date
from dispute_ai.state import CaseState


def run(state: CaseState) -> CaseState:
    today = date.today()

    try:
        deadline = date.fromisoformat(state.filing_deadline)
    except ValueError:
        state.days_remaining    = -1
        state.urgency_level     = "UNKNOWN"
        state.recommended_action = "Could not parse deadline — verify filing date manually"
        return state

    state.days_remaining = (deadline - today).days

    if state.days_remaining < 0:
        state.urgency_level      = "EXPIRED"
        state.recommended_action = "Deadline has passed — escalate to legal team immediately"
    elif state.days_remaining <= 3:
        state.urgency_level      = "CRITICAL"
        state.recommended_action = "File TODAY — same business day, no exceptions"
    elif state.days_remaining <= 7:
        state.urgency_level      = "URGENT"
        state.recommended_action = "File within 48 hours"
    else:
        state.urgency_level      = "NORMAL"
        state.recommended_action = "File within 5 business days"

    reminders = []
    if state.days_remaining >= 7:
        reminders.append(f"Day {state.days_remaining - 5}: Prepare and review dispute letter")
    if state.days_remaining >= 3:
        reminders.append(f"Day {state.days_remaining - 2}: Final check — confirm all evidence attached")
    reminders.append(f"Day {state.days_remaining}:     *** FILING DEADLINE — confirm submission ***")

    state.reminder_schedule = reminders
    return state
```

---

## 17. dispute_ai/pipeline.py

This is the AutoGen orchestration layer. It wraps each agent function in an AutoGen
`AssistantAgent`, then drives them sequentially using a `UserProxyAgent` as the initiator.

**Architecture decision:** AutoGen's `GroupChat` is overkill for a fixed sequential pipeline.
Instead, use a simple `UserProxyAgent` → `AssistantAgent` pair per stage, where the
`UserProxyAgent` passes the serialised state as the message and the `AssistantAgent`'s
tool-call executes the real agent function. This keeps AutoGen's tracing and message history
intact while keeping the pipeline deterministic.

```python
import json
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dispute_ai.state import CaseState
from dispute_ai.llm_client import get_autogen_llm_config
from dispute_ai.agents import (
    classifier,
    evidence_collector,
    strategy,
    response_writer,
    timeline,
)


def _make_model_client() -> OpenAIChatCompletionClient:
    """Build an AutoGen-compatible model client from the shared llm_config."""
    cfg = get_autogen_llm_config()
    entry = cfg["config_list"][0]
    return OpenAIChatCompletionClient(
        model=entry["model"],
        base_url=entry["base_url"],
        api_key=entry["api_key"],
    )


# ── Agent wrapper factory ─────────────────────────────────────────────────────

def _make_agent(name: str, description: str, model_client: OpenAIChatCompletionClient):
    """
    Create a lightweight AssistantAgent.
    The actual processing is done by the corresponding agent function —
    AutoGen provides the message passing, tracing, and history.
    """
    return AssistantAgent(
        name=name,
        description=description,
        model_client=model_client,
        system_message=(
            f"You are the {name} in the DisputeAI pipeline. "
            "Acknowledge each task with a brief confirmation. "
            "The orchestrator will call your processing function directly."
        ),
    )


# ── Sequential pipeline runner ────────────────────────────────────────────────

async def run_pipeline_async(
    state: CaseState,
    on_agent_complete: callable = None,
) -> CaseState:
    """
    Runs the five-agent pipeline sequentially.

    AutoGen is used for agent identity, message tracing, and the model client.
    Each agent's business logic is in its own module under agents/.

    `on_agent_complete` is an optional callback — main.py passes it the renderer
    function so the terminal UI can print output after each step.

    Args:
        state: The shared CaseState dataclass
        on_agent_complete: callback(agent_name: str, state: CaseState) -> None
    """
    model_client = _make_model_client()

    STAGES = [
        ("ClassifierAgent",       "Classifies the dispute type",              classifier.run),
        ("EvidenceCollectorAgent","Collects and structures evidence",          evidence_collector.run),
        ("StrategyAgent",         "Builds the optimal dispute strategy",       strategy.run),
        ("ResponseWriterAgent",   "Drafts the formal dispute letter",          response_writer.run),
        ("TimelineAgent",         "Calculates deadlines and urgency",          timeline.run),
    ]

    for agent_name, description, agent_fn in STAGES:
        # Create the AutoGen agent (used for identity/tracing)
        _ = _make_agent(agent_name, description, model_client)

        # Execute the actual business logic — updates state in place
        state = agent_fn(state)

        # Fire the UI callback if provided
        if on_agent_complete:
            on_agent_complete(agent_name, state)

    return state


def run_pipeline(
    state: CaseState,
    on_agent_complete: callable = None,
) -> CaseState:
    """Synchronous wrapper around run_pipeline_async for CLI use."""
    return asyncio.run(run_pipeline_async(state, on_agent_complete))
```

---

## 18. dispute_ai/renderer.py

All Rich terminal rendering is isolated here. `main.py` imports from this module.

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from dispute_ai.state import CaseState

console = Console()

URGENCY_COLOURS = {
    "CRITICAL": "bold red",
    "URGENT":   "bold yellow",
    "NORMAL":   "bold green",
    "EXPIRED":  "bold red blink",
    "UNKNOWN":  "bold white",
}

STRENGTH_COLOURS = {
    "strong":   "bold green",
    "moderate": "bold yellow",
    "weak":     "bold red",
}


def render_banner():
    console.print()
    console.rule("[bold]DisputeAI[/bold] · Autonomous Payment Dispute Resolution")
    console.print()


def render_input_panel(state: CaseState):
    content = (
        f"[bold]Case ID:[/bold]       {state.case_id}\n"
        f"[bold]Merchant:[/bold]      {state.merchant_id}\n"
        f"[bold]Customer:[/bold]      {state.customer_name}\n"
        f"[bold]Amount:[/bold]        {state.currency} {state.dispute_amount:,.2f}\n"
        f"[bold]Code:[/bold]          {state.chargeback_code}\n"
        f"[bold]Reason:[/bold]        {state.chargeback_reason}\n"
        f"[bold]Deadline:[/bold]      {state.filing_deadline}"
    )
    console.print(Panel(content, title="[bold white]📥 CHARGEBACK RECEIVED[/bold white]", border_style="white"))


def render_agent_output(agent_name: str, state: CaseState):
    """Dispatch to the correct render function based on agent name."""
    dispatch = {
        "ClassifierAgent":        _render_classifier,
        "EvidenceCollectorAgent": _render_evidence,
        "StrategyAgent":          _render_strategy,
        "ResponseWriterAgent":    _render_letter,
        "TimelineAgent":          _render_timeline,
    }
    fn = dispatch.get(agent_name)
    if fn:
        fn(state)
        console.print()


def _render_classifier(state: CaseState):
    content = (
        f"[bold]Dispute Type:[/bold]  [bold cyan]{state.dispute_type}[/bold cyan]\n"
        f"[bold]Confidence:[/bold]    [cyan]{state.confidence_score:.0%}[/cyan]\n"
        f"[bold]Reasoning:[/bold]     {state.classifier_reasoning}"
    )
    console.print(Panel(content, title="[bold cyan]🔍 AGENT 1 — CLASSIFIER[/bold cyan]", border_style="cyan"))


def _render_evidence(state: CaseState):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    table.add_column("Evidence Item", style="white", width=35)
    table.add_column("Value", style="cyan")

    for key, value in state.evidence.items():
        label = key.replace("_", " ").title()
        if isinstance(value, bool):
            display = "[green]✓ Yes[/green]" if value else "[red]✗ No[/red]"
        elif value is None:
            display = "[dim]—[/dim]"
        else:
            display = str(value)
        table.add_row(label, display)

    console.print(Panel(table, title="[bold blue]📋 AGENT 2 — EVIDENCE COLLECTOR[/bold blue]", border_style="blue"))


def _render_strategy(state: CaseState):
    strength_colour = STRENGTH_COLOURS.get(state.argument_strength, "white")
    rec_colour = "green" if state.recommendation == "file_dispute" else "yellow"
    content = (
        f"[bold]Strength:[/bold]       [{strength_colour}]{state.argument_strength.upper()}[/{strength_colour}]\n"
        f"[bold]Recommendation:[/bold] [{rec_colour}]{state.recommendation}[/{rec_colour}]\n"
        f"[bold]Argument:[/bold]       {state.winning_argument}\n"
        f"[bold]Key Evidence:[/bold]   {', '.join(state.key_evidence_refs)}"
    )
    console.print(Panel(content, title="[bold yellow]⚖️  AGENT 3 — STRATEGY[/bold yellow]", border_style="yellow"))


def _render_letter(state: CaseState):
    if state.recommendation != "file_dispute":
        content = (
            f"[yellow]Letter not generated.[/yellow]\n\n"
            f"[bold]Recommendation:[/bold] {state.recommendation}\n\n"
            f"{state.dispute_letter}"
        )
        console.print(Panel(content, title="[bold yellow]✍️  AGENT 4 — RESPONSE WRITER[/bold yellow]", border_style="yellow"))
    else:
        preview = state.dispute_letter[:600] + "\n\n[dim]... (full letter saved to output/)[/dim]"
        console.print(Panel(preview, title="[bold green]✍️  AGENT 4 — RESPONSE WRITER[/bold green]", border_style="green"))


def _render_timeline(state: CaseState):
    urgency_colour = URGENCY_COLOURS.get(state.urgency_level, "white")
    reminders_text = "\n".join(f"  • {r}" for r in state.reminder_schedule)
    content = (
        f"[bold]Days Remaining:[/bold]  [{urgency_colour}]{state.days_remaining} days[/{urgency_colour}]\n"
        f"[bold]Urgency:[/bold]         [{urgency_colour}]{state.urgency_level}[/{urgency_colour}]\n"
        f"[bold]Action:[/bold]          {state.recommended_action}\n\n"
        f"[bold]Reminder Schedule:[/bold]\n{reminders_text}"
    )
    console.print(Panel(content, title="[bold magenta]📅 AGENT 5 — TIMELINE[/bold magenta]", border_style="magenta"))


def render_final_summary(state: CaseState):
    strength_colour = STRENGTH_COLOURS.get(state.argument_strength, "white")
    urgency_colour  = URGENCY_COLOURS.get(state.urgency_level, "white")
    rec_colour      = "green" if state.recommendation == "file_dispute" else "yellow"
    content = (
        f"  [bold]Case:[/bold]           {state.case_id}\n"
        f"  [bold]Dispute Type:[/bold]   {state.dispute_type}\n"
        f"  [bold]Case Strength:[/bold]  [{strength_colour}]{state.argument_strength.upper()}[/{strength_colour}]\n"
        f"  [bold]Decision:[/bold]       [{rec_colour}]{state.recommendation}[/{rec_colour}]\n"
        f"  [bold]Urgency:[/bold]        [{urgency_colour}]{state.urgency_level} — {state.days_remaining} days[/{urgency_colour}]\n"
        f"  [bold]Letter:[/bold]         output/{state.case_id}_letter.txt\n"
    )
    console.print()
    console.print(Panel(content, title="[bold] ✅  PIPELINE COMPLETE [/bold]", border_style="white", padding=(1, 2)))
    console.print()
```

---

## 19. dispute_ai/main.py

```python
import json
import sys
from pathlib import Path

from dispute_ai.state import CaseState
from dispute_ai.pipeline import run_pipeline
from dispute_ai.renderer import (
    console,
    render_banner,
    render_input_panel,
    render_agent_output,
    render_final_summary,
)


def main():
    data_path = Path(__file__).parent / "mock_data" / "chargebacks.json"
    all_cases = json.loads(data_path.read_text())

    target_id = sys.argv[1] if len(sys.argv) > 1 else "CB-2024-001"
    case = next((c for c in all_cases if c["case_id"] == target_id), None)

    if not case:
        console.print(f"[red]Error: Case ID '{target_id}' not found.[/red]")
        console.print(f"Available: {[c['case_id'] for c in all_cases]}")
        sys.exit(1)

    state = CaseState(**case)

    render_banner()
    render_input_panel(state)
    console.print()

    def on_agent_complete(agent_name: str, updated_state: CaseState):
        console.print(f"[green]✓[/green] {agent_name} complete")
        render_agent_output(agent_name, updated_state)

    state = run_pipeline(state, on_agent_complete=on_agent_complete)

    render_final_summary(state)


if __name__ == "__main__":
    main()
```

---

## 20. dispute_ai/__init__.py

```python
# dispute_ai package
```

---

## 21. Run Instructions

### Local (without Docker)

```bash
# 1. Ensure Ollama is running with gemma3 pulled
ollama pull gemma3
ollama serve   # runs on localhost:11434 by default

# 2. Create and activate virtual environment with uv
uv venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
uv pip install -e .

# 4. Configure environment
cp .env.example .env
# .env already defaults to LLM_PROVIDER=ollama — no edits needed for local dev

# 5. Run the three demo scenarios
python -m dispute_ai.main CB-2024-001   # Strong case
python -m dispute_ai.main CB-2024-002   # Moderate case
python -m dispute_ai.main CB-2024-003   # Weak case — settle_with_customer
```

### Docker

```bash
# Ensure Ollama is running on the host (not inside Docker)
ollama serve

# Build and run
docker compose build
docker compose run dispute-ai CB-2024-001
docker compose run dispute-ai CB-2024-003
```

---

## 22. Expected Output Per Scenario

### CB-2024-001 (Strong Case)
- Classifier: `item_not_received`, high confidence
- Evidence: delivery confirmed ✓, OTP proof ✓, post-delivery app activity ✓, review left ✓
- Strategy: `strong`, recommendation: `file_dispute`
- Letter: generated and saved to `output/CB-2024-001_letter.txt`
- Timeline: NORMAL urgency (~47 days to deadline)

### CB-2024-002 (Moderate Case)
- Classifier: `unauthorized_transaction`, high confidence
- Evidence: delivery confirmed ✓, UPI PIN ✓, prior dispute on record ⚠
- Strategy: `moderate`, recommendation: `file_dispute`
- Letter: generated and saved
- Timeline: NORMAL urgency (~32 days)

### CB-2024-003 (Weak Case — critical demo moment)
- Classifier: `item_not_as_described`, high confidence
- Evidence: delivery confirmed ✓, support contacted before dispute ⚠
- Strategy: `weak`, recommendation: `settle_with_customer`
- Letter: **not generated** — settlement rationale displayed instead
- Timeline: URGENT (~14 days)

---

## 23. Error Handling Requirements

1. **LLM JSON parse failure**: Retry up to 3 times with 1-second delay. After 3 failures, raise `ValueError` with the raw response included in the message so the developer can see what the model returned.
2. **Missing mock data record**: Return `CaseState` with empty evidence dict. Log a warning with `console.print("[yellow]Warning: no record found for transaction_id {x}[/yellow]")`. Do not crash.
3. **Invalid filing deadline**: Set `urgency_level = "UNKNOWN"`, set `recommended_action` to a manual check message. Do not crash.
4. **Ollama not running**: The `openai` client will raise a `ConnectionError` or `httpx.ConnectError`. Let it propagate with a clear error — do not catch it silently. The error message itself tells the developer to run `ollama serve`.
5. **Wrong LLM_PROVIDER value**: `llm_client.py` raises `ValueError` with a clear message listing valid options.

---

## 24. Do Not Add

- Do not add a web server, Flask, FastAPI, or any HTTP layer
- Do not add a database or SQLite
- Do not add LangChain or LangGraph
- Do not add streaming LLM responses
- Do not add unit tests unless explicitly asked
- Do not add logging to files — console output only
- Do not add async/await outside of `pipeline.py` — all other files are synchronous

---

## 25. Definition of Done

The build is complete when all of the following pass:

- [ ] `python -m dispute_ai.main CB-2024-001` runs end-to-end and prints all five agent panels in colour
- [ ] `python -m dispute_ai.main CB-2024-003` produces a `settle_with_customer` recommendation with no dispute letter generated
- [ ] `output/CB-2024-001_letter.txt` exists and contains a 300–400 word formal dispute letter
- [ ] All five agents execute in sequence with a visible Rich panel output per agent
- [ ] `docker compose run dispute-ai CB-2024-001` runs successfully
- [ ] No hardcoded API keys or model names anywhere — all sourced from `.env`
- [ ] Changing `LLM_PROVIDER=bedrock` in `.env` does not require any code changes

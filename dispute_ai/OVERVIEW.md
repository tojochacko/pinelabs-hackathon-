# DisputeAI — Autonomous Payment Dispute Resolution

## Problem

Indian merchants lose significant revenue to payment chargebacks. For every dispute, a merchant must manually:

1. Assess whether the dispute is worth fighting
2. Gather transaction, delivery, and communication evidence
3. Draft a formal chargeback response letter
4. Track filing deadlines (RBI-mandated, typically 30–45 days)

This process is time-consuming, error-prone, and inconsistent — most small merchants lack the expertise to fight winnable disputes, and waste effort on disputes they cannot win.

---

## Solution

DisputeAI is a multi-agent AI service that automatically processes incoming chargebacks end-to-end:

- Classifies the dispute type (non-delivery, unauthorized transaction, item not as described, etc.)
- Collects and structures evidence from transaction records, delivery logs, and customer communications
- Recommends a strategy: **FIGHT** (file dispute) or **ACCEPT** (settle with customer)
- Drafts a formal dispute letter ready for submission
- Calculates filing deadlines and urgency levels
- Notifies the merchant via **WhatsApp** immediately after the decision is made
- Surfaces all disputes on a **real-time reporting dashboard**

---

## Five-Agent Pipeline

```
Chargeback Webhook
       │
       ▼
┌─────────────────┐
│  ClassifierAgent │  → Identifies dispute type + confidence score
└────────┬────────┘
         ▼
┌──────────────────────┐
│ EvidenceCollectorAgent│  → Pulls transaction, delivery, comms data
└────────┬─────────────┘
         ▼
┌───────────────┐
│ StrategyAgent  │  → FIGHT / ACCEPT decision + win probability (0–100%)
└────────┬──────┘    → Triggers WhatsApp notification to merchant
         ▼
┌────────────────────┐
│ ResponseWriterAgent │  → Drafts formal chargeback dispute letter
└────────┬───────────┘
         ▼
┌──────────────┐
│ TimelineAgent │  → Filing deadline + urgency level (CRITICAL / URGENT / NORMAL)
└──────────────┘
         │
         ▼
  Supabase (disputes table) → Dashboard
```

---

## Technical Stack

| Layer | Technology |
|---|---|
| Agent framework | AutoGen (Microsoft) |
| LLM | Amazon Bedrock — Claude Sonnet 4.6 (inference profile) |
| API server | FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| Dashboard | Vanilla JS + Tailwind CSS, served from FastAPI |
| WhatsApp notifications | CallMeBot (free, per-merchant API key) |
| Payment integration | Pine Labs webhook + mock client |
| Containerisation | Docker |
| Deployment | AWS App Runner (ECR image) |
| Local dev LLM | Ollama (gemma3) |

---

## Running the Service

### Prerequisites

- Docker (for containerised run) or Python 3.11 + `uv` (for local run)
- Supabase project with migrations applied
- Amazon Bedrock API key (Bearer token) **or** Ollama running locally

### 1. Configure environment

```bash
cp .env.example .env
# Fill in: LLM_PROVIDER, AWS_BEARER_TOKEN_BEDROCK, BEDROCK_MODEL,
#          AWS_REGION, SUPABASE_URL, SUPABASE_KEY
```

### 2. Apply database migrations

Run in order in the Supabase SQL editor:

```
migrations/001_initial.sql       — creates disputes + audit_events tables
migrations/002_merchant_phone.sql — adds merchant_phone column
migrations/003_mock_data.sql      — optional: 13 sample disputes
```

### 3a. Run locally

```bash
uv sync
uvicorn dispute_ai.webhook:app --reload --port 8000
```

### 3b. Run with Docker

```bash
docker build -t dispute-ai .
docker run --env-file .env -p 8000:8000 dispute-ai
```

### 4. Simulate a dispute

```bash
curl -X POST http://localhost:8000/simulate/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TXN-UL-8821993",
    "merchant_id": "MERCH-URBAN-LADDER",
    "amount": 4500,
    "currency": "INR",
    "reason": "Customer claims item was never delivered.",
    "chargeback_code": "RBI-CB-4855",
    "customer_name": "Priya Mehta",
    "merchant_phone": "+919876543210",
    "merchant_whatsapp_key": "YOUR_CALLMEBOT_KEY"
  }'
```

### 5. View the dashboard

```
http://localhost:8000/dashboard
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook/pine-labs` | Signed webhook from Pine Labs (HMAC-SHA256) |
| `POST` | `/simulate/dispute` | Trigger pipeline without signature (demo/testing) |
| `GET` | `/dashboard` | Merchant reporting dashboard UI |
| `GET` | `/api/disputes` | All disputes as JSON |
| `GET` | `/api/disputes?decision=FIGHT` | Filter by FIGHT or ACCEPT |

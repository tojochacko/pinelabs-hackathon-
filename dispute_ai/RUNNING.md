# Running DisputeAI — Mock Data Guide

## Prerequisites

Ollama must be running with the model pulled:

```bash
ollama pull gemma3
ollama serve
```

---

## Mode A — CLI

Runs the five-agent pipeline directly from a chargeback JSON record. No server needed.

```bash
cd /Users/tojochacko/code/PineLabs/dispute_ai
source .venv/bin/activate

python -m dispute_ai.main CB-2024-001   # "never delivered" → expect FIGHT
python -m dispute_ai.main CB-2024-002   # unauthorized transaction
python -m dispute_ai.main CB-2024-003   # item not as described → expect settle
```

Output: rich terminal panels for each of the five agents.

---

## Mode B — Webhook / FastAPI

### Terminal 1 — start the server

```bash
cd /Users/tojochacko/code/PineLabs/dispute_ai
source .venv/bin/activate
uvicorn dispute_ai.webhook:app --reload --port 8000
```

### Terminal 2 — simulate a dispute

`POST /simulate/dispute` requires no signature. The curl returns immediately with `{"status":"accepted"}`; the pipeline runs in the background and prints to Terminal 1.

**CB-2024-001** — "never delivered" (expect FIGHT):
```bash
curl -s -X POST http://localhost:8000/simulate/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TXN-UL-8821993",
    "merchant_id": "MERCH-URBAN-LADDER",
    "amount": 4500,
    "currency": "INR",
    "reason": "Customer claims item was never delivered.",
    "chargeback_code": "RBI-CB-4855",
    "customer_name": "Priya Mehta"
  }'
```

**CB-2024-002** — unauthorized transaction:
```bash
curl -s -X POST http://localhost:8000/simulate/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TXN-UL-9934421",
    "merchant_id": "MERCH-URBAN-LADDER",
    "amount": 8200,
    "currency": "INR",
    "reason": "Cardholder states this transaction was not authorized by them.",
    "chargeback_code": "RBI-CB-4853",
    "customer_name": "Rahul Sharma"
  }'
```

**CB-2024-003** — item not as described (expect settle):
```bash
curl -s -X POST http://localhost:8000/simulate/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TXN-UL-7712088",
    "merchant_id": "MERCH-URBAN-LADDER",
    "amount": 3100,
    "currency": "INR",
    "reason": "Item received but significantly not as described.",
    "chargeback_code": "RBI-CB-4853",
    "customer_name": "Anjali Singh"
  }'
```

---

## Mode C — Signed Webhook (production simulation)

`POST /webhook/pine-labs` verifies an HMAC-SHA256 signature. The secret is `PINE_LABS_WEBHOOK_SECRET` in `.env`.

Compute the signature and send the request:

```bash
BODY='{"order_id":"TXN-UL-8821993","merchant_id":"MERCH-URBAN-LADDER","amount":4500,"currency":"INR","reason":"Customer claims item was never delivered.","chargeback_code":"RBI-CB-4855","customer_name":"Priya Mehta"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "your-hmac-secret" | awk '{print $2}')

curl -s -X POST http://localhost:8000/webhook/pine-labs \
  -H "Content-Type: application/json" \
  -H "X-Pine-Signature: $SIG" \
  -d "$BODY"
```

A wrong or missing signature returns `401 {"detail":"Invalid signature"}`.

---

## Expected output

| What | Where |
|---|---|
| Immediate response | `{"status":"accepted"}` in the terminal running curl |
| Agent pipeline output | Terminal 1 (uvicorn logs), one section per agent |
| Final summary | Case ID, win probability %, FIGHT/ACCEPT decision, recommendation, urgency level |
| Supabase | One row in `disputes`, six rows in `audit_events` (pipeline_started + one per agent) |

---

## Mock data reference

The three order IDs with full mock data:

| order_id | case | scenario |
|---|---|---|
| `TXN-UL-8821993` | CB-2024-001 | Item not delivered — strong merchant evidence |
| `TXN-UL-9934421` | CB-2024-002 | Unauthorized transaction |
| `TXN-UL-7712088` | CB-2024-003 | Item not as described — weak merchant evidence |

Mock data files are in `dispute_ai/mock_data/`: `chargebacks.json`, `transactions.json`, `deliveries.json`, `customer_comms.json`.

Pine Labs mock mode is controlled by `PINE_LABS_MOCK=true` in `.env` (default). Set to `false` to call the real API.

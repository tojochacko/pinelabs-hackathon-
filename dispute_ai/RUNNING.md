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

## Dashboard

With the webhook server running, open the merchant dashboard in a browser:

```
http://localhost:8000/dashboard
```

The dashboard shows:
- **Summary cards** — total disputes, FIGHT count, ACCEPT count with total INR value
- **Filterable table** — switch between All / FIGHT / ACCEPT tabs
- **Detail modal** — click any row to see the full case including the dispute letter
- Auto-refreshes every 30 seconds

The underlying data endpoint is also available directly:

```bash
# All disputes
curl http://localhost:8000/api/disputes

# Only FIGHT decisions
curl "http://localhost:8000/api/disputes?decision=FIGHT"

# Only ACCEPT decisions
curl "http://localhost:8000/api/disputes?decision=ACCEPT"
```

---

## WhatsApp Notifications

After the StrategyAgent labels a dispute (FIGHT/ACCEPT), the merchant receives a WhatsApp message with the decision details. This uses **CallMeBot** — free with no subscription.

### One-time merchant activation

Each merchant must activate once:

1. Add `+34 644 60 20 96` to WhatsApp contacts (name it "CallMeBot")
2. Send this exact message to that number:
   ```
   I allow callmebot to send me messages
   ```
3. Within seconds, CallMeBot replies with a personal API key — save it

### Sending a dispute with WhatsApp notification

Add `merchant_phone` (E.164 format) and `merchant_whatsapp_key` to any simulate or webhook payload:

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
    "customer_name": "Priya Mehta",
    "merchant_phone": "+919876543210",
    "merchant_whatsapp_key": "1234567"
  }'
```

The WhatsApp message arrives after the StrategyAgent step (before the pipeline finishes) and contains:

```
DisputeAI Alert
Case: CASE-TXN-UL-8821993-XXXXXX
Order: TXN-UL-8821993
Amount: 4500.0 INR
Decision: FIGHT
Win Probability: 78%
Recommendation: file_dispute
Dispute Type: non_delivery
Argument Strength: strong
```

**Note:** `merchant_phone` and `merchant_whatsapp_key` are not stored in Supabase. They are used transiently during the pipeline run.

**Single-merchant shortcut:** Set `CALLMEBOT_API_KEY=<key>` in `.env` and omit `merchant_whatsapp_key` from the payload — the env var is used as fallback.

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
| Dashboard | `http://localhost:8000/dashboard` — updates on next 30s refresh or manual refresh |
| WhatsApp | Merchant receives message after StrategyAgent step (if `merchant_phone` + `merchant_whatsapp_key` provided) |

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

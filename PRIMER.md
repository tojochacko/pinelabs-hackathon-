# PRIMER — DisputeAI Project

## What was done

### Session 1 — CLI baseline
Built the complete DisputeAI project from scratch per `DisputeAI_CodeAgent.md` spec.
Five-agent pipeline (classifier → evidence_collector → strategy → response_writer → timeline) running via `python -m dispute_ai.main CB-2024-001`.

### Session 2 — Webhook / API layer
Evolved the project into a webhook-driven service:

**New files:**
- `dispute_ai/pine_labs_client.py` — stub for `GET /api/checkout/v1/orders/{order_id}`. Mock mode (default) reads `transactions.json` + `deliveries.json`. Live mode via httpx.
- `dispute_ai/db.py` — Supabase client wrapper: `upsert_dispute(state)`, `log_event(case_id, event, payload)`
- `dispute_ai/webhook.py` — FastAPI app with two endpoints:
  - `POST /webhook/pine-labs` — HMAC-SHA256 signature verification, 200 + background pipeline
  - `POST /simulate/dispute` — no signature check, for hackathon demos
- `dispute_ai/migrations/001_initial.sql` — `disputes` + `audit_events` tables

**Modified files:**
- `state.py` — added `order_id`, `approval_code`, `rrn`, `acquirer_ref`, `card_network`, `payment_method`, `win_probability`, `pipeline_decision`
- `agents/evidence_collector.py` — now calls `pine_labs_client.get_order()` instead of reading JSON directly
- `agents/strategy.py` — LLM prompt now requests `win_probability` (0-100) and `pipeline_decision` (FIGHT|ACCEPT)
- `pipeline.py` — added `run_webhook_pipeline_async(state, on_step)` alongside unchanged CLI functions
- `pyproject.toml` — added fastapi, uvicorn[standard], supabase, httpx; added `dispute-ai-webhook` script entry
- `.env.example` — added Pine Labs and Supabase env vars

### Session 3 — Dashboard + WhatsApp notifications

**New files:**
- `dispute_ai/notifier.py` — WhatsApp notifications via CallMeBot (free forever). `notify_strategy_decision(state)` sends decision details to merchant after StrategyAgent runs.
- `dispute_ai/migrations/002_merchant_phone.sql` — adds `merchant_phone TEXT` column to `disputes` table

**Modified files:**
- `state.py` — added `merchant_phone`, `merchant_whatsapp_key` fields
- `db.py` — `upsert_dispute` now stores `merchant_phone`; added `get_disputes(decision=None)` for dashboard API
- `webhook.py` — added `merchant_phone`/`merchant_whatsapp_key` to `DisputePayload`; calls `_try_notify(state)` after StrategyAgent in `on_step`; added `GET /dashboard` (HTML) and `GET /api/disputes` (JSON) endpoints
- `.env.example` — added `CALLMEBOT_API_KEY` with setup instructions

## Current state
Full webhook + dashboard + notifications. Supabase is the single source of truth for the dashboard. WhatsApp notifications are per-merchant (each merchant has their own CallMeBot API key tied to their phone number).

## Next steps
1. Run `dispute_ai/migrations/002_merchant_phone.sql` in Supabase dashboard
2. Set `CALLMEBOT_API_KEY` in `.env` (fallback for single-merchant setups)
3. Access dashboard at `http://localhost:8000/dashboard` after starting the server
4. Simulate a dispute with merchant phone for WhatsApp notification:
   ```bash
   curl -X POST http://localhost:8000/simulate/dispute \
     -H "Content-Type: application/json" \
     -d '{"order_id":"TXN-UL-8821993","merchant_id":"MERCH-URBAN-LADDER","amount":4500,"currency":"INR","reason":"Customer claims item was never delivered.","chargeback_code":"RBI-CB-4855","customer_name":"Priya Mehta","merchant_phone":"+919876543210","merchant_whatsapp_key":"YOUR_CALLMEBOT_KEY"}'
   ```
5. **CallMeBot merchant activation:** Each merchant adds `+34 644 60 20 96` on WhatsApp and sends "I allow callmebot to send me messages" — they receive their personal API key

**API:**
- `GET /dashboard` — merchant dashboard UI
- `GET /api/disputes` — all disputes (JSON)
- `GET /api/disputes?decision=FIGHT` — filter by FIGHT or ACCEPT
- `POST /simulate/dispute` — trigger pipeline
- `POST /webhook/pine-labs` — signed webhook from Pine Labs

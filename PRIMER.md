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

## Current state
All imports verified clean. Mock Pine Labs client returns correct data. CLI path unchanged.
Supabase calls will gracefully skip (logged as warnings) if `SUPABASE_URL`/`SUPABASE_KEY` not set.

## Next steps
1. `cp dispute_ai/.env.example dispute_ai/.env` and fill in secrets (or leave `PINE_LABS_MOCK=true`)
2. `cd dispute_ai && uv sync`
3. Start Ollama: `ollama serve`
4. Start FastAPI: `uvicorn dispute_ai.webhook:app --reload --port 8000`
5. Simulate a dispute:
   ```bash
   curl -X POST http://localhost:8000/simulate/dispute \
     -H "Content-Type: application/json" \
     -d '{"order_id":"TXN-UL-8821993","merchant_id":"MERCH-URBAN-LADDER","amount":4500,"currency":"INR","reason":"Customer claims item was never delivered.","chargeback_code":"RBI-CB-4855","customer_name":"Priya Mehta"}'
   ```
6. Run SQL migration in Supabase dashboard: `dispute_ai/migrations/001_initial.sql`
7. Set `SUPABASE_URL` and `SUPABASE_KEY` to enable DB persistence
8. Test signed webhook with `POST /webhook/pine-labs` + `X-Pine-Signature` header

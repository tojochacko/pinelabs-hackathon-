# DisputeAI — Production Considerations

## 1. Evidence Collection: Type-Specific Collectors

The current `evidence_collector.py` is hardcoded to the **non-delivery** dispute archetype. In production, the classifier output (`state.dispute_type`) must route to a type-specific collector, each integrated with the relevant internal or third-party system.

### Routing architecture

```
Agent 1: Classifier → state.dispute_type
    ↓
Agent 2: Evidence Router → selects collector based on dispute_type
    ↓
Type-specific collector → calls relevant APIs
    ↓
Normalised evidence bundle → passed to Strategy LLM
```

### Collector map

| Dispute Type | Evidence Source | Key Fields |
|---|---|---|
| Non-delivery | Logistics API (Delhivery, Bluedart, Shiprocket) | `delivery_proof`, `gps_coordinates`, `receiver_otp` |
| Subscription cancellation | Chargebee / Recurly / internal billing DB | `cancellation_timestamp`, `ack_sent`, `billing_cycle_at_cancel` |
| Unauthorized transaction | 3DS logs, device fingerprint, IP geolocation | `3ds_authenticated`, `device_match`, `ip_country` |
| Item not as described | Product catalogue, return/QC logs | `listing_snapshot`, `return_initiated`, `qc_report` |
| Duplicate charge | Payment gateway ledger | `idempotency_key`, `duplicate_txn_id` |
| Service not rendered | Booking system, airline/hotel APIs | `booking_confirmation`, `service_status`, `vendor_cancellation_reason` |
| Partial delivery | WMS / order fulfilment logs | `items_shipped`, `items_delivered`, `shortfall_acknowledged` |
| Warranty / defective | Service centre CRM | `warranty_status`, `service_request_id`, `damage_assessment` |

---

## 2. Rule Engine Before the LLM (Pre-filter Layer)

Certain chargeback code + evidence combinations have deterministic outcomes. Running these through the LLM adds latency and cost with no accuracy benefit. A rule engine should intercept these before the Strategy agent.

### Examples of deterministic rules

```
RBI-CB-4841 + cancellation_timestamp < charge_timestamp  →  SETTLE
Duplicate charge + idempotency_key matches existing txn   →  FIGHT
3DS authenticated + device_match = true + OTP confirmed   →  FIGHT
service_status = CANCELLED_BY_VENDOR                      →  SETTLE
```

The LLM should only handle cases where rules produce no clear signal — genuinely ambiguous disputes where evidence is mixed or incomplete.

---

## 3. Pine Labs API Integration (Replace Mock)

Set `PINE_LABS_MOCK=false` and configure credentials in `.env`. The `pine_labs_client.py` live path calls `GET /api/checkout/v1/orders/{order_id}` via httpx. Additional fields to pull in production:

- `card_network` (VISA / MASTERCARD / RUPAY) — network rules differ per scheme
- `acquirer_ref` — needed for formal dispute filing with the acquirer
- `rrn` — Reference Retrieval Number required in all RBI chargeback submissions
- `mcc` — Merchant Category Code affects which chargeback reason codes are valid

---

## 4. Supabase / Database

- Run `migrations/001_initial.sql` against the production Supabase project
- Add a `updated_at` trigger so the column stays accurate on upserts:
  ```sql
  CREATE OR REPLACE FUNCTION update_updated_at()
  RETURNS TRIGGER AS $$
  BEGIN NEW.updated_at = now(); RETURN NEW; END;
  $$ LANGUAGE plpgsql;

  CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON disputes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  ```
- Use the **service role key** (not anon key) for the webhook service — the anon key has RLS restrictions that will block inserts
- Enable Row Level Security (RLS) policies scoped per `merchant_id` for multi-tenant deployments

---

## 5. Webhook Security

- Rotate `PINE_LABS_WEBHOOK_SECRET` and store it in a secrets manager (AWS Secrets Manager, GCP Secret Manager, or Supabase Vault) — not in `.env` in production
- Add replay attack protection: reject webhooks where the timestamp in the payload is older than 5 minutes
- Rate-limit `/webhook/pine-labs` per source IP to prevent payload flooding

---

## 6. LLM in Production

- Replace Ollama with a managed provider (Amazon Bedrock, Azure OpenAI, or Google Vertex) — set `LLM_PROVIDER=bedrock` and configure AWS credentials
- Add a **structured output schema** (JSON Schema or Pydantic) to the LLM call to eliminate the JSON parsing retry loop in `llm_client.py`
- Log all LLM inputs and outputs to the `audit_events` table for dispute auditability — regulators may require a paper trail of AI-assisted decisions
- Set a **confidence threshold**: if `argument_strength = weak` and `win_probability < 40`, auto-recommend SETTLE without human review

---

## 7. Observability

- Instrument each agent with latency metrics — the 30-second SLA is tight if the LLM or external APIs are slow
- Alert if `pipeline_decision = FIGHT` but `win_probability < 50` — this is a contradiction that warrants human review
- Track `win_probability` accuracy over time by comparing predictions against actual chargeback outcomes; use this to fine-tune prompts

---

## 8. Compliance (RBI / Card Network Rules)

- Chargeback response deadlines vary by card network: Visa (30 days), Mastercard (45 days), RuPay (30 days) — the Timeline agent must be network-aware
- Certain dispute types (e.g., `RBI-CB-4853` — fraud) require the merchant to submit the response directly to the acquirer, not via the payment gateway — the Response Writer's letter format must match acquirer-specific templates
- Maintain an immutable audit log of every pipeline run with the full evidence bundle and LLM reasoning — required for RBI regulatory audits

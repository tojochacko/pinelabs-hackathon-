
## THE COMPLETE REALISTIC FLOW — All 3 Steps Together
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  TRIGGER (Pick one for hackathon):                  │
│  Option A: REFUND_PROCESSED webhook fires           │
│  Option B: Your simulator POST /simulate/dispute    │
│            ↓                                        │
│  STEP 1: WEBHOOK RECEIVER                           │
│  → Verify Pine Labs signature (HMAC-SHA256)         │
│  → Parse: order_id, amount, refund details          │
│  → Classify: is this dispute-related?               │
│  → Acknowledge 200 in < 3 seconds                   │
│  → setImmediate → async pipeline                    │
│            ↓                                        │
│  STEP 2: EVIDENCE GATHERING                         │
│  → Generate fresh auth token                        │
│  → GET /api/checkout/v1/orders/{order_id}           │
│  → Extract: approval_code, RRN, acquirer_ref        │
│  → Extract: card_network, payment_method            │
│  → Query Supabase: prior orders same customer_id    │
│  → Build evidence package (no raw PII to Claude)    │
│            ↓                                        │
│  STEP 3: CLAUDE AI ANALYSIS (AWS Bedrock)           │
│  → Send tokenized evidence package                  │
│  → Claude classifies: FRIENDLY_FRAUD / NOT_RECEIVED │
│    / UNAUTHORIZED / QUALITY                         │
│  → Claude scores: win probability 0-100             │
│  → Claude decides: FIGHT or ACCEPT                  │
│  → Claude writes: full defense document             │
│            ↓                                        │
│  STEP 4: FILING / ACCEPTANCE                        │
│  → If FIGHT:                                        │
│     - Store response in DB                          │
│     - Generate PDF dispute response document        │
│     - Mark as FILED in dashboard                    │
│     - Send merchant WhatsApp: "Defended ✅"         │
│  → If ACCEPT:                                       │
│     - Optionally trigger refund API                 │
│     - Notify merchant: "Accepted — loss avoided     │
│       (fight probability too low)"                  │
│            ↓                                        │
│  STEP 5: AUDIT LOG                                  │
│  → Every step timestamped in Supabase               │
│  → Dashboard shows full timeline                    │
│  → Total time: < 30 seconds                         │
│                                                     │
└─────────────────────────────────────────────────────┘
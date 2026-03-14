DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS disputes;

CREATE TABLE disputes (
    case_id TEXT PRIMARY KEY,
    order_id TEXT,
    merchant_id TEXT,
    transaction_id TEXT,
    dispute_amount NUMERIC,
    currency TEXT DEFAULT 'INR',
    dispute_type TEXT,
    argument_strength TEXT,
    win_probability INT,
    pipeline_decision TEXT,
    recommendation TEXT,
    dispute_letter TEXT,
    urgency_level TEXT,
    days_remaining INT,
    filing_deadline TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT REFERENCES disputes(case_id),
    event TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON audit_events (case_id);

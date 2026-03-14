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

    # ── WEBHOOK / PINE LABS API ───────────────────────────────────────────────
    order_id: str = ""
    approval_code: str = ""
    rrn: str = ""               # Reference Retrieval Number
    acquirer_ref: str = ""
    card_network: str = ""      # VISA | MASTERCARD | RUPAY
    payment_method: str = ""    # UPI | CARD | NETBANKING

    # ── STRATEGY (extended) ───────────────────────────────────────────────────
    win_probability: int = 0    # 0-100, from LLM
    pipeline_decision: str = "" # FIGHT | ACCEPT

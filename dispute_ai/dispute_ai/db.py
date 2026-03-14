import os
from dotenv import load_dotenv

load_dotenv()


def get_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    return create_client(url, key)


def upsert_dispute(state) -> None:
    client = get_client()
    client.table("disputes").upsert({
        "case_id": state.case_id,
        "order_id": state.order_id or state.transaction_id,
        "merchant_id": state.merchant_id,
        "transaction_id": state.transaction_id,
        "dispute_amount": state.dispute_amount,
        "currency": state.currency,
        "dispute_type": state.dispute_type,
        "argument_strength": state.argument_strength,
        "win_probability": state.win_probability,
        "pipeline_decision": state.pipeline_decision,
        "recommendation": state.recommendation,
        "dispute_letter": state.dispute_letter,
        "urgency_level": state.urgency_level,
        "days_remaining": state.days_remaining,
        "filing_deadline": state.filing_deadline,
        "status": "completed",
    }).execute()


def log_event(case_id: str, event: str, payload: dict) -> None:
    client = get_client()
    client.table("audit_events").insert({
        "case_id": case_id,
        "event": event,
        "payload": payload,
    }).execute()

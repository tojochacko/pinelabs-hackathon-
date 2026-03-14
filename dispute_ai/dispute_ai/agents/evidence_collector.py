import json
from pathlib import Path
from dispute_ai.state import CaseState
from dispute_ai import pine_labs_client

DATA_DIR = Path(__file__).parent.parent / "mock_data"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _find(records: list, key: str, value: str) -> dict | None:
    return next((r for r in records if r.get(key) == value), None)


def run(state: CaseState) -> CaseState:
    comms_data = _load("customer_comms.json")

    lookup_id = state.order_id or state.transaction_id
    order = pine_labs_client.get_order(lookup_id)

    transactions = _load("transactions.json")
    txn = _find(transactions, "transaction_id", lookup_id)

    customer_id = txn.get("customer_id") if txn else None
    comms = _find(comms_data, "customer_id", customer_id) if customer_id else None

    post_delivery_activity = False
    customer_review_left   = False
    prior_disputes_count   = 0

    if comms:
        prior_disputes_count = len(comms.get("prior_disputes", []))
        delivery_ts = order.get("delivery_timestamp")
        for event in comms.get("events", []):
            if delivery_ts and event["timestamp"] > delivery_ts:
                post_delivery_activity = True
            if event["event"] == "review_submitted":
                customer_review_left = True

    state.evidence = {
        "transaction_found":              txn is not None,
        "auth_method":                    txn.get("auth_method") if txn else None,
        "transaction_timestamp":          txn.get("timestamp") if txn else None,
        "delivery_confirmed":             order.get("delivery_status") == "DELIVERED",
        "delivery_timestamp":             order.get("delivery_timestamp"),
        "delivery_proof":                 order.get("delivery_proof"),
        "tracking_id":                    order.get("tracking_id"),
        "post_delivery_activity":         post_delivery_activity,
        "customer_review_left":           customer_review_left,
        "prior_disputes_count":           prior_disputes_count,
        "support_contacted_before_dispute": any(
            e["event"] == "support_contacted"
            for e in (comms.get("events", []) if comms else [])
        ),
    }

    return state

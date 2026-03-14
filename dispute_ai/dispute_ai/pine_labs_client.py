import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "mock_data"
_MOCK = os.getenv("PINE_LABS_MOCK", "true").lower() == "true"


def _load(filename: str) -> list:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _find(records: list, key: str, value: str) -> dict | None:
    return next((r for r in records if r.get(key) == value), None)


def get_order(order_id: str) -> dict:
    """
    Returns Pine Labs order data for the given order_id.
    In mock mode, looks up transactions.json + deliveries.json by transaction_id.
    In live mode, calls GET /api/checkout/v1/orders/{order_id} via httpx.
    """
    if _MOCK:
        return _get_order_mock(order_id)
    return _get_order_live(order_id)


def _get_order_mock(order_id: str) -> dict:
    transactions = _load("transactions.json")
    deliveries = _load("deliveries.json")

    txn = _find(transactions, "transaction_id", order_id)
    delivery = _find(deliveries, "transaction_id", order_id)

    return {
        "order_id": order_id,
        "approval_code": txn.get("auth_method", "") if txn else "",
        "rrn": txn.get("device_id", "") if txn else "",
        "acquirer_ref": f"ACQ-{order_id}" if txn else "",
        "card_network": _infer_card_network(txn),
        "payment_method": _infer_payment_method(txn),
        "delivery_status": delivery.get("delivery_status") if delivery else None,
        "delivery_timestamp": delivery.get("delivery_timestamp") if delivery else None,
        "delivery_proof": delivery.get("delivery_proof") if delivery else None,
        "tracking_id": delivery.get("tracking_id") if delivery else None,
    }


def _infer_card_network(txn: dict | None) -> str:
    if not txn:
        return ""
    method = txn.get("auth_method", "")
    if "UPI" in method:
        return "RUPAY"
    return ""


def _infer_payment_method(txn: dict | None) -> str:
    if not txn:
        return ""
    method = txn.get("auth_method", "")
    if "UPI" in method:
        return "UPI"
    if "OTP" in method or "PIN" in method:
        return "CARD"
    return "NETBANKING"


def _get_order_live(order_id: str) -> dict:
    import httpx

    base_url = os.getenv("PINE_LABS_BASE_URL", "https://api.pinelabs.com")
    client_id = os.getenv("PINE_LABS_CLIENT_ID", "")
    client_secret = os.getenv("PINE_LABS_CLIENT_SECRET", "")

    resp = httpx.get(
        f"{base_url}/api/checkout/v1/orders/{order_id}",
        headers={
            "X-Client-Id": client_id,
            "X-Client-Secret": client_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    return {
        "order_id": order_id,
        "approval_code": data.get("approval_code", ""),
        "rrn": data.get("rrn", ""),
        "acquirer_ref": data.get("acquirer_ref", ""),
        "card_network": data.get("card_network", ""),
        "payment_method": data.get("payment_method", ""),
        "delivery_status": data.get("delivery_status"),
        "delivery_proof": data.get("delivery_proof"),
        "tracking_id": data.get("tracking_id"),
    }

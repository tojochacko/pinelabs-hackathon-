import os

import httpx

_CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(phone: str, message: str, api_key: str = "") -> None:
    key = api_key or os.getenv("CALLMEBOT_API_KEY", "")
    if not key or not phone:
        return
    try:
        httpx.get(
            _CALLMEBOT_URL,
            params={"phone": phone, "text": message, "apikey": key},
            timeout=10,
        )
    except Exception:
        pass


def notify_strategy_decision(state) -> None:
    phone = getattr(state, "merchant_phone", "")
    if not phone:
        return
    lines = [
        "DisputeAI Alert",
        f"Case: {state.case_id}",
        f"Order: {state.order_id or state.transaction_id}",
        f"Amount: {state.dispute_amount} {state.currency}",
        f"Decision: {state.pipeline_decision}",
        f"Win Probability: {state.win_probability}%",
        f"Recommendation: {state.recommendation}",
        f"Dispute Type: {state.dispute_type}",
        f"Argument Strength: {state.argument_strength}",
    ]
    send_whatsapp(
        phone,
        "\n".join(lines),
        api_key=getattr(state, "merchant_whatsapp_key", ""),
    )

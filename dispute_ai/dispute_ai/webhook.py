import hashlib
import hmac
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from rich.console import Console

load_dotenv()

from dispute_ai import db, pine_labs_client
from dispute_ai.pipeline import run_webhook_pipeline_async
from dispute_ai.state import CaseState

app = FastAPI(title="DisputeAI Webhook Service")
console = Console()

_WEBHOOK_SECRET = os.getenv("PINE_LABS_WEBHOOK_SECRET", "")


class DisputePayload(BaseModel):
    order_id: str = "TXN-UL-8821993"
    merchant_id: str = "MERCH-URBAN-LADDER"
    amount: float = 4500.0
    currency: str = "INR"
    reason: str = "Customer claims item was never delivered."
    chargeback_code: str = "RBI-CB-4855"
    customer_name: str = "Priya Mehta"


@app.post("/webhook/pine-labs")
async def pine_labs_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Pine-Signature", "")

    if _WEBHOOK_SECRET:
        expected = hmac.new(
            _WEBHOOK_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    import json
    payload = DisputePayload(**json.loads(raw_body))
    background_tasks.add_task(_run_pipeline_bg, payload)
    return JSONResponse({"status": "accepted"})


@app.post("/simulate/dispute")
async def simulate_dispute(payload: DisputePayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_pipeline_bg, payload)
    return JSONResponse({"status": "accepted", "order_id": payload.order_id})


async def _run_pipeline_bg(payload: DisputePayload) -> None:
    case_id = f"CASE-{payload.order_id}-{uuid.uuid4().hex[:6].upper()}"

    state = CaseState(
        case_id=case_id,
        order_id=payload.order_id,
        transaction_id=payload.order_id,
        merchant_id=payload.merchant_id,
        dispute_amount=payload.amount,
        currency=payload.currency,
        chargeback_reason=payload.reason,
        chargeback_code=payload.chargeback_code,
        customer_name=payload.customer_name,
        filing_deadline=(datetime.now().strftime("%Y-%m-%d")),
    )

    order = pine_labs_client.get_order(payload.order_id)
    state.approval_code = order.get("approval_code", "")
    state.rrn = order.get("rrn", "")
    state.acquirer_ref = order.get("acquirer_ref", "")
    state.card_network = order.get("card_network", "")
    state.payment_method = order.get("payment_method", "")

    # Insert stub row first so audit_events FK is satisfied
    _try_db_upsert(state)

    _try_log(case_id, "pipeline_started", {
        "order_id": payload.order_id,
        "merchant_id": payload.merchant_id,
        "amount": payload.amount,
    })

    def on_step(agent_name: str, s: CaseState) -> None:
        _try_log(case_id, f"agent_completed:{agent_name}", {
            "dispute_type": s.dispute_type,
            "argument_strength": s.argument_strength,
            "win_probability": s.win_probability,
            "pipeline_decision": s.pipeline_decision,
        })

    try:
        state = await run_webhook_pipeline_async(state, on_step=on_step)
    except Exception as exc:
        console.print(f"[red]Pipeline error for {case_id}: {exc}[/red]")
        _try_log(case_id, "pipeline_error", {"error": str(exc)})
        return

    _try_db_upsert(state)

    console.print(f"\n[bold green]DisputeAI — {case_id}[/bold green]")
    console.print(f"  Dispute type    : {state.dispute_type}")
    console.print(f"  Win probability : {state.win_probability}%")
    console.print(f"  Decision        : {state.pipeline_decision}")
    console.print(f"  Recommendation  : {state.recommendation}")
    console.print(f"  Urgency         : {state.urgency_level} ({state.days_remaining}d remaining)")


def _try_log(case_id: str, event: str, payload: dict) -> None:
    try:
        db.log_event(case_id, event, payload)
    except Exception as exc:
        console.print(f"[yellow]DB log skipped ({event}): {exc}[/yellow]")


def _try_db_upsert(state: CaseState) -> None:
    try:
        db.upsert_dispute(state)
    except Exception as exc:
        console.print(f"[yellow]DB upsert skipped: {exc}[/yellow]")

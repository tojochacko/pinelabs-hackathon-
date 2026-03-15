import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from rich.console import Console

load_dotenv()

from dispute_ai import db, pine_labs_client
from dispute_ai.notifier import notify_strategy_decision
from dispute_ai.pipeline import run_webhook_pipeline_async
from dispute_ai.state import CaseState

app = FastAPI(title="DisputeAI Webhook Service")
console = Console()

_WEBHOOK_SECRET = os.getenv("PINE_LABS_WEBHOOK_SECRET", "")
_REFUND_EVENTS = {"REFUND_PROCESSED", "REFUND_FAILED", "REFUND_INITIATED"}


# ── Pine Labs webhook payload models ──────────────────────────────────────────

class _Amount(BaseModel):
    value: int = 0       # Pine Labs sends amounts in paise (1 INR = 100 paise)
    currency: str = "INR"


class _RefundItem(BaseModel):
    id: str = ""
    merchant_refund_reference: str = ""
    status: str = ""
    refund_amount: Optional[_Amount] = None
    reason: str = ""


class _WebhookData(BaseModel):
    order_id: str = ""
    merchant_id: str = ""
    merchant_order_reference: str = ""
    status: str = ""
    order_amount: Optional[_Amount] = None
    refunds: List[_RefundItem] = []


class PineLabsWebhookEvent(BaseModel):
    event_type: str
    data: _WebhookData


# ── Internal dispute payload (used by simulate endpoint) ──────────────────────

class DisputePayload(BaseModel):
    order_id: str = "TXN-UL-8821993"
    merchant_id: str = "MERCH-URBAN-LADDER"
    amount: float = 4500.0
    currency: str = "INR"
    reason: str = "Customer claims item was never delivered."
    chargeback_code: str = "RBI-CB-4855"
    customer_name: str = "Priya Mehta"
    merchant_phone: str = ""         # E.164, e.g. +919876543210
    merchant_whatsapp_key: str = ""  # CallMeBot API key for that phone


def _verify_signature(raw_body: bytes, headers) -> None:
    """Verify Pine Labs HMAC-SHA256 webhook signature.

    Message = "{webhook-id}.{webhook-timestamp}.{raw_body}"
    Key     = base64-decoded PINE_LABS_WEBHOOK_SECRET
    Header  = "webhook-signature: v1,<base64(HMAC-SHA256)>"
    """
    webhook_id = headers.get("webhook-id", "")
    webhook_timestamp = headers.get("webhook-timestamp", "")
    signature_header = headers.get("webhook-signature", "")

    message = f"{webhook_id}.{webhook_timestamp}.{raw_body.decode()}"
    secret_bytes = base64.b64decode(_WEBHOOK_SECRET)
    expected = base64.b64encode(
        hmac.new(secret_bytes, message.encode(), hashlib.sha256).digest()
    ).decode()

    # Header format: "v1,<signature>"
    provided = signature_header.split(",", 1)[-1] if "," in signature_header else signature_header
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _map_event_to_payload(event: PineLabsWebhookEvent) -> DisputePayload:
    """Map a Pine Labs refund webhook event to the internal DisputePayload."""
    data = event.data
    refund = data.refunds[0] if data.refunds else None

    if refund and refund.refund_amount:
        amount = refund.refund_amount.value / 100  # paise → rupees
        currency = refund.refund_amount.currency
        reason = refund.reason or f"Refund {event.event_type} on order {data.order_id}"
    elif data.order_amount:
        amount = data.order_amount.value / 100
        currency = data.order_amount.currency
        reason = f"Refund {event.event_type} on order {data.order_id}"
    else:
        amount = 0.0
        currency = "INR"
        reason = f"Refund {event.event_type} on order {data.order_id}"

    return DisputePayload(
        order_id=data.order_id or data.merchant_order_reference,
        merchant_id=data.merchant_id,
        amount=amount,
        currency=currency,
        reason=reason,
        chargeback_code="",
        customer_name="",
        merchant_phone=os.getenv("MERCHANT_PHONE", ""),
        merchant_whatsapp_key=os.getenv("MERCHANT_WHATSAPP_KEY", ""),
    )


@app.post("/webhook/pine-labs")
async def pine_labs_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()

    if _WEBHOOK_SECRET:
        _verify_signature(raw_body, request.headers)

    event = PineLabsWebhookEvent(**json.loads(raw_body))

    if event.event_type not in _REFUND_EVENTS:
        return JSONResponse({"status": "ignored", "event_type": event.event_type})

    payload = _map_event_to_payload(event)
    background_tasks.add_task(_run_pipeline_bg, payload)
    return JSONResponse({"status": "accepted", "event_type": event.event_type})


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
        merchant_phone=payload.merchant_phone,
        merchant_whatsapp_key=payload.merchant_whatsapp_key,
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
        if agent_name == "StrategyAgent":
            _try_notify(s)

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


def _try_notify(state: CaseState) -> None:
    try:
        notify_strategy_decision(state)
    except Exception as exc:
        console.print(f"[yellow]WhatsApp notification skipped: {exc}[/yellow]")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(_DASHBOARD_HTML)


@app.get("/api/disputes")
async def api_disputes(decision: str = None):
    try:
        return JSONResponse(db.get_disputes(decision))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DisputeAI — Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">DisputeAI</h1>
        <p class="text-gray-500 text-sm mt-0.5">Merchant Dispute Dashboard</p>
      </div>
      <button onclick="load()" class="text-sm text-blue-600 hover:underline">Refresh</button>
    </div>

    <div class="grid grid-cols-3 gap-4 mb-8" id="summary">
      <div class="bg-white rounded-lg shadow-sm p-6 h-24 animate-pulse"></div>
      <div class="bg-white rounded-lg shadow-sm p-6 h-24 animate-pulse"></div>
      <div class="bg-white rounded-lg shadow-sm p-6 h-24 animate-pulse"></div>
    </div>

    <div class="flex gap-2 mb-4">
      <button id="tab-ALL" onclick="setFilter('ALL')"
        class="px-4 py-1.5 rounded text-sm font-medium bg-blue-600 text-white">All</button>
      <button id="tab-FIGHT" onclick="setFilter('FIGHT')"
        class="px-4 py-1.5 rounded text-sm font-medium bg-white border text-gray-700 hover:bg-gray-50">FIGHT</button>
      <button id="tab-ACCEPT" onclick="setFilter('ACCEPT')"
        class="px-4 py-1.5 rounded text-sm font-medium bg-white border text-gray-700 hover:bg-gray-50">ACCEPT</button>
    </div>

    <div class="bg-white rounded-lg shadow-sm overflow-hidden">
      <table class="min-w-full text-sm divide-y divide-gray-100">
        <thead class="bg-gray-50 text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3 text-left">Case</th>
            <th class="px-4 py-3 text-left">Merchant</th>
            <th class="px-4 py-3 text-left">Amount</th>
            <th class="px-4 py-3 text-left">Type</th>
            <th class="px-4 py-3 text-left">Win %</th>
            <th class="px-4 py-3 text-left">Decision</th>
            <th class="px-4 py-3 text-left">Urgency</th>
            <th class="px-4 py-3 text-left">Date</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody id="tbody" class="divide-y divide-gray-50">
          <tr><td colspan="9" class="px-4 py-10 text-center text-gray-400">Loading\u2026</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div id="modal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
       onclick="if(event.target===this)closeModal()">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between p-6 border-b">
        <h2 class="font-bold text-lg" id="modal-title"></h2>
        <button onclick="closeModal()" class="text-gray-400 hover:text-gray-700 text-2xl leading-none">&times;</button>
      </div>
      <div id="modal-body" class="p-6"></div>
    </div>
  </div>

  <script>
    let disputes = [];
    let filter = 'ALL';

    async function load() {
      try {
        const r = await fetch('/api/disputes');
        const body = await r.json();
        if (!r.ok) {
          throw new Error(body.detail || r.statusText);
        }
        disputes = body;
        renderSummary();
        renderTable();
      } catch(e) {
        document.getElementById('tbody').innerHTML =
          `<tr><td colspan="9" class="px-4 py-10 text-center text-red-500">Failed to load data: ${e.message}</td></tr>`;
      }
    }

    function renderSummary() {
      const total = disputes.length;
      const fight = disputes.filter(d => d.pipeline_decision === 'FIGHT').length;
      const accept = disputes.filter(d => d.pipeline_decision === 'ACCEPT').length;
      const amt = disputes.reduce((s, d) => s + (d.dispute_amount || 0), 0);
      document.getElementById('summary').innerHTML = `
        <div class="bg-white rounded-lg shadow-sm p-6">
          <div class="text-3xl font-bold">${total}</div>
          <div class="text-gray-500 text-sm mt-1">Total Disputes</div>
          <div class="text-xs text-gray-400">INR ${amt.toLocaleString('en-IN')}</div>
        </div>
        <div class="bg-white rounded-lg shadow-sm p-6 border-l-4 border-red-500">
          <div class="text-3xl font-bold text-red-600">${fight}</div>
          <div class="text-gray-500 text-sm mt-1">FIGHT</div>
          <div class="text-xs text-gray-400">File dispute</div>
        </div>
        <div class="bg-white rounded-lg shadow-sm p-6 border-l-4 border-green-500">
          <div class="text-3xl font-bold text-green-600">${accept}</div>
          <div class="text-gray-500 text-sm mt-1">ACCEPT</div>
          <div class="text-xs text-gray-400">Settle with customer</div>
        </div>`;
    }

    function renderTable() {
      const data = filter === 'ALL' ? disputes : disputes.filter(d => d.pipeline_decision === filter);
      if (!data.length) {
        document.getElementById('tbody').innerHTML =
          '<tr><td colspan="9" class="px-4 py-10 text-center text-gray-400">No disputes found</td></tr>';
        return;
      }
      document.getElementById('tbody').innerHTML = data.map(d => {
        const pct = d.win_probability || 0;
        const barColor = pct >= 60 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';
        const decBadge = d.pipeline_decision === 'FIGHT'
          ? 'bg-red-100 text-red-700' : d.pipeline_decision === 'ACCEPT'
          ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600';
        const urgBadge = d.urgency_level === 'CRITICAL' ? 'bg-red-100 text-red-700'
          : d.urgency_level === 'URGENT' ? 'bg-orange-100 text-orange-700'
          : d.urgency_level === 'NORMAL' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500';
        const date = d.created_at ? new Date(d.created_at).toLocaleDateString('en-IN') : '-';
        return `<tr class="hover:bg-gray-50">
          <td class="px-4 py-3 font-mono text-xs text-blue-600 whitespace-nowrap">${d.case_id || '-'}</td>
          <td class="px-4 py-3 text-gray-700">${d.merchant_id || '-'}</td>
          <td class="px-4 py-3 font-medium whitespace-nowrap">${d.currency || 'INR'} ${(d.dispute_amount||0).toLocaleString('en-IN')}</td>
          <td class="px-4 py-3 text-gray-600 text-xs">${d.dispute_type || '-'}</td>
          <td class="px-4 py-3">
            <div class="flex items-center gap-1.5">
              <div class="w-12 bg-gray-200 rounded-full h-1.5 flex-shrink-0">
                <div class="h-1.5 rounded-full ${barColor}" style="width:${pct}%"></div>
              </div>
              <span class="text-xs">${pct}%</span>
            </div>
          </td>
          <td class="px-4 py-3">
            <span class="px-2 py-0.5 rounded-full text-xs font-semibold ${decBadge}">${d.pipeline_decision || 'PENDING'}</span>
          </td>
          <td class="px-4 py-3">
            <span class="px-2 py-0.5 rounded text-xs ${urgBadge}">${d.urgency_level || '-'}</span>
          </td>
          <td class="px-4 py-3 text-xs text-gray-500">${date}</td>
          <td class="px-4 py-3">
            <button onclick="showDetail('${d.case_id}')" class="text-xs text-blue-600 hover:underline">Details</button>
          </td>
        </tr>`;
      }).join('');
    }

    function setFilter(f) {
      filter = f;
      ['ALL','FIGHT','ACCEPT'].forEach(k => {
        document.getElementById('tab-'+k).className = k === f
          ? 'px-4 py-1.5 rounded text-sm font-medium bg-blue-600 text-white'
          : 'px-4 py-1.5 rounded text-sm font-medium bg-white border text-gray-700 hover:bg-gray-50';
      });
      renderTable();
    }

    function showDetail(caseId) {
      const d = disputes.find(x => x.case_id === caseId);
      if (!d) return;
      document.getElementById('modal-title').textContent = d.case_id;
      document.getElementById('modal-body').innerHTML = `
        <div class="grid grid-cols-2 gap-4 text-sm mb-4">
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Merchant</div><div class="font-medium">${d.merchant_id||'-'}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Order ID</div><div class="font-mono text-xs">${d.order_id||'-'}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Amount</div><div class="font-medium">${d.currency||'INR'} ${(d.dispute_amount||0).toLocaleString('en-IN')}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Dispute Type</div><div>${d.dispute_type||'-'}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Decision</div>
            <span class="px-2 py-0.5 rounded-full text-xs font-semibold ${d.pipeline_decision==='FIGHT'?'bg-red-100 text-red-700':'bg-green-100 text-green-700'}">${d.pipeline_decision||'-'}</span>
          </div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Win Probability</div><div class="font-medium">${d.win_probability||0}%</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Argument Strength</div><div class="capitalize">${d.argument_strength||'-'}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Urgency</div><div>${d.urgency_level||'-'} \u00b7 ${d.days_remaining||0} days left</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Filing Deadline</div><div>${d.filing_deadline||'-'}</div></div>
          <div><div class="text-xs uppercase text-gray-400 mb-0.5">Recommendation</div><div>${d.recommendation||'-'}</div></div>
        </div>
        ${d.dispute_letter ? `
        <div>
          <div class="text-xs uppercase text-gray-400 mb-2">Dispute Letter</div>
          <pre class="bg-gray-50 rounded p-3 text-xs whitespace-pre-wrap font-sans text-gray-700 max-h-56 overflow-y-auto border">${d.dispute_letter}</pre>
        </div>` : ''}`;
      document.getElementById('modal').classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('modal').classList.add('hidden');
    }

    load();
    setInterval(load, 30000);
  </script>
</body></html>"""

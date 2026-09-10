from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from ap.services.approval import evaluate_invoice, resolve_exception, sync_approval_workflow, advance_workflow
from ap.services.invoice_feed import simulate_new_invoice
from ap.store import INVOICES, INVOICE_FEED_EVENTS
from ap.routers.auth import get_user_from_header
from wc.cash_events import ensure_ap_wc_fields

router = APIRouter()

class ResolveRequest(BaseModel):
    action: str
    note: str | None = None
    owner: str | None = None

class InvoicePayload(BaseModel):
    data: dict[str, Any]

class SimulateInvoiceRequest(BaseModel):
    scenario: str | None = None
    count: int = 1

class AdvanceWorkflowRequest(BaseModel):
    role: str | None = None
    decision: str = "Approved"
    note: str | None = None


@router.get("/feed/events")
def feed_events():
    return INVOICE_FEED_EVENTS

@router.post("/simulate-new")
def simulate_new(payload: SimulateInvoiceRequest | None = None):
    scenario = payload.scenario if payload else None
    return simulate_new_invoice(scenario)

@router.post("/simulate-batch")
def simulate_batch(payload: SimulateInvoiceRequest):
    count = max(1, min(payload.count or 1, 10))
    return [simulate_new_invoice(payload.scenario) for _ in range(count)]

@router.get("")
def list_invoices(status: str | None = None, risk: str | None = None, q: str | None = None):
    for invoice_id in list(INVOICES.keys()):
        evaluate_invoice(invoice_id)
        sync_approval_workflow(INVOICES[invoice_id])
        ensure_ap_wc_fields(INVOICES[invoice_id])
    items = list(INVOICES.values())
    if status and status != "All":
        items = [i for i in items if i.get("status") == status]
    if risk and risk != "All":
        items = [i for i in items if i.get("risk") == risk]
    if q:
        query = q.lower()
        items = [i for i in items if query in str(i).lower()]
    return items

@router.get("/{invoice_id}")
def get_invoice(invoice_id: str):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    evaluate_invoice(invoice_id)
    inv = sync_approval_workflow(INVOICES[invoice_id])
    return ensure_ap_wc_fields(inv)

@router.post("/{invoice_id}/workflow/advance")
def advance(invoice_id: str, payload: AdvanceWorkflowRequest, authorization: str | None = Header(default=None)):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    user = get_user_from_header(authorization)
    evaluate_invoice(invoice_id)
    invoice = INVOICES[invoice_id]
    required_role = invoice.get("currentApprovalRole")
    if not required_role:
        from ap.services.approval import sync_approval_workflow
        required_role = sync_approval_workflow(invoice).get("currentApprovalRole")
    if required_role not in ["Completed", user.get("approvalRole")]:
        raise HTTPException(status_code=403, detail=f"Only {required_role} can approve this stage. You are signed in as {user.get('approvalRole')}.")
    try:
        return advance_workflow(invoice_id, user.get("approvalRole"), payload.decision, payload.note or f"Approved by {user.get('name')} ({user.get('approvalRole')}).")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.post("/{invoice_id}/match")
def match_invoice(invoice_id: str):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return evaluate_invoice(invoice_id)

@router.post("/{invoice_id}/approve")
def approve_invoice(invoice_id: str, authorization: str | None = Header(default=None)):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    user = get_user_from_header(authorization)
    result = evaluate_invoice(invoice_id)
    invoice = INVOICES[invoice_id]
    if invoice.get("exception") and invoice["exception"].get("state") != "Resolved":
        raise HTTPException(status_code=409, detail="Invoice has unresolved exception and cannot be approved.")
    try:
        current_role = invoice.get("currentApprovalRole")
        if current_role not in ["Completed", user.get("approvalRole")]:
            raise HTTPException(status_code=403, detail=f"Only {current_role} can approve this stage. You are signed in as {user.get('approvalRole')}.")
        advanced = advance_workflow(invoice_id, user.get("approvalRole"), "Approved", f"Approved by {user.get('name')} ({user.get('approvalRole')}).")
        invoice = advanced["invoice"]
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"invoice": invoice, "checks": result["checks"]}

@router.post("/{invoice_id}/exception/resolve")
def resolve(invoice_id: str, payload: ResolveRequest, authorization: str | None = Header(default=None)):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    user = get_user_from_header(authorization)
    allowed_roles = ["AP Analyst", "Finance Manager", "Tax Reviewer", "Controller"]
    if user.get("approvalRole") not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only AP Analyst, Finance Manager, Tax Reviewer, or Controller can resolve/override exceptions in this demo.")
    owner = payload.owner or user.get("name")
    return resolve_exception(invoice_id, payload.action, payload.note or f"Action by {user.get('name')} ({user.get('approvalRole')}).", owner)

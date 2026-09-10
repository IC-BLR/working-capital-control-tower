from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ap.services.approval import evaluate_invoice
from ap.store import INVOICES, REGULATIONS

router = APIRouter()

@router.get("")
def list_regulations(q: str | None = None):
    items = list(REGULATIONS.values())
    if q:
        items = [r for r in items if q.lower() in str(r).lower()]
    return items

@router.get("/{regulation_id}")
def get_regulation(regulation_id: str):
    if regulation_id not in REGULATIONS:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return REGULATIONS[regulation_id]

@router.post("/{regulation_id}/apply")
def apply_regulation(regulation_id: str):
    if regulation_id not in REGULATIONS:
        raise HTTPException(status_code=404, detail="Regulation not found")
    for invoice in INVOICES.values():
        if invoice.get("amount", 0) >= REGULATIONS[regulation_id].get("approvalThreshold", 0):
            invoice["regulationId"] = regulation_id
    return [evaluate_invoice(invoice_id) for invoice_id in INVOICES]

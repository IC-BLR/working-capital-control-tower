from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ap.services.approval import evaluate_invoice
from ap.store import INVOICES, PURCHASE_ORDERS

router = APIRouter()

class PoPayload(BaseModel):
    data: dict[str, Any]

@router.get("")
def list_purchase_orders(q: str | None = None):
    items = list(PURCHASE_ORDERS.values())
    if q:
        items = [p for p in items if q.lower() in str(p).lower()]
    return items

@router.get("/{po_number}")
def get_purchase_order(po_number: str):
    if po_number not in PURCHASE_ORDERS:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return PURCHASE_ORDERS[po_number]

@router.post("")
def upsert_purchase_order(payload: PoPayload):
    data = payload.data
    po_number = data.get("poNumber")
    if not po_number:
        raise HTTPException(status_code=400, detail="poNumber is required")
    PURCHASE_ORDERS[po_number] = data
    return PURCHASE_ORDERS[po_number]

@router.post("/{po_number}/rematch-invoices")
def rematch_po(po_number: str):
    if po_number not in PURCHASE_ORDERS:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return [evaluate_invoice(invoice_id) for invoice_id, invoice in INVOICES.items() if invoice.get("poNumber") == po_number]

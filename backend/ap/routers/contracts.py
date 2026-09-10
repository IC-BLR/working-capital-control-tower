from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ap.services.approval import evaluate_invoice
from ap.store import CONTRACTS, INVOICES

router = APIRouter()

class ContractPayload(BaseModel):
    data: dict[str, Any]

@router.get("")
def list_contracts(q: str | None = None):
    items = list(CONTRACTS.values())
    if q:
        items = [c for c in items if q.lower() in str(c).lower()]
    return items

@router.get("/{contract_id}")
def get_contract(contract_id: str):
    if contract_id not in CONTRACTS:
        raise HTTPException(status_code=404, detail="Contract not found")
    return CONTRACTS[contract_id]

@router.post("")
def upsert_contract(payload: ContractPayload):
    data = payload.data
    contract_id = data.get("id") or data.get("contractId")
    if not contract_id:
        raise HTTPException(status_code=400, detail="id or contractId is required")
    data["id"] = contract_id
    CONTRACTS[contract_id] = data
    return CONTRACTS[contract_id]

@router.post("/{contract_id}/rematch-invoices")
def rematch_contract(contract_id: str):
    if contract_id not in CONTRACTS:
        raise HTTPException(status_code=404, detail="Contract not found")
    return [evaluate_invoice(invoice_id) for invoice_id, invoice in INVOICES.items() if invoice.get("contractId") == contract_id]

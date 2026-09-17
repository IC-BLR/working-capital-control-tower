"""Working Capital API routes — /api/wc/*"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ap.store import INVOICES
from ar.server import get_duckdb
from wc.calendar_service import build_calendar
from wc.cash_events import ensure_ap_wc_fields
from wc.metrics import compute_wc_metrics
from wc.store import COLLECT_PRIORITIES

router = APIRouter()


class HoldRequest(BaseModel):
    hold: bool = True
    note: str | None = None


class PlannedPayRequest(BaseModel):
    plannedPayDate: str


class CollectPriorityRequest(BaseModel):
    partner_code: str | None = None
    invoice_number: str | None = None
    note: str | None = None
    active: bool = True


@router.get("/calendar")
def calendar(
    days: int = Query(30, ge=1, le=365),
    scenario: str | None = Query(None),
    defer_ap_days: int = Query(0, ge=0, le=90),
    period_days: int = Query(90, ge=7, le=365),
):
    """Dated AR inflows + AP outflows → net working-capital calendar (+ metrics & alerts)."""
    # Map friendly WC scenario names onto AR forecast scenarios
    ar_scenario = scenario
    if scenario == "ar_delay_7":
        ar_scenario = "payment_delay_7"
    elif scenario == "ar_delay_14":
        ar_scenario = "payment_delay_14"
    elif scenario == "ar_delay_30":
        ar_scenario = "payment_delay_30"
    elif scenario in ("defer_ap_7", "defer_ap_14"):
        # handled via defer_ap_days; keep AR baseline
        ar_scenario = "baseline"
        if defer_ap_days == 0:
            defer_ap_days = 7 if scenario == "defer_ap_7" else 14

    return build_calendar(
        days=days,
        scenario=ar_scenario,
        defer_ap_days=defer_ap_days,
        period_days=period_days,
    )


@router.get("/metrics")
def metrics(period_days: int = Query(90, ge=7, le=365)):
    """DSO / DPO / CCC (DIO N/A) for the rolling period."""
    try:
        db = get_duckdb()
    except Exception:
        db = None
    return compute_wc_metrics(
        db,
        ap_invoices=list(INVOICES.values()),
        period_days=period_days,
    )


@router.get("/alerts")
def alerts(
    days: int = Query(30, ge=1, le=365),
    scenario: str | None = Query(None),
    defer_ap_days: int = Query(0, ge=0, le=90),
    period_days: int = Query(90, ge=7, le=365),
):
    """Cash alerts derived from the current calendar snapshot."""
    payload = calendar(
        days=days,
        scenario=scenario,
        defer_ap_days=defer_ap_days,
        period_days=period_days,
    )
    return {
        "as_of": payload.get("as_of"),
        "horizon_days": payload.get("horizon_days"),
        "scenario": payload.get("scenario"),
        "alerts": payload.get("alerts") or [],
    }


@router.post("/ap/{invoice_id}/hold")
def set_hold(invoice_id: str, payload: HoldRequest):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = ensure_ap_wc_fields(INVOICES[invoice_id])
    inv["cashHold"] = bool(payload.hold)
    trail = inv.setdefault("approvalTrail", [])
    action = "Cash hold applied" if payload.hold else "Cash hold released"
    note = payload.note or action
    trail.append(f"{action}: {note}")
    return {"invoice": inv}


@router.patch("/ap/{invoice_id}/planned-pay-date")
def set_planned_pay(invoice_id: str, payload: PlannedPayRequest):
    if invoice_id not in INVOICES:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv = ensure_ap_wc_fields(INVOICES[invoice_id])
    try:
        datetime.fromisoformat(payload.plannedPayDate[:10])
    except ValueError:
        raise HTTPException(status_code=400, detail="plannedPayDate must be YYYY-MM-DD")
    inv["plannedPayDate"] = payload.plannedPayDate[:10]
    inv.setdefault("approvalTrail", []).append(f"Planned pay date set to {inv['plannedPayDate']}")
    return {"invoice": inv}


@router.post("/collect-priority")
def collect_priority(payload: CollectPriorityRequest):
    if not payload.partner_code and not payload.invoice_number:
        raise HTTPException(status_code=400, detail="partner_code or invoice_number required")
    key = (
        f"ar:{payload.invoice_number}"
        if payload.invoice_number
        else payload.partner_code
    )
    if not payload.active:
        COLLECT_PRIORITIES.pop(key, None)
        if payload.partner_code:
            COLLECT_PRIORITIES.pop(payload.partner_code, None)
        return {"status": "cleared", "key": key}
    COLLECT_PRIORITIES[key] = {
        "partner_code": payload.partner_code,
        "invoice_number": payload.invoice_number,
        "note": payload.note or "Prioritized for collection from WC calendar",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    return {"status": "active", "key": key, "priority": COLLECT_PRIORITIES[key]}


@router.get("/collect-priority")
def list_collect_priorities():
    return list(COLLECT_PRIORITIES.values())

"""Map AR forecast + AP invoices into canonical CashEvent records."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def ensure_ap_wc_fields(invoice: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Ensure plannedPayDate and cashHold exist on an AP invoice (mutates)."""
    today = today or date.today()
    exc = invoice.get("exception")
    unresolved = bool(exc and exc.get("state") not in (None, "Resolved"))
    status = invoice.get("status") or ""

    if "cashHold" not in invoice or invoice.get("cashHold") is None:
        invoice["cashHold"] = unresolved or status == "Exception"
    elif unresolved:
        # Open exception always forces hold for WC purposes
        invoice["cashHold"] = True

    if not invoice.get("plannedPayDate"):
        due = _parse_date(invoice.get("dueDate"))
        if due and due >= today:
            invoice["plannedPayDate"] = due.isoformat()
        else:
            # Stagger historical demo dues into the near horizon so calendar is useful
            offset = (abs(hash(invoice.get("id") or "x")) % 25) + 1
            invoice["plannedPayDate"] = (today + timedelta(days=offset)).isoformat()

    return invoice


def ap_certainty(invoice: dict[str, Any]) -> str | None:
    """Map AP invoice to WC certainty; None = exclude from cash calendar events."""
    if invoice.get("cashHold"):
        return "held"
    status = invoice.get("status") or ""
    if status in ("Payment Ready", "Approved"):
        return "obligated"
    if status in ("Pending Approval", "Regulation Review"):
        return "pipeline"
    if status == "Exception":
        return "held"
    return None


def ar_events_from_forecast(forecast: dict[str, Any], collect_priorities: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    collect_priorities = collect_priorities or {}
    events: list[dict[str, Any]] = []
    for raw in forecast.get("cashflow_events") or []:
        cash_date = raw.get("forecast_date")
        amount = float(raw.get("forecast_amount") or 0)
        if not cash_date or amount <= 0:
            continue
        partner_code = raw.get("partner_code") or ""
        invoice_number = raw.get("invoice_number") or ""
        key = f"ar:{invoice_number}" if invoice_number else f"partner:{partner_code}"
        priority = collect_priorities.get(key) or collect_priorities.get(partner_code)
        events.append(
            {
                "event_id": f"ar-{invoice_number or partner_code}-{cash_date}",
                "direction": "inflow",
                "amount": amount,
                "currency": "INR",
                "cash_date": str(cash_date)[:10],
                "certainty": "forecast",
                "counterparty_type": "customer",
                "counterparty_id": partner_code,
                "counterparty_name": raw.get("partner_name") or partner_code,
                "source_system": "ar",
                "source_ref": invoice_number,
                "status": "Expected receipt",
                "risk": "High" if priority else None,
                "collect_priority": bool(priority),
                "links": {
                    "ui_path": f"/ar/partners/{partner_code}/details"
                    if partner_code
                    else "/ar/forecast"
                },
            }
        )
    return events


def ap_events_from_invoices(invoices: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    events: list[dict[str, Any]] = []
    for inv in invoices:
        ensure_ap_wc_fields(inv, today)
        certainty = ap_certainty(inv)
        if not certainty:
            continue
        amount = float(inv.get("amount") or 0)
        if amount <= 0:
            continue
        cash_date = inv.get("plannedPayDate") or inv.get("dueDate")
        cash_date = str(cash_date)[:10] if cash_date else today.isoformat()
        inv_id = inv.get("id") or ""
        events.append(
            {
                "event_id": f"ap-{inv_id}-{cash_date}",
                "direction": "outflow",
                "amount": amount,
                "currency": inv.get("currency") or "INR",
                "cash_date": cash_date,
                "certainty": certainty,
                "counterparty_type": "vendor",
                "counterparty_id": inv.get("vendor") or "",
                "counterparty_name": inv.get("vendor") or "",
                "source_system": "ap",
                "source_ref": inv_id,
                "status": inv.get("status"),
                "risk": inv.get("risk"),
                "cash_hold": bool(inv.get("cashHold")),
                "links": {"ui_path": f"/ap?invoice={inv_id}"},
            }
        )
    return events

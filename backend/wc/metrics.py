"""Working Capital ratio metrics — DSO, DPO, CCC (DIO N/A without inventory)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable


ASSUMPTIONS = [
    "Credit sales = sum of AR Invoice Amount in the period",
    "Purchases = sum of AP invoice amount with submittedDate in the period",
    "DIO not applicable (no inventory data) — CCC = DSO − DPO",
]


def _safe_days(amount: float, daily: float) -> float | None:
    if daily is None or daily <= 0:
        return None
    return round(float(amount) / float(daily), 1)


def _period_bounds(as_of: date, period_days: int, offset_periods: int = 0) -> tuple[date, date]:
    """Return [start, end] inclusive for a rolling window ending `offset_periods` windows ago."""
    end = as_of - timedelta(days=period_days * offset_periods)
    start = end - timedelta(days=period_days - 1)
    return start, end


def _ar_drivers(db: Any, start: date, end: date) -> dict[str, float]:
    """AR outstanding (current) + credit sales in [start, end]."""
    ar_outstanding = 0.0
    credit_sales = 0.0

    # Preferred: payment_allocations (source of Invoice Date / Due Amount)
    try:
        row = db.execute(
            """
            SELECT
                COALESCE(SUM("Due Amount"), 0) AS outstanding,
                COALESCE(SUM(CASE
                    WHEN "Invoice Date" IS NOT NULL
                         AND "Invoice Date" >= ?
                         AND "Invoice Date" <= ?
                    THEN "Invoice Amount" ELSE 0 END), 0) AS sales
            FROM payment_allocations
            """,
            [start, end],
        ).fetchone()
        if row:
            ar_outstanding = float(row[0] or 0)
            credit_sales = float(row[1] or 0)
            return {"ar_outstanding": ar_outstanding, "credit_sales_in_period": credit_sales}
    except Exception:
        pass

    # Fallback: invoice_level_view (may lack Invoice Date filter)
    try:
        row = db.execute(
            """
            SELECT
                COALESCE(SUM("Due Amount"), 0),
                COALESCE(SUM("Invoice Amount"), 0)
            FROM invoice_level_view
            """
        ).fetchone()
        if row:
            ar_outstanding = float(row[0] or 0)
            credit_sales = float(row[1] or 0)
    except Exception:
        pass

    return {"ar_outstanding": ar_outstanding, "credit_sales_in_period": credit_sales}


def _ap_drivers(invoices: list[dict[str, Any]], start: date, end: date) -> dict[str, float]:
    """AP outstanding (open) + purchases in [start, end]."""
    open_statuses = {
        "Pending Approval",
        "Regulation Review",
        "Exception",
        "Approved",
        "Payment Ready",
    }
    ap_outstanding = 0.0
    purchases = 0.0
    for inv in invoices:
        amount = float(inv.get("amount") or 0)
        status = inv.get("status") or ""
        if status in open_statuses or inv.get("cashHold"):
            ap_outstanding += amount
        submitted = inv.get("submittedDate") or inv.get("dueDate")
        if not submitted:
            continue
        try:
            d = date.fromisoformat(str(submitted)[:10])
        except ValueError:
            continue
        if start <= d <= end:
            purchases += amount
    return {"ap_outstanding": ap_outstanding, "purchases_in_period": purchases}


def _ratios_from_drivers(drivers: dict[str, float], period_days: int) -> dict[str, float | None]:
    sales = drivers.get("credit_sales_in_period") or 0.0
    purchases = drivers.get("purchases_in_period") or 0.0
    daily_sales = sales / period_days if period_days else 0.0
    daily_purchases = purchases / period_days if period_days else 0.0
    dso = _safe_days(drivers.get("ar_outstanding") or 0.0, daily_sales)
    dpo = _safe_days(drivers.get("ap_outstanding") or 0.0, daily_purchases)
    dio = None  # no inventory
    if dso is None and dpo is None:
        ccc = None
    else:
        ccc = round((dso or 0.0) - (dpo or 0.0), 1)
    return {"dso": dso, "dpo": dpo, "dio": dio, "ccc": ccc}


def compute_wc_metrics(
    db: Any | None,
    ap_invoices: list[dict[str, Any]] | None = None,
    period_days: int = 90,
    as_of: date | None = None,
) -> dict[str, Any]:
    """
    Compute DSO / DPO / CCC for the rolling period ending on as_of,
    plus prior-period comparison and driver amounts.
    """
    period_days = max(7, min(int(period_days or 90), 365))
    as_of = as_of or date.today()
    ap_invoices = ap_invoices or []

    start, end = _period_bounds(as_of, period_days, 0)
    prior_start, prior_end = _period_bounds(as_of, period_days, 1)

    current_drivers: dict[str, float] = {
        "ar_outstanding": 0.0,
        "credit_sales_in_period": 0.0,
        "ap_outstanding": 0.0,
        "purchases_in_period": 0.0,
    }
    prior_drivers: dict[str, float] = dict(current_drivers)

    if db is not None:
        current_drivers.update(_ar_drivers(db, start, end))
        # Prior AR sales use prior window; outstanding stays point-in-time (same snapshot)
        prior_ar = _ar_drivers(db, prior_start, prior_end)
        prior_drivers["ar_outstanding"] = current_drivers["ar_outstanding"]
        prior_drivers["credit_sales_in_period"] = prior_ar["credit_sales_in_period"]

    ap_cur = _ap_drivers(ap_invoices, start, end)
    ap_prior = _ap_drivers(ap_invoices, prior_start, prior_end)
    current_drivers.update(ap_cur)
    prior_drivers["ap_outstanding"] = ap_cur["ap_outstanding"]
    prior_drivers["purchases_in_period"] = ap_prior["purchases_in_period"]

    current = _ratios_from_drivers(current_drivers, period_days)
    prior = _ratios_from_drivers(prior_drivers, period_days)

    return {
        "period_days": period_days,
        "as_of": as_of.isoformat(),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "dso": current["dso"],
        "dpo": current["dpo"],
        "dio": current["dio"],
        "ccc": current["ccc"],
        "prior": {
            "dso": prior["dso"],
            "dpo": prior["dpo"],
            "dio": prior["dio"],
            "ccc": prior["ccc"],
            "period_start": prior_start.isoformat(),
            "period_end": prior_end.isoformat(),
        },
        "drivers": {
            "ar_outstanding": round(current_drivers["ar_outstanding"], 2),
            "ap_outstanding": round(current_drivers["ap_outstanding"], 2),
            "credit_sales_in_period": round(current_drivers["credit_sales_in_period"], 2),
            "purchases_in_period": round(current_drivers["purchases_in_period"], 2),
        },
        "assumptions": list(ASSUMPTIONS),
    }


def compute_wc_metrics_from_getter(
    get_duckdb: Callable[[], Any] | None,
    ap_invoices: list[dict[str, Any]] | None = None,
    period_days: int = 90,
    as_of: date | None = None,
) -> dict[str, Any]:
    db = None
    if get_duckdb is not None:
        try:
            db = get_duckdb()
        except Exception:
            db = None
    return compute_wc_metrics(db, ap_invoices=ap_invoices, period_days=period_days, as_of=as_of)

"""Aggregate AR + AP into Working Capital calendar."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ar.server import get_duckdb
from ar.services.forecast_service import ForecastService
from ar.services.services import APIServices
from ap.store import INVOICES
from ap.services.approval import evaluate_invoice, sync_approval_workflow

from wc.action_ranking import build_and_rank_actions
from wc.alerts import evaluate_alerts
from wc.cash_events import ap_events_from_invoices, ar_events_from_forecast, ensure_ap_wc_fields
from wc.metrics import compute_wc_metrics
from wc.store import COLLECT_PRIORITIES


def _shift_ap_dates(events: list[dict[str, Any]], defer_days: int) -> list[dict[str, Any]]:
    if not defer_days:
        return events
    out = []
    for e in events:
        if e.get("direction") != "outflow" or e.get("certainty") == "held":
            out.append(e)
            continue
        d = date.fromisoformat(e["cash_date"])
        shifted = dict(e)
        shifted["cash_date"] = (d + timedelta(days=defer_days)).isoformat()
        shifted["event_id"] = f"{e['event_id']}-defer{defer_days}"
        out.append(shifted)
    return out


def build_calendar(
    days: int = 30,
    scenario: str | None = None,
    defer_ap_days: int = 0,
    period_days: int = 90,
) -> dict[str, Any]:
    days = max(1, min(int(days or 30), 365))
    defer_ap_days = max(0, min(int(defer_ap_days or 0), 90))
    period_days = max(7, min(int(period_days or 90), 365))
    today = date.today()
    end = today + timedelta(days=days - 1)

    # Refresh AP workflow state + WC fields
    for invoice_id in list(INVOICES.keys()):
        try:
            evaluate_invoice(invoice_id)
            sync_approval_workflow(INVOICES[invoice_id])
        except Exception:
            pass
        ensure_ap_wc_fields(INVOICES[invoice_id], today)

    # AR forecast (scenario e.g. baseline, recession, growth, payment_delay_*)
    ar_scenario = None if not scenario or scenario in ("baseline", "none") else scenario
    # Map WC-friendly delay scenarios onto AR forecast scenarios when possible
    if scenario == "ar_delay_7":
        ar_scenario = "payment_delay_7"
    elif scenario == "ar_delay_14":
        ar_scenario = "payment_delay_14"
    elif scenario == "ar_delay_30":
        ar_scenario = "payment_delay_30"

    forecast: dict[str, Any] = {}
    ar_summary: dict[str, Any] = {}
    db = None
    try:
        db = get_duckdb()
        forecast_svc = ForecastService(db)
        # Prefer known scenario ids from AR; unknown → baseline
        try:
            forecast = forecast_svc.forecast(days=days, partner_code=None, scenario=ar_scenario)
        except Exception:
            forecast = forecast_svc.forecast(days=days, partner_code=None, scenario=None)
    except Exception as exc:
        forecast = {"cashflow_events": [], "forecast_data": [], "error": str(exc)}

    try:
        summary_model = APIServices(get_duckdb).get_summary()
        ar_summary = (
            summary_model.model_dump()
            if hasattr(summary_model, "model_dump")
            else {
                "overall_exposure": getattr(summary_model, "overall_exposure", 0),
                "total_invoice_amount": getattr(summary_model, "total_invoice_amount", 0),
            }
        )
    except Exception:
        ar_summary = {}

    inflows = ar_events_from_forecast(forecast, COLLECT_PRIORITIES)
    outflows = ap_events_from_invoices(list(INVOICES.values()), today)
    outflows = _shift_ap_dates(outflows, defer_ap_days)

    def in_horizon(ev: dict[str, Any]) -> bool:
        d = date.fromisoformat(ev["cash_date"])
        return today <= d <= end

    horizon_events = [e for e in inflows + outflows if in_horizon(e) or e.get("certainty") == "held"]
    # Held may have cash_date outside horizon — still include for KPI
    held_all = [e for e in outflows if e.get("certainty") == "held"]

    series_map: dict[str, dict[str, float]] = {}
    for i in range(days):
        d = (today + timedelta(days=i)).isoformat()
        series_map[d] = {
            "date": d,
            "inflow": 0.0,
            "outflow_obligated": 0.0,
            "outflow_pipeline": 0.0,
            "net": 0.0,
        }

    for e in horizon_events:
        if e.get("certainty") == "held":
            continue
        d = e["cash_date"]
        if d not in series_map:
            continue
        if e["direction"] == "inflow":
            series_map[d]["inflow"] += e["amount"]
        elif e["certainty"] == "obligated":
            series_map[d]["outflow_obligated"] += e["amount"]
        elif e["certainty"] == "pipeline":
            series_map[d]["outflow_pipeline"] += e["amount"]

    series = []
    for d in sorted(series_map.keys()):
        row = series_map[d]
        row["net"] = row["inflow"] - row["outflow_obligated"]
        series.append(row)

    inflows_h = sum(e["amount"] for e in horizon_events if e["direction"] == "inflow")
    obligated_h = sum(
        e["amount"] for e in horizon_events if e["direction"] == "outflow" and e["certainty"] == "obligated"
    )
    pipeline_h = sum(
        e["amount"] for e in horizon_events if e["direction"] == "outflow" and e["certainty"] == "pipeline"
    )
    held_amt = sum(e["amount"] for e in held_all)

    cash_at_risk = float(
        ar_summary.get("overall_exposure")
        or ar_summary.get("total_overdue")
        or 0
    )

    wc_metrics = compute_wc_metrics(
        db,
        ap_invoices=list(INVOICES.values()),
        period_days=period_days,
        as_of=today,
    )

    kpis = {
        "inflows": inflows_h,
        "obligated_outflows": obligated_h,
        "pipeline_outflows": pipeline_h,
        "held": held_amt,
        "net": inflows_h - obligated_h,
        "cash_at_risk": cash_at_risk,
        "forecast_confidence": forecast.get("confidence_score"),
        "ar_overall_exposure": ar_summary.get("overall_exposure"),
        "ar_invoice_amount": ar_summary.get("total_invoice_amount"),
        "wc_metrics": wc_metrics,
    }

    actions = build_and_rank_actions(
        horizon_events=horizon_events,
        held_events=held_all,
        kpis=kpis,
        series=series,
        today=today,
        horizon_days=days,
        limit=8,
    )

    sc_label = scenario or "baseline"
    baseline_net = None
    if sc_label not in ("baseline", "none", None) or defer_ap_days > 0:
        baseline_net = _baseline_net(days=days, today=today)

    alerts = evaluate_alerts(
        series=series,
        kpis=kpis,
        wc_metrics=wc_metrics,
        held_events=held_all,
        scenario=sc_label,
        baseline_net=baseline_net,
        today=today,
        action_ids=[a["id"] for a in actions],
    )

    return {
        "horizon_days": days,
        "as_of": today.isoformat(),
        "scenario": sc_label,
        "defer_ap_days": defer_ap_days,
        "kpis": kpis,
        "series": series,
        "events": sorted(
            horizon_events + [e for e in held_all if e not in horizon_events],
            key=lambda e: (e["cash_date"], e["direction"]),
        ),
        "actions_suggested": actions,
        "alerts": alerts,
        "ar_forecast_meta": {
            "trend_direction": forecast.get("trend_direction"),
            "projected_balance": forecast.get("projected_balance"),
            "event_count": len(forecast.get("cashflow_events") or []),
        },
    }


def _baseline_net(days: int, today: date) -> float:
    """Lightweight baseline net (no scenario / no defer) for stress comparison."""
    try:
        forecast_svc = ForecastService(get_duckdb())
        forecast = forecast_svc.forecast(days=days, partner_code=None, scenario=None)
    except Exception:
        forecast = {"cashflow_events": []}
    inflows = ar_events_from_forecast(forecast, COLLECT_PRIORITIES)
    outflows = ap_events_from_invoices(list(INVOICES.values()), today)
    end = today + timedelta(days=days - 1)
    inflows_h = sum(
        e["amount"]
        for e in inflows
        if today <= date.fromisoformat(e["cash_date"]) <= end
    )
    obligated_h = sum(
        e["amount"]
        for e in outflows
        if e.get("certainty") == "obligated"
        and today <= date.fromisoformat(e["cash_date"]) <= end
    )
    return float(inflows_h - obligated_h)

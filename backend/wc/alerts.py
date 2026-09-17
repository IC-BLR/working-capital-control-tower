"""Evaluate Working Capital cash alerts from calendar payload + WC metrics."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from wc.alert_config import load_alert_config


def _fmt_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"


def evaluate_alerts(
    *,
    series: list[dict[str, Any]],
    kpis: dict[str, Any],
    wc_metrics: dict[str, Any] | None,
    held_events: list[dict[str, Any]] | None = None,
    scenario: str | None = None,
    baseline_net: float | None = None,
    today: date | None = None,
    config: dict | None = None,
    action_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return severity-sorted alert objects."""
    cfg = config or load_alert_config()
    today = today or date.today()
    held_events = held_events or []
    action_ids = action_ids or []
    alerts: list[dict[str, Any]] = []

    # Negative net days in series
    neg_days = [row for row in series if float(row.get("net") or 0) < 0]
    if neg_days:
        related = [row["date"] for row in neg_days[:5]]
        collect_holds = [aid for aid in action_ids if aid.startswith(("hold-", "collect-"))][:4]
        alerts.append(
            {
                "id": "NEG_NET_DAY",
                "severity": "high",
                "title": "Negative net cash days",
                "detail": f"{len(neg_days)} day(s) below zero in the selected horizon",
                "metric_value": float(neg_days[0].get("net") or 0),
                "related_dates": related,
                "suggested_action_ids": collect_holds,
            }
        )

    net = float(kpis.get("net") or 0)
    if net < 0:
        alerts.append(
            {
                "id": "NET_WC_NEGATIVE",
                "severity": "high",
                "title": "Negative net WC signal",
                "detail": f"Net WC signal {_fmt_inr(net)} over the horizon",
                "metric_value": net,
                "related_dates": [],
                "suggested_action_ids": [aid for aid in action_ids if aid.startswith("hold-")][:3],
            }
        )

    cash_at_risk = float(kpis.get("cash_at_risk") or 0)
    threshold = float(cfg["cash_at_risk_threshold"])
    if cash_at_risk > threshold:
        alerts.append(
            {
                "id": "CASH_AT_RISK",
                "severity": "high",
                "title": "Elevated AR cash at risk",
                "detail": f"{_fmt_inr(cash_at_risk)} overdue / exposure exceeds {_fmt_inr(threshold)}",
                "metric_value": cash_at_risk,
                "related_dates": [],
                "suggested_action_ids": [aid for aid in action_ids if aid.startswith("collect-")][:3],
            }
        )

    # Hold ageing
    aging_days = int(cfg["hold_aging_days"])
    aged = []
    aged_amt = 0.0
    for e in held_events:
        cd = e.get("cash_date")
        try:
            d = date.fromisoformat(str(cd)[:10]) if cd else None
        except ValueError:
            d = None
        if d and (today - d).days >= aging_days:
            aged.append(e)
            aged_amt += float(e.get("amount") or 0)
    if aged:
        alerts.append(
            {
                "id": "HOLD_AGING",
                "severity": "medium",
                "title": "Aged AP holds",
                "detail": f"{_fmt_inr(aged_amt)} held {aging_days}+ days — review exceptions",
                "metric_value": aged_amt,
                "related_dates": [],
                "suggested_action_ids": ["review_holds"] if "review_holds" in action_ids else [],
            }
        )

    # Outflow cluster in next N days
    cluster_days = int(cfg["outflow_cluster_days"])
    ratio_limit = float(cfg["outflow_cluster_ratio"])
    end_cluster = today + timedelta(days=cluster_days - 1)
    inflow_w = 0.0
    outflow_w = 0.0
    for row in series:
        try:
            d = date.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue
        if today <= d <= end_cluster:
            inflow_w += float(row.get("inflow") or 0)
            outflow_w += float(row.get("outflow_obligated") or 0)
    if inflow_w > 0 and (outflow_w / inflow_w) >= ratio_limit:
        alerts.append(
            {
                "id": "LARGE_OUTFLOW_CLUSTER",
                "severity": "medium",
                "title": "Outflow cluster ahead",
                "detail": (
                    f"Next {cluster_days} days: outflows {_fmt_inr(outflow_w)} "
                    f"are {outflow_w / inflow_w:.1f}× expected inflows"
                ),
                "metric_value": outflow_w / inflow_w,
                "related_dates": [],
                "suggested_action_ids": [aid for aid in action_ids if aid.startswith("hold-")][:3],
            }
        )
    elif inflow_w <= 0 and outflow_w > 0:
        alerts.append(
            {
                "id": "LARGE_OUTFLOW_CLUSTER",
                "severity": "medium",
                "title": "Outflow cluster ahead",
                "detail": f"Next {cluster_days} days: {_fmt_inr(outflow_w)} obligated with little expected inflow",
                "metric_value": outflow_w,
                "related_dates": [],
                "suggested_action_ids": [aid for aid in action_ids if aid.startswith("hold-")][:3],
            }
        )

    # CCC deterioration
    if wc_metrics:
        ccc = wc_metrics.get("ccc")
        prior_ccc = (wc_metrics.get("prior") or {}).get("ccc")
        det = float(cfg["ccc_deterioration_days"])
        if ccc is not None and prior_ccc is not None and (ccc - prior_ccc) > det:
            delta = round(ccc - prior_ccc, 1)
            alerts.append(
                {
                    "id": "CCC_DETERIORATION",
                    "severity": "medium",
                    "title": "Cash conversion cycle worsened",
                    "detail": f"CCC worsened {delta} days vs prior period ({prior_ccc} → {ccc})",
                    "metric_value": delta,
                    "related_dates": [],
                    "suggested_action_ids": [aid for aid in action_ids if aid.startswith("collect-")][:2],
                }
            )

    # Scenario stress vs baseline net
    sc = (scenario or "baseline").lower()
    drop = float(cfg["scenario_stress_drop"])
    if sc not in ("baseline", "none", "") and baseline_net is not None and baseline_net != 0:
        drop_frac = (baseline_net - net) / abs(baseline_net)
        if drop_frac >= drop:
            alerts.append(
                {
                    "id": "SCENARIO_STRESS",
                    "severity": "info",
                    "title": "Scenario stress on net cash",
                    "detail": (
                        f"{scenario}: net {_fmt_inr(net)} is "
                        f"{drop_frac:.0%} below baseline {_fmt_inr(baseline_net)}"
                    ),
                    "metric_value": drop_frac,
                    "related_dates": [],
                    "suggested_action_ids": action_ids[:3],
                }
            )

    severity_order = {"high": 0, "medium": 1, "info": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a.get("severity"), 9))
    return alerts

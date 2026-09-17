"""Rank Cash Calendar suggested actions by cash-impact score."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


CERTAINTY_WEIGHT = {
    "obligated": 1.0,
    "pipeline": 0.55,
    "forecast": 0.7,
    "held": 0.85,
}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _horizon_weight(cash_date: date | None, today: date, horizon_days: int) -> float:
    if cash_date is None:
        return 0.5
    days_out = (cash_date - today).days
    if days_out <= 0:
        return 1.25
    if days_out <= 7:
        return 1.15
    if days_out <= 14:
        return 1.0
    if days_out <= 30:
        return 0.75
    if days_out <= horizon_days:
        return 0.5
    return 0.35


def _fmt_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"


def _negative_net_dates(series: list[dict[str, Any]]) -> set[str]:
    return {row["date"] for row in series if float(row.get("net") or 0) < 0}


def build_and_rank_actions(
    horizon_events: list[dict[str, Any]],
    held_events: list[dict[str, Any]],
    kpis: dict[str, Any],
    series: list[dict[str, Any]],
    today: date | None = None,
    horizon_days: int = 30,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Build hold / collect / review-holds actions and rank by cash impact.
    score = amount × horizon_weight × certainty_weight × risk/type boosts
    """
    today = today or date.today()
    neg_dates = _negative_net_dates(series)
    actions: list[dict[str, Any]] = []

    held_amt = float(kpis.get("held") or 0)
    if held_amt > 0:
        # Age boost: if any held event cash_date is already past or far stale
        age_boost = 1.0
        for e in held_events:
            cd = _parse_date(e.get("cash_date"))
            if cd and (today - cd).days >= 7:
                age_boost = 1.35
                break
        score = held_amt * 0.9 * age_boost
        actions.append(
            {
                "id": "review_holds",
                "label": "Review AP holds",
                "detail": f"{_fmt_inr(held_amt)} blocked by exceptions/holds",
                "ui_path": "/ap",
                "action_type": "review_holds",
                "cash_impact_score": round(score, 2),
                "cash_impact_label": f"Unlocks up to {_fmt_inr(held_amt)} held AP cash",
            }
        )

    for e in horizon_events:
        if e.get("direction") != "inflow":
            continue
        if e.get("collect_priority"):
            continue
        amount = float(e.get("amount") or 0)
        if amount <= 0:
            continue
        cd = _parse_date(e.get("cash_date"))
        hw = _horizon_weight(cd, today, horizon_days)
        cw = CERTAINTY_WEIGHT.get(e.get("certainty") or "forecast", 0.7)
        risk_boost = 1.25 if (e.get("risk") or "").lower() == "high" else 1.0
        overdue_boost = 1.2 if cd and cd < today else 1.0
        neg_boost = 1.15 if cd and cd.isoformat() in neg_dates else 1.0
        score = amount * hw * cw * risk_boost * overdue_boost * neg_boost * 1.1
        days_label = "overdue" if cd and cd < today else f"in next {(cd - today).days if cd else '?'} days"
        actions.append(
            {
                "id": f"collect-{e.get('source_ref')}",
                "label": "Prioritize collect",
                "detail": f"{e.get('counterparty_name')} · {_fmt_inr(amount)}",
                "ui_path": (e.get("links") or {}).get("ui_path"),
                "partner_code": e.get("counterparty_id"),
                "invoice_number": e.get("source_ref"),
                "action_type": "collect",
                "cash_impact_score": round(score, 2),
                "cash_impact_label": f"Accelerates {_fmt_inr(amount)} inflow {days_label}",
            }
        )

    for e in horizon_events:
        if e.get("certainty") != "obligated":
            continue
        amount = float(e.get("amount") or 0)
        if amount <= 0:
            continue
        cd = _parse_date(e.get("cash_date"))
        hw = _horizon_weight(cd, today, horizon_days)
        cw = CERTAINTY_WEIGHT["obligated"]
        neg_boost = 1.3 if cd and cd.isoformat() in neg_dates else 1.0
        near_boost = 1.2 if cd and 0 <= (cd - today).days <= 7 else 1.0
        score = amount * hw * cw * neg_boost * near_boost
        if cd and (cd - today).days <= 7:
            impact = f"Protects {_fmt_inr(amount)} outflow in next 7 days"
        else:
            impact = f"Defers {_fmt_inr(amount)} obligated outflow"
        actions.append(
            {
                "id": f"hold-{e.get('source_ref')}",
                "label": "Hold pay",
                "detail": f"{e.get('counterparty_name')} · {_fmt_inr(amount)}",
                "ui_path": (e.get("links") or {}).get("ui_path"),
                "invoice_id": e.get("source_ref"),
                "action_type": "hold",
                "cash_impact_score": round(score, 2),
                "cash_impact_label": impact,
            }
        )

    actions.sort(key=lambda a: a.get("cash_impact_score") or 0, reverse=True)
    ranked = []
    for i, a in enumerate(actions[:limit], start=1):
        item = dict(a)
        item["rank"] = i
        ranked.append(item)
    return ranked

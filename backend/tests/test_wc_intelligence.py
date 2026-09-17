"""Unit tests for WC metrics, alerts, and action ranking."""
from __future__ import annotations

from datetime import date, timedelta

from wc.action_ranking import build_and_rank_actions
from wc.alerts import evaluate_alerts
from wc.metrics import compute_wc_metrics, _ratios_from_drivers


def test_ratios_from_drivers_basic():
    drivers = {
        "ar_outstanding": 300_000,
        "credit_sales_in_period": 900_000,  # 10k/day over 90d
        "ap_outstanding": 150_000,
        "purchases_in_period": 450_000,  # 5k/day
    }
    ratios = _ratios_from_drivers(drivers, 90)
    assert ratios["dso"] == 30.0
    assert ratios["dpo"] == 30.0
    assert ratios["dio"] is None
    assert ratios["ccc"] == 0.0


def test_ratios_zero_sales_returns_null_dso():
    drivers = {
        "ar_outstanding": 100_000,
        "credit_sales_in_period": 0,
        "ap_outstanding": 50_000,
        "purchases_in_period": 90_000,
    }
    ratios = _ratios_from_drivers(drivers, 90)
    assert ratios["dso"] is None
    assert ratios["dpo"] is not None
    assert ratios["ccc"] is not None  # uses 0 for missing DSO


def test_compute_wc_metrics_ap_only():
    today = date(2026, 9, 15)
    invoices = [
        {
            "id": "INV-1",
            "amount": 90_000,
            "status": "Payment Ready",
            "submittedDate": "2026-08-01",
            "dueDate": "2026-09-01",
        },
        {
            "id": "INV-2",
            "amount": 45_000,
            "status": "Exception",
            "cashHold": True,
            "submittedDate": "2026-07-15",
            "dueDate": "2026-08-15",
        },
    ]
    result = compute_wc_metrics(None, ap_invoices=invoices, period_days=90, as_of=today)
    assert result["period_days"] == 90
    assert result["drivers"]["ap_outstanding"] == 135_000
    assert result["drivers"]["purchases_in_period"] == 135_000
    assert result["dio"] is None
    assert "assumptions" in result
    assert result["prior"] is not None


def test_action_ranking_near_term_outranks_far():
    today = date(2026, 9, 15)
    events = [
        {
            "direction": "outflow",
            "certainty": "obligated",
            "amount": 80_000,
            "cash_date": (today + timedelta(days=60)).isoformat(),
            "counterparty_name": "Far Vendor",
            "source_ref": "INV-FAR",
            "links": {"ui_path": "/ap"},
        },
        {
            "direction": "outflow",
            "certainty": "obligated",
            "amount": 50_000,
            "cash_date": (today + timedelta(days=3)).isoformat(),
            "counterparty_name": "Near Vendor",
            "source_ref": "INV-NEAR",
            "links": {"ui_path": "/ap"},
        },
        {
            "direction": "inflow",
            "certainty": "forecast",
            "amount": 40_000,
            "cash_date": (today + timedelta(days=5)).isoformat(),
            "counterparty_name": "Customer",
            "counterparty_id": "P1",
            "source_ref": "AR-1",
            "collect_priority": False,
            "links": {"ui_path": "/ar"},
        },
    ]
    series = [
        {"date": (today + timedelta(days=3)).isoformat(), "net": -10_000, "inflow": 0, "outflow_obligated": 50_000},
    ]
    ranked = build_and_rank_actions(
        horizon_events=events,
        held_events=[],
        kpis={"held": 0},
        series=series,
        today=today,
        horizon_days=90,
        limit=8,
    )
    assert ranked[0]["invoice_id"] == "INV-NEAR"
    assert ranked[0]["rank"] == 1
    assert "cash_impact_label" in ranked[0]
    # Already-prioritized collect should be skipped
    events[2]["collect_priority"] = True
    ranked2 = build_and_rank_actions(
        horizon_events=events,
        held_events=[],
        kpis={"held": 0},
        series=series,
        today=today,
        horizon_days=90,
    )
    assert not any(a.get("invoice_number") == "AR-1" for a in ranked2)


def test_evaluate_alerts_neg_net_and_cash_at_risk():
    today = date(2026, 9, 15)
    series = [
        {"date": today.isoformat(), "net": -5000, "inflow": 0, "outflow_obligated": 5000},
        {"date": (today + timedelta(days=1)).isoformat(), "net": 1000, "inflow": 2000, "outflow_obligated": 1000},
    ]
    kpis = {"net": -200_000, "cash_at_risk": 5_000_000, "held": 80_000}
    wc_metrics = {
        "ccc": 40.0,
        "prior": {"ccc": 30.0},
    }
    held_events = [
        {
            "amount": 80_000,
            "cash_date": (today - timedelta(days=12)).isoformat(),
        }
    ]
    alerts = evaluate_alerts(
        series=series,
        kpis=kpis,
        wc_metrics=wc_metrics,
        held_events=held_events,
        scenario="recession",
        baseline_net=100_000,
        today=today,
        action_ids=["hold-1", "collect-2", "review_holds"],
        config={
            "cash_at_risk_threshold": 1_000_000,
            "hold_aging_days": 7,
            "outflow_cluster_days": 7,
            "outflow_cluster_ratio": 1.2,
            "ccc_deterioration_days": 5.0,
            "scenario_stress_drop": 0.15,
        },
    )
    ids = {a["id"] for a in alerts}
    assert "NEG_NET_DAY" in ids
    assert "NET_WC_NEGATIVE" in ids
    assert "CASH_AT_RISK" in ids
    assert "HOLD_AGING" in ids
    assert "CCC_DETERIORATION" in ids
    assert "SCENARIO_STRESS" in ids
    assert alerts[0]["severity"] == "high"

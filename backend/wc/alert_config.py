"""Default thresholds for Working Capital cash alerts (env-overridable)."""
from __future__ import annotations

import os


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_alert_config() -> dict:
    return {
        # Absolute cash-at-risk (AR overdue / exposure) trigger
        "cash_at_risk_threshold": _float("WC_ALERT_CASH_AT_RISK", 1_000_000.0),
        # Days an AP hold can age before alerting
        "hold_aging_days": _int("WC_ALERT_HOLD_AGING_DAYS", 7),
        # Next-N-days outflow vs inflow ratio for cluster alert
        "outflow_cluster_days": _int("WC_ALERT_CLUSTER_DAYS", 7),
        "outflow_cluster_ratio": _float("WC_ALERT_CLUSTER_RATIO", 1.2),
        # CCC days worse than prior period
        "ccc_deterioration_days": _float("WC_ALERT_CCC_DAYS", 5.0),
        # Scenario stress: net drop vs baseline fraction
        "scenario_stress_drop": _float("WC_ALERT_SCENARIO_DROP", 0.15),
    }

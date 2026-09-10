"""Working Capital cash spine — shared store for WC actions."""
from __future__ import annotations

from typing import Any

# key: partner_code or ar:invoice_number → { note, created_at, ... }
COLLECT_PRIORITIES: dict[str, dict[str, Any]] = {}

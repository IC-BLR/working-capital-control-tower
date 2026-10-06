"""
Working Capital Control Tower — single FastAPI entrypoint.

AR (cashflow) routes  → /api/ar/*
AP (document intel)   → /api/ap/*
WC (cash spine)       → /api/wc/*
"""
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ar.server import api_router as ar_router, startup_ar, shutdown_ar
from ap.demo_dataset import apply_demo_dataset
from ap.store import INVOICES
from ap.routers import (
    auth,
    dashboard,
    documents,
    invoices,
    purchase_orders,
    contracts,
    regulations,
    demo,
)
from wc.router import router as wc_router
from wc.cash_events import ensure_ap_wc_fields

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Seed AP in-memory demo data at import (same as Archive standalone)
apply_demo_dataset()


def _enrich_ap_for_wc_demo():
    """Ensure AP demo has payment-ready + planned pay dates in the near horizon."""
    today = date.today()
    if "INV-PO-1001" in INVOICES:
        INVOICES["INV-PO-1001"]["status"] = "Payment Ready"
        INVOICES["INV-PO-1001"]["workflowCompleted"] = True
        INVOICES["INV-PO-1001"]["plannedPayDate"] = (today + timedelta(days=5)).isoformat()
        INVOICES["INV-PO-1001"]["cashHold"] = False
    if "INV-CTR-2001" in INVOICES:
        INVOICES["INV-CTR-2001"]["plannedPayDate"] = (today + timedelta(days=12)).isoformat()
        INVOICES["INV-CTR-2001"]["cashHold"] = False
    for inv in INVOICES.values():
        ensure_ap_wc_fields(inv, today)


_enrich_ap_for_wc_demo()

# Init DuckDB + register AR handlers before mounting router
startup_ar()

app = FastAPI(
    title="Working Capital Control Tower API",
    version="1.0.0",
    description="AR Sensei + AP Document Intelligence + Working Capital cash calendar.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3064,http://127.0.0.1:3064",
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AR under /api/ar
app.include_router(ar_router, prefix="/api/ar", tags=["AR Cashflow"])

# AP under /api/ap/...
app.include_router(auth.router, prefix="/api/ap/auth", tags=["AP Authentication"])
app.include_router(dashboard.router, prefix="/api/ap/dashboard", tags=["AP Dashboard"])
app.include_router(documents.router, prefix="/api/ap/documents", tags=["AP Document Intake"])
app.include_router(documents.router, prefix="/api/ap/intake", tags=["AP Compatibility Intake"])
app.include_router(invoices.router, prefix="/api/ap/invoices", tags=["AP Invoices"])
app.include_router(purchase_orders.router, prefix="/api/ap/purchase-orders", tags=["AP Purchase Orders"])
app.include_router(contracts.router, prefix="/api/ap/contracts", tags=["AP Contracts"])
app.include_router(regulations.router, prefix="/api/ap/regulations", tags=["AP Regulations"])
app.include_router(demo.router, prefix="/api/ap/demo", tags=["AP Demo Utilities"])

# Working Capital cash spine
app.include_router(wc_router, prefix="/api/wc", tags=["Working Capital"])


@app.on_event("shutdown")
async def shutdown():
    shutdown_ar()


@app.get("/")
def root():
    return {
        "service": "working-capital-control-tower",
        "status": "running",
        "docs": "/docs",
        "ar": "/api/ar",
        "ap": "/api/ap",
        "wc": "/api/wc",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "working-capital-control-tower",
        "modules": {
            "ar": ["summary", "partners", "invoices", "insights", "forecast", "chatbot", "pipeline"],
            "ap": [
                "auth",
                "documents",
                "ocr",
                "live_invoice_feed",
                "invoices",
                "purchase_orders",
                "contracts",
                "regulations",
                "exceptions",
                "role_based_approvals",
            ],
            "wc": ["calendar", "hold", "planned_pay_date", "collect_priority"],
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8064")),
        reload=True,
    )

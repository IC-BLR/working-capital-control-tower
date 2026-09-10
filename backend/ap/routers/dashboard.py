from fastapi import APIRouter
from ap.store import CONTRACTS, DOCUMENTS, INVOICES, PURCHASE_ORDERS, REGULATIONS, INVOICE_FEED_EVENTS

router = APIRouter()

@router.get("/summary")
def summary():
    invoices = list(INVOICES.values())
    exceptions = [i for i in invoices if i.get("exception") and i["exception"].get("state") != "Resolved"]
    approved = [i for i in invoices if i.get("status") == "Approved"]
    exposure = sum(float(i.get("exception", {}).get("financialExposure", 0)) for i in exceptions)
    return {
        "invoiceCount": len(invoices),
        "approvedCount": len(approved),
        "exceptionCount": len(exceptions),
        "documentCount": len(DOCUMENTS),
        "purchaseOrderCount": len(PURCHASE_ORDERS),
        "contractCount": len(CONTRACTS),
        "regulationCount": len(REGULATIONS),
        "financialExposure": exposure,
        "liveFeedCount": len(INVOICE_FEED_EVENTS),
        "latestFeedEvents": INVOICE_FEED_EVENTS[:6],
        "approvalRate": round(len(approved) / len(invoices) * 100, 1) if invoices else 0,
        "statusBreakdown": {status: len([i for i in invoices if i.get("status") == status]) for status in sorted({i.get("status") for i in invoices})},
        "riskBreakdown": {risk: len([i for i in invoices if i.get("risk") == risk]) for risk in ["Low", "Medium", "High"]},
    }

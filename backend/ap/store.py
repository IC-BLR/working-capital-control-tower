from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


DOCUMENTS: dict[str, dict[str, Any]] = {}


DEMO_USERS: dict[str, dict[str, Any]] = {
    "ap.analyst@demo.com": {
        "id": "USR-001",
        "name": "Anita Rao",
        "email": "ap.analyst@demo.com",
        "password": "Demo@123",
        "role": "AP Analyst",
        "approvalRole": "AP Analyst",
        "department": "AP Operations",
        "title": "Accounts Payable Analyst",
    },
    "finance.manager@demo.com": {
        "id": "USR-002",
        "name": "Ravi Menon",
        "email": "finance.manager@demo.com",
        "password": "Demo@123",
        "role": "Finance Manager",
        "approvalRole": "Finance Manager",
        "department": "Finance Operations",
        "title": "Finance Manager",
    },
    "tax.reviewer@demo.com": {
        "id": "USR-003",
        "name": "Priya Nair",
        "email": "tax.reviewer@demo.com",
        "password": "Demo@123",
        "role": "Tax Reviewer",
        "approvalRole": "Tax Reviewer",
        "department": "Tax Compliance",
        "title": "GST / TDS Reviewer",
    },
    "controller@demo.com": {
        "id": "USR-004",
        "name": "Karan Shah",
        "email": "controller@demo.com",
        "password": "Demo@123",
        "role": "Controller",
        "approvalRole": "Controller",
        "department": "Controllership",
        "title": "Financial Controller",
    },
}

ACTIVE_TOKENS: dict[str, str] = {}

def make_auth_token(email: str) -> str:
    return "demo-token-" + uuid4().hex[:20].upper()


INVOICES: dict[str, dict[str, Any]] = {
    "INV-10428": {
        "id": "INV-10428",
        "vendor": "Northstar Logistics",
        "category": "Transportation",
        "amount": 42800.00,
        "currency": "USD",
        "submittedDate": "2026-06-10",
        "dueDate": "2026-06-25",
        "status": "Approved",
        "risk": "Low",
        "assignedTo": "AP Automation",
        "poNumber": "PO-77821",
        "contractId": "CTR-9014",
        "confidence": 96,
        "description": "Freight and logistics services for Q2 regional distribution lanes.",
        "regulationId": "REG-SOX-001",
        "exception": None,
        "approvalTrail": ["OCR extracted invoice", "PO matched", "Contract valid", "SOX approval controls passed"],
        "aiRecommendation": "Approved for payment. PO, contract, and regulation checks are aligned.",
    },
    "INV-10429": {
        "id": "INV-10429",
        "vendor": "Orion Cloud Services",
        "category": "Cloud Services",
        "amount": 18450.00,
        "currency": "USD",
        "submittedDate": "2026-06-11",
        "dueDate": "2026-06-26",
        "status": "Regulation Review",
        "risk": "Medium",
        "assignedTo": "Legal Ops",
        "poNumber": "PO-78110",
        "contractId": "CTR-8842",
        "confidence": 82,
        "description": "Managed cloud hosting, monitoring, storage, and support services.",
        "regulationId": "REG-DATA-004",
        "exception": None,
        "approvalTrail": ["OCR extracted invoice", "PO matched", "Contract overage requires policy review"],
        "aiRecommendation": "Route for contract owner review because cloud overage requires data-processing validation.",
    },
    "INV-10430": {
        "id": "INV-10430",
        "vendor": "Apex Components",
        "category": "Manufacturing Parts",
        "amount": 76200.00,
        "currency": "USD",
        "submittedDate": "2026-06-12",
        "dueDate": "2026-06-20",
        "status": "Exception",
        "risk": "High",
        "assignedTo": "AP Review",
        "poNumber": "PO-77994",
        "contractId": "CTR-7729",
        "confidence": 67,
        "description": "Machined component batches for industrial assemblies.",
        "regulationId": "REG-AUD-002",
        "exception": {
            "id": "EXC-9001",
            "type": "PO Amount Variance",
            "severity": "High",
            "state": "New",
            "owner": "AP Review",
            "dueDate": "2026-06-18",
            "financialExposure": 8940.00,
            "rootCause": "Invoice amount exceeds PO remaining balance and unit price differs from contract schedule.",
            "recommendation": "Hold payment and route to AP Review and Strategic Sourcing.",
            "evidence": [
                "PO number matched but invoice exceeds remaining PO balance by $8,940.",
                "Contract tolerance is 2%; observed variance is higher.",
                "SOX policy requires documented exception before payment.",
            ],
            "timeline": [
                {"time": "2026-06-14 10:42", "event": "AI detected PO amount variance."},
                {"time": "2026-06-14 10:45", "event": "Exception routed to AP Review."},
            ],
        },
        "approvalTrail": ["OCR extracted invoice", "PO matched", "Variance detected", "Exception opened"],
        "aiRecommendation": "Hold payment. Request vendor clarification and compare against previous invoice INV-10392.",
    },
}

PURCHASE_ORDERS: dict[str, dict[str, Any]] = {
    "PO-77821": {
        "poNumber": "PO-77821",
        "vendorName": "Northstar Logistics",
        "category": "Transportation",
        "status": "Open",
        "risk": "Low",
        "totalAmount": 42800.00,
        "remainingAmount": 42800.00,
        "consumedAmount": 0.0,
        "currency": "USD",
        "paymentTerms": "Net 30",
        "buyer": "Procurement Ops",
        "requestedBy": "Distribution Team",
        "createdDate": "2026-05-18",
        "expectedDeliveryDate": "2026-06-21",
        "linkedContractId": "CTR-9014",
        "description": "Freight and logistics services for Q2 regional distribution lanes.",
        "lineItems": [{"description": "Freight and logistics services", "quantity": 12, "unitPrice": 3566.67, "amount": 42800.00}],
    },
    "PO-77994": {
        "poNumber": "PO-77994",
        "vendorName": "Apex Components",
        "category": "Manufacturing Parts",
        "status": "Exception",
        "risk": "High",
        "totalAmount": 67260.00,
        "remainingAmount": 67260.00,
        "consumedAmount": 0.0,
        "currency": "USD",
        "paymentTerms": "Net 45",
        "buyer": "Strategic Sourcing",
        "requestedBy": "Industrial Assembly Plant",
        "createdDate": "2026-05-20",
        "expectedDeliveryDate": "2026-06-18",
        "linkedContractId": "CTR-7729",
        "description": "Machined component batches for industrial assemblies.",
        "lineItems": [{"description": "Machined component batch", "quantity": 120, "unitPrice": 560.50, "amount": 67260.00}],
    },
    "PO-78110": {
        "poNumber": "PO-78110",
        "vendorName": "Orion Cloud Services",
        "category": "Cloud Services",
        "status": "Open",
        "risk": "Medium",
        "totalAmount": 17500.00,
        "remainingAmount": 17500.00,
        "consumedAmount": 0.0,
        "currency": "USD",
        "paymentTerms": "Net 30",
        "buyer": "IT Procurement",
        "requestedBy": "Cloud Platform Team",
        "createdDate": "2026-05-28",
        "expectedDeliveryDate": "2026-06-30",
        "linkedContractId": "CTR-8842",
        "description": "Managed cloud services and support.",
        "lineItems": [{"description": "Cloud hosting services", "quantity": 1, "unitPrice": 17500.00, "amount": 17500.00}],
    },
}

CONTRACTS: dict[str, dict[str, Any]] = {
    "CTR-9014": {
        "id": "CTR-9014",
        "vendor": "Northstar Logistics",
        "category": "Transportation",
        "status": "Active",
        "risk": "Low",
        "owner": "Procurement Ops",
        "startDate": "2026-01-01",
        "endDate": "2026-12-31",
        "value": 520000.00,
        "currency": "USD",
        "paymentTerms": "Net 30",
        "tolerancePercent": 2.0,
        "linkedPOs": ["PO-77821"],
        "summary": "Transportation services agreement covering freight lanes.",
        "clauses": [{"type": "payment_terms", "summary": "Invoices payable Net 30 after PO and delivery evidence."}],
        "aiFinding": "No pricing or compliance exceptions detected.",
    },
    "CTR-7729": {
        "id": "CTR-7729",
        "vendor": "Apex Components",
        "category": "Manufacturing Parts",
        "status": "Active",
        "risk": "High",
        "owner": "Strategic Sourcing",
        "startDate": "2025-10-01",
        "endDate": "2026-09-30",
        "value": 875000.00,
        "currency": "USD",
        "paymentTerms": "Net 45",
        "tolerancePercent": 2.0,
        "linkedPOs": ["PO-77994"],
        "summary": "Manufacturing parts agreement with unit pricing and holdback terms.",
        "clauses": [{"type": "price_tolerance", "summary": "Unit price variance above 2% requires sourcing approval."}],
        "aiFinding": "Unit price mismatch and duplicate billing warning require review.",
    },
    "CTR-8842": {
        "id": "CTR-8842",
        "vendor": "Orion Cloud Services",
        "category": "Cloud Services",
        "status": "Active",
        "risk": "Medium",
        "owner": "Legal Ops",
        "startDate": "2026-01-15",
        "endDate": "2027-01-14",
        "value": 240000.00,
        "currency": "USD",
        "paymentTerms": "Net 30",
        "tolerancePercent": 5.0,
        "linkedPOs": ["PO-78110"],
        "summary": "Cloud services agreement with data-processing and overage controls.",
        "clauses": [{"type": "data_processing", "summary": "Cloud service invoices require DPA and data residency review."}],
        "aiFinding": "Overage needs policy validation before payment.",
    },
}

REGULATIONS: dict[str, dict[str, Any]] = {
    "REG-SOX-001": {
        "id": "REG-SOX-001",
        "title": "SOX Standard AP Approval Control",
        "category": "Audit",
        "jurisdiction": "Global",
        "status": "Active",
        "risk": "Low",
        "owner": "Finance Controls",
        "effectiveDate": "2025-01-01",
        "lastUpdated": "2026-04-22",
        "approvalThreshold": 50000.00,
        "requiresPO": True,
        "requiresContract": True,
        "requiresExceptionDocumentation": True,
        "summary": "Invoices require PO linkage, contract validation, segregation of duties, and approval audit trail.",
        "guidance": ["Match invoice to PO.", "Validate payment terms against contract.", "Document exceptions before payment."],
        "aiFinding": "Compliant invoices can be auto-approved below materiality threshold.",
    },
    "REG-AUD-002": {
        "id": "REG-AUD-002",
        "title": "SOX Material Invoice Exception Policy",
        "category": "Audit",
        "jurisdiction": "Global",
        "status": "Active",
        "risk": "High",
        "owner": "Finance Controls",
        "effectiveDate": "2025-10-01",
        "lastUpdated": "2026-04-22",
        "approvalThreshold": 50000.00,
        "requiresPO": True,
        "requiresContract": True,
        "requiresExceptionDocumentation": True,
        "summary": "Material invoices require clear approval trail, PO linkage, contract validation, segregation of duties, and exception documentation.",
        "guidance": ["High-value invoices must be approved by authorized approvers.", "PO and contract mismatches must be documented before payment.", "Duplicate invoice risk must be reviewed by AP controls."],
        "aiFinding": "Apex Components invoice must be held until variance evidence is resolved and documented.",
    },
    "REG-DATA-004": {
        "id": "REG-DATA-004",
        "title": "Cloud Data Processing Invoice Review",
        "category": "Data Privacy",
        "jurisdiction": "US / EU",
        "status": "Active",
        "risk": "Medium",
        "owner": "Privacy Office",
        "effectiveDate": "2026-02-01",
        "lastUpdated": "2026-05-11",
        "approvalThreshold": 15000.00,
        "requiresPO": True,
        "requiresContract": True,
        "requiresExceptionDocumentation": True,
        "summary": "Cloud and data processing invoices require validation against DPA and approved service scope.",
        "guidance": ["Confirm DPA coverage.", "Review overages before payment.", "Escalate data residency exceptions."],
        "aiFinding": "Orion invoice requires policy review due to overage above approved PO amount.",
    },
}


def make_document_id() -> str:
    return "DOC-" + uuid4().hex[:8].upper()


def make_invoice_id() -> str:
    return "INV-" + uuid4().hex[:5].upper()

INVOICE_FEED_EVENTS: list[dict[str, Any]] = []


def make_feed_event(invoice_id: str, event_type: str, title: str, detail: str) -> dict[str, Any]:
    event = {
        "id": "EVT-" + uuid4().hex[:8].upper(),
        "invoiceId": invoice_id,
        "eventType": event_type,
        "title": title,
        "detail": detail,
        "createdAt": now_iso(),
    }
    INVOICE_FEED_EVENTS.insert(0, event)
    del INVOICE_FEED_EVENTS[40:]
    return event

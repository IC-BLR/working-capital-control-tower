from __future__ import annotations

from itertools import cycle
from typing import Any
from ap.services.approval import evaluate_invoice
from ap.store import INVOICES, make_feed_event, now_iso

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "approval_ready",
        "vendor": "Northstar Logistics",
        "category": "Transportation",
        "amount": 42150.00,
        "currency": "USD",
        "poNumber": "PO-77821",
        "contractId": "CTR-9014",
        "paymentTerms": "Net 30",
        "regulationId": "REG-SOX-001",
        "description": "Freight services with PO, contract, and SOX control alignment.",
        "message": "New invoice passed PO, contract, and regulation checks.",
    },
    {
        "name": "po_variance_exception",
        "vendor": "Apex Components",
        "category": "Manufacturing Parts",
        "amount": 76200.00,
        "currency": "USD",
        "poNumber": "PO-77994",
        "contractId": "CTR-7729",
        "paymentTerms": "Net 45",
        "regulationId": "REG-AUD-002",
        "description": "Machined component batch exceeds PO balance and contract tolerance.",
        "message": "New invoice generated a PO variance exception and payment hold.",
    },
    {
        "name": "cloud_policy_review",
        "vendor": "Orion Cloud Services",
        "category": "Cloud Services",
        "amount": 18450.00,
        "currency": "USD",
        "poNumber": "PO-78110",
        "contractId": "CTR-8842",
        "paymentTerms": "Net 30",
        "regulationId": "REG-DATA-004",
        "description": "Cloud services over approved PO amount; requires data-processing policy review.",
        "message": "New cloud invoice routed for regulation review.",
    },
    {
        "name": "missing_contract",
        "vendor": "Nimbus Legal Process LLP",
        "category": "Legal Services",
        "amount": 36800.00,
        "currency": "USD",
        "poNumber": "PO-99002",
        "contractId": "CTR-LEG-2026-044",
        "paymentTerms": "Net 30",
        "regulationId": "REG-SOX-001",
        "description": "Legal services invoice referencing a missing or not-yet-approved contract.",
        "message": "New invoice needs contract evidence before payment.",
    },
]

_cycle = cycle(range(len(SCENARIOS)))


def next_invoice_number() -> str:
    numeric = []
    for invoice_id in INVOICES:
        if invoice_id.startswith("INV-"):
            suffix = invoice_id.replace("INV-", "")
            if suffix.isdigit():
                numeric.append(int(suffix))
    return f"INV-{(max(numeric) if numeric else 10430) + 1}"


def simulate_new_invoice(scenario: str | None = None) -> dict[str, Any]:
    if scenario:
        template = next((item for item in SCENARIOS if item["name"] == scenario), SCENARIOS[0])
    else:
        template = SCENARIOS[next(_cycle)]

    invoice_id = next_invoice_number()
    invoice = {
        "id": invoice_id,
        "vendor": template["vendor"],
        "category": template["category"],
        "amount": template["amount"],
        "currency": template["currency"],
        "submittedDate": now_iso()[:10],
        "dueDate": now_iso()[:10],
        "status": "New",
        "risk": "Medium",
        "assignedTo": "Live Invoice Feed",
        "poNumber": template["poNumber"],
        "contractId": template["contractId"],
        "paymentTerms": template["paymentTerms"],
        "confidence": 88,
        "description": template["description"],
        "regulationId": template["regulationId"],
        "exception": None,
        "approvalTrail": ["Received through Live Invoice Feed", "OCR extracted invoice header and line summary"],
        "aiRecommendation": "New invoice received. Running automated controls.",
        "createdAt": now_iso(),
        "source": "Live Invoice Feed",
        "lineItems": [
            {"description": template["description"], "quantity": 1, "unitPrice": template["amount"], "amount": template["amount"]}
        ],
    }
    INVOICES[invoice_id] = invoice
    result = evaluate_invoice(invoice_id)
    event = make_feed_event(
        invoice_id=invoice_id,
        event_type=template["name"],
        title=f"{invoice_id} received from {template['vendor']}",
        detail=template["message"],
    )
    return {"invoice": INVOICES[invoice_id], "event": event, "decision": result}

SCENARIOS = [
    {"name":"clean_po_invoice", "vendor":"ApexCloud Technologies Pvt Ltd", "category":"Cloud Infrastructure", "amount":102700.0, "taxAmount":18486.0, "currency":"INR", "invoiceType":"PO_BACKED", "primaryMatchType":"PO", "poNumber":"PO-78219", "contractId":None, "supportingContractId":"CTR-AC-2026-019", "paymentTerms":"Net 45", "regulationId":"REG-PO-001", "description":"Clean PO-backed cloud invoice.", "message":"New PO-backed invoice passed PO and regulation controls."},
    {"name":"po_variance_exception", "vendor":"ApexCloud Technologies Pvt Ltd", "category":"Cloud Infrastructure", "amount":121800.0, "taxAmount":21924.0, "currency":"INR", "invoiceType":"PO_BACKED", "primaryMatchType":"PO", "poNumber":"PO-78219", "contractId":None, "supportingContractId":"CTR-AC-2026-019", "paymentTerms":"Net 45", "regulationId":"REG-PO-003", "description":"PO-backed cloud invoice exceeding PO tolerance.", "message":"New PO-backed invoice created REG-PO-003 tolerance exception."},
    {"name":"clean_contract_invoice", "vendor":"Nimbus Legal Services LLP", "category":"Legal Services", "amount":295000.0, "taxAmount":45000.0, "tdsSection":"194J", "tdsAmount":25000.0, "currency":"INR", "invoiceType":"NON_PO_CONTRACT", "primaryMatchType":"CONTRACT", "poNumber":None, "contractId":"CTR-LEG-2026-044", "paymentTerms":"Net 30", "regulationId":"REG-CTR-001", "description":"Clean non-PO contract legal retainer invoice.", "message":"New non-PO invoice matched contract and routed for high-value approval."},
    {"name":"contract_rate_exception", "vendor":"Nimbus Legal Services LLP", "category":"Legal Services", "amount":354000.0, "taxAmount":54000.0, "tdsSection":"194J", "tdsAmount":30000.0, "currency":"INR", "invoiceType":"NON_PO_CONTRACT", "primaryMatchType":"CONTRACT", "poNumber":None, "contractId":"CTR-LEG-2026-044", "paymentTerms":"Net 30", "regulationId":"REG-CTR-002", "description":"Non-PO contract invoice with rate-card mismatch.", "message":"New non-PO invoice created REG-CTR-002 rate-card exception."},
    {"name":"tax_exception", "vendor":"Nimbus Legal Services LLP", "category":"Legal Services Tax Review", "amount":295000.0, "taxAmount":30000.0, "tdsSection":None, "tdsAmount":0.0, "currency":"INR", "invoiceType":"NON_PO_CONTRACT", "primaryMatchType":"CONTRACT", "poNumber":None, "contractId":"CTR-LEG-2026-044", "paymentTerms":"Net 30", "regulationId":"REG-TAX-004", "taxException":True, "description":"Non-PO contract invoice with GST/TDS exception.", "message":"New non-PO invoice routed to Tax Reviewer by REG-TAX-004."},
]

def simulate_new_invoice(scenario: str | None = None) -> dict[str, Any]:  # type: ignore[override]
    if scenario:
        template = next((item for item in SCENARIOS if item["name"] == scenario), SCENARIOS[0])
    else:
        template = SCENARIOS[next(_cycle)]
    invoice_id = next_invoice_number()
    invoice = {
        "id": invoice_id,
        "vendor": template["vendor"],
        "category": template["category"],
        "amount": template["amount"],
        "taxAmount": template.get("taxAmount", 0.0),
        "tdsSection": template.get("tdsSection"),
        "tdsAmount": template.get("tdsAmount", 0.0),
        "currency": template["currency"],
        "submittedDate": now_iso()[:10],
        "dueDate": now_iso()[:10],
        "status": "New",
        "risk": "Medium",
        "assignedTo": "Live Invoice Feed",
        "invoiceType": template["invoiceType"],
        "primaryMatchType": template["primaryMatchType"],
        "primaryMatchId": template.get("poNumber") if template["primaryMatchType"] == "PO" else template.get("contractId"),
        "poNumber": template.get("poNumber"),
        "contractId": template.get("contractId"),
        "supportingContractId": template.get("supportingContractId"),
        "paymentTerms": template["paymentTerms"],
        "confidence": 90,
        "description": template["description"],
        "regulationId": template["regulationId"],
        "taxException": template.get("taxException", False),
        "exception": None,
        "approvalTrail": ["Received through Live Invoice Feed", f"Primary match selected: {template['primaryMatchType']}"],
        "aiRecommendation": "New invoice received. Running primary-match and regulation controls.",
        "createdAt": now_iso(),
        "source": "Live Invoice Feed",
        "lineItems": [
            {"description": "Cloud compute reserved capacity" if template["primaryMatchType"] == "PO" else "Monthly legal retainer", "quantity": 1, "unitPrice": 300000.0 if template["name"] == "contract_rate_exception" else (250000.0 if template["primaryMatchType"] == "CONTRACT" else template["amount"]), "amount": template["amount"]}
        ],
    }
    INVOICES[invoice_id] = invoice
    result = evaluate_invoice(invoice_id)
    event = make_feed_event(invoice_id=invoice_id, event_type=template["name"], title=f"{invoice_id} received from {template['vendor']}", detail=template["message"])
    return {"invoice": INVOICES[invoice_id], "event": event, "decision": result}

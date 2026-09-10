from __future__ import annotations
from ap.store import INVOICES, PURCHASE_ORDERS, CONTRACTS, REGULATIONS

def apply_demo_dataset() -> None:
    PURCHASE_ORDERS.clear()
    PURCHASE_ORDERS.update({
        "PO-78219": {
            "poNumber": "PO-78219", "vendorName": "ApexCloud Technologies Pvt Ltd", "category": "Cloud Infrastructure", "status": "Open", "risk": "Low", "poType": "PO_BACKED",
            "totalAmount": 150000.0, "remainingAmount": 110000.0, "consumedAmount": 40000.0, "currency": "INR", "paymentTerms": "Net 45",
            "buyer": "PhonePe Cloud Procurement", "requestedBy": "Platform Engineering", "createdDate": "2026-04-27", "expectedDeliveryDate": "2026-06-30",
            "linkedContractId": "CTR-AC-2026-019", "tolerancePercent": 5.0,
            "description": "Approved cloud infrastructure capacity and managed support for May 2026.",
            "lineItems": [
                {"description": "Cloud compute reserved capacity", "hsnSac": "998315", "quantity": 40, "unit": "node-days", "unitPrice": 1800.0, "amount": 72000.0},
                {"description": "Managed support and monitoring", "hsnSac": "998313", "quantity": 1, "unit": "month", "unitPrice": 38000.0, "amount": 38000.0},
            ],
        }
    })
    CONTRACTS.clear()
    CONTRACTS.update({
        "CTR-AC-2026-019": {
            "id": "CTR-AC-2026-019", "vendor": "ApexCloud Technologies Pvt Ltd", "category": "Cloud Infrastructure", "status": "Active", "contractType": "Master Services Agreement",
            "risk": "Low", "owner": "Cloud Procurement", "startDate": "2026-01-01", "effectiveDate": "2026-01-01", "endDate": "2026-12-31", "expiryDate": "2026-12-31",
            "value": 2400000.0, "currency": "INR", "paymentTerms": "Net 45", "tolerancePercent": 5.0, "linkedPOs": ["PO-78219"],
            "summary": "Master cloud services contract. For PO-backed invoices this is supporting evidence inherited through the PO, not the primary match.",
            "rateCards": [
                {"service": "Cloud compute reserved capacity", "rate": 1800.0, "unit": "node-day", "currency": "INR"},
                {"service": "Managed support and monitoring", "rate": 38000.0, "unit": "month", "currency": "INR"},
            ],
            "clauses": [
                {"type": "payment_terms", "summary": "Invoices payable Net 45 after PO-backed validation."},
                {"type": "price_tolerance", "summary": "PO-backed invoices may not exceed PO remaining balance plus 5 percent tolerance."},
            ],
            "aiFinding": "Active contract; PO remains the primary evidence for PO-backed invoices.",
        },
        "CTR-LEG-2026-044": {
            "id": "CTR-LEG-2026-044", "vendor": "Nimbus Legal Services LLP", "category": "Legal Services", "status": "Active", "contractType": "Non-PO Services Contract",
            "risk": "Medium", "owner": "Legal Operations", "startDate": "2026-01-01", "effectiveDate": "2026-01-01", "endDate": "2026-12-31", "expiryDate": "2026-12-31",
            "value": 3600000.0, "currency": "INR", "paymentTerms": "Net 30", "tolerancePercent": 0.0, "linkedPOs": [],
            "summary": "Non-PO legal services retainer with monthly billing and professional-services tax controls.",
            "rateCards": [
                {"service": "Monthly legal retainer", "rate": 250000.0, "unit": "month", "currency": "INR"},
                {"service": "Senior counsel review", "rate": 18000.0, "unit": "hour", "currency": "INR"},
                {"service": "Regulatory filing support", "rate": 45000.0, "unit": "filing", "currency": "INR"},
            ],
            "clauses": [
                {"type": "billing_period", "summary": "Invoices must identify a monthly billing period within contract validity."},
                {"type": "rate_card", "summary": "Rates must match contract rate card unless Controller override is documented."},
                {"type": "tax", "summary": "Professional services require GST at 18 percent and TDS under section 194J."},
            ],
            "aiFinding": "Primary matching contract for non-PO legal-services invoices.",
        },
    })
    REGULATIONS.clear()
    base = {"jurisdiction":"India", "status":"Active", "effectiveDate":"2026-01-01", "lastUpdated":"2026-05-30", "approvalThreshold":250000.0}
    REGULATIONS.update({
        "REG-PO-001": {**base, "id":"REG-PO-001", "title":"PO-backed Invoice Mandatory PO Control", "category":"PO Control", "risk":"Low", "owner":"AP Controls", "requiresPO":True, "requiresContract":False, "summary":"PO-backed invoices must match an approved PO. Contract may be inherited through PO but is not the primary match.", "guidance":["Verify PO exists", "Confirm supplier matches PO", "Check remaining amount and tolerance"], "aiFinding":"Use PO as primary evidence."},
        "REG-PO-003": {**base, "id":"REG-PO-003", "title":"PO Amount Tolerance and Payment Hold Control", "category":"PO Control", "risk":"High", "owner":"Finance Controls", "requiresPO":True, "requiresContract":False, "summary":"Invoice amount must not exceed PO remaining balance plus tolerance. Failure blocks Finance Manager approval.", "guidance":["Calculate variance", "Open exception if tolerance is breached", "Hold payment until resolution"], "aiFinding":"PO tolerance failures create an approval-blocking exception."},
        "REG-CTR-001": {**base, "id":"REG-CTR-001", "title":"Non-PO Contract Active and Billing Period Control", "category":"Contract Control", "risk":"Medium", "owner":"Legal Operations", "requiresPO":False, "requiresContract":True, "summary":"Non-PO invoices must match an active contract and billing period inside validity.", "guidance":["Do not require PO", "Verify contract active", "Validate billing period"], "aiFinding":"Contract is primary evidence."},
        "REG-CTR-002": {**base, "id":"REG-CTR-002", "title":"Contract Rate Card Match Control", "category":"Contract Control", "risk":"High", "owner":"Finance Controls", "requiresPO":False, "requiresContract":True, "summary":"Billed service rate must match contract rate card. Mismatch blocks approval.", "guidance":["Compare service, quantity, rate and amount", "Open rate mismatch exception"], "aiFinding":"Rate-card mismatch is visibly marked on approval."},
        "REG-TAX-004": {**base, "id":"REG-TAX-004", "title":"GST and TDS Review for Professional Services", "category":"Tax Compliance", "risk":"High", "owner":"Tax Compliance", "requiresPO":False, "requiresContract":True, "summary":"Professional service invoices require 18 percent GST and TDS under 194J.", "guidance":["Verify GST", "Verify TDS 194J", "Route tax exceptions to Tax Reviewer"], "aiFinding":"Tax exceptions route to Tax Reviewer."},
        "REG-APP-005": {**base, "id":"REG-APP-005", "title":"High Value Controller Approval Threshold", "category":"Approval Matrix", "risk":"Medium", "owner":"Controllership", "requiresPO":False, "requiresContract":False, "summary":"Invoices above INR 250,000 require Controller approval.", "guidance":["Route high-value invoices to Controller"], "aiFinding":"Controller stage is triggered for high-value invoices."},
    })
    INVOICES.clear()
    def inv(id, typ, primary, vendor, category, amount, tax, po, contract, reg, status, risk, desc, line_price, exc=False, tax_exc=False):
        return {"id":id, "invoiceType":typ, "primaryMatchType":primary, "primaryMatchId": po if primary=="PO" else contract, "vendor":vendor, "category":category, "amount":amount, "taxAmount":tax, "tdsSection": (None if tax_exc else ("194J" if primary=="CONTRACT" else None)), "tdsAmount": (0.0 if tax_exc else (25000.0 if primary=="CONTRACT" else 0.0)), "currency":"INR", "submittedDate":"2026-06-07", "dueDate":"2026-06-30", "status":status, "risk":risk, "assignedTo":"AP Analyst", "poNumber":po, "contractId":contract if primary=="CONTRACT" else None, "supportingContractId":"CTR-AC-2026-019" if primary=="PO" else None, "paymentTerms":"Net 45" if primary=="PO" else "Net 30", "confidence":92, "description":desc, "regulationId":reg, "taxException":tax_exc, "exception":None, "lineItems":[{"description":"Cloud compute reserved capacity" if primary=="PO" else "Monthly legal retainer", "quantity":1 if primary=="CONTRACT" else 35, "unit":"month" if primary=="CONTRACT" else "node-days", "unitPrice":line_price, "amount":line_price if primary=="CONTRACT" else amount}], "approvalTrail":["Received through OCR intake", f"Primary match selected: {'Purchase Order ' + po if primary=='PO' else 'Contract ' + contract}"], "aiRecommendation":desc}
    INVOICES.update({
        "INV-PO-1001": inv("INV-PO-1001", "PO_BACKED", "PO", "ApexCloud Technologies Pvt Ltd", "Cloud Infrastructure", 102700.0, 18486.0, "PO-78219", None, "REG-PO-001", "Pending Approval", "Low", "Clean PO-backed invoice: PO is primary match; regulation controls passed.", 1800.0),
        "INV-PO-1002": inv("INV-PO-1002", "PO_BACKED", "PO", "ApexCloud Technologies Pvt Ltd", "Cloud Infrastructure", 121800.0, 21924.0, "PO-78219", None, "REG-PO-003", "Exception", "High", "PO-backed exception: invoice exceeds PO tolerance and blocks Finance Manager approval.", 1800.0),
        "INV-CTR-2001": inv("INV-CTR-2001", "NON_PO_CONTRACT", "CONTRACT", "Nimbus Legal Services LLP", "Legal Services", 295000.0, 45000.0, None, "CTR-LEG-2026-044", "REG-CTR-001", "Pending Approval", "Medium", "Clean non-PO contract invoice: contract is primary match; rate, GST and TDS are aligned.", 250000.0),
        "INV-CTR-2002": inv("INV-CTR-2002", "NON_PO_CONTRACT", "CONTRACT", "Nimbus Legal Services LLP", "Legal Services", 354000.0, 54000.0, None, "CTR-LEG-2026-044", "REG-CTR-002", "Exception", "High", "Contract exception: billed retainer rate exceeds contract rate card.", 300000.0),
        "INV-TAX-3001": inv("INV-TAX-3001", "NON_PO_CONTRACT", "CONTRACT", "Nimbus Legal Services LLP", "Legal Services Tax Review", 295000.0, 30000.0, None, "CTR-LEG-2026-044", "REG-TAX-004", "Regulation Review", "High", "Tax exception: GST below expected and TDS section 194J is missing.", 250000.0, tax_exc=True),
    })

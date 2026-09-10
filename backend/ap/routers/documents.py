from __future__ import annotations

from typing import Any
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ap.services.ocr import classify_document, extract_by_type, read_document_text
from ap.services.document_intelligence import run_document_intelligence
from ap.services.approval import evaluate_invoice
from ap.store import CONTRACTS, DOCUMENTS, INVOICES, PURCHASE_ORDERS, REGULATIONS, make_document_id, make_invoice_id, now_iso

router = APIRouter()


class ApproveExtractionRequest(BaseModel):
    extracted: dict[str, Any] | None = None


@router.get("")
def list_documents():
    return list(DOCUMENTS.values())


@router.post("/extract")
async def extract_document(file: UploadFile = File(...), documentType: str = Form("auto")):
    file_bytes = await file.read()
    raw_text = read_document_text(file_bytes, file.filename or "", file.content_type or "")
    if not raw_text:
        raise HTTPException(status_code=422, detail="OCR could not extract readable text. For demos, upload a searchable PDF/image or a .txt sample.")

    classification = classify_document(raw_text, documentType)
    doc_type = classification["documentType"]
    if doc_type == "unknown":
        raise HTTPException(status_code=422, detail="Could not classify this document. Select Invoice, Purchase Order, Contract, or Regulation and retry.")

    ai_extraction = run_document_intelligence(raw_text, doc_type)
    extracted = ai_extraction["structured"]
    document_id = make_document_id()
    record = {
        "id": document_id,
        "filename": file.filename,
        "contentType": file.content_type,
        "documentType": doc_type,
        "classificationConfidence": classification["confidence"],
        "extractionConfidence": ai_extraction.get("confidence", extracted.get("confidence", 50)),
        "status": "Extracted",
        "rawTextPreview": raw_text[:1500],
        "pageCountEstimate": max(1, raw_text.count("\f") + 1),
        "extracted": extracted,
        "aiExtraction": ai_extraction,
        "fieldConfidence": ai_extraction.get("fieldConfidence", {}),
        "evidence": ai_extraction.get("evidence", {}),
        "validation": ai_extraction.get("validation", {}),
        "linkedEntityId": None,
        "createdAt": now_iso(),
    }
    DOCUMENTS[document_id] = record
    return record


@router.post("/{document_id}/ai-extract")
def rerun_ai_extraction(document_id: str):
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = DOCUMENTS[document_id]
    raw_text = doc.get("rawTextPreview", "")
    if not raw_text:
        raise HTTPException(status_code=422, detail="Raw text is not available for this document")
    ai_extraction = run_document_intelligence(raw_text, doc["documentType"])
    doc["aiExtraction"] = ai_extraction
    doc["extracted"] = ai_extraction["structured"]
    doc["fieldConfidence"] = ai_extraction.get("fieldConfidence", {})
    doc["evidence"] = ai_extraction.get("evidence", {})
    doc["validation"] = ai_extraction.get("validation", {})
    doc["extractionConfidence"] = ai_extraction.get("confidence", doc.get("extractionConfidence", 50))
    return doc


@router.get("/{document_id}")
def get_document(document_id: str):
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    return DOCUMENTS[document_id]


@router.post("/{document_id}/approve")
def approve_document(document_id: str, payload: ApproveExtractionRequest):
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = DOCUMENTS[document_id]
    extracted = payload.extracted or doc["extracted"]
    doc_type = doc["documentType"]

    if doc_type == "invoice":
        invoice_id = extracted.get("invoiceNumber") or make_invoice_id()
        invoice = {
            "id": invoice_id,
            "vendor": extracted.get("vendorName") or "Unknown Vendor",
            "category": extracted.get("category") or "Uncategorized",
            "amount": float(extracted.get("totalAmount") or 0),
            "currency": extracted.get("currency") or "USD",
            "submittedDate": extracted.get("invoiceDate") or now_iso()[:10],
            "dueDate": extracted.get("dueDate") or now_iso()[:10],
            "status": "New",
            "risk": "Medium",
            "assignedTo": "AP Automation",
            "invoiceType": extracted.get("invoiceType") or ("PO_BACKED" if extracted.get("poNumber") else "NON_PO_CONTRACT"),
            "primaryMatchType": extracted.get("primaryMatchType") or ("PO" if extracted.get("poNumber") else "CONTRACT"),
            "primaryMatchId": extracted.get("primaryMatchId") or extracted.get("poNumber") or extracted.get("contractId"),
            "poNumber": extracted.get("poNumber"),
            "contractId": extracted.get("contractId"),
            "supportingContractId": None,
            "paymentTerms": extracted.get("paymentTerms"),
            "confidence": extracted.get("confidence", 70),
            "description": "Created from Document Intake Studio.",
            "regulationId": extracted.get("regulationId"),
            "exception": None,
            "approvalTrail": [f"Created from OCR document {document_id}"],
            "aiRecommendation": "Ready for matching.",
            "lineItems": extracted.get("lineItems") or [],
            "tax": extracted.get("tax") or {},
            "taxAmount": extracted.get("taxAmount") or (extracted.get("tax") or {}).get("gstTotal"),
            "taxException": bool(extracted.get("taxException")),
            "tdsSection": extracted.get("tdsSection") or (extracted.get("tax") or {}).get("tdsSection"),
            "billingPeriod": extracted.get("billingPeriod") or {},
            "aiEvidence": doc.get("evidence", {}),
            "fieldConfidence": doc.get("fieldConfidence", {}),
        }
        INVOICES[invoice_id] = invoice
        result = evaluate_invoice(invoice_id)
        entity = INVOICES[invoice_id]
    elif doc_type == "purchase_order":
        po_number = extracted.get("poNumber") or "PO-" + document_id[-5:]
        PURCHASE_ORDERS[po_number] = {
            "poNumber": po_number,
            "vendorName": extracted.get("vendorName") or "Unknown Vendor",
            "category": extracted.get("category") or "Uncategorized",
            "status": "Open",
            "risk": "Low",
            "totalAmount": float(extracted.get("totalAmount") or 0),
            "remainingAmount": float(extracted.get("remainingAmount") or extracted.get("totalAmount") or 0),
            "consumedAmount": 0.0,
            "currency": extracted.get("currency") or "USD",
            "paymentTerms": extracted.get("paymentTerms") or "Net 30",
            "buyer": extracted.get("buyer") or "Procurement",
            "requestedBy": extracted.get("requestedBy") or "Business Requestor",
            "createdDate": extracted.get("poDate") or now_iso()[:10],
            "expectedDeliveryDate": extracted.get("expectedDeliveryDate") or now_iso()[:10],
            "linkedContractId": extracted.get("contractId"),
            "tolerancePercent": float(extracted.get("tolerancePercent") or 5.0),
            "description": "Created from OCR document intake.",
            "lineItems": extracted.get("lineItems") or [],
            "aiEvidence": doc.get("evidence", {}),
            "fieldConfidence": doc.get("fieldConfidence", {}),
        }
        impacted = [evaluate_invoice(i) for i, inv in INVOICES.items() if inv.get("poNumber") == po_number]
        result = {"impactedInvoices": impacted}
        entity = PURCHASE_ORDERS[po_number]
    elif doc_type == "contract":
        contract_id = extracted.get("contractId") or "CTR-" + document_id[-5:]
        CONTRACTS[contract_id] = {
            "id": contract_id,
            "vendor": extracted.get("vendorName") or "Unknown Vendor",
            "category": extracted.get("category") or "Uncategorized",
            "status": "Active",
            "risk": "Low",
            "owner": "Legal Ops",
            "startDate": extracted.get("effectiveDate") or now_iso()[:10],
            "endDate": extracted.get("endDate") or "2027-12-31",
            "value": float(extracted.get("contractValue") or 0),
            "currency": extracted.get("currency") or "USD",
            "paymentTerms": extracted.get("paymentTerms") or "Net 30",
            "tolerancePercent": float(extracted.get("tolerancePercent") or 2.0),
            "linkedPOs": [],
            "summary": "Created from OCR contract extraction.",
            "clauses": extracted.get("clauses") or [],
            "rateCards": extracted.get("rateCards") or [],
            "billingRules": extracted.get("billingRules") or [],
            "taxClauses": extracted.get("taxClauses") or [],
            "aiEvidence": doc.get("evidence", {}),
            "fieldConfidence": doc.get("fieldConfidence", {}),
            "aiFinding": "Contract extraction approved and available for invoice compliance checks.",
        }
        impacted = [evaluate_invoice(i) for i, inv in INVOICES.items() if inv.get("contractId") == contract_id]
        result = {"impactedInvoices": impacted}
        entity = CONTRACTS[contract_id]
    elif doc_type == "regulation":
        regulation_id = extracted.get("regulationId") or "REG-" + document_id[-5:]
        REGULATIONS[regulation_id] = {
            "id": regulation_id,
            "title": extracted.get("title") or "Uploaded AP Regulation",
            "category": extracted.get("category") or "Compliance",
            "jurisdiction": extracted.get("jurisdiction") or "Global",
            "status": "Active",
            "risk": "Medium",
            "owner": "Finance Controls",
            "effectiveDate": now_iso()[:10],
            "lastUpdated": now_iso()[:10],
            "approvalThreshold": float(extracted.get("approvalThreshold") or 50000),
            "requiresPO": bool(extracted.get("requiresPO")),
            "requiresContract": bool(extracted.get("requiresContract")),
            "requiresExceptionDocumentation": bool(extracted.get("requiresExceptionDocumentation")),
            "summary": extracted.get("summary") or "Uploaded AP policy.",
            "guidance": extracted.get("guidance") or [],
            "controls": extracted.get("controls") or [],
            "aiEvidence": doc.get("evidence", {}),
            "fieldConfidence": doc.get("fieldConfidence", {}),
            "aiFinding": "Uploaded regulation is active for future approval checks.",
        }
        impacted = [evaluate_invoice(i) for i in INVOICES]
        result = {"impactedInvoices": impacted}
        entity = REGULATIONS[regulation_id]
    else:
        raise HTTPException(status_code=400, detail="Unsupported document type")

    doc["status"] = "Approved"
    doc["extracted"] = extracted
    doc["linkedEntityId"] = entity.get("id") or entity.get("poNumber")
    return {"document": doc, "entity": entity, "result": result}

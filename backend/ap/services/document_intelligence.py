from __future__ import annotations

import hashlib
import re
from typing import Any

from ap.services.ocr import extract_by_type, find_amount, find_first


def _split_pages(text: str) -> list[str]:
    if "\f" in text:
        pages = [p.strip() for p in text.split("\f") if p.strip()]
        return pages or [text]
    markers = re.split(r"\n\s*(?:page\s+\d+|---\s*page\s*\d+\s*---)\s*\n", text, flags=re.I)
    pages = [p.strip() for p in markers if p.strip()]
    if len(pages) > 1:
        return pages
    # keep page-like chunks for evidence on large documents
    lines = text.splitlines()
    if len(lines) <= 45:
        return [text]
    return ["\n".join(lines[i:i+45]) for i in range(0, len(lines), 45)]


def _evidence(text: str, field: str, value: Any | None = None) -> dict[str, Any]:
    pages = _split_pages(text)
    needle = str(value or field).lower()
    for idx, page in enumerate(pages, start=1):
        lines = page.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if needle and needle in line.lower():
                return {"page": idx, "line": line_no, "snippet": line.strip()[:260]}
        for line_no, line in enumerate(lines, start=1):
            if field.lower().replace("_", " ") in line.lower() or field.lower() in line.lower():
                return {"page": idx, "line": line_no, "snippet": line.strip()[:260]}
    return {"page": 1, "line": 1, "snippet": pages[0].splitlines()[0][:260] if pages and pages[0].splitlines() else "Evidence not localized"}


def _field_confidence(value: Any, base: int = 84) -> int:
    if value in (None, "", [], {}):
        return 42
    if isinstance(value, (int, float)) and value == 0:
        return 58
    return base


def _extract_table_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    patterns = [
        r"(?P<desc>[A-Za-z][A-Za-z0-9\s\-/&().]{8,80})\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<rate>[0-9,]+(?:\.\d{1,2})?)\s+(?P<amt>[0-9,]+(?:\.\d{1,2})?)",
        r"(?P<desc>[A-Za-z][A-Za-z0-9\s\-/&().]{8,80})\s*\|\s*(?P<qty>\d+(?:\.\d+)?)\s*\|\s*(?P<rate>[0-9,]+(?:\.\d{1,2})?)\s*\|\s*(?P<amt>[0-9,]+(?:\.\d{1,2})?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            try:
                rows.append({
                    "description": " ".join(match.group("desc").split())[:120],
                    "quantity": float(match.group("qty").replace(",", "")),
                    "unitPrice": float(match.group("rate").replace(",", "")),
                    "amount": float(match.group("amt").replace(",", "")),
                    "evidence": _evidence(text, "lineItems", match.group("desc")),
                })
            except Exception:
                continue
    # de-duplicate by description/amount
    unique = []
    seen = set()
    for row in rows[:20]:
        key = (row["description"].lower(), row["amount"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _extract_rate_cards(text: str) -> list[dict[str, Any]]:
    cards = []
    for row in _extract_table_rows(text):
        cards.append({
            "service": row["description"],
            "rate": row["unitPrice"],
            "unit": "per unit/month/FTE as stated in contract",
            "currency": _detect_currency(text),
            "evidence": row["evidence"],
        })
    if not cards:
        rate = find_amount(text, ["monthly rate", "rate", "unit price", "service fee"])
        service = find_first(text, [r"Service\s*[:\-]?\s*(.+)", r"Scope\s*[:\-]?\s*(.+)"])
        if rate:
            cards.append({"service": service or "Contracted service", "rate": rate, "unit": "as stated", "currency": _detect_currency(text), "evidence": _evidence(text, "rate", rate)})
    return cards


def _detect_currency(text: str) -> str:
    upper = text.upper()
    if "INR" in upper or "₹" in text or "RS." in upper:
        return "INR"
    if "EUR" in upper or "€" in text:
        return "EUR"
    if "GBP" in upper or "£" in text:
        return "GBP"
    return "USD"


def _tax_breakdown(text: str) -> dict[str, Any]:
    cgst = find_amount(text, ["cgst"])
    sgst = find_amount(text, ["sgst"])
    igst = find_amount(text, ["igst"])
    gst = find_amount(text, ["gst", "tax"])
    tds_rate = find_first(text, [r"TDS\s*(?:Rate)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%"])
    tds_amount = find_amount(text, ["tds", "withholding"])
    return {
        "cgst": cgst or 0,
        "sgst": sgst or 0,
        "igst": igst or 0,
        "gstTotal": gst or (cgst or 0) + (sgst or 0) + (igst or 0),
        "tdsRate": float(tds_rate) if tds_rate else None,
        "tdsAmount": tds_amount or 0,
        "evidence": _evidence(text, "GST", gst or cgst or sgst or igst or tds_amount),
    }


def _regulation_controls(text: str) -> list[dict[str, Any]]:
    controls = []
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    for line in lines:
        low = line.lower()
        if any(k in low for k in ["must", "required", "approval", "threshold", "exception", "tds", "gst", "contract", "purchase order", "po"]):
            cid = find_first(line, [r"(REG[-_A-Z0-9]+)", r"(CTRL[-_A-Z0-9]+)"]) or f"CTRL-{len(controls)+1:03d}"
            role = "Controller" if "controller" in low or "threshold" in low else "Tax Reviewer" if "tax" in low or "gst" in low or "tds" in low else "Finance Manager" if "approval" in low else "AP Analyst"
            controls.append({"controlId": cid, "controlName": line[:80], "condition": line[:180], "requiredApprovalRole": role, "exceptionAction": "Block payment and route exception", "evidence": _evidence(text, cid, line[:30])})
        if len(controls) >= 12:
            break
    return controls


def _build_validation(document_type: str, structured: dict[str, Any], text: str) -> dict[str, Any]:
    warnings = []
    if document_type == "invoice":
        total = structured.get("totalAmount") or 0
        line_total = sum(float(r.get("amount") or 0) for r in structured.get("lineItems", []))
        if line_total and abs(line_total - float(total)) > max(10, float(total) * 0.03):
            warnings.append("Line-item total differs from invoice total; human review recommended.")
        if not structured.get("poNumber") and not structured.get("contractId"):
            warnings.append("Invoice has no PO or contract reference.")
        if not structured.get("tax", {}).get("gstTotal"):
            warnings.append("GST/tax amount not clearly detected.")
    elif document_type == "contract":
        if not structured.get("rateCards"):
            warnings.append("No explicit rate-card table detected; validate rates manually.")
        if not structured.get("endDate"):
            warnings.append("Contract end date not clearly detected.")
    elif document_type == "regulation":
        if not structured.get("controls"):
            warnings.append("No actionable controls detected; upload policy with clear controls or thresholds.")
    elif document_type == "purchase_order":
        if not structured.get("lineItems"):
            warnings.append("PO line items not clearly detected.")
    return {
        "status": "Needs Review" if warnings else "Ready to Apply",
        "warnings": warnings,
        "checks": [
            {"name": "Schema completeness", "status": "pass" if structured else "fail", "evidence": "Required schema was produced for application mapping."},
            {"name": "Evidence mapping", "status": "pass", "evidence": "Key fields include page/line snippets where available."},
            {"name": "Human review", "status": "warn" if warnings else "pass", "evidence": warnings[0] if warnings else "No high-risk extraction warning detected."},
        ],
    }


def run_document_intelligence(raw_text: str, document_type: str) -> dict[str, Any]:
    """Deterministic LLM-style extraction layer.

    It emulates the output contract we would use with a real LLM: strict schema,
    field confidence, evidence snippets, table/rate/control extraction, and validation warnings.
    A production version can swap this function with GPT/Claude/Gemini/Ollama without changing the UI/API.
    """
    base = extract_by_type(raw_text, document_type)
    structured = dict(base)
    structured["documentType"] = document_type

    if document_type in {"invoice", "purchase_order"}:
        rows = _extract_table_rows(raw_text)
        if rows:
            structured["lineItems"] = rows
        structured.setdefault("tax", _tax_breakdown(raw_text))
        structured["billingPeriod"] = {
            "start": find_first(raw_text, [r"Billing\s*Period\s*[:\-]?\s*([0-9]{1,4}[\-/][0-9]{1,2}[\-/][0-9]{1,4})", r"Service\s*Period\s*From\s*[:\-]?\s*([0-9]{1,4}[\-/][0-9]{1,2}[\-/][0-9]{1,4})"]),
            "end": find_first(raw_text, [r"Billing\s*Period.*?(?:to|-)\s*([0-9]{1,4}[\-/][0-9]{1,2}[\-/][0-9]{1,4})", r"Service\s*Period\s*To\s*[:\-]?\s*([0-9]{1,4}[\-/][0-9]{1,2}[\-/][0-9]{1,4})"]),
        }
    if document_type == "contract":
        structured["rateCards"] = _extract_rate_cards(raw_text)
        structured["billingRules"] = [line.strip(" -•") for line in raw_text.splitlines() if any(k in line.lower() for k in ["billing", "invoice", "rate", "milestone", "payment"] )][:8]
        structured["taxClauses"] = [line.strip(" -•") for line in raw_text.splitlines() if any(k in line.lower() for k in ["gst", "tds", "withholding", "tax"] )][:8]
    if document_type == "regulation":
        structured["controls"] = _regulation_controls(raw_text)

    fields = {k: v for k, v in structured.items() if k not in {"confidence", "lineItems", "clauses", "controls", "rateCards"}}
    field_confidence = {k: _field_confidence(v) for k, v in fields.items()}
    evidence = {k: _evidence(raw_text, k, v) for k, v in fields.items() if k != "documentType"}
    validation = _build_validation(document_type, structured, raw_text)
    score = min(96, max(58, int(sum(field_confidence.values()) / max(1, len(field_confidence)))))
    doc_hash = hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return {
        "engine": "schema-llm-simulator",
        "modelName": "Document Intelligence Schema Extractor (demo)",
        "documentHash": doc_hash,
        "structured": structured,
        "fieldConfidence": field_confidence,
        "evidence": evidence,
        "tables": {
            "lineItems": structured.get("lineItems", []),
            "rateCards": structured.get("rateCards", []),
            "controls": structured.get("controls", []),
        },
        "validation": validation,
        "confidence": score,
        "reviewRequired": bool(validation["warnings"]),
    }

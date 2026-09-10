from __future__ import annotations

from typing import Any
from ap.store import CONTRACTS, INVOICES, PURCHASE_ORDERS, REGULATIONS, now_iso


def risk_rank(risk: str) -> int:
    return {"Low": 1, "Medium": 2, "High": 3}.get(risk, 2)


APPROVAL_STAGES: list[dict[str, Any]] = [
    {
        "role": "AP Analyst",
        "label": "AP Analyst Review",
        "owner": "AP Operations",
        "purpose": "Verify OCR extraction, supplier, PO reference, invoice completeness, and duplicate risk.",
    },
    {
        "role": "Finance Manager",
        "label": "Finance Manager Approval",
        "owner": "Finance Operations",
        "purpose": "Approve budget, PO consumption, materiality threshold, and exception documentation.",
    },
    {
        "role": "Tax Reviewer",
        "label": "Tax Reviewer Check",
        "owner": "Tax Compliance",
        "purpose": "Review GST/TDS, tax registration, withholding, and regulatory tax controls.",
    },
    {
        "role": "Controller",
        "label": "Controller Final Sign-off",
        "owner": "Controllership",
        "purpose": "Final sign-off for high-value, high-risk, override, or policy-exception invoices.",
    },
]


def workflow_required_stages(invoice: dict[str, Any]) -> list[str]:
    amount = float(invoice.get("amount", 0) or 0)
    risk = invoice.get("risk", "Medium")
    category = (invoice.get("category") or "").lower()
    regulation_id = invoice.get("regulationId") or ""
    exception = invoice.get("exception")
    required = ["AP Analyst", "Finance Manager"]
    if risk in ["Medium", "High"] or "tax" in category or "cloud" in category or "DATA" in regulation_id or invoice.get("taxAmount"):
        required.append("Tax Reviewer")
    if amount >= 50000 or risk == "High" or exception or invoice.get("overrideApproved"):
        required.append("Controller")
    return required


def sync_approval_workflow(invoice: dict[str, Any]) -> dict[str, Any]:
    required = workflow_required_stages(invoice)
    existing = {step.get("role"): step for step in invoice.get("approvalWorkflow", [])}
    status = invoice.get("status", "New")
    active_exception = invoice.get("exception") and invoice.get("exception", {}).get("state") != "Resolved"
    # Single source of truth: an invoice is truly Approved only after the
    # role workflow has completed. Some intake/evaluation paths may mark a
    # clean invoice as "Approved" too early; normalize that back to
    # Pending Approval so the current role/button state stays in sync.
    if status == "Approved" and not invoice.get("workflowCompleted"):
        status = "Pending Approval"
        invoice["status"] = "Pending Approval"

    if active_exception:
        assigned_role = invoice.get("assignedTo") if invoice.get("assignedTo") in [stage["role"] for stage in APPROVAL_STAGES] else None
        current_role = assigned_role or "AP Analyst"
        current_state = "Exception Review"
    elif status == "Approved" and invoice.get("workflowCompleted"):
        current_role = "Completed"
        current_state = "Approved"
    elif status == "Payment Ready":
        current_role = "Completed"
        current_state = "Payment Ready"
    elif status == "Regulation Review":
        current_role = "Tax Reviewer"
        current_state = "Tax Review"
    elif status == "Pending Approval":
        # Keep the first required stage that is not already completed.
        current_role = next((role for role in required if existing.get(role, {}).get("status") != "Completed"), "Finance Manager")
        current_state = current_role
    else:
        current_role = "AP Analyst"
        current_state = "AP Analyst"

    workflow: list[dict[str, Any]] = []
    current_seen = False
    for stage in APPROVAL_STAGES:
        role = stage["role"]
        prev = existing.get(role, {})
        step = {**stage}
        step["required"] = role in required
        step["completedAt"] = prev.get("completedAt")
        step["decision"] = prev.get("decision")
        step["note"] = prev.get("note")

        if not step["required"]:
            step["status"] = "Not Required"
        elif status in ["Approved", "Payment Ready"] and invoice.get("workflowCompleted"):
            step["status"] = "Completed"
            step["decision"] = step.get("decision") or "Approved"
            step["completedAt"] = step.get("completedAt") or now_iso()
        elif active_exception and role != current_role:
            step["status"] = "Blocked"
        elif role == current_role:
            step["status"] = "Current"
            current_seen = True
        elif not current_seen and role in required:
            step["status"] = "Completed"
            step["decision"] = step.get("decision") or "System validated"
            step["completedAt"] = step.get("completedAt") or now_iso()
        elif role in required:
            step["status"] = "Pending"
        workflow.append(step)

    invoice["approvalWorkflow"] = workflow
    invoice["currentApprovalRole"] = current_role
    invoice["currentApprovalState"] = current_state
    if current_role == "Completed":
        invoice["assignedTo"] = "AP Automation" if status == "Approved" else invoice.get("assignedTo", "AP Automation")
    elif active_exception:
        invoice["assignedTo"] = current_role
    else:
        invoice["assignedTo"] = current_role
    return invoice


def advance_workflow(invoice_id: str, role: str | None = None, decision: str = "Approved", note: str | None = None) -> dict[str, Any]:
    invoice = sync_approval_workflow(INVOICES[invoice_id])
    if invoice.get("exception") and invoice["exception"].get("state") != "Resolved":
        raise ValueError("Invoice has unresolved exception and cannot move forward in approval workflow.")
    current = invoice.get("currentApprovalRole")
    if current == "Completed":
        return {"invoice": invoice, "message": "Workflow already completed."}
    target = role or current
    updated = False
    for step in invoice.get("approvalWorkflow", []):
        if step.get("role") == target and step.get("required"):
            step["status"] = "Completed"
            step["decision"] = decision
            step["note"] = note or f"{target} completed approval."
            step["completedAt"] = now_iso()
            updated = True
            invoice.setdefault("approvalTrail", []).append(f"{target}: {decision}. {note or ''}".strip())
            break
    if not updated:
        raise ValueError(f"Approval role {target} is not required for this invoice.")

    required = workflow_required_stages(invoice)
    completed = {step["role"] for step in invoice.get("approvalWorkflow", []) if step.get("status") == "Completed"}
    next_role = next((r for r in required if r not in completed), None)
    if next_role:
        invoice["workflowCompleted"] = False
        invoice["status"] = "Pending Approval" if next_role != "Tax Reviewer" else "Regulation Review"
        invoice["assignedTo"] = next_role
    else:
        invoice["workflowCompleted"] = True
        invoice["status"] = "Approved"
        invoice["risk"] = "Low" if invoice.get("risk") != "High" else "Medium"
        invoice["assignedTo"] = "AP Automation"
        invoice["aiRecommendation"] = "Approval workflow completed. Invoice is approved and ready for payment batch simulation."
    sync_approval_workflow(invoice)
    return {"invoice": invoice, "message": "Approval workflow advanced."}


def find_regulation_for_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    if invoice.get("regulationId") and invoice["regulationId"] in REGULATIONS:
        return REGULATIONS[invoice["regulationId"]]
    category = (invoice.get("category") or "").lower()
    if "cloud" in category:
        return REGULATIONS["REG-DATA-004"]
    if invoice.get("amount", 0) >= 50000:
        return REGULATIONS["REG-AUD-002"]
    return REGULATIONS["REG-SOX-001"]


def evaluate_invoice(invoice_id: str) -> dict[str, Any]:
    invoice = INVOICES[invoice_id]
    po = PURCHASE_ORDERS.get(invoice.get("poNumber"))
    contract = CONTRACTS.get(invoice.get("contractId"))
    regulation = find_regulation_for_invoice(invoice)

    checks: list[dict[str, Any]] = []
    exceptions: list[str] = []
    confidence = 55

    if po:
        checks.append({"name": "PO linkage", "status": "pass", "evidence": f"Matched {po['poNumber']}"})
        confidence += 10
        if po.get("vendorName", "").lower() != invoice.get("vendor", "").lower():
            checks.append({"name": "Vendor match", "status": "fail", "evidence": "Invoice vendor differs from PO vendor"})
            exceptions.append("Vendor mismatch")
        else:
            checks.append({"name": "Vendor match", "status": "pass", "evidence": "Invoice vendor matches PO vendor"})
            confidence += 8
        variance = round(float(invoice.get("amount", 0)) - float(po.get("remainingAmount", 0)), 2)
        if variance > 0:
            checks.append({"name": "PO amount", "status": "fail", "evidence": f"Invoice exceeds PO remaining amount by {invoice.get('currency', 'USD')} {variance:,.2f}"})
            exceptions.append("PO Amount Variance")
        else:
            checks.append({"name": "PO amount", "status": "pass", "evidence": "Invoice amount is within PO remaining amount"})
            confidence += 10
    else:
        checks.append({"name": "PO linkage", "status": "fail", "evidence": "Referenced PO was not found"})
        exceptions.append("Missing PO")

    if contract:
        checks.append({"name": "Contract linkage", "status": "pass", "evidence": f"Matched {contract['id']}"})
        confidence += 10
        po_amount = float(po.get("remainingAmount", 0)) if po else float(invoice.get("amount", 0))
        tolerance = float(contract.get("tolerancePercent", 2.0))
        if po_amount > 0:
            variance_pct = abs(float(invoice.get("amount", 0)) - po_amount) / po_amount * 100
        else:
            variance_pct = 0
        if variance_pct > tolerance:
            checks.append({"name": "Contract tolerance", "status": "fail", "evidence": f"Variance {variance_pct:.1f}% exceeds {tolerance:.1f}% tolerance"})
            exceptions.append("Contract Price Tolerance Breach")
        else:
            checks.append({"name": "Contract tolerance", "status": "pass", "evidence": f"Variance {variance_pct:.1f}% is within {tolerance:.1f}% tolerance"})
            confidence += 7
        if contract.get("paymentTerms") and invoice.get("paymentTerms") and contract.get("paymentTerms") != invoice.get("paymentTerms"):
            checks.append({"name": "Payment terms", "status": "warn", "evidence": "Invoice terms differ from contract terms"})
    else:
        checks.append({"name": "Contract linkage", "status": "fail", "evidence": "Referenced contract was not found"})
        exceptions.append("Missing Contract")

    if regulation:
        invoice["regulationId"] = regulation["id"]
        checks.append({"name": "Regulation", "status": "pass", "evidence": f"Applied {regulation['title']}"})
        if regulation.get("requiresPO") and not po:
            exceptions.append("Regulatory PO Control Failure")
        if regulation.get("requiresContract") and not contract:
            exceptions.append("Regulatory Contract Control Failure")
        if float(invoice.get("amount", 0)) >= float(regulation.get("approvalThreshold", 0)) and exceptions:
            checks.append({"name": "Materiality approval", "status": "fail", "evidence": "Material invoice has unresolved exceptions"})
        else:
            checks.append({"name": "Materiality approval", "status": "pass", "evidence": "Regulatory approval conditions satisfied"})
            confidence += 8

    if exceptions:
        severity = "High" if any("Variance" in item or "Regulatory" in item for item in exceptions) else "Medium"
        invoice["status"] = "Exception"
        invoice["risk"] = severity
        invoice["assignedTo"] = "AP Review"
        invoice["exception"] = {
            "id": invoice.get("exception", {}).get("id") if invoice.get("exception") else "EXC-" + invoice_id.replace("INV-", ""),
            "type": exceptions[0],
            "severity": severity,
            "state": "New",
            "owner": "AP Review",
            "dueDate": invoice.get("dueDate"),
            "financialExposure": max(0, float(invoice.get("amount", 0)) - float(po.get("remainingAmount", 0)) if po else float(invoice.get("amount", 0))),
            "rootCause": "; ".join(exceptions),
            "recommendation": "Hold payment until evidence is corrected and approval trail is documented.",
            "evidence": [c["evidence"] for c in checks if c["status"] in ["fail", "warn"]],
            "timeline": [{"time": now_iso(), "event": "Regulations-driven matching evaluated the invoice."}],
        }
        invoice["aiRecommendation"] = "Hold payment and resolve exception before approval."
    else:
        invoice["status"] = "Approved" if float(invoice.get("amount", 0)) < float(regulation.get("approvalThreshold", 50000)) else "Pending Approval"
        invoice["risk"] = "Low"
        invoice["exception"] = None
        invoice["assignedTo"] = "AP Manager" if invoice["status"] == "Pending Approval" else "AP Automation"
        invoice["aiRecommendation"] = "Approval-ready. PO, contract, and regulatory checks passed."

    invoice["confidence"] = min(99, confidence)
    invoice["approvalTrail"] = [c["evidence"] for c in checks]
    sync_approval_workflow(invoice)
    return {
        "invoiceId": invoice_id,
        "status": invoice["status"],
        "risk": invoice["risk"],
        "confidence": invoice["confidence"],
        "regulation": regulation,
        "po": po,
        "contract": contract,
        "checks": checks,
        "exception": invoice.get("exception"),
        "recommendation": invoice["aiRecommendation"],
    }


def resolve_exception(invoice_id: str, action: str, note: str | None = None, owner: str | None = None) -> dict[str, Any]:
    invoice = INVOICES[invoice_id]
    exception = invoice.get("exception")
    if not exception:
        return {"invoice": invoice, "message": "No active exception."}
    exception.setdefault("timeline", []).append({"time": now_iso(), "event": f"{action}: {note or 'No note provided'}"})
    if action in ["Approve Override", "Resolve"]:
        exception["state"] = "Resolved"
        exception["resolvedAt"] = now_iso()
        exception["resolvedBy"] = owner or "AP Review"
        invoice["exceptionResolved"] = True
        invoice["overrideApproved"] = action == "Approve Override"
        invoice["workflowCompleted"] = False
        invoice["status"] = "Pending Approval"
        invoice["risk"] = "Medium" if action == "Approve Override" else "Low"
        invoice["assignedTo"] = invoice.get("currentApprovalRole") or "AP Analyst"
        invoice.setdefault("approvalTrail", []).append(f"Exception {exception['id']} resolved by {action}. {note or ''}".strip())
        invoice["aiRecommendation"] = "Exception documented. Invoice can continue through role-based approval workflow."
    elif action == "Request Vendor Info":
        exception["state"] = "Awaiting Vendor"
        invoice["assignedTo"] = owner or "Vendor Management"
    elif action == "Hold Payment":
        exception["state"] = "In Review"
        invoice["status"] = "Exception"
        invoice["assignedTo"] = owner or "AP Controls"
    else:
        exception["state"] = "In Review"
        invoice["assignedTo"] = owner or exception.get("owner", "AP Review")
    sync_approval_workflow(invoice)
    return {"invoice": invoice, "message": "Exception workflow updated."}

# ---------------------------------------------------------------------------
# Demo-specific approval and regulation engine v2
# ---------------------------------------------------------------------------
def workflow_required_stages(invoice: dict[str, Any]) -> list[str]:  # type: ignore[override]
    amount = float(invoice.get("amount", 0) or 0)
    required = ["AP Analyst", "Finance Manager"]
    if invoice.get("invoiceType") == "NON_PO_CONTRACT" or invoice.get("taxException"):
        required.append("Tax Reviewer")
    if amount >= 250000 or invoice.get("risk") == "High" or invoice.get("exception") or invoice.get("overrideApproved"):
        required.append("Controller")
    out = []
    for role in required:
        if role not in out:
            out.append(role)
    return out


def _reg_control(control_id: str, name: str, result: str, impact: str, role: str, evidence: str) -> dict[str, Any]:
    return {"id": control_id, "name": name, "result": result, "impact": impact, "role": role, "evidence": evidence}


def _money(invoice: dict[str, Any], value: float) -> str:
    return f"{invoice.get('currency', 'INR')} {float(value or 0):,.2f}"


def _find_contract_rate(contract: dict[str, Any] | None, service_text: str) -> float | None:
    if not contract:
        return None
    service_text = (service_text or "").lower()
    for row in contract.get("rateCards", []):
        service = row.get("service", "").lower()
        if service in service_text or service_text in service or "retainer" in service:
            return float(row.get("rate") or 0)
    return None


def find_regulation_for_invoice(invoice: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
    rid = invoice.get("regulationId")
    if rid and rid in REGULATIONS:
        return REGULATIONS[rid]
    if invoice.get("primaryMatchType") == "PO":
        return REGULATIONS["REG-PO-001"]
    if invoice.get("taxException"):
        return REGULATIONS["REG-TAX-004"]
    return REGULATIONS["REG-CTR-001"]


def evaluate_invoice(invoice_id: str) -> dict[str, Any]:  # type: ignore[override]
    invoice = INVOICES[invoice_id]
    invoice_type = invoice.get("invoiceType") or ("PO_BACKED" if invoice.get("poNumber") else "NON_PO_CONTRACT")
    primary = invoice.get("primaryMatchType") or ("PO" if invoice_type == "PO_BACKED" else "CONTRACT")
    invoice["invoiceType"] = invoice_type
    invoice["primaryMatchType"] = primary
    invoice["primaryMatchId"] = invoice.get("poNumber") if primary == "PO" else invoice.get("contractId")
    regulation = find_regulation_for_invoice(invoice)
    checks: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    exceptions: list[str] = []
    confidence = 70

    if primary == "PO":
        po = PURCHASE_ORDERS.get(invoice.get("poNumber"))
        if not po:
            checks.append({"name":"Primary PO match", "status":"fail", "evidence":"PO-backed invoice has no matching PO record"})
            controls.append(_reg_control("REG-PO-001", "PO-backed invoice must reference approved PO", "Failed", "Block approval until PO is uploaded", "AP Analyst", "PO missing"))
            exceptions.append("Missing PO")
        else:
            checks.append({"name":"Primary PO match", "status":"pass", "evidence":f"Primary match is Purchase Order {po['poNumber']}"})
            controls.append(_reg_control("REG-PO-001", "PO-backed invoice must reference approved PO", "Passed", "Continue AP Analyst review", "AP Analyst", f"PO {po['poNumber']} found and marked {po.get('status', 'Open')}"))
            confidence += 12
            if po.get("vendorName", "").lower() == invoice.get("vendor", "").lower():
                checks.append({"name":"Supplier match", "status":"pass", "evidence":"Invoice supplier matches PO supplier"})
                confidence += 8
            else:
                checks.append({"name":"Supplier match", "status":"fail", "evidence":"Invoice supplier differs from PO supplier"})
                controls.append(_reg_control("REG-PO-002", "Supplier must match PO supplier", "Failed", "Block approval until supplier is corrected", "AP Analyst", "Supplier mismatch"))
                exceptions.append("PO Supplier Mismatch")
            tol = float(po.get("tolerancePercent", 5.0) or 5.0)
            allowed = float(po.get("remainingAmount", 0) or 0) * (1 + tol / 100)
            variance = float(invoice.get("amount", 0) or 0) - allowed
            if variance > 0:
                checks.append({"name":"PO amount tolerance", "status":"fail", "evidence":f"Invoice exceeds PO remaining balance plus {tol:.1f}% tolerance by {_money(invoice, variance)}"})
                controls.append(_reg_control("REG-PO-003", "PO amount tolerance", "Failed", "Block Finance Manager approval until exception is resolved", "Finance Manager", f"Invoice {_money(invoice, invoice.get('amount', 0))}; allowed {_money(invoice, allowed)}"))
                exceptions.append("PO Amount Variance")
            else:
                checks.append({"name":"PO amount tolerance", "status":"pass", "evidence":f"Invoice is within PO remaining balance plus {tol:.1f}% tolerance"})
                controls.append(_reg_control("REG-PO-003", "PO amount tolerance", "Passed", "Continue Finance Manager approval", "Finance Manager", f"Invoice {_money(invoice, invoice.get('amount', 0))}; allowed {_money(invoice, allowed)}"))
                confidence += 10
            if invoice.get("supportingContractId"):
                checks.append({"name":"Supporting contract", "status":"pass", "evidence":f"Contract {invoice.get('supportingContractId')} is inherited through PO and shown as supporting evidence only"})
    else:
        contract = CONTRACTS.get(invoice.get("contractId"))
        if not contract:
            checks.append({"name":"Primary contract match", "status":"fail", "evidence":"Non-PO invoice has no matching contract record"})
            controls.append(_reg_control("REG-CTR-001", "Non-PO invoice must match active contract", "Failed", "Block approval until contract is uploaded", "Finance Manager", "Contract missing"))
            exceptions.append("Missing Contract")
        else:
            checks.append({"name":"Primary contract match", "status":"pass", "evidence":f"Primary match is Contract {contract['id']}"})
            controls.append(_reg_control("REG-CTR-001", "Non-PO invoice must match active contract", "Passed", "Continue contract validation", "Finance Manager", f"Contract {contract['id']} is {contract.get('status', 'Active')}"))
            confidence += 12
            billed = (invoice.get("lineItems") or [{}])[0]
            billed_rate = float(billed.get("unitPrice") or invoice.get("amount") or 0)
            contract_rate = _find_contract_rate(contract, billed.get("description", ""))
            if contract_rate and billed_rate > contract_rate:
                checks.append({"name":"Contract rate card", "status":"fail", "evidence":f"Billed rate {_money(invoice, billed_rate)} exceeds contract rate {_money(invoice, contract_rate)}"})
                controls.append(_reg_control("REG-CTR-002", "Contract rate-card match", "Failed", "Block Finance Manager approval until rate exception is resolved", "Finance Manager", f"Billed {_money(invoice, billed_rate)}; contract {_money(invoice, contract_rate)}"))
                exceptions.append("Contract Rate Mismatch")
            else:
                checks.append({"name":"Contract rate card", "status":"pass", "evidence":"Billed rate matches contract rate card"})
                controls.append(_reg_control("REG-CTR-002", "Contract rate-card match", "Passed", "Continue Finance Manager approval", "Finance Manager", "Rate card matched"))
                confidence += 10
        if invoice.get("taxException") or (invoice.get("tdsSection") in [None, ""] and "legal" in (invoice.get("category") or "").lower()):
            checks.append({"name":"GST / TDS compliance", "status":"warn", "evidence":"GST/TDS evidence requires Tax Reviewer confirmation"})
            controls.append(_reg_control("REG-TAX-004", "GST and TDS review", "Review", "Route to Tax Reviewer and block downstream approval", "Tax Reviewer", "TDS section or GST amount is missing/mismatched"))
            exceptions.append("GST / TDS Compliance Review")
        else:
            checks.append({"name":"GST / TDS compliance", "status":"pass", "evidence":"GST and TDS evidence present for professional services"})
            controls.append(_reg_control("REG-TAX-004", "GST and TDS review", "Passed", "Continue Tax Reviewer approval", "Tax Reviewer", "GST/TDS fields present"))
            confidence += 6

    if float(invoice.get("amount", 0) or 0) >= 250000:
        checks.append({"name":"Approval threshold", "status":"warn", "evidence":"Controller approval required by REG-APP-005"})
        controls.append(_reg_control("REG-APP-005", "High-value Controller threshold", "Triggered", "Controller approval required before payment readiness", "Controller", f"Invoice amount {_money(invoice, invoice.get('amount', 0))} exceeds INR 250,000"))
    else:
        controls.append(_reg_control("REG-APP-005", "High-value Controller threshold", "Passed", "Controller approval not required", "Controller", "Below INR 250,000 threshold"))

    invoice["regulationId"] = regulation["id"]
    invoice["regulationResults"] = controls
    invoice["matchSummary"] = {"primaryMatchType": primary, "primaryMatchId": invoice.get("primaryMatchId"), "supportingReference": invoice.get("supportingContractId") if primary == "PO" else None, "decision": "Blocked" if exceptions else "Approval Ready"}
    active_resolution = bool(invoice.get("exceptionResolved")) or (invoice.get("exception") and invoice.get("exception", {}).get("state") == "Resolved")
    if exceptions and not active_resolution:
        severity = "High"
        invoice["status"] = "Regulation Review" if "Compliance" in exceptions[0] else "Exception"
        invoice["risk"] = severity
        if "Compliance" in exceptions[0] or "GST" in exceptions[0] or "TDS" in exceptions[0]:
            invoice["assignedTo"] = "Tax Reviewer"
        elif "Amount" in exceptions[0] or "Rate" in exceptions[0] or "Variance" in exceptions[0] or "Contract" in exceptions[0]:
            invoice["assignedTo"] = "Finance Manager"
        else:
            invoice["assignedTo"] = "AP Analyst"
        previous_exception = invoice.get("exception") if isinstance(invoice.get("exception"), dict) else {}
        timeline = previous_exception.get("timeline") or []
        if not timeline:
            timeline = [{"time": now_iso(), "event": "Regulation engine applied primary-match controls."}]
        invoice["exception"] = {
            "id": previous_exception.get("id") or "EXC-" + invoice_id.replace("INV-", ""),
            "type": exceptions[0],
            "severity": severity,
            "state": previous_exception.get("state", "New"),
            "owner": invoice["assignedTo"],
            "dueDate": invoice.get("dueDate"),
            "financialExposure": float(invoice.get("amount", 0) or 0),
            "rootCause": "; ".join(exceptions),
            "recommendation": "Hold payment and resolve the regulation-marked exception before approval continues.",
            "evidence": [c["evidence"] for c in checks if c["status"] in ["fail", "warn"]],
            "timeline": timeline,
        }
    elif exceptions and active_resolution:
        # Keep the regulation finding visible, but do not block the approval workflow again after resolution/override.
        previous_exception = invoice.get("exception") if isinstance(invoice.get("exception"), dict) else {}
        previous_exception.update({
            "id": previous_exception.get("id") or "EXC-" + invoice_id.replace("INV-", ""),
            "type": previous_exception.get("type") or exceptions[0],
            "severity": previous_exception.get("severity") or "High",
            "state": "Resolved",
            "owner": previous_exception.get("owner") or invoice.get("assignedTo") or "AP Review",
            "dueDate": previous_exception.get("dueDate") or invoice.get("dueDate"),
            "financialExposure": previous_exception.get("financialExposure") or float(invoice.get("amount", 0) or 0),
            "rootCause": previous_exception.get("rootCause") or "; ".join(exceptions),
            "recommendation": "Exception was resolved/overridden. Continue role-based approval with audit trail retained.",
            "evidence": previous_exception.get("evidence") or [c["evidence"] for c in checks if c["status"] in ["fail", "warn"]],
            "timeline": previous_exception.get("timeline") or [{"time": now_iso(), "event": "Exception already resolved; validation finding retained for audit."}],
        })
        invoice["exception"] = previous_exception
        if not invoice.get("workflowCompleted") and invoice.get("status") not in ["Payment Ready"]:
            invoice["status"] = "Pending Approval"
        invoice["risk"] = "Medium" if invoice.get("overrideApproved") else "Low"
        invoice["assignedTo"] = invoice.get("currentApprovalRole") or "AP Analyst"
        invoice["matchSummary"]["decision"] = "Exception Resolved - Approval Ready"
    else:
        invoice["exception"] = None
        invoice["exceptionResolved"] = False
        if not invoice.get("workflowCompleted") and invoice.get("status") not in ["Payment Ready"]:
            invoice["status"] = "Pending Approval"
        invoice["risk"] = "Low" if float(invoice.get("amount", 0) or 0) < 250000 else "Medium"
        invoice["assignedTo"] = invoice.get("currentApprovalRole") or "AP Analyst"
    invoice["confidence"] = min(99, confidence)
    invoice["validationTrail"] = [c["evidence"] for c in checks]
    invoice.setdefault("approvalTrail", [])
    sync_approval_workflow(invoice)
    return {"invoice": invoice, "checks": checks, "regulationResults": controls, "primaryMatchType": primary, "primaryMatchId": invoice.get("primaryMatchId")}

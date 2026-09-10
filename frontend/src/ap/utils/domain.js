export function workflowTone(status) {
  return status === "Completed" ? "success" : status === "Current" ? "info" : status === "Blocked" ? "danger" : status === "Pending" ? "warn" : "neutral";
}

export function currentState(invoice) {
  return invoice?.currentApprovalState || invoice?.assignedTo || invoice?.status || "—";
}

export function canApprove(invoice, user) {
  return Boolean(user && invoice && invoice.currentApprovalRole && invoice.currentApprovalRole !== "Completed" && invoice.currentApprovalRole === user.approvalRole);
}

export function controlTone(result) {
  return result === "Passed" ? "success" : result === "Failed" ? "danger" : result === "Triggered" ? "info" : result === "Review" ? "warn" : "neutral";
}

export function primaryMatchLabel(invoice) {
  if (!invoice) return "—";
  if (invoice.primaryMatchType === "PO") return `PO-backed · ${invoice.primaryMatchId || invoice.poNumber || "PO pending"}`;
  if (invoice.primaryMatchType === "CONTRACT") return `Non-PO contract · ${invoice.primaryMatchId || invoice.contractId || "Contract pending"}`;
  return invoice.poNumber ? `PO-backed · ${invoice.poNumber}` : invoice.contractId ? `Non-PO contract · ${invoice.contractId}` : "Unmatched";
}

function fallbackControls(invoice) {
  const primary = invoice?.primaryMatchType || (invoice?.poNumber ? "PO" : "CONTRACT");
  const amount = Number(invoice?.amount || 0);
  const highValue = amount >= 250000;
  const exception = invoice?.exception && invoice.exception.state !== "Resolved" ? invoice.exception : null;
  if (primary === "PO") {
    return [
      { id: "REG-PO-001", name: "PO-backed invoice must reference approved PO", result: invoice.poNumber ? "Passed" : "Failed", impact: invoice.poNumber ? "Continue AP Analyst review" : "Block approval until PO is uploaded", role: "AP Analyst", evidence: invoice.poNumber ? `PO ${invoice.poNumber} referenced` : "PO missing" },
      { id: "REG-PO-003", name: "PO amount tolerance", result: exception ? "Failed" : "Passed", impact: exception ? "Block Finance Manager approval until exception is resolved" : "Continue Finance Manager approval", role: "Finance Manager", evidence: exception?.evidence?.[0] || "No PO tolerance issue detected" },
      { id: "REG-APP-005", name: "High-value Controller threshold", result: highValue ? "Triggered" : "Passed", impact: highValue ? "Controller approval required" : "Controller approval not required", role: "Controller", evidence: highValue ? `${invoice.currency || "INR"} ${amount.toLocaleString()} exceeds threshold` : "Below threshold" },
    ];
  }
  return [
    { id: "REG-CTR-001", name: "Non-PO invoice must match active contract", result: invoice.contractId ? "Passed" : "Failed", impact: invoice.contractId ? "Continue contract validation" : "Block approval until contract is uploaded", role: "Finance Manager", evidence: invoice.contractId ? `Contract ${invoice.contractId} referenced` : "Contract missing" },
    { id: "REG-CTR-002", name: "Contract rate-card match", result: exception && /rate|contract/i.test(exception.type || "") ? "Failed" : "Passed", impact: exception ? "Block Finance Manager approval until exception is resolved" : "Continue approval workflow", role: "Finance Manager", evidence: exception?.evidence?.[0] || "Rate card matched" },
    { id: "REG-TAX-004", name: "GST and TDS review", result: invoice.taxException || invoice.status === "Regulation Review" ? "Review" : "Passed", impact: invoice.taxException || invoice.status === "Regulation Review" ? "Route to Tax Reviewer" : "Continue Tax Reviewer approval", role: "Tax Reviewer", evidence: invoice.taxException ? "GST/TDS mismatch detected" : "Tax evidence present" },
    { id: "REG-APP-005", name: "High-value Controller threshold", result: highValue ? "Triggered" : "Passed", impact: highValue ? "Controller approval required" : "Controller approval not required", role: "Controller", evidence: highValue ? `${invoice.currency || "INR"} ${amount.toLocaleString()} exceeds threshold` : "Below threshold" },
  ];
}

export function deriveRegulationImpact(invoice, latestMatch = null) {
  if (!invoice) return null;
  const controls = latestMatch?.regulationResults || invoice.regulationResults || fallbackControls(invoice);
  const exceptionResolved = invoice?.exceptionResolved || invoice?.exception?.state === "Resolved";
  const activeException = invoice?.exception && invoice.exception.state !== "Resolved";
  const failed = exceptionResolved ? [] : controls.filter(c => c.result === "Failed");
  const review = exceptionResolved ? [] : controls.filter(c => c.result === "Review");
  const triggered = controls.filter(c => c.result === "Triggered");
  let status = "Passed";
  let tone = "success";
  let primaryControl = controls.find(c => c.result === "Failed")?.id || controls.find(c => c.result === "Review")?.id || controls.find(c => c.result === "Triggered")?.id || `${invoice.regulationId || "REG"} passed`;
  let impact = "Regulation controls allow the invoice to continue through approval.";
  let requiredAction = "No regulation action required.";
  let requiredRole = invoice.currentApprovalRole || invoice.assignedTo || "AP Analyst";
  let evidence = controls.find(c => c.result !== "Passed")?.evidence || controls[0]?.evidence || "Controls evaluated.";

  if (exceptionResolved && controls.some(c => c.result === "Failed" || c.result === "Review")) {
    status = "Resolved";
    tone = "info";
    const c = controls.find(c => c.result === "Failed" || c.result === "Review") || controls[0];
    primaryControl = `${c.id} - ${c.name}`;
    impact = "Regulation finding has been documented and the approval workflow can continue.";
    requiredAction = "Continue role-based approval.";
    requiredRole = invoice.currentApprovalRole || "AP Analyst";
    evidence = c.evidence;
  } else if (failed.length) {
    const c = failed[0];
    status = "Blocked";
    tone = "danger";
    primaryControl = `${c.id} - ${c.name}`;
    impact = c.impact;
    requiredAction = invoice.exception?.recommendation || "Resolve failed regulation control before approving.";
    requiredRole = c.role;
    evidence = c.evidence;
  } else if (review.length) {
    const c = review[0];
    status = "Review Required";
    tone = "warn";
    primaryControl = `${c.id} - ${c.name}`;
    impact = c.impact;
    requiredAction = "Review tax/compliance evidence and record decision.";
    requiredRole = c.role;
    evidence = c.evidence;
  } else if (triggered.length && invoice.currentApprovalRole === "Controller") {
    const c = triggered[0];
    status = "Controller Approval";
    tone = "info";
    primaryControl = `${c.id} - ${c.name}`;
    impact = c.impact;
    requiredAction = "Controller must approve final payment readiness.";
    requiredRole = c.role;
    evidence = c.evidence;
  }

  return {
    status, tone, primaryControl, impact, requiredAction, requiredRole, evidence, controls,
    failedCount: failed.length,
    reviewCount: review.length + triggered.length,
    passedCount: controls.filter(c => c.result === "Passed").length,
  };
}

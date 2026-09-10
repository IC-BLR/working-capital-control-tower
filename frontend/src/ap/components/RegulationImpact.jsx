import React from "react";
import { Scale, ShieldCheck } from "lucide-react";
import { Badge } from "./common.jsx";
import { controlTone, deriveRegulationImpact } from "../utils/domain.js";

export function RegulationImpactCard({ invoice, match, compact = false, onOpen }) {
  const impact = deriveRegulationImpact(invoice, match);
  if (!impact) return null;
  return <div className={`reg-impact-card ${impact.tone} ${compact ? "compact" : ""}`}>
    <div className="reg-impact-main"><Scale size={20}/><div><span>Regulation Impact</span><strong>{impact.status}</strong><p>{impact.impact}</p></div></div>
    <div className="reg-impact-meta">
      <div><span>Primary control</span><strong>{impact.primaryControl}</strong></div>
      <div><span>Required action</span><strong>{impact.requiredAction}</strong></div>
      <div><span>Required role</span><strong>{impact.requiredRole}</strong></div>
    </div>
    {onOpen && <button className="secondary" onClick={onOpen}>View control evidence</button>}
  </div>;
}

export function RegulationApprovalMatrix({ impact }) {
  return <div className="reg-matrix"><h3><ShieldCheck size={20}/> Regulation → Approval Impact</h3>
    <div className="reg-matrix-head"><span>Control</span><span>Result</span><span>Approval impact</span><span>Role</span></div>
    {impact.controls.map(control => <div className="reg-matrix-row" key={control.id}>
      <div><strong>{control.id}</strong><small>{control.name}</small></div>
      <Badge tone={controlTone(control.result)}>{control.result}</Badge>
      <span>{control.impact}</span>
      <strong>{control.role}</strong>
    </div>)}
  </div>;
}

export function RegulationTab({ invoice, match, onOpenEvidence, onOpenPolicy }) {
  const impact = deriveRegulationImpact(invoice, match);
  return <div className="reg-tab-layout">
    <RegulationImpactCard invoice={invoice} match={match} onOpen={onOpenEvidence}/>
    <div className="reg-decision-chain">
      {[
        ["Invoice Uploaded", "OCR and schema extraction completed"],
        ["PO Matched", invoice.poNumber ? `Referenced ${invoice.poNumber}` : "PO evidence missing"],
        ["Contract Validated", invoice.contractId ? `Referenced ${invoice.contractId}` : "Contract evidence missing"],
        ["Regulation Controls Applied", impact.primaryControl],
        ["Approval Route Decided", impact.requiredRole],
      ].map(([title, detail], idx) => <div className="chain-step" key={title}><span>{idx + 1}</span><div><strong>{title}</strong><small>{detail}</small></div></div>)}
    </div>
    <div className="reg-tab-actions"><button className="secondary" onClick={onOpenPolicy}>View full regulation policy</button><button className="ghost" onClick={onOpenEvidence}>Open control evidence</button></div>
    <RegulationApprovalMatrix impact={impact}/>
  </div>;
}

export function RegulationEvidenceLayer({ invoice, match }) {
  const impact = deriveRegulationImpact(invoice, match);
  return <div className="reg-evidence-layer">
    <RegulationImpactCard invoice={invoice} match={match}/>
    <div className="evidence-callout"><strong>Evidence used for approval routing</strong><p>{impact.evidence}</p></div>
    <RegulationApprovalMatrix impact={impact}/>
    <div className="reg-action-box"><h3>Business explanation</h3><p>Regulation controls decide whether this invoice can advance, which role must approve next, and whether payment should be blocked. Failed controls create or maintain exceptions. Review controls route the invoice to the appropriate approver without hiding the evidence.</p></div>
  </div>;
}

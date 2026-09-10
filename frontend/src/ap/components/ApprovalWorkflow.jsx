import React from "react";
import { ShieldCheck } from "lucide-react";
import { Badge } from "./common.jsx";
import { controlTone, currentState, workflowTone } from "../utils/domain.js";

export function ApprovalRail({ invoice, impact }) {
  const workflow = invoice.approvalWorkflow || [];
  const controlsByRole = Object.fromEntries((impact?.controls || []).map(c => [c.role, c]));
  return <div className="approval-rail">{workflow.map((step, idx) => {
    const control = controlsByRole[step.role];
    return <div key={step.role} className={`rail-step ${String(step.status || "").toLowerCase().replaceAll(" ", "-")}`}>
      <span>{idx + 1}</span><strong>{step.role}</strong><small>{step.status}</small>
      {control && <em className={`rail-reg ${controlTone(control.result)}`}>{control.id}: {control.result}</em>}
    </div>;
  })}</div>;
}

export function ApprovalWorkflow({ invoice, user, onAdvance, disabled }) {
  const workflow = invoice.approvalWorkflow || [];
  return <div className="workflow-card in-layer">
    <div className="workflow-header"><div><h3><ShieldCheck size={20}/> Approval workflow</h3><p>AP Analyst → Finance Manager → Tax Reviewer → Controller</p></div><Badge tone="info">Current: {currentState(invoice)}</Badge></div>
    <div className="workflow-steps compact-workflow">{workflow.map((step, idx) => <div className={`workflow-step ${String(step.status || "").toLowerCase().replaceAll(" ", "-")}`} key={step.role}>
      <div className="step-index">{idx + 1}</div>
      <div className="step-body"><div className="step-title"><strong>{step.role}</strong><Badge tone={workflowTone(step.status)}>{step.status}</Badge></div><span>{step.purpose}</span>{step.completedAt && <small>{step.decision || "Completed"} · {step.completedAt}</small>}{step.note && <small>{step.note}</small>}</div>
    </div>)}</div>
    <div className="workflow-footer"><button className="secondary" disabled={disabled || invoice.currentApprovalRole === "Completed"} onClick={onAdvance}>{invoice.currentApprovalRole === "Completed" ? "Workflow complete" : disabled ? `Signed in as ${user?.approvalRole}; waiting for ${invoice.currentApprovalRole}` : `Approve as ${user?.approvalRole}`}</button></div>
  </div>;
}

import React, { useState } from "react";
import { AlertTriangle, BookOpenCheck, Brain, FileSearch, FileText, Radio, RefreshCw, Scale, ShieldCheck, UserRound } from "lucide-react";
import { api } from "../api/client.js";
import { Badge, Layer, Money } from "../components/common.jsx";
import { ApprovalRail, ApprovalWorkflow } from "../components/ApprovalWorkflow.jsx";
import { DocumentMatchCard, DocumentPreviewDrawer, SourceDocumentStrip, buildLinkedDocumentSet } from "../components/DocumentPreviewDrawer.jsx";
import { RegulationEvidenceLayer, RegulationImpactCard, RegulationTab } from "../components/RegulationImpact.jsx";
import { canApprove, currentState, deriveRegulationImpact, primaryMatchLabel } from "../utils/domain.js";

export default function InvoiceApproval({ invoices, pos = [], contracts = [], regulations = [], documents = [], selected, setSelected, onDone, receiveInvoice, user }) {
  const [match, setMatch] = useState(null);
  const [note, setNote] = useState("Variance reviewed and documented for approval trail.");
  const [tab, setTab] = useState("summary");
  const [drawer, setDrawer] = useState(null);
  const [query, setQuery] = useState("");
  const [localBusy, setLocalBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const visibleInvoices = invoices.filter(inv => `${inv.id} ${inv.vendor} ${inv.status} ${currentState(inv)}`.toLowerCase().includes(query.toLowerCase()));

  async function rematch(id) { const r = await api(`/invoices/${id}/match`, { method: "POST" }); setMatch(r); setDrawer("decision"); await onDone(); }
  async function refreshSelected(id) {
    const latest = await api(`/invoices/${id}`);
    setSelected(latest);
    await onDone();
    return latest;
  }

  async function resolve(id, action) {
    setLocalBusy(true);
    setNotice("");
    try {
      const result = await api(`/invoices/${id}/exception/resolve`, { method: "POST", body: JSON.stringify({ action, note, owner: user?.name }) });
      const latest = result.invoice || await api(`/invoices/${id}`);
      setSelected(latest);
      await onDone();
      const resolved = latest?.exception?.state === "Resolved";
      setNotice(`${action} completed. ${resolved ? "Exception resolved — approval workflow can continue." : `Exception state is now ${latest?.exception?.state || "updated"}.`}`);
      if (resolved) setDrawer("workflow");
    } catch (e) {
      setNotice(e.message || "Exception action failed.");
    } finally {
      setLocalBusy(false);
    }
  }

  async function advance(id) {
    setLocalBusy(true);
    setNotice("");
    try {
      const result = await api(`/invoices/${id}/workflow/advance`, { method: "POST", body: JSON.stringify({ decision: "Approved", note }) });
      const latest = result.invoice || await api(`/invoices/${id}`);
      setSelected(latest);
      await onDone();
      setNotice(latest.currentApprovalRole === "Completed" ? "Invoice workflow completed." : `Approved. Next stage: ${latest.currentApprovalRole}.`);
    } catch (e) { setNotice(e.message || "Approval failed."); }
    finally { setLocalBusy(false); }
  }

  const exceptionOpen = selected?.exception && selected.exception.state !== "Resolved";
  const approvalAllowed = canApprove(selected, user);
  const linkedPO = selected ? pos.find(p => p.poNumber === selected.poNumber) : null;
  const linkedContract = selected ? contracts.find(c => c.id === (selected.contractId || selected.supportingContractId) || c.contractId === (selected.contractId || selected.supportingContractId)) : null;
  const linkedRegulation = selected ? regulations.find(r => r.id === selected.regulationId) || regulations[0] : null;
  const linkedDocs = selected ? buildLinkedDocumentSet(selected, linkedPO, linkedContract, linkedRegulation, documents) : {};
  const impact = deriveRegulationImpact(selected, match);
  const openDoc = (kind) => setDrawer(`document:${kind}`);

  return <section className="approval-console">
    <div className="panel approval-list">
      <div className="list-head"><div><h3>Invoice queue</h3><p className="muted-mini">Current state shown for every invoice</p></div><button onClick={() => receiveInvoice(null)}><Radio size={16}/>New</button></div>
      <input className="search-box" placeholder="Search invoice, vendor, state..." value={query} onChange={e => setQuery(e.target.value)} />
      <div className="queue-scroll">{visibleInvoices.map(inv => {
        const rowImpact = deriveRegulationImpact(inv);
        return <button key={inv.id} className={`invoice-row compact-row ${selected?.id === inv.id ? "active" : ""}`} onClick={() => { setSelected(inv); setMatch(null); setTab("summary"); }}>
          <div><strong>{inv.id}</strong><span>{inv.vendor}</span><span className="state-line">{currentState(inv)}</span><span className={`reg-mini ${rowImpact.tone}`}>{rowImpact.status}: {rowImpact.primaryControl}</span></div>
          <div className="queue-amount"><Money value={inv.amount} currency={inv.currency}/></div>
          <div className="row-badges"><Badge tone={inv.risk === "High" ? "danger" : inv.risk === "Medium" ? "warn" : "success"}>{inv.status}</Badge><Badge tone={rowImpact.tone}>{rowImpact.status}</Badge></div>
        </button>;
      })}</div>
    </div>
    <div className="approval-workspace">{selected ? <>
      {notice && <div className={`inline-notice ${notice.toLowerCase().includes("failed") || notice.toLowerCase().includes("only ") ? "danger" : "success"}`} onClick={() => setNotice("")}>{notice}</div>}
      <div className="approval-sticky-head">
        <div className="detail-head compact-detail-head"><div><p className="eyebrow">Invoice approval cockpit</p><h2>{selected.id} · {selected.vendor}</h2><p className="state-summary">Current state: <strong>{currentState(selected)}</strong> · Assigned to <strong>{selected.assignedTo || selected.currentApprovalRole || "—"}</strong> · Signed in as <strong>{user.approvalRole}</strong></p></div><div className="status-stack"><Badge tone={selected.risk === "High" ? "danger" : selected.risk === "Medium" ? "warn" : "success"}>{selected.risk} risk</Badge><Badge tone="info">{selected.status}</Badge><Badge tone={impact.tone}>{impact.status}</Badge></div></div>
        <RegulationImpactCard invoice={selected} match={match} compact={true} onOpen={() => { setTab("regulation"); setDrawer("regulationEvidence"); }}/>
        <ApprovalRail invoice={selected} impact={impact}/>
        <div className="approval-toolbar">
          <button onClick={() => rematch(selected.id)}><RefreshCw size={17}/>Validate</button>
          <button className="secondary" onClick={() => advance(selected.id)} disabled={localBusy || exceptionOpen || !approvalAllowed || selected.currentApprovalRole === "Completed"}>{selected.currentApprovalRole === "Completed" ? "Workflow completed" : exceptionOpen ? "Resolve exception first" : approvalAllowed ? `Approve as ${user.approvalRole}` : `Waiting for ${selected.currentApprovalRole}`}</button>
          <button className="secondary" onClick={() => setDrawer("workflow")}>Workflow</button>
          {selected.exception && <button className="danger-btn" onClick={() => setDrawer("exception")}><AlertTriangle size={16}/>Exception</button>}
        </div>
      </div>
      <div className="approval-tabs">{[["summary","Summary"],["matching","Matching"],["regulation","Regulation"],["trail","Audit Trail"]].map(([id,label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}</div>
      <div className="tab-surface">
        {tab === "summary" && <SummaryTab selected={selected} user={user} approvalAllowed={approvalAllowed} match={match} linkedPO={linkedPO} linkedContract={linkedContract} linkedRegulation={linkedRegulation} openDoc={openDoc} setDrawer={setDrawer} setTab={setTab}/>} 
        {tab === "matching" && <MatchingTab selected={selected} linkedPO={linkedPO} linkedContract={linkedContract} linkedRegulation={linkedRegulation} match={match} openDoc={openDoc} rematch={rematch}/>} 
        {tab === "regulation" && <RegulationTab invoice={selected} match={match} onOpenEvidence={() => setDrawer("regulationEvidence")} onOpenPolicy={() => openDoc("regulation")}/>} 
        {tab === "trail" && <AuditTrail selected={selected}/>} 
      </div>
    </> : <div className="empty"><p>Select an invoice to inspect the approval state.</p></div>}</div>

    {drawer === "workflow" && <Layer title="Approval Workflow" icon={<ShieldCheck size={22}/>} onClose={() => setDrawer(null)}><ApprovalWorkflow invoice={selected} user={user} onAdvance={() => advance(selected.id)} disabled={localBusy || exceptionOpen || !approvalAllowed}/></Layer>}
    {drawer === "exception" && selected?.exception && <Layer title="Exception Resolution" icon={<AlertTriangle size={22}/>} onClose={() => setDrawer(null)}><ExceptionPanel invoice={selected} note={note} setNote={setNote} resolve={resolve} busy={localBusy} notice={notice}/></Layer>}
    {drawer === "decision" && <Layer title="Decision Evidence" icon={<Brain size={22}/>} onClose={() => setDrawer(null)}><DecisionPanel match={match} selected={selected} rematch={rematch}/></Layer>}
    {drawer === "regulationEvidence" && <Layer title="Regulation Evidence" icon={<Scale size={22}/>} onClose={() => setDrawer(null)}><RegulationEvidenceLayer invoice={selected} match={match}/></Layer>}
    {drawer?.startsWith("document:") && <Layer title={`Full ${drawer.split(":")[1]} document`} icon={<FileSearch size={22}/>} onClose={() => setDrawer(null)}><DocumentPreviewDrawer kind={drawer.split(":")[1]} invoice={selected} po={linkedPO} contract={linkedContract} regulation={linkedRegulation} uploadedDoc={linkedDocs[drawer.split(":")[1]]}/></Layer>}
  </section>;
}

function SummaryTab({ selected, user, approvalAllowed, match, linkedPO, linkedContract, linkedRegulation, openDoc, setDrawer, setTab }) {
  return <div className="summary-grid">
    <div className="kpi-card"><span>Invoice Amount</span><strong><Money value={selected.amount} currency={selected.currency}/></strong></div>
    <div className="kpi-card"><span>Invoice Type</span><strong>{selected.invoiceType === "NON_PO_CONTRACT" ? "Non-PO Contract" : "PO-backed"}</strong></div>
    <div className="kpi-card"><span>Primary Match</span><strong>{primaryMatchLabel(selected)}</strong></div>
    <div className="kpi-card"><span>OCR Confidence</span><strong>{selected.confidence || 0}%</strong></div>
    <div className="summary-wide recommendation"><Brain size={18}/>{selected.aiRecommendation}</div>
    <div className={`summary-wide role-gate ${approvalAllowed ? "allowed" : "blocked"}`}><UserRound size={18}/>{approvalAllowed ? `You can approve this stage as ${user.approvalRole}.` : selected.currentApprovalRole === "Completed" ? "Workflow is complete." : `This stage is assigned to ${selected.currentApprovalRole}. Sign in with that role to approve.`}</div>
    <div className="summary-wide quick-panels">
      <button className="info-tile" onClick={() => setDrawer("workflow")}><ShieldCheck size={20}/><strong>Approval workflow</strong><span>AP Analyst → Finance Manager → Tax Reviewer → Controller</span></button>
      <button className="info-tile" onClick={() => setDrawer("exception")} disabled={!selected.exception}><AlertTriangle size={20}/><strong>Exception layer</strong><span>{selected.exception ? selected.exception.type : "No active exception"}</span></button>
      <button className="info-tile regulation-tile" onClick={() => { setTab("regulation"); setDrawer("regulationEvidence"); }}><Scale size={20}/><strong>Regulation impact</strong><span>{deriveRegulationImpact(selected, match).impact}</span></button>
      <button className="info-tile" onClick={() => setDrawer("decision")}><Brain size={20}/><strong>Decision evidence</strong><span>{match ? "Latest validation available" : "Run validation to refresh evidence"}</span></button>
    </div>
    <SourceDocumentStrip invoice={selected} linkedPO={linkedPO} linkedContract={linkedContract} linkedRegulation={linkedRegulation} onOpen={openDoc}/>
  </div>;
}

function MatchingTab({ selected, linkedPO, linkedContract, linkedRegulation, openDoc, rematch }) {
  const impact = deriveRegulationImpact(selected);
  const primary = selected.primaryMatchType || (selected.poNumber ? "PO" : "CONTRACT");
  return <div className="matching-doc-grid">
    {primary === "PO" ? <>
      <DocumentMatchCard title="Primary Purchase Order Match" icon={<FileText size={20}/>} id={selected.poNumber} status={linkedPO?.status || (selected.poNumber ? "Referenced" : "Missing")} detail={linkedPO ? `${linkedPO.vendorName} · ${linkedPO.currency || selected.currency} ${Number(linkedPO.remainingAmount || linkedPO.totalAmount || 0).toLocaleString()} remaining · PO is the approval evidence` : "No linked PO record found"} onOpen={() => openDoc("po")} disabled={!selected.poNumber}/>
      <DocumentMatchCard title="Supporting Contract Reference" icon={<BookOpenCheck size={20}/>} id={selected.supportingContractId || linkedPO?.linkedContractId || "Inherited via PO"} status="Supporting only" detail="Shown for evidence. This invoice is not contract-matched directly; contract is inherited through the purchase order." onOpen={() => openDoc("contract")} disabled={!selected.supportingContractId && !linkedPO?.linkedContractId}/>
    </> : <>
      <DocumentMatchCard title="Primary Contract Match" icon={<BookOpenCheck size={20}/>} id={selected.contractId} status={linkedContract?.status || (selected.contractId ? "Referenced" : "Missing")} detail={linkedContract ? `${linkedContract.vendor || linkedContract.vendorName} · ${linkedContract.paymentTerms || "terms available"} · rate-card validation` : "No linked contract record found"} onOpen={() => openDoc("contract")} disabled={!selected.contractId}/>
      <DocumentMatchCard title="Purchase Order" icon={<FileText size={20}/>} id="Not applicable" status="Not required" detail="This is a non-PO contract invoice, so the contract is the primary matching evidence." onOpen={() => openDoc("po")} disabled={true}/>
    </>}
    <DocumentMatchCard title="Regulation Policy" icon={<Scale size={20}/>} id={selected.regulationId || linkedRegulation?.id} status={impact.status} detail={impact.impact} onOpen={() => openDoc("regulation")} />
    <DocumentMatchCard title="Source Invoice" icon={<FileSearch size={20}/>} id={selected.id} status={selected.status} detail={`${selected.vendor} · ${selected.paymentTerms || "payment terms pending"}`} onOpen={() => openDoc("invoice")} />
    <button onClick={() => rematch(selected.id)}><RefreshCw size={17}/>Run latest checks</button>
  </div>;
}

function AuditTrail({ selected }) {
  return <div className="audit-list">{(selected.approvalTrail || selected.timeline || []).map((e, idx) => <div className="audit-row" key={idx}><span>{e.timestamp || e.createdAt || "—"}</span><strong>{e.actor || e.owner || e.role || "System"}</strong><p>{e.action || e.decision || e.note || e}</p></div>)}</div>;
}

function ExceptionPanel({ invoice, note, setNote, resolve, busy, notice }) {
  const state = invoice.exception?.state || "New";
  const isResolved = state === "Resolved";
  return <div className="exception layer-exception">
    <div className={`exception-state-banner ${isResolved ? "resolved" : "active"}`}>
      <strong>{isResolved ? "Resolved exception" : `Active exception · ${state}`}</strong>
      <span>{isResolved ? "The invoice can now continue through the approval workflow." : "Approval remains blocked until Resolve exception or Approve override is completed."}</span>
    </div>
    {notice && <div className={`inline-notice ${notice.toLowerCase().includes("failed") ? "danger" : "success"}`}>{notice}</div>}
    <h3><AlertTriangle size={20}/> {invoice.exception.type}</h3>
    <p>{invoice.exception.rootCause}</p>
    <ul>{invoice.exception.evidence?.map((e, idx) => <li key={idx}>{e}</li>)}</ul>
    <label className="field-label">Resolution / approval note</label>
    <textarea value={note} onChange={e => setNote(e.target.value)} />
    <div className="action-row">
      <button className="danger-btn" disabled={busy || isResolved} onClick={() => resolve(invoice.id, "Hold Payment")}>Hold payment</button>
      <button className="secondary" disabled={busy || isResolved} onClick={() => resolve(invoice.id, "Request Vendor Info")}>Request vendor info</button>
      <button disabled={busy || isResolved} onClick={() => resolve(invoice.id, "Resolve")}>{busy ? "Working..." : "Resolve exception"}</button>
      <button disabled={busy || isResolved} onClick={() => resolve(invoice.id, "Approve Override")}>{busy ? "Working..." : "Approve override"}</button>
    </div>
    <div className="helper-note">Demo behavior: Hold / Request Vendor Info updates the exception state. Resolve / Approve Override clears the blocker and reopens the role-based approval workflow.</div>
  </div>;
}

function DecisionPanel({ match, selected, rematch }) {
  return <div className="decision-panel"><p className="recommendation"><Brain size={18}/>{selected.aiRecommendation}</p>{match ? match.checks.map((c, i) => <div className="check" key={i}><Badge tone={c.status === "fail" ? "danger" : c.status === "warn" ? "warn" : "success"}>{c.status}</Badge><strong>{c.name}</strong><span>{c.evidence}</span></div>) : <div className="empty"><p>No latest validation result in this session.</p><button onClick={() => rematch(selected.id)}><RefreshCw size={17}/>Run PO + contract + regulation checks</button></div>}</div>;
}

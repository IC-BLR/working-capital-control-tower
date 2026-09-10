import React, { useState } from "react";
import { Brain, CheckCircle2, FileSearch, UploadCloud } from "lucide-react";
import { api } from "../api/client.js";
import { Badge } from "../components/common.jsx";

export default function Intake({ onDone }) {
  const [file, setFile] = useState(null);
  const [type, setType] = useState("auto");
  const [doc, setDoc] = useState(null);
  const [json, setJson] = useState("");
  const [reviewTab, setReviewTab] = useState("fields");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function extract() {
    if (!file) return setMessage("Choose a PDF, image, or .txt demo file first.");
    setBusy(true); setMessage("");
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("documentType", type);
      const result = await api("/documents/extract", { method: "POST", body: fd });
      setDoc(result); setJson(JSON.stringify(result.extracted, null, 2)); setReviewTab("fields");
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }
  async function rerunAi() {
    if (!doc) return;
    setBusy(true);
    try {
      const result = await api(`/documents/${doc.id}/ai-extract`, { method: "POST" });
      setDoc(result); setJson(JSON.stringify(result.extracted, null, 2)); setMessage("Document intelligence extraction refreshed.");
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }
  async function approve() {
    setBusy(true);
    try {
      const result = await api(`/documents/${doc.id}/approve`, { method: "POST", body: JSON.stringify({ extracted: JSON.parse(json) }) });
      setDoc(result.document); setMessage(`Approved and linked to ${result.document.linkedEntityId}. Related invoices were re-evaluated.`); await onDone();
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }
  function sample(text, name) { const blob = new Blob([text], { type: "text/plain" }); setFile(new File([blob], name, { type: "text/plain" })); }
  const warnings = doc?.validation?.warnings || [];
  const tableCount = (doc?.aiExtraction?.tables?.lineItems?.length || 0) + (doc?.aiExtraction?.tables?.rateCards?.length || 0) + (doc?.aiExtraction?.tables?.controls?.length || 0);
  return <section className="two-col intake-layout">
    <div className="panel upload-panel">
      <h3><UploadCloud size={20}/> AI Document Intake Studio</h3>
      <p>Upload invoices, purchase orders, contracts, and regulations. OCR plus document intelligence extracts evidence, confidence, tables, clauses, controls, and warnings before applying data to the application.</p>
      <div className="capability-strip"><Badge tone="info">OCR</Badge><Badge tone="info">LLM-style schema</Badge><Badge tone="info">Evidence</Badge><Badge tone="info">Review & Apply</Badge></div>
      <select value={type} onChange={e => setType(e.target.value)}><option value="auto">Auto classify</option><option value="invoice">Invoice</option><option value="purchase_order">Purchase Order</option><option value="contract">Contract</option><option value="regulation">Regulation</option></select>
      <label className="drop"><input type="file" onChange={e => setFile(e.target.files?.[0])}/><UploadCloud size={32}/><strong>{file?.name || "Drop or choose complex document"}</strong><span>PDF, image, or text sample</span></label>
      <button onClick={extract} disabled={busy}>{busy ? "Processing..." : "Extract with Document Intelligence"}</button>
      <div className="sample-grid">
        <button className="ghost" onClick={() => sample("Invoice Number: INV-55501\nVendor: Apex Components\nGSTIN: 29ABCDE1234F1Z5\nPO Number: PO-77994\nContract ID: CTR-7729\nBilling Period: 2026-05-01 to 2026-05-31\nDescription | Qty | Unit Price | Amount\nCloud platform subscription | 120 | 525.00 | 63000.00\nPremium support hours | 24 | 550.00 | 13200.00\nSubtotal: USD 76200\nGST: USD 13716\nTDS Rate: 10%\nTDS: USD 7620\nInvoice Total: USD 89916\nPayment Terms: Net 45", "complex-invoice.txt")}>Complex invoice</button>
        <button className="ghost" onClick={() => sample("Purchase Order Number: PO-99977\nVendor: Northstar Logistics\nBuyer: Procurement Ops\nRequested By: Infrastructure Services\nContract ID: CTR-9014\nItem | Qty | Unit Price | Amount\nManaged transport lane A | 12 | 1800.00 | 21600.00\nEmergency freight reserve | 4 | 5100.00 | 20400.00\nPO Total: USD 42000\nPayment Terms: Net 30", "complex-po.txt")}>Complex PO</button>
        <button className="ghost" onClick={() => sample("Contract ID: CTR-99977\nVendor: Apex Components\nCategory: Cloud Services\nEffective Date: 2026-01-01\nEnd Date: 2026-12-31\nContract Value: USD 900000\nPayment Terms: Net 45\nTolerance: 2%\nRate Card\nCloud platform subscription | 1 | 525.00 | 525.00\nPremium support hours | 1 | 550.00 | 550.00\nBilling rule: invoices must cover monthly service periods only.\nTax clause: GST and TDS must be shown separately.", "complex-contract.txt")}>Contract + rate card</button>
        <button className="ghost" onClick={() => sample("Policy ID: REG-NEW-010\nTitle: Material Invoice Approval Policy\nCategory: Audit\nJurisdiction: India\nApproval Threshold: USD 50000\nREG-001: Invoices must have purchase order linkage.\nREG-002: All invoices above threshold require Finance Manager approval.\nREG-003: GST and TDS evidence must be reviewed by Tax Reviewer.\nREG-004: Missing contract or rate card mismatch must block payment.\nREG-005: Controller approval is required for override payments.", "complex-regulation.txt")}>Policy controls</button>
      </div>
      {message && <div className="message">{message}</div>}
    </div>
    <div className="panel review-panel doc-intel-panel">
      <h3><FileSearch size={20}/> Document Review & Apply</h3>
      {doc ? <>
        <div className="doc-summary"><Badge tone="info">{doc.documentType}</Badge><Badge>{doc.classificationConfidence}% classified</Badge><Badge>{doc.extractionConfidence}% AI extracted</Badge><Badge tone={warnings.length ? "warn" : "success"}>{warnings.length ? `${warnings.length} warnings` : "Ready"}</Badge><Badge>{tableCount} tables/controls</Badge></div>
        <div className="review-tabs">{[["fields","Fields"],["tables","Tables / Clauses"],["evidence","Evidence"],["warnings","Validation"],["json","JSON"]].map(([id,label]) => <button key={id} className={reviewTab === id ? "active" : ""} onClick={() => setReviewTab(id)}>{label}</button>)}</div>
        <div className="review-surface">
          {reviewTab === "fields" && <FieldConfidenceGrid fields={doc.extracted} confidence={doc.fieldConfidence}/>} 
          {reviewTab === "tables" && <IntakeDocumentTables doc={doc}/>} 
          {reviewTab === "evidence" && <EvidenceGrid evidence={doc.evidence}/>} 
          {reviewTab === "warnings" && <ValidationPanel validation={doc.validation}/>} 
          {reviewTab === "json" && <textarea value={json} onChange={e => setJson(e.target.value)} />}
        </div>
        <div className="action-row"><button className="secondary" onClick={rerunAi} disabled={busy}><Brain size={18}/>Re-run AI extraction</button><button onClick={approve} disabled={busy}><CheckCircle2 size={18}/>Approve & apply to app</button></div>
      </> : <div className="empty"><p>Extracted fields, tables, confidence, evidence, warnings, and JSON will appear here for review and correction before application records are created.</p></div>}
    </div>
  </section>;
}

function FieldConfidenceGrid({ fields = {}, confidence = {} }) {
  const entries = Object.entries(fields).filter(([k]) => !["lineItems","rateCards","controls","clauses","billingRules","taxClauses"].includes(k));
  return <div className="field-confidence-grid">{entries.map(([k,v]) => <div className="confidence-row" key={k}><span>{k}</span><strong>{typeof v === "object" ? JSON.stringify(v) : String(v ?? "—")}</strong><Badge tone={(confidence[k] || 0) > 80 ? "success" : (confidence[k] || 0) > 60 ? "warn" : "danger"}>{confidence[k] || 0}%</Badge></div>)}</div>;
}

function IntakeDocumentTables({ doc }) {
  const tables = doc?.aiExtraction?.tables || {};
  const groups = [["Line items", tables.lineItems || []], ["Rate cards", tables.rateCards || []], ["Regulation controls", tables.controls || []], ["Clauses", doc?.extracted?.clauses || []]];
  return <div className="doc-table-groups">{groups.map(([title, rows]) => <div className="mini-table" key={title}><h4>{title}</h4>{rows.length ? rows.map((row, idx) => <pre key={idx}>{JSON.stringify(row, null, 2)}</pre>) : <p className="muted-mini">No {title.toLowerCase()} detected.</p>}</div>)}</div>;
}

function EvidenceGrid({ evidence = {} }) {
  const entries = Object.entries(evidence);
  return <div className="evidence-grid">{entries.length ? entries.map(([field, ev]) => <div className="evidence-card" key={field}><strong>{field}</strong><span>Page {ev.page || 1}, line {ev.line || 1}</span><p>{ev.snippet}</p></div>) : <p>No evidence mapped yet.</p>}</div>;
}

function ValidationPanel({ validation = {} }) {
  return <div className="validation-panel"><Badge tone={validation.status === "Ready to Apply" ? "success" : "warn"}>{validation.status || "Not validated"}</Badge>{validation.warnings?.length ? <ul>{validation.warnings.map((w,i) => <li key={i}>{w}</li>)}</ul> : <p>No high-risk extraction warnings detected.</p>}<div className="compact-cards">{validation.checks?.map((c,i) => <div className="check" key={i}><Badge tone={c.status === "pass" ? "success" : c.status === "warn" ? "warn" : "danger"}>{c.status}</Badge><strong>{c.name}</strong><span>{c.evidence}</span></div>)}</div></div>;
}

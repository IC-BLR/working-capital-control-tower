import React from "react";
import { FileText, Scale, ShieldCheck } from "lucide-react";
import { api } from "../api/client.js";
import { Badge, Field, Money } from "../components/common.jsx";

export default function Regulations({ regulations, invoices, onDone }) {
  async function apply(id) { await api(`/regulations/${id}/apply`, { method: "POST" }); await onDone(); }
  return <section className="grid-stack">
    <div className="panel"><h3><Scale size={20}/> Regulations knowledgebase</h3><p>Regulations actively shape invoice decisions: approval threshold, required PO, required contract, exception documentation, and routed approver.</p></div>
    <div className="card-grid">{regulations.map(r => <div className="record-card" key={r.id}><div className="record-title"><ShieldCheck size={20}/><div><strong>{r.title}</strong><span>{r.id} · {r.jurisdiction}</span></div></div><p>{r.summary}</p><div className="field-grid compact"><Field label="Threshold" value={<Money value={r.approvalThreshold}/>}/><Field label="Requires PO" value={r.requiresPO ? "Yes" : "No"}/><Field label="Requires Contract" value={r.requiresContract ? "Yes" : "No"}/><Field label="Risk" value={r.risk}/></div><ul>{r.guidance?.map((g, i) => <li key={i}>{g}</li>)}</ul><button onClick={() => apply(r.id)}>Apply to material invoices</button></div>)}</div>
    <div className="panel"><h3>Regulation impact</h3>{invoices.map(i => <div className="list-row" key={i.id}><FileText size={18}/><div><strong>{i.id} · {i.vendor}</strong><span>{i.regulationId} → {i.status}</span></div><Badge tone={i.risk === "High" ? "danger" : i.risk === "Medium" ? "warn" : "success"}>{i.risk}</Badge></div>)}</div>
  </section>;
}

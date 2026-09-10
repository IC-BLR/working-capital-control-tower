import React from "react";
import { BookOpenCheck, FileText, UploadCloud } from "lucide-react";
import { Badge, Money } from "../components/common.jsx";

export default function Records({ pos, contracts, documents }) {
  return <section className="grid-stack">
    <div className="two-col">
      <div className="panel"><h3>Purchase orders</h3>{pos.map(p => <div className="list-row" key={p.poNumber}><FileText size={18}/><div><strong>{p.poNumber} · {p.vendorName}</strong><span><Money value={p.remainingAmount} currency={p.currency}/> remaining · {p.linkedContractId}</span></div><Badge tone={p.risk === "High" ? "danger" : p.risk === "Medium" ? "warn" : "success"}>{p.status}</Badge></div>)}</div>
      <div className="panel"><h3>Contracts</h3>{contracts.map(c => <div className="list-row" key={c.id}><BookOpenCheck size={18}/><div><strong>{c.id} · {c.vendor}</strong><span>{c.paymentTerms} · {c.tolerancePercent}% tolerance</span></div><Badge tone={c.risk === "High" ? "danger" : c.risk === "Medium" ? "warn" : "success"}>{c.status}</Badge></div>)}</div>
    </div>
    <div className="panel"><h3>Document intake audit</h3>{documents.length ? documents.map(d => <div className="list-row" key={d.id}><UploadCloud size={18}/><div><strong>{d.filename}</strong><span>{d.documentType} · {d.status} · linked to {d.linkedEntityId || "pending"}</span></div><Badge>{d.extractionConfidence}%</Badge></div>) : <p>No uploaded documents yet.</p>}</div>
  </section>;
}

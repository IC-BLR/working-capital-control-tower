import React from "react";
import { Activity, AlertTriangle, BadgeCheck, FileText, Gavel, Radio, ShieldCheck, UploadCloud } from "lucide-react";
import { Badge } from "../components/common.jsx";

export default function Dashboard({ summary, invoices, regulations, feedEvents, receiveInvoice, setView }) {
  const exception = invoices.find(i => i.status === "Exception");
  return <section className="grid-stack">
    <div className="hero-card">
      <div><p className="eyebrow">Functional demo path</p><h2>Live invoices arrive, OCR extracts, controls validate, exceptions route, and approved invoices become payment-ready.</h2><p>This package demonstrates AP intelligence across invoices, purchase orders, contracts, regulations, and exception handling.</p></div>
      <div className="hero-actions"><button onClick={() => receiveInvoice(null)}><Radio size={18}/>Receive live invoice</button><button className="secondary" onClick={() => setView("intake")}><UploadCloud size={18}/>Upload document</button></div>
    </div>
    <div className="metric-grid">
      <Metric label="Invoices" value={summary?.invoiceCount} icon={FileText}/>
      <Metric label="Approved" value={summary?.approvedCount} icon={BadgeCheck}/>
      <Metric label="Exceptions" value={summary?.exceptionCount} icon={AlertTriangle}/>
      <Metric label="Exposure" value={`$${Number(summary?.financialExposure || 0).toLocaleString()}`} icon={Gavel}/>
    </div>
    <div className="two-col">
      <div className="panel"><h3><Activity size={20}/>Live invoice feed</h3><LiveFeed events={feedEvents}/></div>
      <div className="panel"><h3>Approval scenario</h3>{exception ? <InvoiceMini invoice={exception}/> : <p>No active exceptions.</p>}<button className="secondary" onClick={() => setView("invoices")}>Open invoice workflow</button></div>
    </div>
    <div className="panel"><h3>Active regulations</h3>{regulations.map(r => <div className="list-row" key={r.id}><ShieldCheck size={18}/><div><strong>{r.title}</strong><span>{r.summary}</span></div><Badge tone={r.risk === "High" ? "danger" : "info"}>{r.risk}</Badge></div>)}</div>
  </section>;
}

function Metric({ label, value, icon: Icon }) { return <div className="metric"><Icon size={20}/><span>{label}</span><strong>{value ?? "—"}</strong></div>; }
function InvoiceMini({ invoice }) { return <div className="invoice-mini"><div><strong>{invoice.id}</strong><span>{invoice.vendor}</span></div><Badge tone={invoice.risk === "High" ? "danger" : invoice.risk === "Medium" ? "warn" : "success"}>{invoice.status}</Badge><p>{invoice.aiRecommendation}</p></div>; }
function LiveFeed({ events }) { return <div className="feed-list">{events.length ? events.map(e => <div className="feed-event" key={e.id}><div className="pulse-dot"/><div><strong>{e.title}</strong><span>{e.detail}</span><small>{e.createdAt}</small></div></div>) : <p className="empty-small">No live invoices received yet. Click Receive new invoice.</p>}</div>; }

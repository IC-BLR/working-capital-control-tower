import React from "react";
import { Activity, AlertTriangle, BadgeCheck, FileText, Gavel, Radio, ShieldCheck, UploadCloud } from "lucide-react";
import { Badge } from "../components/common.jsx";
import { formatMoney } from "../../lib/formatMoney";
import KpiTile from "../../components/KpiTile";

export default function Dashboard({ summary, invoices, regulations, feedEvents, receiveInvoice, setView }) {
  const exception = invoices.find((i) => i.status === "Exception");
  return (
    <section className="grid-stack">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Invoices" value={summary?.invoiceCount ?? "—"} icon={FileText} tone="slate" />
        <KpiTile label="Approved" value={summary?.approvedCount ?? "—"} icon={BadgeCheck} tone="emerald" />
        <KpiTile label="Exceptions" value={summary?.exceptionCount ?? "—"} icon={AlertTriangle} tone="rose" />
        <KpiTile label="Exposure" value={formatMoney(summary?.financialExposure)} icon={Gavel} tone="amber" />
      </div>
      <div className="two-col">
        <div className="panel">
          <h3>
            <Activity size={20} />
            Live invoice feed
          </h3>
          <LiveFeed events={feedEvents} />
        </div>
        <div className="panel">
          <h3>Approval scenario</h3>
          {exception ? <InvoiceMini invoice={exception} /> : <p>No active exceptions.</p>}
          <button className="secondary" onClick={() => setView("invoices")}>
            Open invoice workflow
          </button>
        </div>
      </div>
      <div className="panel">
        <h3>Active regulations</h3>
        {regulations.map((r) => (
          <div className="list-row" key={r.id}>
            <ShieldCheck size={18} />
            <div>
              <strong>{r.title}</strong>
              <span>{r.summary}</span>
            </div>
            <Badge tone={r.risk === "High" ? "danger" : "info"}>{r.risk}</Badge>
          </div>
        ))}
      </div>
      <div className="panel" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => receiveInvoice(null)}>
          <Radio size={16} />
          Receive live invoice
        </button>
        <button className="secondary" onClick={() => setView("intake")}>
          <UploadCloud size={16} />
          Upload document
        </button>
      </div>
    </section>
  );
}

function InvoiceMini({ invoice }) {
  return (
    <div className="invoice-mini">
      <div>
        <strong>{invoice.id}</strong>
        <span>{invoice.vendor}</span>
      </div>
      <Badge tone={invoice.risk === "High" ? "danger" : invoice.risk === "Medium" ? "warn" : "success"}>{invoice.status}</Badge>
      <p>{invoice.aiRecommendation}</p>
    </div>
  );
}
function LiveFeed({ events }) {
  return (
    <div className="feed-list">
      {events.length ? (
        events.map((e) => (
          <div className="feed-event" key={e.id}>
            <div className="pulse-dot" />
            <div>
              <strong>{e.title}</strong>
              <span>{e.detail}</span>
              <small>{e.createdAt}</small>
            </div>
          </div>
        ))
      ) : (
        <p className="empty-small">No live invoices received yet. Receive an invoice to start.</p>
      )}
    </div>
  );
}

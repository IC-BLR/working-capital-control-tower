import React, { useState } from "react";
import { BookOpenCheck, FileSearch, FileText, Scale, Table2 } from "lucide-react";
import { Badge, Field, Money } from "./common.jsx";
import { deriveRegulationImpact } from "../utils/domain.js";

export function buildLinkedDocumentSet(invoice, po, contract, regulation, documents = []) {
  const matchByEntity = (id) => documents.find(d => d.linkedEntityId === id || d.id === id || d.filename?.includes(id || "__missing__"));
  return {
    invoice: matchByEntity(invoice?.id),
    po: matchByEntity(po?.poNumber || invoice?.poNumber),
    contract: matchByEntity(contract?.id || invoice?.contractId),
    regulation: matchByEntity(regulation?.id || invoice?.regulationId),
  };
}

export function SourceDocumentStrip({ invoice, linkedPO, linkedContract, linkedRegulation, onOpen }) {
  const primary = invoice.primaryMatchType || (invoice.poNumber ? "PO" : "CONTRACT");
  const items = primary === "PO" ? [
    ["invoice", "Source Invoice", invoice.id, invoice.status],
    ["po", "Primary PO", invoice.poNumber || "Missing", linkedPO?.status || "Referenced"],
    ["contract", "Contract via PO", invoice.supportingContractId || linkedPO?.linkedContractId || "Missing", "Supporting"],
    ["regulation", "Regulation Policy", invoice.regulationId || linkedRegulation?.id || "Policy", "Controls"],
  ] : [
    ["invoice", "Source Invoice", invoice.id, invoice.status],
    ["contract", "Primary Contract", invoice.contractId || "Missing", linkedContract?.status || "Referenced"],
    ["po", "Purchase Order", "Not applicable", "Non-PO"],
    ["regulation", "Regulation Policy", invoice.regulationId || linkedRegulation?.id || "Policy", "Controls"],
  ];
  return <div className="source-doc-strip summary-wide">{items.map(([kind, label, id, status]) => <button className="source-doc-chip" key={kind} onClick={() => onOpen(kind)} disabled={id === "Missing" || id === "Not applicable"}>
    <FileSearch size={18}/><span>{label}</span><strong>{id}</strong><Badge>{status}</Badge>
  </button>)}</div>;
}

export function DocumentMatchCard({ title, icon, id, status, detail, onOpen, disabled }) {
  return <div className="match-doc-card">
    <div className="record-title">{icon}<div><strong>{title}</strong><span>{id || "Not linked"}</span></div></div>
    <Badge tone={String(status).toLowerCase().includes("missing") ? "danger" : String(status).toLowerCase().includes("review") ? "warn" : "success"}>{status}</Badge>
    <p>{detail}</p>
    <button className="secondary" disabled={disabled} onClick={onOpen}>View full {title}</button>
  </div>;
}

export function DocumentPreviewDrawer({ kind, invoice, po, contract, regulation, uploadedDoc }) {
  const [tab, setTab] = useState("preview");
  const model = buildDocumentPreviewModel(kind, invoice, po, contract, regulation, uploadedDoc);
  return <div className="doc-preview">
    <div className="doc-preview-head">{model.icon}<div><span>{model.type}</span><strong>{model.title}</strong><p>{model.subtitle}</p></div><Badge tone={model.tone}>{model.status}</Badge></div>
    <div className="review-tabs doc-preview-tabs">{[["preview","Full document"],["fields","Extracted fields"],["tables","Tables / clauses"],["evidence","Evidence"],["json","JSON"]].map(([id,label]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>)}</div>
    <div className="doc-preview-body">
      {tab === "preview" && <pre className="full-doc-text">{model.fullText}</pre>}
      {tab === "fields" && <div className="field-grid compact">{model.fields.map(([label, value]) => <Field key={label} label={label} value={value}/>)}</div>}
      {tab === "tables" && <PreviewDocumentTables model={model}/>} 
      {tab === "evidence" && <div className="evidence-grid">{model.evidence.map((e, i) => <div className="evidence-card" key={i}><strong>{e.title}</strong><span>{e.source}</span><p>{e.snippet}</p></div>)}</div>}
      {tab === "json" && <pre className="json-block">{JSON.stringify(model.raw, null, 2)}</pre>}
    </div>
  </div>;
}

function PreviewDocumentTables({ model }) {
  if (!model.tables?.length) return <p>No tables were modeled for this document.</p>;
  return <div className="doc-table-groups">{model.tables.map((table, i) => <div className="mini-table rich-table" key={i}><h4><Table2 size={16}/>{table.title}</h4><pre>{table.rows.map(row => typeof row === "string" ? row : Object.entries(row).map(([k,v]) => `${k}: ${v}`).join(" | ")).join("\n")}</pre></div>)}</div>;
}

function buildDocumentPreviewModel(kind, invoice, po, contract, regulation, uploadedDoc) {
  const currency = invoice.currency || po?.currency || "USD";
  if (kind === "po") {
    const rows = po?.lineItems || [{ item: "Cloud infrastructure services", quantity: 1, unitPrice: invoice.amount, amount: invoice.amount }, { item: "Managed support and monitoring", quantity: 1, unitPrice: Math.round(invoice.amount * .18), amount: Math.round(invoice.amount * .18) }];
    return { type: "Purchase Order", title: po?.poNumber || invoice.poNumber || "Linked PO", subtitle: `${po?.vendorName || invoice.vendor} · ${po?.paymentTerms || invoice.paymentTerms || "Terms pending"}`, status: po?.status || (invoice.poNumber ? "Referenced" : "Missing"), tone: po ? "success" : "warn", icon: <FileText size={26}/>, fields: [["PO Number", po?.poNumber || invoice.poNumber], ["Vendor", po?.vendorName || invoice.vendor], ["Buyer", po?.buyer || "PhonePe AP Operations"], ["Total Amount", <Money value={po?.totalAmount || invoice.amount} currency={currency}/>], ["Remaining Amount", <Money value={po?.remainingAmount || po?.totalAmount || invoice.amount} currency={currency}/>], ["Linked Contract", po?.linkedContractId || invoice.contractId], ["Payment Terms", po?.paymentTerms || invoice.paymentTerms]], tables: [{ title: "PO line items", rows }], evidence: [{ title: "PO reference", source: "PO header", snippet: `Invoice ${invoice.id} references PO ${invoice.poNumber || "not available"}.` }, { title: "Amount validation", source: "PO financial summary", snippet: `Invoice amount ${currency} ${Number(invoice.amount || 0).toLocaleString()} is compared with PO remaining balance.` }], fullText: generateFullPoText(invoice, po, rows), raw: po || { poNumber: invoice.poNumber, vendor: invoice.vendor, amount: invoice.amount, uploadedDocument: uploadedDoc } };
  }
  if (kind === "contract") {
    const rateRows = contract?.rateCards || [{ service: "Cloud compute unit", rate: `${currency} 42/hour`, billing: "Monthly actuals" }, { service: "Managed support", rate: `${currency} 950/day`, billing: "Monthly retainer" }];
    const clauses = contract?.clauses || ["Payment due within contract terms after invoice approval.", "Invoice variance beyond tolerance requires Finance Manager review.", "Tax and withholding must comply with India AP policy."];
    return { type: "Contract", title: contract?.id || invoice.contractId || "Linked Contract", subtitle: `${contract?.vendor || invoice.vendor} · Validity and rate-card terms`, status: contract?.status || (invoice.contractId ? "Referenced" : "Missing"), tone: contract ? "success" : "warn", icon: <BookOpenCheck size={26}/>, fields: [["Contract ID", contract?.id || invoice.contractId], ["Vendor", contract?.vendor || invoice.vendor], ["Effective Date", contract?.effectiveDate || "2026-01-01"], ["Expiry Date", contract?.endDate || contract?.expiryDate || "2026-12-31"], ["Payment Terms", contract?.paymentTerms || invoice.paymentTerms], ["Tolerance", `${contract?.tolerancePercent ?? 3}%`]], tables: [{ title: "Rate card", rows: rateRows }, { title: "Key clauses", rows: clauses }], evidence: [{ title: "Contract match", source: "Contract header", snippet: `Invoice ${invoice.id} is linked to contract ${invoice.contractId || "not available"}.` }, { title: "Tolerance clause", source: "Commercial terms", snippet: "Contract tolerance is used to determine whether variance requires exception approval." }], fullText: generateFullContractText(invoice, contract, rateRows, clauses), raw: contract || { contractId: invoice.contractId, vendor: invoice.vendor, uploadedDocument: uploadedDoc } };
  }
  if (kind === "regulation") {
    const impact = deriveRegulationImpact(invoice);
    return { type: "Regulation / AP Policy", title: regulation?.title || invoice.regulationId || "AP Regulation Policy", subtitle: `${regulation?.jurisdiction || "India"} · Approval controls and exception routing`, status: impact.status, tone: impact.tone, icon: <Scale size={26}/>, fields: [["Policy ID", regulation?.id || invoice.regulationId], ["Jurisdiction", regulation?.jurisdiction || "India"], ["Approval Threshold", <Money value={regulation?.approvalThreshold || 50000} currency={currency}/>], ["Requires PO", regulation?.requiresPO === false ? "No" : "Yes"], ["Requires Contract", regulation?.requiresContract === false ? "No" : "Yes"], ["Primary Control", impact.primaryControl]], tables: [{ title: "Regulation controls", rows: impact.controls }], evidence: impact.controls.map(c => ({ title: `${c.id} · ${c.name}`, source: c.role, snippet: `${c.result}: ${c.evidence}` })), fullText: generateFullRegulationText(invoice, regulation, impact), raw: regulation || { regulationId: invoice.regulationId, decision: impact, uploadedDocument: uploadedDoc } };
  }
  const lineItems = invoice.lineItems || [{ description: "Services billed for current period", quantity: 1, unitPrice: invoice.amount, amount: invoice.amount }];
  return { type: "Invoice", title: invoice.id, subtitle: `${invoice.vendor} · ${invoice.status}`, status: invoice.status, tone: invoice.risk === "High" ? "danger" : invoice.risk === "Medium" ? "warn" : "success", icon: <FileSearch size={26}/>, fields: [["Invoice ID", invoice.id], ["Vendor", invoice.vendor], ["PO Number", invoice.poNumber], ["Contract ID", invoice.contractId], ["Amount", <Money value={invoice.amount} currency={currency}/>], ["Tax Amount", <Money value={invoice.taxAmount || 0} currency={currency}/>], ["Payment Terms", invoice.paymentTerms], ["Due Date", invoice.dueDate]], tables: [{ title: "Invoice line items", rows: lineItems }], evidence: [{ title: "OCR extraction", source: "Invoice page 1", snippet: `OCR confidence ${invoice.confidence || 0}% for ${invoice.id}.` }, { title: "Approval recommendation", source: "AI decision", snippet: invoice.aiRecommendation || "No recommendation available." }], fullText: generateFullInvoiceText(invoice, lineItems), raw: invoice };
}

function generateFullInvoiceText(invoice, rows) {
  return `INVOICE DOCUMENT\n\nInvoice: ${invoice.id}\nSupplier: ${invoice.vendor}\nPO Number: ${invoice.poNumber || "N/A"}\nContract: ${invoice.contractId || "N/A"}\nPayment Terms: ${invoice.paymentTerms || "N/A"}\nDue Date: ${invoice.dueDate || "N/A"}\nStatus: ${invoice.status}\nRisk: ${invoice.risk}\n\nLine Items\n${rows.map((r, i) => `${i+1}. ${r.description || r.item || r.service || "Service"} | Qty ${r.quantity || 1} | Unit ${r.unitPrice || r.rate || "—"} | Amount ${r.amount || "—"}`).join("\n")}\n\nTotal Amount: ${invoice.currency || "USD"} ${Number(invoice.amount || 0).toLocaleString()}\nTax Amount: ${invoice.currency || "USD"} ${Number(invoice.taxAmount || 0).toLocaleString()}\n\nAI Recommendation\n${invoice.aiRecommendation || "Review invoice validations before approval."}`;
}
function generateFullPoText(invoice, po, rows) {
  return `PURCHASE ORDER DOCUMENT\n\nPO Number: ${po?.poNumber || invoice.poNumber || "N/A"}\nVendor: ${po?.vendorName || invoice.vendor}\nBuyer Entity: ${po?.buyer || "PhonePe AP Operations"}\nLinked Contract: ${po?.linkedContractId || invoice.contractId || "N/A"}\nPayment Terms: ${po?.paymentTerms || invoice.paymentTerms || "N/A"}\nStatus: ${po?.status || "Referenced"}\n\nCommercial Lines\n${rows.map((r, i) => `${i+1}. ${r.item || r.description || r.service || "Service"} | Qty ${r.quantity || 1} | Unit ${r.unitPrice || r.rate || "—"} | Amount ${r.amount || "—"}`).join("\n")}\n\nValidation Use\nThis purchase order is used to validate supplier, amount, remaining balance, approved service scope, and approval evidence for invoice ${invoice.id}.`;
}
function generateFullContractText(invoice, contract, rateRows, clauses) {
  return `CONTRACT DOCUMENT\n\nContract ID: ${contract?.id || invoice.contractId || "N/A"}\nVendor: ${contract?.vendor || invoice.vendor}\nEffective Date: ${contract?.effectiveDate || "2026-01-01"}\nExpiry Date: ${contract?.endDate || contract?.expiryDate || "2026-12-31"}\nPayment Terms: ${contract?.paymentTerms || invoice.paymentTerms || "N/A"}\nTolerance: ${contract?.tolerancePercent ?? 3}%\n\nRate Card\n${rateRows.map((r, i) => `${i+1}. ${r.service || r.item || "Service"} | Rate ${r.rate || r.unitPrice || "—"} | Billing ${r.billing || r.billingModel || "—"}`).join("\n")}\n\nKey Clauses\n${clauses.map((c, i) => `${i+1}. ${typeof c === "string" ? c : c.summary || JSON.stringify(c)}`).join("\n")}\n\nValidation Use\nThis contract is used for rate-card, payment-term, validity, tolerance, and tax/compliance checks for invoice ${invoice.id}.`;
}
function generateFullRegulationText(invoice, regulation, impact) {
  return `REGULATION / AP POLICY DOCUMENT\n\nPolicy: ${regulation?.title || invoice.regulationId || "AP Regulation Policy"}\nJurisdiction: ${regulation?.jurisdiction || "India"}\nPrimary Impact: ${impact.primaryControl}\nApproval Impact: ${impact.impact}\nRequired Action: ${impact.requiredAction}\nRequired Role: ${impact.requiredRole}\n\nControls\n${impact.controls.map(c => `${c.id} - ${c.name}\nResult: ${c.result}\nApproval Impact: ${c.impact}\nRole: ${c.role}\nEvidence: ${c.evidence}`).join("\n\n")}\n\nBusiness Use\nThese controls actively route invoice ${invoice.id} through approval stages and block payment when mandatory controls fail.`;
}

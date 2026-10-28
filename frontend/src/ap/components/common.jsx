import React from "react";
import { formatMoney } from "../../lib/formatMoney";

export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Money({ value, currency = "INR" }) {
  return <>{formatMoney(value, currency)}</>;
}

export function Field({ label, value }) {
  return <div className="field"><span>{label}</span><strong>{value || "—"}</strong></div>;
}

export function Layer({ title, icon, onClose, children }) {
  return <div className="layer-backdrop" onMouseDown={onClose}>
    <div className="layer-panel" onMouseDown={e => e.stopPropagation()}>
      <div className="layer-head"><h3>{icon}{title}</h3><button className="ghost" onClick={onClose}>Close</button></div>
      <div className="layer-body">{children}</div>
    </div>
  </div>;
}

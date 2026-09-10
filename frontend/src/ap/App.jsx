import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  FileText,
  LayoutDashboard,
  LogOut,
  PauseCircle,
  PlayCircle,
  Radio,
  RefreshCw,
  Scale,
  UploadCloud,
  UserRound,
} from "lucide-react";
import { api } from "./api/client";
import Dashboard from "./screens/Dashboard";
import Intake from "./screens/Intake";
import InvoiceApproval from "./screens/InvoiceApproval";
import Regulations from "./screens/Regulations";
import Records from "./screens/Records";
import BrandLockup from "./components/BrandLockup";
import ModuleSwitcher from "../components/ModuleSwitcher";
import { useAuth } from "../auth/AuthContext";
import "./styles.css";

export default function ApApp() {
  const { user, logout: sharedLogout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [view, setView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("invoice") ? "invoices" : "dashboard";
  });
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [pos, setPos] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [regulations, setRegulations] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [feedEvents, setFeedEvents] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [autoFeed, setAutoFeed] = useState(false);

  async function handleLogout() {
    await sharedLogout();
    navigate("/login", { replace: true });
  }

  async function loadAll() {
    setBusy(true);
    try {
      const [s, i, p, c, r, d, f] = await Promise.all([
        api("/dashboard/summary"),
        api("/invoices"),
        api("/purchase-orders"),
        api("/contracts"),
        api("/regulations"),
        api("/documents"),
        api("/invoices/feed/events"),
      ]);
      setSummary(s);
      setInvoices(i);
      setPos(p);
      setContracts(c);
      setRegulations(r);
      setDocuments(d);
      setFeedEvents(f);
      setSelectedInvoice((current) => {
        const params = new URLSearchParams(window.location.search);
        const focus = params.get("invoice");
        if (focus) {
          return i.find((x) => x.id === focus) || current || i[0];
        }
        return current ? i.find((x) => x.id === current.id) || i[0] : i[0];
      });
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function receiveInvoice(scenario = null) {
    setBusy(true);
    try {
      const result = await api("/invoices/simulate-new", {
        method: "POST",
        body: JSON.stringify({ scenario }),
      });
      setToast(`${result.invoice.id} received · ${result.invoice.status}`);
      await loadAll();
      setSelectedInvoice(result.invoice);
      setView("invoices");
    } catch (e) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (isAuthenticated) loadAll();
  }, [isAuthenticated]);

  useEffect(() => {
    if (!autoFeed) return undefined;
    const id = setInterval(() => receiveInvoice(null), 10000);
    return () => clearInterval(id);
  }, [autoFeed]);

  if (!isAuthenticated || !user) return null;

  const nav = [
    ["dashboard", LayoutDashboard, "Control Tower"],
    ["intake", UploadCloud, "Document Intake"],
    ["invoices", FileText, "Invoice Approval"],
    ["regulations", Scale, "Regulations"],
    ["records", BookOpenCheck, "PO / Contracts"],
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="app-brand">
          <BrandLockup variant="sidebar" />
        </div>
        <nav>
          <p className="nav-section-label">Navigate</p>
          {nav.map(([id, Icon, label]) => (
            <button
              key={id}
              onClick={() => setView(id)}
              className={view === id ? "active" : ""}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar topbar-with-modules">
          <div className="topbar-leading">
            <ModuleSwitcher compact />
            <div>
              <p className="eyebrow">AP Control Tower</p>
              <h1>{nav.find((n) => n[0] === view)?.[2]}</h1>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="user-pill">
              <UserRound size={16} />
              <span>{user.name}</span>
              <strong>{user.approvalRole}</strong>
            </div>
            <button onClick={() => receiveInvoice(null)} disabled={busy}>
              <Radio size={16} />
              Receive new invoice
            </button>
            <button
              className={autoFeed ? "danger-btn" : "secondary"}
              onClick={() => setAutoFeed((v) => !v)}
            >
              {autoFeed ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
              Auto feed {autoFeed ? "ON" : "OFF"}
            </button>
            <button className="ghost" onClick={loadAll}>
              <RefreshCw size={16} />
              {busy ? "Refreshing" : "Refresh"}
            </button>
            <button className="ghost" onClick={handleLogout}>
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </header>
        {toast && (
          <div className="toast" onClick={() => setToast("")}>
            {toast}
          </div>
        )}
        {view === "dashboard" && (
          <Dashboard
            summary={summary}
            invoices={invoices}
            regulations={regulations}
            feedEvents={feedEvents}
            receiveInvoice={receiveInvoice}
            setView={setView}
          />
        )}
        {view === "intake" && <Intake onDone={loadAll} />}
        {view === "invoices" && (
          <InvoiceApproval
            invoices={invoices}
            pos={pos}
            contracts={contracts}
            regulations={regulations}
            documents={documents}
            selected={selectedInvoice}
            setSelected={setSelectedInvoice}
            onDone={loadAll}
            receiveInvoice={receiveInvoice}
            user={user}
          />
        )}
        {view === "regulations" && (
          <Regulations regulations={regulations} invoices={invoices} onDone={loadAll} />
        )}
        {view === "records" && (
          <Records pos={pos} contracts={contracts} documents={documents} />
        )}
      </main>
    </div>
  );
}

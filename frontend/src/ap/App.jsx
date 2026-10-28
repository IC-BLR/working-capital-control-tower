import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  FileText,
  LayoutDashboard,
  PauseCircle,
  PlayCircle,
  Radio,
  RefreshCw,
  Scale,
  UploadCloud,
} from "lucide-react";
import { api } from "./api/client";
import Dashboard from "./screens/Dashboard";
import Intake from "./screens/Intake";
import InvoiceApproval from "./screens/InvoiceApproval";
import Regulations from "./screens/Regulations";
import Records from "./screens/Records";
import { useAuth } from "../auth/AuthContext";
import AppHeader from "../components/AppHeader";
import AppSidebar from "../components/AppSidebar";
import PageHeader from "../components/PageHeader";
import { Button } from "../components/ui/button";
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

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
    { key: "dashboard", icon: LayoutDashboard, label: "Overview" },
    { key: "intake", icon: UploadCloud, label: "Document intake" },
    { key: "invoices", icon: FileText, label: "Invoices" },
    { key: "regulations", icon: Scale, label: "Regulations" },
    { key: "records", icon: BookOpenCheck, label: "PO / Contracts" },
  ];

  const pageMeta = {
    dashboard: {
      title: "Payables overview",
      subtitle: "Invoice intake, exceptions, and payment-ready exposure",
    },
    intake: {
      title: "Document intake",
      subtitle: "Upload and extract invoice, PO, and contract documents",
    },
    invoices: {
      title: "Invoices",
      subtitle: "Approval queue, exceptions, and payment-ready exposure",
    },
    regulations: {
      title: "Regulations",
      subtitle: "Controls that route and block invoice approval",
    },
    records: {
      title: "PO / Contracts",
      subtitle: "Purchase orders, contracts, and intake audit",
    },
  };

  const meta = pageMeta[view] || pageMeta.dashboard;
  const showInvoiceActions = view === "dashboard" || view === "invoices";

  return (
    <div className="min-h-screen flex bg-slate-50">
      <AppSidebar
        moduleLabel="Payables"
        accent="violet"
        items={nav.map((item) => ({
          key: item.key,
          label: item.label,
          icon: item.icon,
          active: view === item.key,
          onClick: () => setView(item.key),
        }))}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
        mobileOpen={sidebarOpen}
        onCloseMobile={() => setSidebarOpen(false)}
      />
      <main className="flex-1 min-h-screen min-w-0 flex flex-col">
        <AppHeader
          user={user}
          onLogout={handleLogout}
          onMenuClick={() => setSidebarOpen(true)}
        />
        <div className="p-6 lg:p-8 flex-1 min-w-0">
        <PageHeader
          title={meta.title}
          subtitle={meta.subtitle}
          actions={
            <>
              {showInvoiceActions && (
                <>
                  <Button variant="outline" size="sm" onClick={() => receiveInvoice(null)} disabled={busy}>
                    <Radio className="w-4 h-4" />
                    Receive invoice
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAutoFeed((v) => !v)}
                    className={autoFeed ? "text-rose-700 border-rose-200" : ""}
                  >
                    {autoFeed ? <PauseCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
                    Auto feed {autoFeed ? "on" : "off"}
                  </Button>
                </>
              )}
              <Button variant="outline" size="sm" onClick={loadAll} disabled={busy}>
                <RefreshCw className={`w-4 h-4 ${busy ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </>
          }
        />
        {toast && (
          <div className="toast" onClick={() => setToast("")}>
            {toast}
          </div>
        )}
        <div className="ap-content">
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
        </div>
        </div>
      </main>
    </div>
  );
}

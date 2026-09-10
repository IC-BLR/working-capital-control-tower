import { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { ArrowDownRight, ArrowUpRight, Landmark, RefreshCw } from "lucide-react";
import { AR_API_BASE, AP_API_BASE } from "../config";
import { Button } from "../components/ui/button";

function formatMoney(value) {
  const n = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function sumForecastInflows(forecast) {
  if (!forecast) return 0;
  if (Array.isArray(forecast.cashflow_events)) {
    return forecast.cashflow_events.reduce((s, e) => s + Number(e.amount || e.expected_amount || 0), 0);
  }
  if (Array.isArray(forecast.forecast_data)) {
    return forecast.forecast_data.reduce(
      (s, d) => s + Number(d.inflow || d.expected_inflow || d.amount || 0),
      0
    );
  }
  return Number(forecast.projected_balance || 0);
}

export default function NetLiquidity() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [arSummary, setArSummary] = useState(null);
  const [arForecast, setArForecast] = useState(null);
  const [apSummary, setApSummary] = useState(null);
  const [paymentReadyTotal, setPaymentReadyTotal] = useState(0);
  const [paymentReadyCount, setPaymentReadyCount] = useState(0);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("ap_auth_token");
      const apHeaders = token ? { Authorization: `Bearer ${token}` } : {};

      const [summaryRes, forecastRes, apDashRes, apInvRes] = await Promise.all([
        axios.get(`${AR_API_BASE}/summary`),
        axios.get(`${AR_API_BASE}/forecast`, { params: { days: 30 } }),
        axios.get(`${AP_API_BASE}/dashboard/summary`, { headers: apHeaders }),
        axios.get(`${AP_API_BASE}/invoices`, { headers: apHeaders }),
      ]);

      setArSummary(summaryRes.data);
      setArForecast(forecastRes.data);
      setApSummary(apDashRes.data);

      const ready = (apInvRes.data || []).filter((inv) => {
        const status = String(inv.status || "");
        return status === "Payment Ready" || status === "Approved";
      });
      setPaymentReadyCount(ready.length);
      setPaymentReadyTotal(ready.reduce((sum, inv) => sum + Number(inv.amount || 0), 0));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Failed to load liquidity view");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const forecastInflows = sumForecastInflows(arForecast);
  const expectedInflows =
    forecastInflows ||
    Number(arSummary?.overall_exposure || 0) ||
    Number(arSummary?.total_invoice_amount || 0);

  const expectedOutflows = paymentReadyTotal;
  const net = expectedInflows - expectedOutflows;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white/80 backdrop-blur px-8 py-5 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Combined view</p>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Manrope, sans-serif" }}>
            Net Liquidity Overview
          </h1>
          <p className="text-slate-600 mt-1 text-sm">
            AR expected inflows vs AP payment-ready / approved outflows
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/">Hub</Link>
          </Button>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-6">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">{error}</div>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          <Metric
            label="AR expected inflows (30d)"
            value={loading ? "…" : formatMoney(expectedInflows)}
            hint="From AR forecast events / exposure"
            icon={ArrowDownRight}
            tone="emerald"
            link="/ar/forecast"
          />
          <Metric
            label="AP payment-ready outflows"
            value={loading ? "…" : formatMoney(expectedOutflows)}
            hint={`${paymentReadyCount} invoice(s) Payment Ready / Approved`}
            icon={ArrowUpRight}
            tone="violet"
            link="/ap"
          />
          <Metric
            label="Net working-capital signal"
            value={loading ? "…" : formatMoney(net)}
            hint={net >= 0 ? "Inflows cover near-term AP" : "AP pressure exceeds near-term AR"}
            icon={Landmark}
            tone={net >= 0 ? "emerald" : "rose"}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border bg-white p-6">
            <h2 className="font-semibold text-slate-900 mb-3">AR snapshot</h2>
            <dl className="space-y-2 text-sm">
              <Row label="Overall exposure" value={formatMoney(arSummary?.overall_exposure)} />
              <Row label="Invoice amount" value={formatMoney(arSummary?.total_invoice_amount)} />
              <Row label="Allocated" value={formatMoney(arSummary?.total_allocated_amount)} />
              <Row label="Partners" value={arSummary?.total_number_of_partners ?? "—"} />
              <Row label="Invoices" value={arSummary?.total_number_of_invoices ?? "—"} />
            </dl>
            <Link to="/ar/dashboard" className="inline-block mt-4 text-sm text-emerald-700 font-medium">
              Open AR Sensei →
            </Link>
          </div>
          <div className="rounded-2xl border bg-white p-6">
            <h2 className="font-semibold text-slate-900 mb-3">AP snapshot</h2>
            <dl className="space-y-2 text-sm">
              <Row label="Invoices" value={apSummary?.invoiceCount ?? "—"} />
              <Row label="Exceptions" value={apSummary?.exceptionCount ?? "—"} />
              <Row label="Approved" value={apSummary?.approvedCount ?? "—"} />
              <Row label="Exception exposure" value={formatMoney(apSummary?.financialExposure)} />
            </dl>
            <Link to="/ap" className="inline-block mt-4 text-sm text-violet-700 font-medium">
              Open AP Control Tower →
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}

function Metric({ label, value, hint, icon: Icon, tone, link }) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-700",
    violet: "bg-violet-50 text-violet-700",
    rose: "bg-rose-50 text-rose-700",
  };
  const body = (
    <div className="rounded-2xl border bg-white p-6 h-full">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${tones[tone] || tones.emerald}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
      <p className="text-xs text-slate-500 mt-2">{hint}</p>
    </div>
  );
  return link ? <Link to={link}>{body}</Link> : body;
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 last:border-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-900">{value ?? "—"}</dd>
    </div>
  );
}

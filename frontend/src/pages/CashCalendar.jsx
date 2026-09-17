import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  Clock,
  Info,
  Landmark,
  LogOut,
  PauseCircle,
  RefreshCw,
  ShieldAlert,
  Target,
  Timer,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import ModuleSwitcher from "../components/ModuleSwitcher";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { WC_API_BASE } from "../config";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

function formatMoney(value) {
  const n = Number(value || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatDays(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${Number(value).toFixed(1)} days`;
}

function deltaBadge(current, prior, invert = false) {
  if (current == null || prior == null) return null;
  const delta = Number(current) - Number(prior);
  if (Math.abs(delta) < 0.05) return { text: "flat vs prior", tone: "slate", Icon: Clock };
  // For DSO/CCC lower is better; for DPO higher can be better for cash (invert=true)
  const improved = invert ? delta > 0 : delta < 0;
  return {
    text: `${delta > 0 ? "+" : ""}${delta.toFixed(1)} vs prior`,
    tone: improved ? "emerald" : "rose",
    Icon: improved ? TrendingDown : TrendingUp,
  };
}

const SCENARIOS = [
  { id: "baseline", label: "Current plan (no changes)", defer: 0 },
  { id: "payment_delay_7", label: "Customers pay 7 days late", defer: 0 },
  { id: "payment_delay_14", label: "Customers pay 14 days late", defer: 0 },
  { id: "recession", label: "AR receipts drop 20%", defer: 0 },
  { id: "defer_ap_7", label: "Defer vendor payments 7 days", defer: 7 },
  { id: "defer_ap_14", label: "Defer vendor payments 14 days", defer: 14 },
];

const HORIZONS = [
  { days: 7, label: "7 days", hint: "This week" },
  { days: 30, label: "30 days", hint: "This month" },
  { days: 90, label: "90 days", hint: "This quarter" },
];

export default function CashCalendar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const [scenario, setScenario] = useState("baseline");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("inflows");
  const [alertsOpen, setAlertsOpen] = useState(true);

  const deferAp = useMemo(() => SCENARIOS.find((s) => s.id === scenario)?.defer || 0, [scenario]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.get(`${WC_API_BASE}/calendar`, {
        params: {
          days,
          scenario: scenario.startsWith("defer_ap") ? "baseline" : scenario,
          defer_ap_days: deferAp,
        },
      });
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Failed to load cash calendar");
    } finally {
      setLoading(false);
    }
  }, [days, scenario, deferAp]);

  useEffect(() => {
    load();
  }, [load]);

  async function holdPay(invoiceId, hold = true) {
    try {
      await axios.post(`${WC_API_BASE}/ap/${invoiceId}/hold`, {
        hold,
        note: hold ? "Held from WC Cash Calendar" : "Released from WC Cash Calendar",
      });
      toast.success(hold ? `Hold applied on ${invoiceId}` : `Hold released on ${invoiceId}`);
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    }
  }

  async function prioritizeCollect(partnerCode, invoiceNumber) {
    try {
      await axios.post(`${WC_API_BASE}/collect-priority`, {
        partner_code: partnerCode,
        invoice_number: invoiceNumber,
        note: "Prioritized from WC Cash Calendar",
        active: true,
      });
      toast.success("Marked for collection priority");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    }
  }

  const kpis = data?.kpis || {};
  const wc = kpis.wc_metrics || {};
  const alerts = data?.alerts || [];
  const highAlerts = alerts.filter((a) => a.severity === "high");
  const events = data?.events || [];
  const inflows = events.filter((e) => e.direction === "inflow");
  const obligated = events.filter((e) => e.certainty === "obligated");
  const pipeline = events.filter((e) => e.certainty === "pipeline");
  const held = events.filter((e) => e.certainty === "held");
  const actionsById = useMemo(() => {
    const map = {};
    (data?.actions_suggested || []).forEach((a) => {
      map[a.id] = a;
    });
    return map;
  }, [data?.actions_suggested]);

  const chartData = (data?.series || []).map((row) => ({
    ...row,
    label: row.date?.slice(5),
  }));

  function scrollToAction(actionId) {
    const el = document.getElementById(`wc-action-${actionId}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#edf5f8]">
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-sky-300/40 blur-3xl" />
        <div className="absolute top-1/4 -right-16 h-96 w-96 rounded-full bg-emerald-300/30 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-cyan-200/35 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(14,165,233,0.14),_transparent_55%)]" />
      </div>

      <header className="relative sticky top-0 z-20 border-b border-sky-200/60 bg-white/55 backdrop-blur-xl shadow-sm shadow-sky-900/5">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-sky-500 to-emerald-500 text-white flex items-center justify-center shrink-0 font-bold shadow-lg shadow-sky-500/30">
              WC
            </div>
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-widest text-sky-700/80 font-semibold">
                Working Capital Control Tower
              </p>
              <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Manrope, sans-serif" }}>
                Cash Calendar
              </h1>
              <p className="text-sm text-slate-600">
                AR expected inflows vs AP obligated outflows — dated net position
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ModuleSwitcher compact />
            <div className="text-right text-sm px-2 hidden sm:block">
              <p className="font-medium text-slate-900">{user?.name}</p>
              <p className="text-xs text-slate-500">{user?.approvalRole}</p>
            </div>
            <Button variant="outline" size="sm" className="bg-white/80 border-sky-200" onClick={load} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="bg-white/80 border-sky-200"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              <LogOut className="w-4 h-4 mr-1" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="relative max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="rounded-2xl border border-sky-200/70 bg-gradient-to-r from-white/90 via-sky-50/80 to-emerald-50/70 p-4 md:p-5 shadow-md shadow-sky-900/5 backdrop-blur-md">
          <div className="flex flex-wrap gap-6 items-end">
            <div className="space-y-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">Look ahead</p>
                <p className="text-xs text-slate-500">How far into the future to show cash in and out</p>
              </div>
              <div
                className="inline-flex rounded-xl border border-sky-200 bg-white/70 p-1 shadow-inner"
                role="group"
                aria-label="Look ahead period"
              >
                {HORIZONS.map((h) => (
                  <button
                    key={h.days}
                    type="button"
                    onClick={() => setDays(h.days)}
                    title={h.hint}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors border ${days === h.days
                      ? "bg-gradient-to-r from-sky-600 to-cyan-600 text-white border-transparent shadow-md shadow-sky-500/25"
                      : "border-transparent text-slate-700 hover:bg-sky-50"
                      }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2 min-w-[240px] flex-1 max-w-md">
              <div>
                <label htmlFor="wc-scenario" className="text-sm font-semibold text-slate-900">
                  What-if scenario
                </label>
                <p className="text-xs text-slate-500">Simulate delays or payment timing changes</p>
              </div>
              <select
                id="wc-scenario"
                className="w-full rounded-xl border border-sky-200 bg-white/90 px-3 py-2.5 text-sm text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-400/40"
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
              >
                {SCENARIOS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            {data?.as_of && (
              <p className="text-xs font-medium text-sky-800/70 pb-2 ml-auto bg-white/50 px-3 py-1.5 rounded-full border border-sky-100">
                Data as of {data.as_of}
              </p>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">{error}</div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi
            label={`Expected inflows (next ${days} days)`}
            value={formatMoney(kpis.inflows)}
            icon={ArrowDownRight}
            tone="emerald"
          />
          <Kpi
            label={`Obligated outflows (next ${days} days)`}
            value={formatMoney(kpis.obligated_outflows)}
            icon={ArrowUpRight}
            tone="rose"
          />
          <Kpi
            label="Net WC signal"
            value={formatMoney(kpis.net)}
            icon={Landmark}
            tone={Number(kpis.net) >= 0 ? "emerald" : "rose"}
          />
          <Kpi
            label="Held / cash at risk"
            value={`${formatMoney(kpis.held)} / ${formatMoney(kpis.cash_at_risk)}`}
            icon={ShieldAlert}
            tone="amber"
            hint={`Pipeline outflows ${formatMoney(kpis.pipeline_outflows)}`}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <WcMetricCard
            label="DSO — Days Sales Outstanding"
            hint="Average days to collect from customers"
            value={formatDays(wc.dso)}
            delta={deltaBadge(wc.dso, wc.prior?.dso, false)}
            icon={Timer}
            assumptions={wc.assumptions}
          />
          <WcMetricCard
            label="DPO — Days Payable Outstanding"
            hint="Average days to pay suppliers"
            value={formatDays(wc.dpo)}
            delta={deltaBadge(wc.dpo, wc.prior?.dpo, true)}
            icon={Clock}
            assumptions={wc.assumptions}
          />
          <WcMetricCard
            label="CCC — Cash Conversion Cycle"
            hint="Days cash is locked in operations (DIO N/A)"
            value={formatDays(wc.ccc)}
            delta={deltaBadge(wc.ccc, wc.prior?.ccc, false)}
            icon={Landmark}
            assumptions={[
              ...(wc.assumptions || []),
              wc.dio == null ? "DIO not applicable — CCC = DSO − DPO" : null,
            ].filter(Boolean)}
            emphasize
          />
        </div>

        {alerts.length > 0 && (
          <div
            className={`rounded-2xl border shadow-md backdrop-blur-md overflow-hidden ${highAlerts.length
                ? "border-rose-300/80 bg-gradient-to-r from-rose-50/95 via-amber-50/80 to-white/90"
                : "border-amber-200/80 bg-gradient-to-r from-amber-50/90 to-white/90"
              }`}
          >
            <button
              type="button"
              className="w-full flex items-center justify-between gap-3 px-4 md:px-6 py-3 text-left"
              onClick={() => setAlertsOpen((v) => !v)}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span
                  className={`rounded-xl p-2 ${highAlerts.length ? "bg-rose-500 text-white" : "bg-amber-500 text-white"
                    }`}
                >
                  <Bell className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold text-slate-900">
                    Cash alerts · {alerts.length}
                    {highAlerts.length ? ` · ${highAlerts.length} high` : ""}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    Threshold breaches and scenario stress on the current horizon
                  </p>
                </div>
              </div>
              <span className="text-xs font-medium text-slate-500 shrink-0">
                {alertsOpen ? "Hide" : "Show"}
              </span>
            </button>
            {alertsOpen && (
              <div className="px-4 md:px-6 pb-4 space-y-2">
                {alerts.map((a) => (
                  <AlertRow
                    key={a.id}
                    alert={a}
                    onFix={(id) => {
                      scrollToAction(id);
                    }}
                    hasLinkedAction={(a.suggested_action_ids || []).some((id) => actionsById[id])}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        <div className="rounded-2xl border border-sky-200/80 bg-white/75 shadow-lg shadow-sky-900/5 backdrop-blur-md overflow-hidden">
          <div className="px-4 md:px-6 py-3 border-b border-sky-100 bg-gradient-to-r from-sky-600/10 via-cyan-500/5 to-emerald-500/10">
            <h2 className="font-semibold text-slate-900">Daily cash trajectory</h2>
            <p className="text-xs text-slate-500 mt-0.5">Inflows, obligated outflows, and net position by day</p>
          </div>
          <div className="p-4 md:p-6 h-80">
            {loading && !data ? (
              <p className="text-sm text-slate-500">Loading calendar…</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#bae6fd" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#475569" }} />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#475569" }}
                    tickFormatter={(v) => `${Math.round(v / 1000)}k`}
                  />
                  <Tooltip
                    formatter={(v) => formatMoney(v)}
                    contentStyle={{ borderRadius: 12, borderColor: "#e0f2fe" }}
                  />
                  <Legend />
                  <Bar dataKey="inflow" name="Inflows" fill="#10b981" opacity={0.9} radius={[4, 4, 0, 0]} />
                  <Bar
                    dataKey="outflow_obligated"
                    name="Obligated outflows"
                    fill="#e11d48"
                    opacity={0.9}
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="outflow_pipeline"
                    name="Pipeline outflows"
                    fill="#fda4af"
                    opacity={0.75}
                    radius={[4, 4, 0, 0]}
                  />
                  <Line type="monotone" dataKey="net" name="Net" stroke="#0284c7" strokeWidth={2.5} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 rounded-2xl border border-sky-200/80 bg-white/75 shadow-lg shadow-sky-900/5 backdrop-blur-md p-4 md:p-6">
            <div className="flex flex-wrap gap-2 mb-4">
              {[
                ["inflows", `Inflows (${inflows.length})`, "emerald"],
                ["obligated", `Obligated (${obligated.length})`, "rose"],
                ["pipeline", `Pipeline (${pipeline.length})`, "sky"],
                ["held", `Held (${held.length})`, "amber"],
              ].map(([id, label, tone]) => {
                const active = tab === id;
                const activeStyles = {
                  emerald: "bg-emerald-100 text-emerald-800 border-emerald-300",
                  rose: "bg-rose-100 text-rose-800 border-rose-300",
                  sky: "bg-sky-100 text-sky-800 border-sky-300",
                  amber: "bg-amber-100 text-amber-900 border-amber-300",
                };
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setTab(id)}
                    className={`px-3 py-1.5 text-sm rounded-xl border transition-colors ${active
                      ? `${activeStyles[tone]} font-semibold shadow-sm`
                      : "bg-white/50 text-slate-600 border-slate-200 hover:bg-white"
                      }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            <EventTable
              rows={
                tab === "inflows"
                  ? inflows
                  : tab === "obligated"
                    ? obligated
                    : tab === "pipeline"
                      ? pipeline
                      : held
              }
              onHold={holdPay}
              onCollect={prioritizeCollect}
            />
          </div>

          <div className="rounded-2xl border border-emerald-200/70 bg-gradient-to-b from-emerald-50/90 to-white/85 shadow-lg shadow-emerald-900/5 backdrop-blur-md p-4 md:p-6 space-y-4">
            <div>
              <h2 className="font-semibold text-slate-900">Suggested actions</h2>
              <p className="text-xs text-slate-500 mt-1">
                Ranked by cash impact. Holds and collect priorities update the calendar immediately.
              </p>
            </div>
            <div className="space-y-3">
              {(data?.actions_suggested || []).length === 0 && (
                <p className="text-sm text-slate-500">No suggested actions for this horizon.</p>
              )}
              {(data?.actions_suggested || []).map((a) => (
                <div
                  key={a.id}
                  id={`wc-action-${a.id}`}
                  className="rounded-xl border border-white bg-white/90 p-3 space-y-2 shadow-sm ring-1 ring-sky-100/80 scroll-mt-28"
                >
                  <div className="flex items-start gap-2">
                    {a.rank != null && (
                      <span className="shrink-0 w-7 h-7 rounded-lg bg-slate-900 text-white text-xs font-bold flex items-center justify-center">
                        #{a.rank}
                      </span>
                    )}
                    {a.label?.includes("Hold") ? (
                      <span className="rounded-lg bg-rose-50 p-1.5">
                        <PauseCircle className="w-4 h-4 text-rose-600" />
                      </span>
                    ) : a.label?.includes("collect") || a.label?.includes("Collect") ? (
                      <span className="rounded-lg bg-emerald-50 p-1.5">
                        <Target className="w-4 h-4 text-emerald-600" />
                      </span>
                    ) : (
                      <span className="rounded-lg bg-amber-50 p-1.5">
                        <ShieldAlert className="w-4 h-4 text-amber-600" />
                      </span>
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900">{a.label}</p>
                      <p className="text-xs text-slate-500">{a.detail}</p>
                      {a.cash_impact_label && (
                        <p className="text-xs text-sky-800 mt-1 font-medium">{a.cash_impact_label}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {a.invoice_id && (
                      <Button size="sm" variant="outline" onClick={() => holdPay(a.invoice_id, true)}>
                        Hold pay
                      </Button>
                    )}
                    {a.partner_code && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => prioritizeCollect(a.partner_code, a.invoice_number)}
                      >
                        Prioritize collect
                      </Button>
                    )}
                    {a.ui_path && (
                      <Button size="sm" variant="ghost" asChild>
                        <Link to={a.ui_path}>Open</Link>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function Kpi({ label, value, icon: Icon, tone, hint }) {
  const tones = {
    emerald: {
      card: "from-emerald-100/90 via-emerald-50 to-white border-emerald-300/70 shadow-emerald-900/10",
      icon: "bg-emerald-500 text-white shadow-emerald-500/35",
      value: "text-emerald-950",
    },
    rose: {
      card: "from-rose-100/90 via-rose-50 to-white border-rose-300/70 shadow-rose-900/10",
      icon: "bg-rose-500 text-white shadow-rose-500/35",
      value: "text-rose-950",
    },
    amber: {
      card: "from-amber-100/90 via-amber-50 to-white border-amber-300/70 shadow-amber-900/10",
      icon: "bg-amber-500 text-white shadow-amber-500/35",
      value: "text-amber-950",
    },
    sky: {
      card: "from-sky-100/90 via-sky-50 to-white border-sky-300/70 shadow-sky-900/10",
      icon: "bg-sky-500 text-white shadow-sky-500/35",
      value: "text-sky-950",
    },
  };
  const t = tones[tone] || tones.sky;
  return (
    <div className={`rounded-2xl border bg-gradient-to-br ${t.card} p-5 shadow-md`}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 shadow-md ${t.icon}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-xs uppercase tracking-wide text-slate-500 font-medium">{label}</p>
      <p className={`text-xl font-bold mt-1 break-words ${t.value}`}>{value}</p>
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

function WcMetricCard({ label, hint, value, delta, icon: Icon, assumptions, emphasize }) {
  const tip = (assumptions || []).join(" · ");
  return (
    <div
      className={`rounded-2xl border p-5 shadow-md bg-gradient-to-br ${emphasize
          ? "from-sky-100/95 via-cyan-50 to-white border-sky-300/80 shadow-sky-900/10"
          : "from-white via-slate-50 to-white border-slate-200/80"
        }`}
      title={tip}
    >
      <div className="flex items-start justify-between gap-2">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-md ${emphasize ? "bg-sky-600 text-white" : "bg-slate-800 text-white"
          }`}>
          <Icon className="w-5 h-5" />
        </div>
        {delta && (
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-medium rounded-full px-2 py-0.5 border ${delta.tone === "emerald"
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : delta.tone === "rose"
                  ? "bg-rose-50 text-rose-800 border-rose-200"
                  : "bg-slate-50 text-slate-600 border-slate-200"
              }`}
          >
            <delta.Icon className="w-3 h-3" />
            {delta.text}
          </span>
        )}
      </div>
      <p className="text-xs uppercase tracking-wide text-slate-500 font-medium mt-3">{label}</p>
      <p className="text-2xl font-bold mt-1 text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1 flex items-start gap-1">
        <Info className="w-3 h-3 mt-0.5 shrink-0" />
        <span>{hint}</span>
      </p>
    </div>
  );
}

function AlertRow({ alert, onFix, hasLinkedAction }) {
  const severityStyles = {
    high: "border-rose-200 bg-rose-50/80 text-rose-950",
    medium: "border-amber-200 bg-amber-50/70 text-amber-950",
    info: "border-sky-200 bg-sky-50/70 text-sky-950",
    low: "border-slate-200 bg-white text-slate-800",
  };
  const style = severityStyles[alert.severity] || severityStyles.info;
  const fixId = (alert.suggested_action_ids || [])[0];
  return (
    <div className={`rounded-xl border px-3 py-2.5 flex flex-wrap items-start justify-between gap-2 ${style}`}>
      <div className="min-w-0">
        <p className="text-sm font-semibold">
          <span className="uppercase text-[10px] tracking-wider opacity-70 mr-2">{alert.severity}</span>
          {alert.title}
        </p>
        <p className="text-xs opacity-80 mt-0.5">{alert.detail}</p>
      </div>
      {hasLinkedAction && fixId && (
        <Button size="sm" variant="outline" className="bg-white/80 shrink-0" onClick={() => onFix(fixId)}>
          Suggested fix
        </Button>
      )}
    </div>
  );
}

function EventTable({ rows, onHold, onCollect }) {
  if (!rows?.length) {
    return <p className="text-sm text-slate-500 py-6">No events in this bucket for the selected horizon.</p>;
  }

  const actionClass =
    "inline-flex items-center h-7 px-0 bg-transparent border-0 shadow-none rounded-none text-xs font-medium hover:underline cursor-pointer";

  return (
    <div className="overflow-x-auto rounded-xl border border-sky-100 bg-white/60">
      <table className="w-full text-sm table-fixed">
        <thead>
          <tr className="text-left text-xs text-slate-500 border-b border-sky-100 bg-sky-50/70">
            <th className="py-2.5 px-3 w-[7.5rem]">Date</th>
            <th className="py-2.5 pr-3">Counterparty</th>
            <th className="py-2.5 pr-3 w-[7rem]">Ref</th>
            <th className="py-2.5 pr-3 w-[7.5rem]">Amount</th>
            <th className="py-2.5 pr-3 w-[6.5rem]">Status</th>
            <th className="py-2.5 pr-3 w-[9.5rem]">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 40).map((e) => (
            <tr key={e.event_id} className="border-b border-sky-50/80 hover:bg-sky-50/40">
              <td className="py-2.5 px-3 whitespace-nowrap align-middle">{e.cash_date}</td>
              <td className="py-2.5 pr-3 align-middle truncate" title={e.counterparty_name}>
                {e.counterparty_name}
              </td>
              <td className="py-2.5 pr-3 font-mono text-xs align-middle truncate" title={e.source_ref}>
                {e.source_ref}
              </td>
              <td className="py-2.5 pr-3 font-medium whitespace-nowrap align-middle">
                {formatMoney(e.amount)}
              </td>
              <td className="py-2.5 pr-3 align-middle">
                <span className="text-xs rounded-full bg-sky-50 text-sky-800 border border-sky-100 px-2 py-0.5 whitespace-nowrap">
                  {e.certainty || e.status}
                </span>
              </td>
              <td className="py-2.5 pr-3 align-middle">
                <div className="flex flex-nowrap items-center gap-3 whitespace-nowrap">
                  {e.links?.ui_path && (
                    <Link className={`${actionClass} text-sky-700`} to={e.links.ui_path}>
                      Open
                    </Link>
                  )}
                  {e.source_system === "ap" && e.certainty === "obligated" && (
                    <button
                      type="button"
                      className={`${actionClass} text-rose-700`}
                      onClick={() => onHold(e.source_ref, true)}
                    >
                      Hold
                    </button>
                  )}
                  {e.source_system === "ap" && e.certainty === "held" && (
                    <button
                      type="button"
                      className={`${actionClass} text-emerald-700`}
                      onClick={() => onHold(e.source_ref, false)}
                    >
                      Release
                    </button>
                  )}
                  {e.source_system === "ar" && (
                    <button
                      type="button"
                      className={`${actionClass} text-emerald-700`}
                      onClick={() => onCollect(e.counterparty_id, e.source_ref)}
                    >
                      Collect
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

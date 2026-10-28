import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ArrowDownRight,
  ArrowUpRight,
  Landmark,
  PauseCircle,
  RefreshCw,
  ShieldAlert,
  Target,
} from "lucide-react";
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
import AppHeader from "../components/AppHeader";
import PageHeader from "../components/PageHeader";
import KpiTile from "../components/KpiTile";
import { formatMoney } from "../lib/formatMoney";

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
  const events = data?.events || [];
  const inflows = events.filter((e) => e.direction === "inflow");
  const obligated = events.filter((e) => e.certainty === "obligated");
  const pipeline = events.filter((e) => e.certainty === "pipeline");
  const held = events.filter((e) => e.certainty === "held");

  const chartData = (data?.series || []).map((row) => ({
    ...row,
    label: row.date?.slice(5),
  }));

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader
        user={user}
        onLogout={async () => {
          await logout();
          navigate("/login");
        }}
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <PageHeader
          title="Cash Calendar"
          subtitle="Expected inflows vs obligated outflows"
          actions={
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          }
        />
        <div className="rounded-xl border border-slate-200 bg-white p-4 md:p-5">
          <div className="flex flex-wrap gap-6 items-end">
            <div className="space-y-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">Look ahead</p>
                <p className="text-xs text-slate-500">How far into the future to show cash in and out</p>
              </div>
              <div
                className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1"
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
                        ? "bg-sky-100 text-sky-800 border-sky-200 font-medium"
                        : "border-transparent text-slate-700 hover:bg-white"
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
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400/40"
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
              <p className="text-xs font-medium text-slate-500 pb-2 ml-auto bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
                Data as of {data.as_of}
              </p>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">{error}</div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiTile
            label={`Expected inflows (next ${days} days)`}
            value={formatMoney(kpis.inflows)}
            icon={ArrowDownRight}
            tone="emerald"
          />
          <KpiTile
            label={`Obligated outflows (next ${days} days)`}
            value={formatMoney(kpis.obligated_outflows)}
            icon={ArrowUpRight}
            tone="rose"
          />
          <KpiTile
            label="Net WC signal"
            value={formatMoney(kpis.net)}
            icon={Landmark}
            tone={Number(kpis.net) >= 0 ? "emerald" : "rose"}
          />
          <KpiTile
            label="Held / cash at risk"
            value={`${formatMoney(kpis.held)} / ${formatMoney(kpis.cash_at_risk)}`}
            icon={ShieldAlert}
            tone="amber"
            hint={`Pipeline outflows ${formatMoney(kpis.pipeline_outflows)}`}
          />
        </div>

        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="px-4 md:px-6 py-3 border-b border-slate-200">
            <h2 className="font-semibold text-slate-900">Daily cash trajectory</h2>
            <p className="text-xs text-slate-500 mt-0.5">Inflows, obligated outflows, and net position by day</p>
          </div>
          <div className="p-4 md:p-6 h-80">
            {loading && !data ? (
              <p className="text-sm text-slate-500">Loading calendar…</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#475569" }} />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#475569" }}
                    tickFormatter={(v) => `${Math.round(v / 1000)}k`}
                  />
                  <Tooltip
                    formatter={(v) => formatMoney(v)}
                    contentStyle={{ borderRadius: 12, borderColor: "#e2e8f0" }}
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
          <div className="lg:col-span-2 rounded-xl border border-slate-200 bg-white p-4 md:p-6">
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

          <div className="rounded-xl border border-slate-200 bg-white p-4 md:p-6 space-y-4">
            <div>
              <h2 className="font-semibold text-slate-900">Suggested actions</h2>
              <p className="text-xs text-slate-500 mt-1">
                Holds and collect priorities update the calendar immediately.
              </p>
            </div>
            <div className="space-y-3">
              {(data?.actions_suggested || []).length === 0 && (
                <p className="text-sm text-slate-500">No suggested actions for this horizon.</p>
              )}
              {(data?.actions_suggested || []).map((a) => (
                <div
                  key={a.id}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-2"
                >
                  <div className="flex items-start gap-2">
                    {a.label?.includes("Hold") ? (
                      <span className="rounded-lg bg-rose-50 p-1.5">
                        <PauseCircle className="w-4 h-4 text-rose-600" />
                      </span>
                    ) : a.label?.includes("collect") ? (
                      <span className="rounded-lg bg-emerald-50 p-1.5">
                        <Target className="w-4 h-4 text-emerald-600" />
                      </span>
                    ) : (
                      <span className="rounded-lg bg-amber-50 p-1.5">
                        <ShieldAlert className="w-4 h-4 text-amber-600" />
                      </span>
                    )}
                    <div>
                      <p className="text-sm font-medium text-slate-900">{a.label}</p>
                      <p className="text-xs text-slate-500">{a.detail}</p>
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

function EventTable({ rows, onHold, onCollect }) {
  if (!rows?.length) {
    return <p className="text-sm text-slate-500 py-6">No events in this bucket for the selected horizon.</p>;
  }

  const actionClass =
    "inline-flex items-center h-7 px-0 bg-transparent border-0 shadow-none rounded-none text-xs font-medium hover:underline cursor-pointer";

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-sm table-fixed">
        <thead>
          <tr className="text-left text-xs text-slate-500 border-b border-slate-200 bg-slate-50">
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
            <tr key={e.event_id} className="border-b border-slate-100 hover:bg-slate-50">
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
                <span className="text-xs rounded-full bg-slate-50 text-slate-700 border border-slate-200 px-2 py-0.5 whitespace-nowrap">
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

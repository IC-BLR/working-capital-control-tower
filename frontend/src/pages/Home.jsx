import { Link } from "react-router-dom";
import { BarChart3, FileStack, Landmark, ArrowRight, LogOut } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/button";

export default function Home() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50 flex flex-col">
      <header className="border-b bg-white/80 backdrop-blur px-8 py-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Unified product</p>
          <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Manrope, sans-serif" }}>
            Working Capital Control Tower
          </h1>
          <p className="text-slate-600 mt-1 max-w-2xl">
            One shell for AR collections analytics, AP document intelligence, and net liquidity —
            shared login, dual API namespaces under a single backend.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right text-sm">
            <p className="font-medium text-slate-900">{user?.name}</p>
            <p className="text-xs text-slate-500">{user?.approvalRole || user?.email}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => logout()}>
            <LogOut className="w-4 h-4 mr-1" />
            Logout
          </Button>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12 grid gap-6 md:grid-cols-3">
        <TowerCard
          to="/"
          title="Cash Calendar"
          description="Dated AR inflows vs AP obligated outflows — the Working Capital product spine."
          icon={Landmark}
          tone="sky"
        />
        <TowerCard
          to="/ar/dashboard"
          title="AR Sensei"
          description="CFO analytics — partners, aging, insights, forecast, pipeline, and AI chatbot."
          icon={BarChart3}
          tone="emerald"
        />
        <TowerCard
          to="/ap"
          title="AP Control Tower"
          description="Document intake, OCR matching, exceptions, live feed, and role-based approvals."
          icon={FileStack}
          tone="violet"
        />
      </main>
    </div>
  );
}

function TowerCard({ to, title, description, icon: Icon, tone }) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-700 group-hover:border-emerald-300",
    violet: "bg-violet-50 text-violet-700 group-hover:border-violet-300",
    sky: "bg-sky-50 text-sky-700 group-hover:border-sky-300",
  };
  const linkTone = {
    emerald: "text-emerald-700",
    violet: "text-violet-700",
    sky: "text-sky-700",
  };
  return (
    <Link
      to={to}
      className={`group rounded-2xl border bg-white p-8 shadow-sm hover:shadow-md transition ${tones[tone]}`}
    >
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${tones[tone]}`}>
        <Icon className="w-6 h-6" />
      </div>
      <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
      <p className="text-slate-600 mt-2 text-sm leading-relaxed">{description}</p>
      <span className={`inline-flex items-center gap-2 mt-6 font-medium text-sm ${linkTone[tone]}`}>
        Open <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
      </span>
    </Link>
  );
}

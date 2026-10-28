import { cn } from "../lib/utils";

const TONES = {
  slate: "bg-slate-100 text-slate-700",
  emerald: "bg-emerald-100 text-emerald-700",
  rose: "bg-rose-100 text-rose-700",
  amber: "bg-amber-100 text-amber-700",
  sky: "bg-sky-100 text-sky-700",
  violet: "bg-violet-100 text-violet-700",
  orange: "bg-orange-100 text-orange-700",
};

export default function KpiTile({ label, value, icon: Icon, tone = "slate", hint, className }) {
  return (
    <div className={cn("rounded-xl border border-slate-200 bg-white p-4 min-w-0", className)}>
      <div className="flex items-center gap-3 min-w-0">
        {Icon && (
          <div className={cn("p-2.5 rounded-lg shrink-0", TONES[tone] || TONES.slate)}>
            <Icon className="w-5 h-5" />
          </div>
        )}
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">{label}</p>
          <p className="text-xl font-bold text-slate-900 mt-0.5 break-words" style={{ fontFamily: "Manrope, sans-serif" }}>
            {value}
          </p>
          {hint && <p className="text-xs text-slate-500 mt-0.5">{hint}</p>}
        </div>
      </div>
    </div>
  );
}

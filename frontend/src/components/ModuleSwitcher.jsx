import { Link, useLocation } from "react-router-dom";
import { Landmark, BarChart3, FileStack } from "lucide-react";
import { cn } from "../lib/utils";

const MODULES = [
  {
    id: "cash",
    label: "Cash Calendar",
    shortLabel: "Cash",
    to: "/",
    icon: Landmark,
    match: (pathname) => pathname === "/" || pathname.startsWith("/liquidity"),
    activeClass: "bg-sky-100 text-sky-800 border-sky-200",
  },
  {
    id: "ar",
    label: "AR Sensei",
    shortLabel: "AR",
    to: "/ar/dashboard",
    icon: BarChart3,
    match: (pathname) => pathname.startsWith("/ar"),
    activeClass: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  {
    id: "ap",
    label: "AP Control Tower",
    shortLabel: "AP",
    to: "/ap",
    icon: FileStack,
    match: (pathname) => pathname.startsWith("/ap"),
    activeClass: "bg-violet-100 text-violet-800 border-violet-200",
  },
];

/**
 * Top-bar module switcher shared by Cash Calendar, AR Sensei, and AP Control Tower.
 */
export default function ModuleSwitcher({ className, compact = false }) {
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="Switch module"
      className={cn(
        "module-switcher inline-flex flex-row flex-nowrap items-center gap-1 rounded-xl border border-slate-200 bg-slate-50/80 p-1",
        className
      )}
    >
      {MODULES.map((mod) => {
        const Icon = mod.icon;
        const active = mod.match(pathname);
        return (
          <Link
            key={mod.id}
            to={mod.to}
            aria-current={active ? "page" : undefined}
            title={mod.label}
            className={cn(
              "inline-flex flex-row items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm font-medium transition-colors whitespace-nowrap",
              active
                ? mod.activeClass
                : "border-transparent text-slate-600 hover:bg-white hover:text-slate-900"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className={compact ? "hidden sm:inline" : ""}>
              {compact ? mod.shortLabel : mod.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

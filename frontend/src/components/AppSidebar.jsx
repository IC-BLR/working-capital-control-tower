import { NavLink } from "react-router-dom";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { cn } from "../lib/utils";
import BrandMark from "./BrandMark";

const ACCENT = {
  emerald: {
    active: "bg-emerald-50 text-emerald-800",
    mark: "bg-emerald-700",
  },
  violet: {
    active: "bg-violet-50 text-violet-800",
    mark: "bg-violet-700",
  },
  sky: {
    active: "bg-sky-50 text-sky-800",
    mark: "bg-sky-700",
  },
};

export default function AppSidebar({
  moduleLabel,
  accent = "emerald",
  items = [],
  adminItems = [],
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onCloseMobile,
}) {
  const tone = ACCENT[accent] || ACCENT.emerald;

  const renderItem = (item) => {
    const Icon = item.icon;
    const className = (active) =>
      cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors w-full text-left text-sm font-medium",
        active ? tone.active : "text-slate-700 hover:bg-slate-100"
      );

    if (item.to) {
      return (
        <NavLink
          key={item.key || item.to}
          to={item.to}
          onClick={onCloseMobile}
          title={collapsed ? item.label : ""}
          className={() => className(item.active)}
        >
          <Icon className="w-5 h-5 shrink-0" />
          {!collapsed && <span>{item.label}</span>}
        </NavLink>
      );
    }

    return (
      <button
        key={item.key || item.label}
        type="button"
        onClick={() => {
          item.onClick?.();
          onCloseMobile?.();
        }}
        title={collapsed ? item.label : ""}
        className={className(item.active)}
      >
        <Icon className="w-5 h-5 shrink-0" />
        {!collapsed && <span>{item.label}</span>}
      </button>
    );
  };

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden" onClick={onCloseMobile} />
      )}
      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 bg-white/80 backdrop-blur-xl border-r border-slate-200 transform transition-all duration-300 ease-in-out",
          collapsed ? "lg:w-20" : "lg:w-64",
          mobileOpen ? "translate-x-0 w-64" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex flex-col h-full p-4">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
              <BrandMark className={cn("lg:hidden", collapsed && "lg:flex")} />
              {!collapsed && (
                <div className="min-w-0 hidden lg:block">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Module</p>
                  <p className="text-sm font-semibold text-slate-900 truncate">{moduleLabel}</p>
                </div>
              )}
              {mobileOpen && !collapsed && (
                <div className="min-w-0 lg:hidden">
                  <p className="text-sm font-semibold text-slate-900">{moduleLabel}</p>
                </div>
              )}
            </div>
            {onToggleCollapsed && (
              <button
                type="button"
                onClick={onToggleCollapsed}
                className="hidden lg:flex p-2 hover:bg-slate-100 rounded-lg text-slate-600"
                title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
              </button>
            )}
            {onCloseMobile && (
              <button type="button" onClick={onCloseMobile} className="lg:hidden p-2 hover:bg-slate-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          <nav className="flex-1 space-y-5">
            <div className="space-y-1">
              {!collapsed && (
                <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Navigate</p>
              )}
              {items.map(renderItem)}
            </div>
            {adminItems.length > 0 && (
              <div className="space-y-1">
                {!collapsed && (
                  <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Admin</p>
                )}
                {adminItems.map(renderItem)}
              </div>
            )}
          </nav>
        </div>
      </aside>
    </>
  );
}

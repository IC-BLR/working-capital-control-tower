import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  Lightbulb,
  Users,
  FileText,
  TrendingUp,
  Menu,
  X,
  Settings,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Bot,
  LogOut,
} from "lucide-react";
import { useState } from "react";
import { cn } from "../lib/utils";
import { useAuth } from "../auth/AuthContext";
import ModuleSwitcher from "./ModuleSwitcher";

const navigateItems = [
  { path: "/ar/dashboard", label: "Dashboard", icon: BarChart3 },
  { path: "/ar/partners", label: "Partners", icon: Users },
  { path: "/ar/insights", label: "Insights", icon: Lightbulb },
  { path: "/ar/invoices", label: "Invoices", icon: FileText },
  { path: "/ar/forecast", label: "Forecast", icon: TrendingUp },
  { path: "/ar/chatbot", label: "AI Assistant", icon: Bot },
];

const adminItems = [
  { path: "/ar/pipeline", label: "Data & settings", icon: Settings },
];

function isNavActive(pathname, path) {
  if (pathname === path) return true;
  return pathname.startsWith(`${path}/`);
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();

  const renderNavLink = (item) => {
    const Icon = item.icon;
    const active = isNavActive(location.pathname, item.path);

    return (
      <NavLink
        key={item.path}
        to={item.path}
        onClick={() => setSidebarOpen(false)}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
          active
            ? "bg-emerald-50 text-emerald-700"
            : "text-slate-700 hover:bg-slate-100"
        )}
        title={collapsed ? item.label : ""}
      >
        <Icon className="w-5 h-5 shrink-0" />
        {!collapsed && <span className="font-medium">{item.label}</span>}
      </NavLink>
    );
  };

  return (
    <div className="min-h-screen flex">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 glass-sidebar transform transition-all duration-300 ease-in-out",
          collapsed ? "lg:w-20" : "lg:w-64",
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex flex-col h-full p-5">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 font-bold">
                WC
              </div>
              {!collapsed && (
                <div>
                  <h1
                    className="text-lg font-bold text-slate-900"
                    style={{ fontFamily: "Manrope" }}
                  >
                    Working Capital
                  </h1>
                  <p className="text-xs text-slate-500">AR Sensei</p>
                </div>
              )}
            </div>

            <button
              onClick={() => setCollapsed(!collapsed)}
              className="hidden lg:flex p-2 hover:bg-slate-100 rounded-lg"
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>

            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 hover:bg-slate-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 space-y-5">
            <div className="space-y-1">
              {!collapsed && (
                <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Navigate
                </p>
              )}
              {navigateItems.map(renderNavLink)}
            </div>

            <div className="space-y-1">
              {!collapsed && (
                <p className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Admin
                </p>
              )}
              {adminItems.map(renderNavLink)}
            </div>
          </nav>
        </div>
      </aside>

      <main className="flex-1 min-h-screen min-w-0">
        <header className="sticky top-0 z-30 bg-white/70 backdrop-blur-xl border-b border-white/50 px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 hover:bg-slate-100 rounded-lg"
            >
              <Menu className="w-5 h-5" />
            </button>

            <ModuleSwitcher compact className="flex-1 min-w-0 justify-center sm:justify-start" />

            <div className="flex items-center gap-3 ml-auto">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-slate-900">
                  {user?.name || "Signed in"}
                </p>
                <p className="text-xs text-slate-500">
                  {user?.approvalRole || "AR + AP access"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => logout()}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-slate-100"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </header>

        <div className="p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Lightbulb,
  Users,
  FileText,
  TrendingUp,
  Settings,
  BarChart3,
  Bot,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import AppHeader from "./AppHeader";
import AppSidebar from "./AppSidebar";

const navigateItems = [
  { path: "/ar/dashboard", label: "Overview", icon: BarChart3 },
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
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const mapItems = (items) =>
    items.map((item) => ({
      key: item.path,
      to: item.path,
      label: item.label,
      icon: item.icon,
      active: isNavActive(location.pathname, item.path),
    }));

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen flex bg-slate-50">
      <AppSidebar
        moduleLabel="Receivables"
        accent="emerald"
        items={mapItems(navigateItems)}
        adminItems={mapItems(adminItems)}
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
        <div className="p-6 lg:p-8 flex-1">{<Outlet />}</div>
      </main>
    </div>
  );
}

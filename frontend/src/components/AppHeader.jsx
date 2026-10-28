import { LogOut, Menu } from "lucide-react";
import { Button } from "./ui/button";
import ModuleSwitcher from "./ModuleSwitcher";
import BrandMark from "./BrandMark";

export default function AppHeader({ user, onLogout, onMenuClick, showBrand = true }) {
  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-xl border-b border-slate-200 px-4 sm:px-6 py-3">
      <div className="flex items-center gap-3 min-w-0">
        {onMenuClick && (
          <button
            type="button"
            onClick={onMenuClick}
            className="lg:hidden p-2 hover:bg-slate-100 rounded-lg text-slate-700"
            aria-label="Open navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {showBrand && (
          <div className="flex items-center gap-2.5 min-w-0 shrink-0">
            <BrandMark />
            <p
              className="hidden xl:block text-sm font-semibold text-slate-900 leading-tight"
              style={{ fontFamily: "Manrope, sans-serif" }}
            >
              Working Capital
            </p>
          </div>
        )}

        <ModuleSwitcher compact className="min-w-0" />

        <div className="flex items-center gap-3 ml-auto shrink-0">
          <div className="text-right hidden xl:block">
            <p className="text-sm font-medium text-slate-900">{user?.name || "Signed in"}</p>
            <p className="text-xs text-slate-500">{user?.approvalRole || ""}</p>
          </div>
          <Button variant="outline" size="sm" type="button" onClick={onLogout}>
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  );
}

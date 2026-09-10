import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  ChevronLeft,
  ChevronRight,
  Search
} from "lucide-react";
import { Button } from "../components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

import { Input } from "../components/ui/input"; // Added Input for search
import { toast } from "sonner";

import { AR_API_BASE } from "../config";

export default function Insights() {
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState(null);
  const [state, setState] = useState("idle"); // idle | running | done | error
  const [sortConfig, setSortConfig] = useState({ column: null, order: "asc" });
  const [page, setPage] = useState(0); // Added from Partners.jsx
  const [search, setSearch] = useState(""); // Added search state
  const [riskFilter, setRiskFilter] = useState(location.state?.riskFilter || null); // Risk filter from navigation
  const limit = 10; // Items per page

  /* =========================
     Export Functions
     ========================= */
  const handleExport = async (format) => {
    try {
      const response = await axios.get(`${AR_API_BASE}/partners/export?format=${format}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      const contentDisposition = response.headers['content-disposition'];
      let filename = `partners_export_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'csv'}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch) filename = filenameMatch[1];
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`Partners exported successfully as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error(`Failed to export partners: ${error.response?.data?.detail || error.message}`);
    }
  };

  /* =========================
     Deferred fetch (NON-BLOCKING)
     ========================= */
  useEffect(() => {
    setState("running");
    // Reset page when risk filter changes
    setPage(0);

    const run = () => {
      axios
        .get(`${AR_API_BASE}/insights`)
        .then((res) => {
          setData(res.data);
          setState("done");
        })
        .catch((err) => {
          console.error(err);
          toast.error("Failed to load partner insights");
          setState("error");
        });
    };

    if ("requestIdleCallback" in window) {
      window.requestIdleCallback(run);
    } else {
      setTimeout(run, 0);
    }
  }, []);

  // Reset page when risk filter changes
  useEffect(() => {
    setPage(0);
  }, [riskFilter]);

  /* =========================
     Render
     ========================= */
  if (state === "running") {
    return (
      <div className="glass-card p-6 flex items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-slate-600" />
        <p className="text-sm text-slate-600">
          Running invoice-level ML classification and aggregating partner risk…
        </p>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="glass-card p-6 text-red-600">
        Unable to generate insights. Please retry.
      </div>
    );
  }

  if (!data) return null;

  const { portfolio_summary, partner_risk } = data;
  const riskPriority = { HIGH: 3, MEDIUM: 2, LOW: 1 };

  // ======= Apply search and risk filters =====
  const filteredPartners = partner_risk.filter(
    (p) => {
      // Search filter
      const matchesSearch = 
        p.partner_name?.toLowerCase().includes(search.toLowerCase()) ||
        p.partner_code?.toLowerCase().includes(search.toLowerCase());
      
      // Risk filter
      const matchesRisk = !riskFilter || p.risk_bucket === riskFilter;
      
      return matchesSearch && matchesRisk;
    }
  );

  // ======= Sorting Logic (Partners.jsx style) =======
  const sortedPartners = [...filteredPartners].sort((a, b) => {
    if (!sortConfig.column) return 0;

    let comparison = 0;

    switch (sortConfig.column) {
      case "partner":
        comparison = (a.partner_name || "").toLowerCase().localeCompare(
          (b.partner_name || "").toLowerCase()
        );
        break;
      case "risk":
        comparison = (riskPriority[a.risk_bucket] || 0) - (riskPriority[b.risk_bucket] || 0);
        break;
      case "invoices":
        comparison = (a.total_invoices || 0) - (b.total_invoices || 0);
        break;
      case "high":
        comparison = (a.invoice_risk_distribution?.HIGH || 0) - (b.invoice_risk_distribution?.HIGH || 0);
        break;
      case "medium":
        comparison = (a.invoice_risk_distribution?.MEDIUM || 0) - (b.invoice_risk_distribution?.MEDIUM || 0);
        break;
      case "low":
        comparison = (a.invoice_risk_distribution?.LOW || 0) - (b.invoice_risk_distribution?.LOW || 0);
        break;
      default:
        return 0;
    }

    return sortConfig.order === "asc" ? comparison : -comparison;
  });

  const handleSort = (column) => {
    setSortConfig((prev) => ({
      column,
      order: prev.column === column && prev.order === "asc" ? "desc" : "asc",
    }));
    setPage(0);
  };

  const SortIcon = ({ column }) => {
    if (sortConfig.column !== column) return <ArrowUpDown className="w-4 h-4 text-slate-400" />;
    return sortConfig.order === "asc" ? <ArrowUp className="w-4 h-4 text-slate-600" /> : <ArrowDown className="w-4 h-4 text-slate-600" />;
  };

  const pagedPartners = sortedPartners.slice(page * limit, page * limit + limit);

  return (
    <div className="space-y-8">
      {/* Header + Export */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Partner Risk Insights</h1>
          <p className="text-slate-500 mt-1">
            Invoice-level ML risk aggregated at partner level
          </p>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="btn-secondary">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => handleExport("excel")}>
              Export as Excel
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport("csv")}>
              Export as CSV
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* ===== Minimal Search Bar Added ===== */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by partner name or code"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              className="pl-10 input-glass"
            />
          </div>
          {riskFilter && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">Filtered by:</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                riskFilter === "HIGH" ? "bg-red-100 text-red-800" :
                riskFilter === "MEDIUM" ? "bg-yellow-100 text-yellow-800" :
                "bg-green-100 text-green-800"
              }`}>
                {riskFilter} Risk
              </span>
              <button
                onClick={() => setRiskFilter(null)}
                className="text-xs text-slate-500 hover:text-slate-700"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Partner Risk Table */}
      {pagedPartners && (
        <div className="glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("partner")}>
                  <div className="flex items-center gap-2">Partner <SortIcon column="partner" /></div>
                </th>
                <th className="text-center px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("risk")}>
                  <div className="flex items-center justify-center gap-2">Risk <SortIcon column="risk" /></div>
                </th>
                <th className="text-center px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("invoices")}>
                  <div className="flex items-center justify-center gap-2">Invoices <SortIcon column="invoices" /></div>
                </th>
                <th className="text-center px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("high")}>
                  <div className="flex items-center justify-center gap-2">HIGH <SortIcon column="high" /></div>
                </th>
                <th className="text-center px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("medium")}>
                  <div className="flex items-center justify-center gap-2">MEDIUM <SortIcon column="medium" /></div>
                </th>
                <th className="text-center px-4 py-3 cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("low")}>
                  <div className="flex items-center justify-center gap-2">LOW <SortIcon column="low" /></div>
                </th>
              </tr>
            </thead>
            <tbody>
              {pagedPartners.map((p) => (
                <tr key={p.partner_code} className="border-b hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => navigate(`/ar/partners/${p.partner_code}/details`, { state: { from: 'insights' } })}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{p.partner_name}</div>
                    <div className="text-xs text-slate-500">{p.partner_code}</div>
                  </td>
                  <td className="text-center px-4 py-3">
                    <RiskBadge bucket={p.risk_bucket} />
                  </td>
                  <td className="text-center px-4 py-3">{p.total_invoices}</td>
                  <td className="text-center px-4 py-3 text-red-600">{p.invoice_risk_distribution.HIGH}</td>
                  <td className="text-center px-4 py-3 text-amber-500">{p.invoice_risk_distribution.MEDIUM}</td>
                  <td className="text-center px-4 py-3 text-emerald-600">{p.invoice_risk_distribution.LOW}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* ======= Partners-style Pagination ======= */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
            <p className="text-sm text-slate-500">
              Showing {page * limit + 1} to {Math.min(page * limit + pagedPartners.length, sortedPartners.length)} of {sortedPartners.length}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-slate-600 px-3">Page {page + 1}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * limit >= sortedPartners.length}
                className="btn-secondary"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* =========================
   Small Components
========================= */

function RiskBadge({ bucket }) {
  const map = {
    HIGH: "bg-red-100 text-red-700",
    MEDIUM: "bg-amber-100 text-amber-700",
    LOW: "bg-emerald-100 text-emerald-700"
  };

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${map[bucket]}`}>
      {bucket}
    </span>
  );
}

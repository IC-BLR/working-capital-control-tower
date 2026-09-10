import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Search,
  Download,
  Users,
  Building2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  Funnel
} from "lucide-react";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { toast } from "sonner";
import { AR_API_BASE } from "../config";
import * as XLSX from "xlsx";

/* =========================
   Helper Functions
========================= */
const formatCurrency = (value) => {
  if (!value) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
};

const formatCrores = (value) => {
  // Display full number without any unit notation
  return formatCurrency(value || 0);
};

/* =========================
   Main Component
========================= */
export default function Partners() {
  const location = useLocation();
  const navigate = useNavigate();
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [sortConfig, setSortConfig] = useState({ column: null, order: "asc" });
  const [filters, setFilters] = useState({
    outstanding: { operator: ">", value: "" },
    overdue: { operator: ">", value: "" },
  });
  const [showFilter, setShowFilter] = useState({ outstanding: false, overdue: false });
  const [agingBucketFilter, setAgingBucketFilter] = useState(location.state?.filterAgingBucket || null);
  const limit = 10;

  // Handle aging bucket filter from navigation
  useEffect(() => {
    if (location.state?.filterAgingBucket) {
      setAgingBucketFilter(location.state.filterAgingBucket);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state?.filterAgingBucket, navigate, location.pathname]);

  /* =========================
     Data Fetch
  ========================== */
  const fetchPartners = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${AR_API_BASE}/partners`);
      setPartners(response.data || []);
    } catch (error) {
      console.error("Error fetching partners:", error);
      toast.error("Failed to load partners");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPartners();
  }, []);

  /* =========================
     Sorting
  ========================== */
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

  /* =========================
     Filter Handling
  ========================== */
  const handleApplyFilter = (column) => {
    setShowFilter((prev) => ({ ...prev, [column]: false }));
    setPage(0);
  };

  const handleCancelFilter = (column) => {
    setFilters((prev) => ({
      ...prev,
      [column]: { operator: ">", value: "" },
    }));
    setShowFilter((prev) => ({ ...prev, [column]: false }));
  };

  const filteredPartners = partners
    .filter(
      (p) =>
        p.partner_name?.toLowerCase().includes(search.toLowerCase()) ||
        p.partner_code?.toLowerCase().includes(search.toLowerCase())
    )
    .filter((p) => {
      // Aging bucket filter
      if (agingBucketFilter && p.aging_bucket !== agingBucketFilter) {
        return false;
      }
      // Outstanding filter
      if (filters.outstanding.value !== "") {
        const val = Math.round(Number(filters.outstanding.value));
        const due = Math.round(Number(p.total_due_amount || 0));

        switch (filters.outstanding.operator) {
          case ">": if (!(due > val)) return false; break;
          case "<": if (!(due < val)) return false; break;
          case "=": if (due !== val) return false; break;
          case ">=": if (!(due >= val)) return false; break;
          case "<=": if (!(due <= val)) return false; break;
        }
      }

      // Overdue filter
      if (filters.overdue.value !== "") {
        const val = Math.round(Number(filters.overdue.value));
        const overdue = Math.round(Number(p.total_overdue || 0));

        switch (filters.overdue.operator) {
          case ">": if (!(overdue > val)) return false; break;
          case "<": if (!(overdue < val)) return false; break;
          case "=": if (overdue !== val) return false; break;
          case ">=": if (!(overdue >= val)) return false; break;
          case "<=": if (!(overdue <= val)) return false; break;
        }
      }

      return true;
    });

  // Calculate totals
  const totalOutstanding = filteredPartners.reduce((sum, p) => sum + (p.total_due_amount || 0), 0);
  const totalOverdue = filteredPartners.reduce((sum, p) => sum + (p.total_overdue || 0), 0);

  // Sorting
  const sortedPartners = [...filteredPartners].sort((a, b) => {
    if (!sortConfig.column) return 0;
    let comparison = 0;
    switch (sortConfig.column) {
      case "partner":
        comparison = (a.partner_name || "").localeCompare(b.partner_name || "");
        break;
      case "outstanding":
        comparison = (a.total_due_amount || 0) - (b.total_due_amount || 0);
        break;
      case "overdue":
        comparison = (a.total_overdue || 0) - (b.total_overdue || 0);
        break;
      default:
        return 0;
    }
    return sortConfig.order === "asc" ? comparison : -comparison;
  });

  const pagedPartners = sortedPartners.slice(page * limit, page * limit + limit);

  /* =========================
     Export filtered data
  ========================== */
  const handleExport = (format) => {
    if (!filteredPartners || filteredPartners.length === 0) return;

    if (format === "csv") {
      const csvContent = [
        ["Partner Name", "Partner Code", "Outstanding", "Overdue"],
        ...filteredPartners.map((p) => [
          p.partner_name,
          p.partner_code,
          p.total_due_amount,
          p.total_overdue
        ])
      ].map(row => row.join(",")).join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `partners_filtered_${new Date().toISOString().split("T")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }

    if (format === "excel") {
      const ws = XLSX.utils.json_to_sheet(
        filteredPartners.map((p) => ({
          "Partner Name": p.partner_name,
          "Partner Code": p.partner_code,
          "Outstanding": p.total_due_amount,
          "Overdue": p.total_overdue
        }))
      );
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Partners");
      XLSX.writeFile(wb, `partners_filtered_${new Date().toISOString().split("T")[0]}.xlsx`);
    }

    toast.success(`Exported ${format.toUpperCase()} successfully`);
  };

  /* =========================
     Render
  ========================== */
  return (
    <div className="space-y-8" data-testid="partners-page">
      {/* Header + Export */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Partners</h1>
          <p className="text-slate-500 mt-1">Partner Records</p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="btn-secondary">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => handleExport("excel")}>Export as Excel</DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport("csv")}>Export as CSV</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SummaryCard label="Total Outstanding" value={totalOutstanding} icon={Building2} color="orange"/>
        <SummaryCard label="Total Overdue" value={totalOverdue} icon={AlertTriangle} color="red"/>
      </div>

      {/* Search */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-4">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by partner name or code"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="pl-10 input-glass"
            />
          </div>
          {agingBucketFilter && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">Filtered by:</span>
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {agingBucketFilter}
              </span>
              <button
                onClick={() => {
                  setAgingBucketFilter(null);
                  setPage(0);
                }}
                className="text-xs text-slate-500 hover:text-slate-700"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="table-header">
              
              {/* PARTNER COLUMN - Working */}
              <TableHead
                className="cursor-pointer hover:bg-slate-100 select-none"
                onClick={() => handleSort("partner")}
              >
                <div className="flex items-center gap-2">Partner <SortIcon column="partner"/></div>
              </TableHead>

              {/* OUTSTANDING COLUMN - Fixed */}
              <TableHead className="select-none">
                <div className="flex items-center gap-2">
                  {/* WRAPPED SORTABLE AREA IN CLICKABLE DIV */}
                  <div 
                    className="flex items-center gap-2 cursor-pointer hover:text-slate-900" 
                    onClick={() => handleSort("outstanding")}
                  >
                    Outstanding Amount
                    <SortIcon column="outstanding" />
                  </div>

                  {/* Filter Button (Stops propagation so it doesn't trigger sort) */}
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowFilter((prev) => ({ ...prev, outstanding: !prev.outstanding }));
                    }}
                  >
                    <Funnel className="w-4 h-4" />
                  </Button>
                </div>
                {/* INLINE FILTER DROPDOWN */}
                {showFilter.outstanding && (
                  <div className="flex gap-2 mt-2">
                    <select
                      value={filters.outstanding.operator}
                      onChange={(e) => setFilters((prev) => ({ ...prev, outstanding: { ...prev.outstanding, operator: e.target.value } }))}
                      className="input-glass"
                    >
                      <option value=">">Greater Than</option>
                      <option value="<">Less Than</option>
                      <option value="=">Equal To</option>
                      <option value=">=">Greater Than or Equal To</option>
                      <option value="<=">Less Than or Equal To</option>
                    </select>
                    <Input
                      type="number"
                      value={filters.outstanding.value}
                      onChange={(e) => setFilters((prev) => ({ ...prev, outstanding: { ...prev.outstanding, value: e.target.value } }))}
                      placeholder="Amount"
                      className="input-glass"
                    />
                    <Button size="sm" onClick={() => handleApplyFilter("outstanding")}>Apply</Button>
                    <Button size="sm" variant="ghost" onClick={() => handleCancelFilter("outstanding")}>Cancel</Button>
                  </div>
                )}
              </TableHead>

              {/* OVERDUE COLUMN - Fixed */}
              <TableHead className="select-none">
                <div className="flex items-center gap-2">
                  {/* WRAPPED SORTABLE AREA IN CLICKABLE DIV */}
                  <div 
                    className="flex items-center gap-2 cursor-pointer hover:text-slate-900" 
                    onClick={() => handleSort("overdue")}
                  >
                    Total Overdue
                    <SortIcon column="overdue" />
                  </div>

                  {/* Filter Button */}
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowFilter((prev) => ({ ...prev, overdue: !prev.overdue }));
                    }}
                  >
                    <Funnel className="w-4 h-4" />
                  </Button>
                </div>
                {/* INLINE FILTER DROPDOWN */}
                {showFilter.overdue && (
                  <div className="flex gap-2 mt-2">
                    <select
                      value={filters.overdue.operator}
                      onChange={(e) => setFilters((prev) => ({ ...prev, overdue: { ...prev.overdue, operator: e.target.value } }))}
                      className="input-glass"
                    >
                      <option value=">">Greater Than</option>
                      <option value="<">Less Than</option>
                      <option value="=">Equal To</option>
                      <option value=">=">Greater Than or Equal To</option>
                      <option value="<=">Less Than or Equal To</option>
                    </select>
                    <Input
                      type="number"
                      value={filters.overdue.value}
                      onChange={(e) => setFilters((prev) => ({ ...prev, overdue: { ...prev.overdue, value: e.target.value } }))}
                      placeholder="Amount"
                      className="input-glass"
                    />
                    <Button size="sm" onClick={() => handleApplyFilter("overdue")}>Apply</Button>
                    <Button size="sm" variant="ghost" onClick={() => handleCancelFilter("overdue")}>Cancel</Button>
                  </div>
                )}
              </TableHead>
              <TableHead>Aging Bucket</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? [...Array(5)].map((_, i) => (
              <TableRow key={i}>
                {[...Array(4)].map((_, j) => (
                  <TableCell key={j}><div className="h-4 bg-slate-200 rounded animate-pulse"/></TableCell>
                ))}
              </TableRow>
            )) : pagedPartners.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-12">
                  <Users className="w-12 h-12 text-slate-300 mx-auto mb-3"/>
                  <p className="text-slate-500">No partners found</p>
                </TableCell>
              </TableRow>
            ) : (
              pagedPartners.map((partner) => (
                <TableRow key={partner.partner_code} className="table-row">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-emerald-700" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{partner.partner_name}</p>
                        <p className="text-xs text-slate-500">{partner.partner_code}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-orange-600 font-medium">{formatCurrency(partner.total_due_amount)}</TableCell>
                  <TableCell className="text-red-600 font-medium">{formatCurrency(partner.total_overdue)}</TableCell>
                  <TableCell><span className="badge-info">{partner.aging_bucket}</span></TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
          <p className="text-sm text-slate-500">
            Showing {page * limit + 1} to {Math.min(page * limit + pagedPartners.length, sortedPartners.length)} of {sortedPartners.length}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary">
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-slate-600 px-3">Page {page + 1}</span>
            <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={(page + 1) * limit >= sortedPartners.length} className="btn-secondary">
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================
   Summary Card
========================= */
function SummaryCard({ label, value, icon: Icon, color }) {
  const colors = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    orange: "bg-orange-100 text-orange-700"
  };

  return (
    <div className="glass-card p-4 flex items-center gap-4">
      <div className={`p-3 rounded-xl ${colors[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="text-2xl font-bold text-slate-900">{formatCrores(value)}</p>
      </div>
    </div>
  );
}
import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import {
  Search,
  Download,
  FileText,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  X,
  CreditCard,
  Calendar,
  Loader2
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

/* ... PaymentHistoryPanel Component stays exactly the same ... */
const PaymentHistoryPanel = ({ invoice, onClose }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const formatCurrency = (val) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(val || 0);
  const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString("en-IN", { year: 'numeric', month: 'short', day: 'numeric' }) : "-";

  useEffect(() => {
    const fetchHistory = async () => {
      if (!invoice) return;
      try {
        setLoading(true);
        const response = await axios.get(`${AR_API_BASE}/invoices/${encodeURIComponent(invoice.invoice_number)}/history`);
        setHistory(response.data || []);
      } catch (error) {
        console.error("History fetch error:", error);
        toast.error("Could not load audit trail");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [invoice]);

  if (!invoice) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white shadow-2xl h-full flex flex-col animate-in slide-in-from-right duration-300">
        <div className="p-6 border-b border-slate-100 flex justify-between items-start bg-slate-50/50">
          <div>
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-500" />
              {invoice.invoice_number}
            </h2>
            <p className="text-sm text-slate-500 mt-1">Audit Trail & Payment History</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 rounded-full hover:bg-slate-200">
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 p-6 bg-white border-b border-slate-100">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Invoice</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(invoice.invoice_amount)}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Balance Due</p>
            <p className={`text-lg font-bold ${invoice.due_amount > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {formatCurrency(invoice.due_amount)}
            </p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30">
          {loading ? (
             <div className="flex flex-col items-center justify-center h-40 gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                <p className="text-xs text-slate-500">Retrieving ledger...</p>
             </div>
          ) : history.length === 0 ? (
             <p className="text-sm text-slate-500 text-center mt-10">No history found.</p>
          ) : (
            <div className="relative pl-4 border-l-2 border-slate-200 space-y-8">
              {history.map((event, idx) => {
                const isPayment = event.event_type === 'Payment Received';
                return (
                  <div key={idx} className="relative group">
                    <div className={`absolute -left-[23px] top-1 h-5 w-5 rounded-full border-2 bg-white flex items-center justify-center
                      ${isPayment ? 'border-emerald-500' : 'border-slate-300'}`}>
                      <div className={`h-2 w-2 rounded-full ${isPayment ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                    </div>
                    <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                      <div className="flex justify-between items-start mb-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide
                          ${isPayment ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                          {event.event_type}
                        </span>
                        <span className="text-xs text-slate-400 flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {formatDate(event.event_date)}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-2 rounded-full ${isPayment ? 'bg-emerald-100' : 'bg-slate-100'}`}>
                          {isPayment ? <CreditCard className="w-4 h-4 text-emerald-700" /> : <FileText className="w-4 h-4 text-slate-600" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">
                             {formatCurrency(isPayment ? event.allocated_amount : event.invoice_total)}
                          </p>
                          {isPayment && event.total_payment_check > event.allocated_amount && (
                             <p className="text-xs text-slate-500 mt-0.5">
                               Part of bulk txn: {formatCurrency(event.total_payment_check)}
                             </p>
                          )}
                        </div>
                      </div>
                      {event.payment_reference && (
                        <div className="bg-slate-50 rounded border border-slate-100 p-2 mt-2">
                          <p className="text-[10px] uppercase text-slate-400 font-semibold">Reference</p>
                          <p className="text-xs font-mono text-slate-600 mt-0.5 break-all">
                            {event.payment_reference}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ==================================================================================
   MAIN COMPONENT (OPTIMIZED)
   ================================================================================== */
export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  // CHANGED: Default sort set to { column: "amount", order: "desc" }
  const [sortConfig, setSortConfig] = useState({ column: "amount", order: "desc" });
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const limit = 15;

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${AR_API_BASE}/invoices`);
      setInvoices(response.data || []);
    } catch (error) {
      console.error("Error fetching invoices:", error);
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value || 0);

  const getStatusBadge = (overdueDays) => {
    if (overdueDays > 90) return <span className="badge-danger">Overdue</span>;
    if (overdueDays > 0) return <span className="badge-warning">Pending</span>;
    return <span className="badge-success">On Time</span>;
  };

  // --- OPTIMIZATION 1: useMemo for Filtering ---
  const filtered = useMemo(() => {
    if (!search) return invoices;
    const lowerSearch = search.toLowerCase();
    return invoices.filter(
      (i) =>
        i.invoice_number?.toLowerCase().includes(lowerSearch) ||
        i.partner_name?.toLowerCase().includes(lowerSearch)
    );
  }, [invoices, search]);

  // --- OPTIMIZATION 2: useMemo for Sorting ---
  const sorted = useMemo(() => {
    const sortable = [...filtered];
    if (!sortConfig.column) return sortable;

    return sortable.sort((a, b) => {
      let comparison = 0;
      switch (sortConfig.column) {
        case "invoice":
          comparison = (a.invoice_number || "").localeCompare(b.invoice_number || "");
          break;
        case "partner":
          comparison = (a.partner_name || "").localeCompare(b.partner_name || "");
          break;
        // ADDED: Logic to sort by invoice amount numerically
        case "amount":
          comparison = (a.invoice_amount || 0) - (b.invoice_amount || 0);
          break;
        default:
          return 0;
      }
      return sortConfig.order === "asc" ? comparison : -comparison;
    });
  }, [filtered, sortConfig]);

  const paged = sorted.slice(page * limit, page * limit + limit);

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

  const handleExport = async (format) => {
    try {
      const response = await axios.get(`${AR_API_BASE}/invoices/export?format=${format}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = `invoices_export_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'csv'}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch) filename = filenameMatch[1];
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Invoices exported successfully as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error(`Failed to export invoices: ${error.response?.data?.detail || error.message}`);
    }
  };

  // --- OPTIMIZATION 3: Summary Calculations in useMemo ---
  const summary = useMemo(() => {
    return {
      total: invoices.length,
      overdue: invoices.filter(i => i.overdue_days > 0).length,
      plus90: invoices.filter(i => i.overdue_days >= 90).length,
      onTime: invoices.filter(i => i.overdue_days <= 0).length
    };
  }, [invoices]);

  return (
    <div className="space-y-8" data-testid="invoices-page">
      
      {selectedInvoice && (
        <PaymentHistoryPanel 
          invoice={selectedInvoice} 
          onClose={() => setSelectedInvoice(null)} 
        />
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="page-title">Invoices</h1>
          <p className="text-slate-500 mt-1">
            Invoice-level aging and payment visibility
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
            <DropdownMenuItem onClick={() => handleExport('excel')}>
              Export as Excel
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport('csv')}>
              Export as CSV
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Summary - Uses Memoized Data */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Total Invoices", value: summary.total },
          { label: "Overdue", value: summary.overdue },
          { label: "90+ Days", value: summary.plus90 },
          { label: "On Time", value: summary.onTime },
        ].map((s, i) => (
          <div key={i} className="glass-card p-4 flex gap-4">
            <div className="p-3 bg-slate-100 rounded-xl">
              <FileText className="w-5 h-5 text-slate-700" />
            </div>
            <div>
              <p className="text-sm text-slate-500">{s.label}</p>
              <p className="text-2xl font-bold">{s.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="glass-card p-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search invoice or partner"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            className="pl-10 input-glass"
          />
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("invoice")}>
                <div className="flex items-center gap-2">Invoice # <SortIcon column="invoice" /></div>
              </TableHead>
              <TableHead className="cursor-pointer hover:bg-slate-100 select-none" onClick={() => handleSort("partner")}>
                <div className="flex items-center gap-2">Partner <SortIcon column="partner" /></div>
              </TableHead>
              <TableHead>Invoice Amount</TableHead>
              <TableHead>Outstanding Amount</TableHead>
              <TableHead>Overdue Amount</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading ? (
              [...Array(8)].map((_, i) => (
                <TableRow key={i}>
                  {[...Array(6)].map((_, j) => (
                    <TableCell key={j}><div className="h-4 bg-slate-200 rounded animate-pulse" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : paged.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12">No invoices found</TableCell>
              </TableRow>
            ) : (
              paged.map((inv, idx) => (
                <TableRow key={idx}>
                  <TableCell 
                    className="font-mono font-medium text-blue-600 hover:text-blue-800 cursor-pointer hover:underline underline-offset-4"
                    onClick={() => setSelectedInvoice(inv)}
                  >
                    {inv.invoice_number}
                  </TableCell>
                  <TableCell>{inv.partner_name}</TableCell>
                  <TableCell className="text-emerald-700 font-semibold">{formatCurrency(inv.invoice_amount)}</TableCell>
                  <TableCell>{formatCurrency(inv.due_amount)}</TableCell>
                  <TableCell className="text-red-600">{formatCurrency(inv.overdue_amount)}</TableCell>
                  <TableCell>{getStatusBadge(inv.overdue_days)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        <div className="flex justify-between items-center px-6 py-4 border-t">
          <p className="text-sm text-slate-500">
            Showing {page * limit + 1} – {Math.min(page * limit + paged.length, sorted.length)} of {sorted.length}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="px-3">Page {page + 1}</span>
            <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={(page + 1) * limit >= sorted.length}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
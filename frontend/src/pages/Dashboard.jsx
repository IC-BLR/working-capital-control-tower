import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  AlertTriangle,
  Building2,
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  PieChart,
  Pie,
  Cell as PieCell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  Sector,
  Text
} from "recharts";

import { AR_API_BASE } from "../config";

/* ============================================================
   CSS STYLES
   ============================================================ */
const dashboardStyles = `
  :root {
    --chart-green: #10b981;
    --chart-teal: #0f766e;
    --chart-amber: #f59e0b;
    --chart-red: #ef4444;
    --bg-slate: #f8fafc;
  }

  .cfo-dashboard-container {
    height: 100vh;
    width: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background-color: var(--bg-slate);
    padding: 16px;
    box-sizing: border-box;
    font-family: 'Inter', sans-serif;
  }

  .dashboard-header {
    flex: 0 0 auto;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* Grid Layout */
  .bento-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: 25% 37% 38%;
    gap: 16px;
    min-height: 0;
  }

  .bento-card {
    background: white;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 16px;
    min-width: 0;
    min-height: 0;
    position: relative;
  }

  .card-header {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 12px;
    flex: 0 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .chart-area {
    flex: 1;
    width: 100%;
    min-height: 0;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Table Styling */
  .table-container {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }
  .table-row-pretty td {
    padding: 8px 4px;
    font-size: 0.85rem;
    border-bottom: 1px solid #f1f5f9;
  }
  .table-row-pretty:last-child td { border-bottom: none; }
  .table-row-pretty:hover { background-color: #f8fafc; cursor: pointer; }

  /* Leaderboard List Styling */
  .leaderboard-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
    position: relative;
  }
  .leaderboard-fill-bar {
    position: absolute;
    left: 0;
    bottom: 4px;
    height: 4px;
    background-color: #10b981;
    border-radius: 2px;
    z-index: 1;
  }

  .col-span-2 { grid-column: span 2; }
`;

/* ============================================================
   Helper Components
   ============================================================ */

const formatCurrency = (value) => {
  if (!value) return "₹0";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatCrores = (value) => {
  // Display full number without any unit notation
  return formatCurrency(value || 0);
};

// 1. KPI Tile (Restored to First Code Style: SummaryCardCompact)
function SummaryCardCompact({ label, value, icon: Icon, color }) {
  const colors = {
    slate: "bg-slate-100 text-slate-700",
    red: "bg-red-100 text-red-700",
    amber: "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    orange: "bg-orange-100 text-orange-700"
  };

  return (
    <div className="bento-card justify-center">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-xl ${colors[color] || colors.slate}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold">{label}</p>
          <p className="text-2xl font-bold text-slate-900">{formatCrores(value)}</p>
        </div>
      </div>
    </div>
  );
}

// 2. Risk Pie (Restored to First Code Style: Active Shape + Navigation)
const RiskPieChart = ({ pieChartData, totalPartners }) => {
  const navigate = useNavigate();
  const [activeIndex, setActiveIndex] = useState(null);

  const onPieClick = (entry) => {
    const riskMap = { "High Risk": "HIGH", "Medium Risk": "MEDIUM", "Low Risk": "LOW" };
    const riskType = riskMap[entry.name];
    if (riskType) navigate("/ar/insights", { state: { riskFilter: riskType } });
  };

  if (!pieChartData || pieChartData.length === 0) {
    return <div className="text-slate-400 text-xs">No Data</div>;
  }

  const renderActiveShape = (props) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
    return (
      <g>
        <Sector
          cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 8}
          startAngle={startAngle} endAngle={endAngle} fill={fill}
        />
        <Sector
          cx={cx} cy={cy} startAngle={startAngle} endAngle={endAngle}
          innerRadius={outerRadius + 8} outerRadius={outerRadius + 10} fill={fill}
        />
        <Text x={cx} y={cy} dy={-10} textAnchor="middle" fill="#334155" fontSize={24} fontWeight={700}>
          {totalPartners}
        </Text>
        <Text x={cx} y={cy} dy={15} textAnchor="middle" fill="#94a3b8" fontSize={10} fontWeight={600} textTransform="uppercase">
          Partners
        </Text>
      </g>
    );
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={pieChartData} cx="50%" cy="50%" innerRadius="60%" outerRadius="80%" paddingAngle={3}
          dataKey="value" activeIndex={activeIndex} activeShape={renderActiveShape}
          onMouseEnter={(_, index) => setActiveIndex(index)} onMouseLeave={() => setActiveIndex(null)}
          onClick={onPieClick} cursor="pointer"
        >
          {pieChartData.map((entry, index) => <PieCell key={index} fill={entry.color} />)}
        </Pie>
        <Tooltip />
        <Legend verticalAlign="bottom" height={36} iconSize={10} wrapperStyle={{fontSize: '11px'}} />
      </PieChart>
    </ResponsiveContainer>
  );
};

// 3. Exposure Pie (Improved Donut Look)
const ExposurePieChart = ({ data }) => {
  const [activeIndex, setActiveIndex] = useState(null);

  const renderActiveShape = (props) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
    return (
      <g>
        <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 6} startAngle={startAngle} endAngle={endAngle} fill={fill} />
      </g>
    );
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data} cx="50%" cy="50%" innerRadius="55%" outerRadius="80%" 
          dataKey="value" paddingAngle={2}
          activeIndex={activeIndex} activeShape={renderActiveShape}
          onMouseEnter={(_, index) => setActiveIndex(index)} onMouseLeave={() => setActiveIndex(null)}
          label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
        >
          {data.map((entry, index) => <PieCell key={index} fill={entry.color} />)}
        </Pie>
        <Tooltip formatter={(v) => [formatCrores(v*10000000), "Outstanding"]} contentStyle={{borderRadius: '8px', border:'none', boxShadow:'0 4px 12px rgba(0,0,0,0.1)'}} />
        <Legend layout="horizontal" verticalAlign="bottom" align="center" iconSize={8} wrapperStyle={{fontSize: '10px'}} />
      </PieChart>
    </ResponsiveContainer>
  );
};

// 4. Gauge Chart (Improved Readability)
const GaugeChart = ({ totalInvoice, totalAllocated }) => {
  const percentAllocated = totalInvoice > 0 ? (totalAllocated / totalInvoice) * 100 : 0;
  const unallocatedAmt = Math.max(0, totalInvoice - totalAllocated);
  
  const data = [
    { name: "Risk", value: 30, color: "#ef4444" },
    { name: "Caution", value: 40, color: "#f59e0b" },
    { name: "Healthy", value: 30, color: "#10b981" },
  ];
  
  const needleRotation = -90 + (percentAllocated / 100) * 180;

  return (
    <div className="flex flex-col items-center justify-between w-full h-full relative p-1">
       
       {/* Large Solid Gauge */}
       <div className="relative w-full flex-1 flex items-center justify-center -mt-2">
         <ResponsiveContainer width="100%" height="120%">
          <PieChart margin={{ bottom: 0 }}>
            <Pie
              dataKey="value" startAngle={180} endAngle={0} data={data}
              cx="50%" cy="85%" innerRadius={0} outerRadius="110%" stroke="none"
            >
              {data.map((entry, index) => <Cell key={index} fill={entry.color} />)}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        
        {/* Needle */}
        <div className="absolute" style={{ top: "85%", transform: "translateY(-50%)" }}>
           <div className="relative w-[140px] flex justify-center items-end">
             <div className="w-4 h-4 bg-slate-800 rounded-full z-10 absolute bottom-[-6px] shadow-md"></div>
             <div 
                style={{
                  width: "5px", height: "70px", background: "#1e293b",
                  position: "absolute", bottom: "-6px", left: "calc(50% - 2.5px)",
                  transformOrigin: "bottom center", transform: `rotate(${needleRotation}deg)`,
                  transition: "transform 1s ease", borderRadius: "4px 4px 0 0", zIndex: 5
                }}
             />
           </div>
        </div>
      </div>

      {/* Detailed Figures */}
      <div className="w-full grid grid-cols-2 gap-1.5 mt-1 border-t border-slate-100 pt-1">
         <div className="text-center bg-slate-50 rounded p-1">
            <span className="text-[9px] text-slate-500 uppercase font-bold block">Invoiced</span>
            <span className="text-xs font-bold text-slate-800">{formatCrores(totalInvoice)}</span>
         </div>
         <div className="text-center bg-slate-50 rounded p-1">
            <span className="text-[9px] text-slate-500 uppercase font-bold block">Allocated</span>
            <span className="text-xs font-bold text-emerald-600">{formatCrores(totalAllocated)}</span>
         </div>
         <div className="col-span-2 text-center flex justify-between px-2 items-center bg-slate-50/50 rounded p-1">
            <span className="text-[10px] text-slate-500">Unallocated: <span className="text-red-500 font-bold">{formatCrores(unallocatedAmt)}</span></span>
            <span className="text-[10px] font-bold text-slate-800">{percentAllocated.toFixed(1)}% Coverage</span>
         </div>
      </div>
    </div>
  );
};

// 5. Top Outstanding List
const TopOutstandingList = ({ data, navigate }) => {
  const maxVal = Math.max(...data.map(d => d.value));
  return (
    <div className="w-full h-full overflow-y-auto pr-2 custom-scrollbar">
      {data.map((item, idx) => (
        <div key={idx} className="leaderboard-item cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => navigate(`/ar/partners/${item.partner_code}/details`)}>
          <div className="absolute inset-0 bg-transparent z-10" /> 
          <div className="leaderboard-fill-bar" style={{ width: `${(item.value / maxVal) * 100}%`, opacity: 0.1, height: '100%', bottom: 0, backgroundColor: '#10b981' }} />
          <div className="flex flex-col z-20 pl-2">
            <span className="font-semibold text-sm text-slate-700 truncate max-w-[150px]">{item.name}</span>
            <span className="text-[10px] text-slate-400">{item.partner_code}</span>
          </div>
          <div className="z-20 pr-2">
             <span className="font-bold text-slate-800">{formatCurrency(item.value * 10000000)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ============================================================
   MAIN DASHBOARD
   ============================================================ */
export default function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("30d");
  const [riskyPartners, setRiskyPartners] = useState([]);
  const [partners, setPartners] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [selectedPartner, setSelectedPartner] = useState("all");
  const [selectedPaymentPartner, setSelectedPaymentPartner] = useState("all");
  const [selectedPaymentMetric, setSelectedPaymentMetric] = useState("allocated");
  /* --- Fetching --- */
  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const [sumRes, partRes, riskRes] = await Promise.all([
          axios.get(`${AR_API_BASE}/summary`, { params: { period } }),
          axios.get(`${AR_API_BASE}/partners`),
          axios.get(`${AR_API_BASE}/insights`)
        ]);
        setSummary(sumRes.data);
        setPartners(partRes.data || []);
        setPortfolioSummary(riskRes.data?.portfolio_summary);
        const highRisk = (riskRes.data?.partner_risk || [])
          .filter(p => p.risk_bucket === "HIGH")
          .sort((a,b) => (b.net_risk_score || 0) - (a.net_risk_score || 0))
          .slice(0, 10);
        setRiskyPartners(highRisk);
      } catch(e) { console.error(e); } finally { setLoading(false); }
    };
    fetchAll();
  }, [period]);

  /* --- Data Prep --- */
  const totalOutstanding = partners.reduce((sum, p) => sum + (p.total_due_amount || 0), 0);
  const totalOverdue = partners.reduce((sum, p) => sum + (p.total_overdue || 0), 0);
  const filteredPartners = selectedPartner === "all" ? partners : partners.filter(p => p.partner_code === selectedPartner);
  const selectedPartnerData = selectedPartner !== "all" ? partners.find(p => p.partner_code === selectedPartner) : null;

  // Chart Data: Cashflow
  const cashFlowData = selectedPartner === "all" 
    ? (summary ? [
        { name: "Total Invoiced", value: (summary.total_invoice_amount || 0) / 10000000 },
        { name: "Allocated", value: (summary.total_allocated_amount || 0) / 10000000 },
        { name: "Outstanding", value: (summary.overall_exposure || 0) / 10000000 },
        { name: "Overdue", value: totalOverdue / 10000000 },
      ] : [])
    : (selectedPartnerData ? [
        { name: "Total Invoiced", value: ((selectedPartnerData.total_due_amount || 0) + (selectedPartnerData.total_allocated_amount || 0)) / 10000000 },
        { name: "Allocated", value: (selectedPartnerData.total_allocated_amount || 0) / 10000000 },
        { name: "Outstanding", value: (selectedPartnerData.total_due_amount || 0) / 10000000 },
        { name: "Overdue", value: (selectedPartnerData.total_overdue || 0) / 10000000 },
      ] : []);

  // Chart Data: Aging
  const agingBuckets = { "Current": 0, "1-30 Days": 0, "31-60 Days": 0, "61-90 Days": 0, "90+ Days": 0 };
  filteredPartners.forEach(p => {
    const bucket = p.aging_bucket || "Current";
    const amt = p.total_due_amount || 0;
    if(bucket.includes("1-30")) agingBuckets["1-30 Days"] += amt;
    else if(bucket.includes("31-60")) agingBuckets["31-60 Days"] += amt;
    else if(bucket.includes("61-90")) agingBuckets["61-90 Days"] += amt;
    else if(bucket.includes("90") || bucket.includes("91")) agingBuckets["90+ Days"] += amt;
    else agingBuckets["Current"] += amt;
  });
  const agingChartData = Object.keys(agingBuckets).map(k => ({ name: k, value: agingBuckets[k] / 10000000 })).filter(i => i.value > 0);

  // Chart Data: Top 5 Outstanding
  const top5OutstandingData = [...partners].sort((a,b) => (b.total_due_amount||0) - (a.total_due_amount||0)).slice(0,5).map(p => ({
    name: p.partner_name, partner_code: p.partner_code, value: (p.total_due_amount||0)/10000000
  }));

  // Chart Data: Exposure Pie
  const exposurePieData = [
    { name: "Top 5 Partners", value: top5OutstandingData.reduce((s,i)=>s+i.value,0), color: "#10b981" },
    { name: "Rest of Portfolio", value: (totalOutstanding/10000000) - top5OutstandingData.reduce((s,i)=>s+i.value,0), color: "#cbd5e1" }
  ].filter(i=>i.value>0);

  // Chart Data: Risk Pie
  const pieChartData = portfolioSummary ? [
    { name: "High Risk", value: portfolioSummary.high_risk_partners || 0, color: "#ef4444" },
    { name: "Medium Risk", value: portfolioSummary.medium_risk_partners || 0, color: "#f59e0b" },
    { name: "Low Risk", value: portfolioSummary.low_risk_partners || 0, color: "#10b981" },
  ].filter(i => i.value > 0) : [];
  const totalPartners = portfolioSummary ? (portfolioSummary.high_risk_partners||0)+(portfolioSummary.medium_risk_partners||0)+(portfolioSummary.low_risk_partners||0) : 0;

  // Gauge Data Prep
  const selPayPartner = selectedPaymentPartner === "all" ? null : partners.find(p=>p.partner_name === selectedPaymentPartner);
  const gaugeInvoice = selPayPartner ? (selPayPartner.total_due_amount||0)+(selPayPartner.total_allocated_amount||0) : summary?.total_invoice_amount || 0;
  const gaugeAllocated = selPayPartner ? (selPayPartner.total_allocated_amount||0) : summary?.total_allocated_amount || 0;


  if (loading) return <div className="h-screen w-full flex items-center justify-center text-slate-500 animate-pulse font-medium">Loading CFO Dashboard...</div>;

  return (
    <>
      <style>{dashboardStyles}</style>
      <div className="cfo-dashboard-container">
        
        {/* --- Header --- */}
        <div className="dashboard-header">
          <h1 className="page-title">CFO Executive Dashboard</h1>
          <div className="flex items-center gap-3">
             <span className="text-sm font-medium text-slate-500">Period:</span>
             <Select value={period} onValueChange={setPeriod}>
                <SelectTrigger className="w-32 h-9 bg-white border-slate-300"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                  <SelectItem value="90d">Last 90 Days</SelectItem>
                </SelectContent>
             </Select>
          </div>
        </div>

        {/* --- Bento Grid --- */}
        <div className="bento-grid">

          {/* === ROW 1 === */}
          
          {/* KPI 1 (Code 1 Style) */}
          <SummaryCardCompact label="Total Outstanding" value={totalOutstanding} icon={Building2} color="orange" />
          
          {/* KPI 2 (Code 1 Style) */}
          <SummaryCardCompact label="Total Overdue" value={totalOverdue} icon={AlertTriangle} color="red" />

          {/* Top 5 Risky Table */}
          <div className="bento-card col-span-2">
            <div className="card-header">Top 5 Risky Partners</div>
            <div className="table-container">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-bold text-slate-700">Partner</TableHead>
                    <TableHead className="font-bold text-slate-700 text-right">Risk Score</TableHead>
                    <TableHead className="font-bold text-slate-700 text-right">Bucket</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {riskyPartners.slice(0, 5).map((p, i) => (
                    <TableRow key={i} className="table-row-pretty" onClick={() => navigate(`/ar/partners/${p.partner_code}/details`)}>
                      <TableCell className="font-medium text-slate-900">{p.partner_name}</TableCell>
                      <TableCell className="text-right font-mono text-slate-600">{p.net_risk_score?.toFixed(2)}</TableCell>
                      <TableCell className="text-right">
                         <span className="px-2 py-1 rounded-md text-[10px] uppercase font-bold bg-red-50 text-red-600 border border-red-100">
                           {p.risk_bucket}
                         </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* === ROW 2 === */}

          {/* Risk Pie (Code 1 Style) */}
          <div className="bento-card">
            <div className="card-header">Partner Risk Profile</div>
            <div className="chart-area">
              <RiskPieChart pieChartData={pieChartData} totalPartners={totalPartners} />
            </div>
          </div>

          {/* Cashflow Chart */}
          <div className="bento-card col-span-2">
            <div className="card-header">
              <span>Cashflow Analysis</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500">Filter:</span>
                <Select value={selectedPartner} onValueChange={setSelectedPartner}>
                  <SelectTrigger className="w-48 h-8 text-xs bg-slate-50 border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Partners</SelectItem>
                    {partners.map(p => <SelectItem key={p.partner_code} value={p.partner_code}>{p.partner_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="chart-area">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cashFlowData} margin={{top: 20, right: 30, left: 0, bottom: 0}} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.4} />
                  <XAxis dataKey="name" tick={{fontSize: 11, fill:"#64748b", fontWeight: 500}} axisLine={{stroke: '#e2e8f0'}} tickLine={false} dy={10} />
                  <YAxis tick={{fontSize: 11, fill:"#64748b"}} axisLine={false} tickLine={false} tickFormatter={(val)=>`₹${val}`} />
                  <Tooltip cursor={{fill: '#f1f5f9'}} formatter={(val) => [formatCrores(val*10000000), "Value"]} contentStyle={{borderRadius: '8px', border:'none', boxShadow:'0 4px 12px rgba(0,0,0,0.1)'}} />
                  <Bar dataKey="value" fill="var(--chart-green)" radius={[6, 6, 0, 0]} barSize={100} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AR Aging */}
          <div className="bento-card">
             <div className="card-header">AR Aging Overview</div>
             <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={agingChartData} margin={{top: 20, right: 10, left: -20, bottom: 0}}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.4} />
                    <XAxis dataKey="name" tick={{fontSize: 10, fill:"#64748b"}} axisLine={{stroke: '#e2e8f0'}} tickLine={false} dy={10} />
                    <YAxis tick={{fontSize: 10, fill:"#64748b"}} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{fill: '#f1f5f9'}} formatter={(val) => [formatCrores(val*10000000), "Outstanding"]} contentStyle={{borderRadius: '8px', border:'none', boxShadow:'0 4px 12px rgba(0,0,0,0.1)'}} />
                    <Bar dataKey="value" fill="var(--chart-green)" radius={[4, 4, 0, 0]} barSize={60} />
                  </BarChart>
                </ResponsiveContainer>
             </div>
          </div>


          {/* === ROW 3 === */}

          {/* Top 5 Outstanding List */}
          <div className="bento-card col-span-2">
            <div className="card-header">Top 5 Partners: Total Outstanding Amount</div>
            <TopOutstandingList data={top5OutstandingData} navigate={navigate} />
          </div>

          {/* Allocation Health Gauge */}
         <div className="bento-card">
             <div className="card-header">
                <span>Alloc. Health</span>
                <Select value={selectedPaymentPartner} onValueChange={setSelectedPaymentPartner}>
                   <SelectTrigger className="w-32 h-7 text-[11px] bg-slate-50 border-slate-200"><SelectValue /></SelectTrigger>
                   <SelectContent>
                     <SelectItem value="all">All Partners</SelectItem>
                     {partners.map(p => <SelectItem key={p.partner_code} value={p.partner_name}>{p.partner_name}</SelectItem>)}
                   </SelectContent>
                </Select>
             </div>
             <div className="chart-area">
                <GaugeChart totalInvoice={gaugeInvoice} totalAllocated={gaugeAllocated} />
             </div>
          </div>


          {/* Exposure Pie */}
           <div className="bento-card">
             <div className="card-header">Exposure Concentration</div>
             <div className="chart-area">
               <ExposurePieChart data={exposurePieData} />
             </div>
          </div>

        </div>
      </div>
    </>
  );
}
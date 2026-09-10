import { useEffect, useState } from "react";
import axios from "axios";
import { 
  ArrowRight,
  Calendar,
  Target,
  Download,
  TrendingUp,
  TrendingDown
} from "lucide-react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine
} from "recharts";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";

import { AR_API_BASE } from "../config";

export default function Forecast() {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState("30");
  const [selectedPartner, setSelectedPartner] = useState("all");
  const [selectedScenario, setSelectedScenario] = useState("baseline");
  const [partners, setPartners] = useState([]);

  const fetchPartners = async () => {
    try {
      const response = await axios.get(`${AR_API_BASE}/partners`);
      setPartners(response.data || []);
    } catch (error) {
      console.error("Error fetching partners:", error);
      // Don't show error toast for partners, just log it
    }
  };

  const fetchForecast = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ days });
      if (selectedPartner && selectedPartner !== "all") {
        params.append("partner_code", selectedPartner);
      }
      const response = await axios.get(`${AR_API_BASE}/forecast?${params.toString()}`);
      if (selectedScenario && selectedScenario !== "baseline") {
        params.append("scenario", selectedScenario);
      }
      setForecast(response.data);
    } catch (error) {
      console.error("Error fetching forecast:", error);
      toast.error("Failed to load forecast");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPartners();
  }, []);

  useEffect(() => {
    fetchForecast();
  }, [days, selectedPartner, selectedScenario]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value || 0);
  };

  const formatCompact = (value) => {
    if (value >= 10000000) {
      return `₹${(value / 10000000).toFixed(1)}Cr`;
    } else if (value >= 100000) {
      return `₹${(value / 100000).toFixed(1)}L`;
    } else if (value >= 1000) {
      return `₹${(value / 1000).toFixed(0)}K`;
    }
    return `₹${(value || 0).toFixed(0)}`;
  };

  const formatBillions = (value) => {
    // Display full number without any unit notation
    return formatCurrency(value || 0);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const aggregateByMonth = (dailyData) => {
    if (!dailyData || dailyData.length === 0) return [];
    
    // Create a map to aggregate by month
    const monthlyData = {};
    
    dailyData.forEach(day => {
      const date = new Date(day.date);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const monthLabel = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      
      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = {
          month: monthLabel,
          monthKey: monthKey,
          projected_inflow: 0,
          projected_outflow: 0,
          projected_net: 0,
          projected_balance: 0,
          invoice_count: 0,
          days: []
        };
      }
      
      monthlyData[monthKey].projected_inflow += day.projected_inflow || 0;
      monthlyData[monthKey].projected_outflow += day.projected_outflow || 0;
      monthlyData[monthKey].projected_net += day.projected_net || 0;
      monthlyData[monthKey].invoice_count += day.invoice_count || 0;
      monthlyData[monthKey].days.push(day);
    });
    
    // Get current month and next 6 months
    const today = new Date();
    const months = [];
    
    for (let i = 0; i < 7; i++) {
      const monthDate = new Date(today.getFullYear(), today.getMonth() + i, 1);
      const monthKey = `${monthDate.getFullYear()}-${String(monthDate.getMonth() + 1).padStart(2, '0')}`;
      const monthLabel = monthDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      
      if (monthlyData[monthKey]) {
        // Use last day's balance for the month
        const lastDay = monthlyData[monthKey].days[monthlyData[monthKey].days.length - 1];
        months.push({
          month: monthLabel,
          monthKey: monthKey,
          projected_inflow: monthlyData[monthKey].projected_inflow,
          projected_outflow: monthlyData[monthKey].projected_outflow,
          projected_net: monthlyData[monthKey].projected_net,
          projected_balance: lastDay?.projected_balance || monthlyData[monthKey].projected_balance,
          invoice_count: monthlyData[monthKey].invoice_count
        });
      } else {
        // Create empty month entry
        months.push({
          month: monthLabel,
          monthKey: monthKey,
          projected_inflow: 0,
          projected_outflow: 0,
          projected_net: 0,
          projected_balance: i === 0 ? (dailyData[0]?.projected_balance || 0) : months[i - 1]?.projected_balance || 0,
          invoice_count: 0
        });
      }
    }
    
    return months;
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse" data-testid="forecast-loading">
        <div className="h-10 bg-slate-200 rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <div key={i} className="h-32 bg-slate-200 rounded-2xl" />
          ))}
        </div>
        <div className="h-96 bg-slate-200 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="forecast-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Cash Flow Forecast</h1>
          <p className="text-slate-500 mt-1">Trend-based projections and recommendations</p>
          {forecast?.scenario_description && (
            <div className="mt-2 flex items-center gap-2">
              <div className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                {selectedScenario === "recession" ? <TrendingDown className="w-3 h-3 inline mr-1" /> : 
                 selectedScenario === "growth" ? <TrendingUp className="w-3 h-3 inline mr-1" /> : 
                 "📊"}
                {forecast.scenario_description}
              </div>
            </div>
          )}
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-40 input-glass" data-testid="forecast-days-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 Days</SelectItem>
              <SelectItem value="14">14 Days</SelectItem>
              <SelectItem value="30">30 Days</SelectItem>
              <SelectItem value="60">60 Days</SelectItem>
              <SelectItem value="90">90 Days</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={selectedPartner} onValueChange={setSelectedPartner}>
            <SelectTrigger className="w-64 input-glass" data-testid="forecast-partner-select">
              <SelectValue placeholder="Select Partner" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Partners</SelectItem>
              {partners.map((partner) => (
                <SelectItem key={partner.partner_code} value={partner.partner_code}>
                  {partner.partner_name || partner.partner_code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedScenario} onValueChange={setSelectedScenario}>
            <SelectTrigger className="w-64 input-glass" data-testid="forecast-scenario-select">
              <SelectValue placeholder="Select Scenario" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="baseline">📊 Baseline Forecast</SelectItem>
              <SelectItem value="partner_increase_10">📈 Partners +10%</SelectItem>
              <SelectItem value="partner_increase_20">📈 Partners +20%</SelectItem>
              <SelectItem value="partner_increase_30">📈 Partners +30%</SelectItem>
              <SelectItem value="partner_decrease_10">📉 Partners -10%</SelectItem>
              <SelectItem value="partner_decrease_20">📉 Partners -20%</SelectItem>
              <SelectItem value="partner_decrease_30">📉 Partners -30%</SelectItem>
              <SelectItem value="payment_delay_7">⏱️ Payment Delay +7 days</SelectItem>
              <SelectItem value="payment_delay_14">⏱️ Payment Delay +14 days</SelectItem>
              <SelectItem value="payment_delay_30">⏱️ Payment Delay +30 days</SelectItem>
              <SelectItem value="invoice_increase_10">💰 Invoice Amounts +10%</SelectItem>
              <SelectItem value="invoice_increase_20">💰 Invoice Amounts +20%</SelectItem>
              <SelectItem value="invoice_decrease_10">💰 Invoice Amounts -10%</SelectItem>
              <SelectItem value="invoice_decrease_20">💰 Invoice Amounts -20%</SelectItem>
              <SelectItem value="payment_coverage_increase_10">✅ Payment Coverage +10%</SelectItem>
              <SelectItem value="payment_coverage_increase_20">✅ Payment Coverage +20%</SelectItem>
              <SelectItem value="payment_coverage_decrease_10">⚠️ Payment Coverage -10%</SelectItem>
              <SelectItem value="payment_coverage_decrease_20">⚠️ Payment Coverage -20%</SelectItem>
              <SelectItem value="recession">📉 Recession Scenario</SelectItem>
              <SelectItem value="growth">📈 Growth Scenario</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-1 gap-6 max-w-md">
        {/* Projected Balance */}
        <div className="glass-highlight p-6 glow-emerald animate-slide-up" data-testid="projected-balance">
          <div className="flex items-start justify-between">
            <div>
              <p className="stat-label">Projected Balance</p>
              <p className="stat-value mt-2 text-emerald-800">
                {formatBillions(forecast?.projected_balance || 0)}
              </p>
              <p className="text-sm text-emerald-600 mt-2">
                End of {days} day period
              </p>
            </div>
            <div className="p-3 bg-emerald-200 rounded-xl">
              <Target className="w-6 h-6 text-emerald-800" />
            </div>
          </div>
        </div>
      </div>

      {/* Forecast Chart */}
      <div className="chart-container" data-testid="forecast-chart">
        <h3 className="section-title mb-6">Projected Cash Flow</h3>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={forecast ? aggregateByMonth(forecast.forecast_data) : []}>
            <defs>
              <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#047857" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#047857" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis 
              dataKey="month" 
              tick={{ fill: '#64748b', fontSize: 12 }}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis 
              tickFormatter={formatCompact}
              tick={{ fill: '#64748b', fontSize: 12 }}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <Tooltip 
              formatter={(value, name) => [formatCurrency(value), name.replace('_', ' ')]}
              labelFormatter={(label) => label}
              contentStyle={{ 
                backgroundColor: 'white', 
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
              }}
            />
            <Area 
              type="monotone" 
              dataKey="projected_balance" 
              stroke="#047857" 
              strokeWidth={3}
              fill="url(#balanceGradient)" 
              name="Projected Balance"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Inflow/Outflow Projection */}
      <div className="chart-container" data-testid="inflow-outflow-chart">
        <h3 className="section-title mb-6">Projected Inflow vs Outflow</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={forecast?.forecast_data || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatDate}
              tick={{ fill: '#64748b', fontSize: 12 }}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis 
              tickFormatter={formatCompact}
              tick={{ fill: '#64748b', fontSize: 12 }}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <Tooltip 
              formatter={(value) => formatCurrency(value)}
              labelFormatter={formatDate}
              contentStyle={{ 
                backgroundColor: 'white', 
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
              }}
            />
            <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
            <Line 
              type="monotone" 
              dataKey="projected_inflow" 
              stroke="#047857" 
              strokeWidth={2}
              dot={false}
              name="Projected Inflow"
            />
            <Line 
              type="monotone" 
              dataKey="projected_outflow" 
              stroke="#dc2626" 
              strokeWidth={2}
              dot={false}
              name="Projected Outflow"
            />
            <Line 
              type="monotone" 
              dataKey="projected_net" 
              stroke="#3b82f6" 
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Net Flow"
            />
          </LineChart>
        </ResponsiveContainer>
        
        {/* Legend */}
        <div className="flex justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-emerald-700" />
            <span className="text-sm text-slate-600">Inflow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-red-600" />
            <span className="text-sm text-slate-600">Outflow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-0.5 bg-blue-500 border-dashed" style={{ borderTop: '2px dashed #3b82f6', height: 0 }} />
            <span className="text-sm text-slate-600">Net Flow</span>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="glass-card p-6" data-testid="recommendations">
        <h3 className="section-title mb-6">Recommendations</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(forecast?.recommendations || []).map((rec, index) => (
            <div 
              key={index}
              className="p-4 bg-gradient-to-br from-emerald-50/50 to-blue-50/50 border border-emerald-100 rounded-xl flex items-start gap-3"
              data-testid={`recommendation-${index}`}
            >
              <div className="p-2 bg-emerald-100 rounded-lg mt-0.5">
                <ArrowRight className="w-4 h-4 text-emerald-700" />
              </div>
              <p className="text-slate-700">{rec}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Forecast Data Table */}
      <div className="glass-card p-6" data-testid="forecast-table">
        <div className="flex items-center justify-between mb-6">
          <h3 className="section-title">Daily Projections</h3>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Calendar className="w-4 h-4" />
            <span>Next {days} days</span>
          </div>
        </div>
        
        <div className="overflow-x-auto max-h-96">
          <table className="w-full">
            <thead className="sticky top-0 bg-slate-50">
              <tr className="text-left text-sm text-slate-500">
                <th className="p-3 font-medium w-32">Date</th>
                <th className="p-3 font-medium text-right w-48">Projected Inflow</th>
                <th className="p-3 font-medium text-right w-48">Balance</th>
              </tr>
            </thead>
            <tbody>
              {(forecast?.forecast_data || []).slice(0, 30).map((day, index) => (
                <tr 
                  key={day.date} 
                  className="border-t border-slate-100 hover:bg-emerald-50/30 transition-colors"
                >
                  <td className="p-3">
                    <span className="font-medium text-slate-900">{formatDate(day.date)}</span>
                  </td>
                  <td className="p-3 text-right">
                    <span className="text-emerald-600 font-medium">
                      {formatCurrency(day.projected_inflow)}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <span className="font-semibold text-slate-900">
                      {formatCurrency(day.projected_balance)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

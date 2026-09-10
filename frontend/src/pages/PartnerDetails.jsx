import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  Shield,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  XCircle,
  Handshake,
  Info,
  Brain,
  Lightbulb,
  ReceiptIndianRupee
} from "lucide-react";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

import { AR_API_BASE } from "../config";

// Helper function to format text with bold amounts (wrapped in **)
const formatTextWithBoldAmounts = (text) => {
  if (!text) return text;
  // Match **₹X Cr** or **₹X** patterns
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const amount = part.slice(2, -2); // Remove **
      return <strong key={idx} className="font-bold text-slate-900">{amount}</strong>;
    }
    return <span key={idx}>{part}</span>;
  });
};

export default function PartnerDetails() {
  const { partnerCode } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Determine where we came from (default to insights for backward compatibility)
  const fromPage = location.state?.from || 'insights';
  const backPath = fromPage === 'dashboard' ? '/ar/dashboard' : '/ar/insights';
  const backLabel = fromPage === 'dashboard' ? 'Back to Dashboard' : 'Back to Insights';

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${AR_API_BASE}/partners/${partnerCode}/details`);
        setData(response.data);
      } catch (error) {
        console.error("Error fetching partner details:", error);
        toast.error("Failed to load partner details");
        navigate(backPath);
      } finally {
        setLoading(false);
      }
    };

    if (partnerCode) {
      fetchDetails();
    }
  }, [partnerCode, navigate, backPath]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-200 rounded-lg">
        <div className="relative">
          <ReceiptIndianRupee className="w-6 h-6 text-slate-600" />
          {/* A small notification dot pulsating */}
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700">Retrieving Partner Financials</p>
          <div className="flex items-center gap-2 mt-1">
              <span className="h-1 w-1 bg-slate-400 rounded-full animate-bounce delay-75"></span>
              <span className="h-1 w-1 bg-slate-400 rounded-full animate-bounce delay-150"></span>
              <span className="h-1 w-1 bg-slate-400 rounded-full animate-bounce delay-300"></span>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const formatCurrency = (value) => {
    if (!value) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getRiskBadgeClass = (bucket) => {
    const map = {
      HIGH: "bg-red-100 text-red-700 border-red-200",
      MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
      LOW: "bg-emerald-100 text-emerald-700 border-emerald-200",
    };
    return map[bucket] || "bg-slate-100 text-slate-700";
  };

  const getScoreColor = (score, maxScore) => {
    const ratio = score / maxScore;
    if (ratio >= 0.8) return "text-emerald-600";
    if (ratio >= 0.5) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <Button
          variant="outline"
          onClick={() => navigate(backPath)}
          className="btn-secondary"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {backLabel}
        </Button>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <h1 className="page-title">{data.partner_name}</h1>
            <p className="text-slate-500 mt-1">Partner Code: {data.partner_code}</p>
          </div>
          <div className={`px-4 py-2 rounded-lg border-2 ${getRiskBadgeClass(data.risk_bucket)}`}>
            <span className="font-semibold">{data.risk_bucket} RISK</span>
          </div>
        </div>
      </div>

      {/* Risk Bucket Explanation */}
      <div className="glass-card p-6">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-slate-900 mb-2">Risk Bucket Explanation</h3>
            <p className="text-slate-600">{data.risk_bucket_explanation}</p>
            <p className="text-sm text-slate-500 mt-2">
              Net Risk Score: <span className="font-semibold">{data.net_risk_score.toFixed(2)}</span> 
              {" "}({data.percentile_ranking.position})
            </p>
          </div>
        </div>
      </div>

      {/* LLM AI Insights */}
      {data.llm_insights && (
        <div className="glass-card p-6">
          <div className="flex items-start gap-3 mb-4">
            <Brain className="w-5 h-5 text-purple-600 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900 mb-1">AI Risk Analysis</h3>
            </div>
          </div>

          {/* Trend Indicator */}
          {data.llm_insights.trend && (
            <div className="mb-4 flex items-center gap-2">
              {data.llm_insights.trend === "improving" && (
                <TrendingUp className="w-4 h-4 text-emerald-600" />
              )}
              {data.llm_insights.trend === "deteriorating" && (
                <TrendingDown className="w-4 h-4 text-red-600" />
              )}
              {data.llm_insights.trend === "stable" && (
                <AlertCircle className="w-4 h-4 text-amber-600" />
              )}
              <span className="text-sm font-medium text-slate-700 capitalize">
                Trend: {data.llm_insights.trend}
              </span>
            </div>
          )}

          {/* Explanation */}
          {data.llm_insights.explanation && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-900 mb-2">Analysis</h4>
              <p className="text-slate-600 text-sm leading-relaxed">{formatTextWithBoldAmounts(data.llm_insights.explanation)}</p>
            </div>
          )}

          {/* Payment Behavior Summary */}
          {data.llm_insights.payment_behavior_summary && (
            <div className="mb-4 p-3 bg-slate-50 rounded-lg">
              <h4 className="text-sm font-semibold text-slate-900 mb-1">Payment Behavior Summary</h4>
              <p className="text-slate-600 text-sm">{formatTextWithBoldAmounts(data.llm_insights.payment_behavior_summary)}</p>
            </div>
          )}

          {/* Key Findings */}
          {data.llm_insights.key_findings && data.llm_insights.key_findings.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-600" />
                Key Findings
              </h4>
              <ul className="space-y-1">
                {data.llm_insights.key_findings.map((finding, idx) => (
                  <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                    <span className="text-amber-600 mt-1">•</span>
                    <span>{formatTextWithBoldAmounts(finding)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {data.llm_insights.recommendations && data.llm_insights.recommendations.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                Recommendations
              </h4>
              <ul className="space-y-1">
                {data.llm_insights.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                    <span className="text-emerald-600 mt-1">✓</span>
                    <span>{formatTextWithBoldAmounts(rec)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Error indicator if LLM failed */}
          {data.llm_insights.is_fallback && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-700">
                Note: AI analysis completed with fallback data. Some insights may be limited.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Score Breakdown */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Score Breakdown</h2>
        <div className="space-y-4">
          {/* Cashflow Continuity */}
          <ScoreCard
            title="Cashflow Continuity"
            score={data.score_breakdown.cashflow_continuity.score}
            maxScore={data.score_breakdown.cashflow_continuity.max_score}
            calculation={data.score_breakdown.cashflow_continuity.calculation}
            value={data.score_breakdown.cashflow_continuity.value}
            explanation={data.score_breakdown.cashflow_continuity.explanation}
            icon={TrendingUp}
            positive
          />

          {/* Cashflow Strength */}
          <ScoreCard
            title="Cashflow Strength"
            score={data.score_breakdown.cashflow_strength.score}
            maxScore={data.score_breakdown.cashflow_strength.max_score}
            calculation={data.score_breakdown.cashflow_strength.calculation}
            value={data.score_breakdown.cashflow_strength.value}
            explanation={data.score_breakdown.cashflow_strength.explanation}
            icon={Shield}
            positive
          />

          {/* Low Overdue */}
          <ScoreCard
            title="Low Overdue Bonus"
            score={data.score_breakdown.low_overdue.score}
            maxScore={data.score_breakdown.low_overdue.max_score}
            calculation={data.score_breakdown.low_overdue.calculation}
            value={data.score_breakdown.low_overdue.value}
            explanation={data.score_breakdown.low_overdue.explanation}
            icon={CheckCircle}
            positive
          />

          {/* Penalty: Severe Stress */}
          <ScoreCard
            title="Severe Stress Penalty"
            score={-data.score_breakdown.penalty_severe_stress.penalty}
            maxScore={data.score_breakdown.penalty_severe_stress.max_penalty}
            calculation={data.score_breakdown.penalty_severe_stress.calculation}
            value={data.score_breakdown.penalty_severe_stress.value}
            explanation={data.score_breakdown.penalty_severe_stress.explanation}
            icon={XCircle}
            positive={false}
          />

          {/* Penalty: Old Overdue */}
          <ScoreCard
            title="Old Overdue Penalty"
            score={-data.score_breakdown.penalty_old_overdue.penalty}
            maxScore={data.score_breakdown.penalty_old_overdue.max_penalty}
            calculation={data.score_breakdown.penalty_old_overdue.calculation}
            value={data.score_breakdown.penalty_old_overdue.value}
            explanation={data.score_breakdown.penalty_old_overdue.explanation}
            icon={AlertCircle}
            positive={false}
          />
        </div>

        {/* Total Score */}
        <div className="mt-6 pt-6 border-t border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-slate-900">Net Risk Score</span>
            <span className={`text-2xl font-bold ${getScoreColor(data.net_risk_score, 110)}`}>
              {data.net_risk_score.toFixed(2)} / 110
            </span>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Key Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <MetricCard label="Total Runs" value={data.metrics.total_runs} />
          <MetricCard label="Paid Runs" value={data.metrics.paid_runs} />
          <MetricCard label="Fully Paid Runs" value={data.metrics.fully_paid_runs} />
          <MetricCard label="Stressed Runs" value={data.metrics.stressed_runs} />
          <MetricCard label="Severely Stressed Runs" value={data.metrics.severely_stressed_runs} />
          <MetricCard label="Avg Invoice Amount" value={formatCurrency(data.metrics.avg_invoice_amount)} />
          <MetricCard label="Avg Allocated Amount" value={formatCurrency(data.metrics.avg_allocated_amount)} />
          <MetricCard label="Avg Due Amount" value={formatCurrency(data.metrics.avg_due_amount)} />
          <MetricCard label="Old Overdue Amount" value={formatCurrency(data.metrics.old_overdue_amount)} />
        </div>
      </div>

      {/* Percentile Context */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Percentile Ranking</h2>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-slate-600">25th Percentile (P25)</span>
            <span className="font-semibold">{data.percentile_ranking.p25.toFixed(2)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-600">50th Percentile (Median)</span>
            <span className="font-semibold">{data.percentile_ranking.p50.toFixed(2)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-600">75th Percentile (P75)</span>
            <span className="font-semibold">{data.percentile_ranking.p75.toFixed(2)}</span>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200">
            <p className="text-sm text-slate-500">
              Your partner's score of <span className="font-semibold text-slate-900">{data.net_risk_score.toFixed(2)}</span> places them in the{" "}
              <span className="font-semibold text-slate-900">{data.percentile_ranking.position}</span> of all partners.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScoreCard({ title, score, maxScore, calculation, value, explanation, icon: Icon, positive }) {
  const getScoreColor = (score, maxScore) => {
    const ratio = Math.abs(score) / maxScore;
    if (positive) {
      if (ratio >= 0.8) return "text-emerald-600";
      if (ratio >= 0.5) return "text-amber-600";
      return "text-red-600";
    } else {
      return "text-red-600";
    }
  };

  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${positive ? "text-emerald-600" : "text-red-600"}`} />
          <h3 className="font-semibold text-slate-900">{title}</h3>
        </div>
        <span className={`text-lg font-bold ${getScoreColor(score, maxScore)}`}>
          {positive ? "+" : ""}{score.toFixed(2)} / {maxScore}
        </span>
      </div>
      <div className="text-sm text-slate-600 space-y-1">
        <p>
          <span className="font-medium">Calculation:</span> {calculation}
        </p>
        <p>
          <span className="font-medium">Value:</span> {value}
        </p>
        <p className="text-slate-500">{explanation}</p>
      </div>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <p className="text-sm text-slate-500 mb-1">{label}</p>
      <p className="text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}


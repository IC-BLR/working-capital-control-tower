"""
Chatbot Service - Natural language query processing for cashflow data
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service for processing natural language queries about cashflow data."""

    def __init__(self, services):
        self.services = services

        self.query_patterns = {
            "total_outstanding": [
                r"^\s*total\s+outstanding(?:\s+amount)?\s*$",
                r"^\s*what.*?total\s+outstanding(?:\s+amount)?\s*$",
                r"^\s*what.*?is.*?total\s+outstanding(?:\s+amount)?\s*$",
                r"^\s*overall\s+outstanding(?:\s+amount)?\s*$",
                r"^\s*show.*?total\s+outstanding(?:\s+amount)?\s*$",
                r"^\s*show.*?overall\s+outstanding(?:\s+amount)?\s*$",
            ],
            "total_overdue": [
                r"^\s*total\s+overdue(?:\s+amount)?\s*$",
                r"^\s*what.*?total\s+overdue(?:\s+amount)?\s*$",
                r"^\s*what.*?is.*?total\s+overdue(?:\s+amount)?\s*$",
                r"^\s*overall\s+overdue(?:\s+amount)?\s*$",
                r"^\s*show.*?total\s+overdue(?:\s+amount)?\s*$",
                r"^\s*show.*?overall\s+overdue(?:\s+amount)?\s*$",
            ],
            "partner_overdue_amount": [
                r"^\s*overdue(?:\s+amount)?\s+for\s+(.+?)(?:\s+partner)?\s*$",
                r"^\s*what.*?is.*?overdue(?:\s+amount)?\s+for\s+(.+?)\s*$",
                r"^\s*show.*?overdue(?:\s+amount)?\s+for\s+(.+?)\s*$",
                r"^\s*how\s+much\s+is\s+overdue\s+for\s+(.+?)\s*$",
            ],
            "forecast": [
                r"\bforecast\b.*?(\d+)\s*days?",
                r"\bpredict\b.*?(\d+)\s*days?",
                r"\bprojection\b.*?(\d+)\s*days?",
                r"\bnext\s+(\d+)\s+days?\b",
                r"\bshow\b.*?\bforecast\b.*?(\d+)\s*days?",
                r"\bshow\b.*?\bforecast\b",
                r"^\s*(?:show\s+me\s+)?forecast\s*$",
                r"^\s*(?:show\s+me\s+)?cashflow\s+forecast\s*$",
            ],
            "what_if_scenario": [
                r"what.*?if.*?partners?.*?(increase|decrease).*(\d+)%",
                r"what.*?if.*?partner\s+count.*?(increase|decrease).*(\d+)%",
                r"what.*?if.*?invoices?.*?(increase|decrease).*(\d+)%",
                r"what.*?if.*?invoice\s+amounts?.*?(increase|decrease).*(\d+)%",
                r"what.*?if.*?payment\s+coverage.*?(increase|decrease).*(\d+)%",
                r"what.*?if.*?payments?.*?delay.*?(\d+)\s*days?",
                r"what.*?if.*?(recession|growth)",
                r"(?:increase|decrease).*?partners?.*?(\d+)%",
                r"(?:increase|decrease).*?invoices?.*?(\d+)%",
                r"(?:increase|decrease).*?payment\s+coverage.*?(\d+)%",
                r"payment\s+delay.*?(\d+)\s*days?",
                r"\b(recession|growth)\b",
            ],
            "partner_insights": [
                r"(?:show|give|tell).*?(?:me\s+)?insights?\s+(?:for|about|on)\s+(.+?)$",
                r"(?:show|give|tell).*?(?:me\s+)?partner\s+insights?\s+(?:for|about|on)\s+(.+?)$",
                r"(?:what\s+are|share).*?insights?\s+(?:for|about|on)\s+(.+?)$",
                r"insights?\s+(?:for|about|on)\s+(.+?)$",
                r"risk\s+insights?\s+(?:for|about|on)\s+(.+?)$",
                r"(?:show|give|tell).*?(?:me\s+)?summary\s+(?:for|about|on)\s+(.+?)$",
                r"(?:show|give|tell).*?(?:me\s+)?analysis\s+(?:for|about|on)\s+(.+?)$",
            ],
            "what_if_revenue": [
                r"what.*?if.*?revenue.*?(?:increases?|rises?|goes?.*?up).*?(\d+)%",
                r"(?:increase|raise).*?revenue.*?(\d+)%",
                r"revenue.*?(?:up|increase).*?(\d+)%",
            ],
            "what_if_expense": [
                r"what.*?if.*?(?:expenses?|costs?).*?(?:increases?|rises?|goes?.*?up).*?(\d+)%",
                r"(?:increase|raise).*?(?:expenses?|costs?).*?(\d+)%",
                r"(?:expenses?|costs?).*?(?:up|increase).*?(\d+)%",
            ],
            "outstanding_amount": [
                r"outstanding.*?for\s+(.+?)(?:\s+partner)?$",
                r"due.*?for\s+(.+?)(?:\s+partner)?$",
                r"owed.*?by\s+(.+?)(?:\s+partner)?$",
                r"what.*?(?:is|are).*?outstanding.*?for\s+(.+?)$",
                r"show.*?outstanding.*?for\s+(.+?)$",
            ],
            "partner_details": [
                r"details.*?for\s+(.+?)(?:\s+partner)?$",
                r"information.*?(?:about|on)\s+(.+?)$",
                r"tell.*?(?:me)?.*?about\s+(.+?)$",
                r"show.*?(?:me)?\s+details?\s+for\s+(.+?)$",
            ],
            "risk_partners": [
                r"\bshow\s+(high|medium|low)\s+risk\s+partners?\b",
                r"\blist\s+(high|medium|low)\s+risk\s+partners?\b",
                r"\b(high|medium|low)\s+risk\s+partners?\b",
                r"\bpartners?\s+with\s+(high|medium|low)\s+risk\b",
                r"\bwhich\s+partners?\s+are\s+(high|medium|low)\s+risk\b",
                r"\bshow\s+partners?\s+at\s+(high|medium|low)\s+risk\b",
            ],
            "partner_list": [
                r"^(?:list|show)\s+(?:all\s+)?partners?$",
                r"who.*?(?:are|is).*?(?:my|our)?\s*partners?$",
                r"partners?.*?list",
                r"\blist all partners\b",
            ],
            "invoice_list": [
                r"(?:list|show).*?(?:all)?.*?invoices?",
                r"invoices?.*?list",
                r"show.*?invoices?",
            ],
            "high_risk_partners": [
                r"high.*?risk.*?partners?",
                r"risky.*?partners?",
                r"partners?.*?(?:at)?.*?risk",
            ],
            "overdue_invoices": [
                r"overdue.*?invoices?",
                r"late.*?(?:payments?|invoices?)",
                r"invoices?.*?overdue",
            ],
        }

    def process_query(self, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        try:
            query_lower = self._normalize_query(query)
            intent, params = self._detect_intent(query_lower)

            logger.info("Detected intent: %s, params: %s", intent, params)

            if intent == "forecast":
                return self._handle_forecast(params)
            elif intent == "what_if_scenario":
                return self._handle_what_if_scenario(params)
            elif intent == "partner_insights":
                return self._handle_partner_insights(params)
            elif intent == "risk_partners":
                return self._handle_risk_partners(params)
            elif intent == "total_outstanding":
                return self._handle_total_outstanding()
            elif intent == "outstanding_amount":
                return self._handle_outstanding_query(params)
            elif intent == "total_overdue":
                return self._handle_total_overdue()
            elif intent == "partner_overdue_amount":
                return self._handle_partner_overdue_amount(params)
            elif intent == "partner_details":
                return self._handle_partner_details(params)
            elif intent == "what_if_revenue":
                return self._handle_what_if_revenue(params)
            elif intent == "what_if_expense":
                return self._handle_what_if_expense(params)
            elif intent == "partner_list":
                return self._handle_partner_list()
            elif intent == "invoice_list":
                return self._handle_invoice_list()
            elif intent == "high_risk_partners":
                return self._handle_high_risk_partners()
            elif intent == "overdue_invoices":
                return self._handle_overdue_invoices()
            else:
                return self._handle_unknown_query(query)

        except Exception as e:
            logger.error("Error processing query: %s", str(e), exc_info=True)
            return {
                "response": f"I encountered an error processing your request: {str(e)}. Please try rephrasing your question.",
                "analysisData": None
            }

    def _detect_intent(self, query: str) -> Tuple[str, Dict[str, Any]]:
        query = query.strip()

        ordered_intents = [
            "forecast",
            "what_if_scenario",
            "partner_insights",
            "risk_partners",
            "total_outstanding",
            "total_overdue",
            "partner_overdue_amount",
            "what_if_revenue",
            "what_if_expense",
            "outstanding_amount",
            "partner_details",
            "partner_list",
            "invoice_list",
            "high_risk_partners",
            "overdue_invoices",
        ]

        for intent in ordered_intents:
            patterns = self.query_patterns.get(intent, [])
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    params = {"raw_match": match.groups(), "query": query}
                    if intent == "forecast":
                        params["days"] = self._extract_days(query, match)
                    return intent, params

        return "unknown", {"query": query}
    def _normalize_query(self, query: str) -> str:
        query = (query or "").lower().strip()
        query = re.sub(r"[?!.]+$", "", query)   # remove ending punctuation
        query = re.sub(r"\s+", " ", query)      # normalize spaces
        return query

    def _extract_days(self, query: str, match: re.Match) -> int:
        for group in match.groups():
            if group and str(group).isdigit():
                return min(max(int(group), 1), 365)

        m = re.search(r"(\d+)\s*days?", query, re.IGNORECASE)
        if m:
            return min(max(int(m.group(1)), 1), 365)

        return 30

    def _extract_what_if_scenario(self, query: str) -> Optional[Tuple[str, str]]:
        query = query.lower().strip()

        m = re.search(r"partners?.*?increase.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"partner_increase_{pct}", f"Partner count increased by {pct}%"

        m = re.search(r"partners?.*?decrease.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"partner_decrease_{pct}", f"Partner count decreased by {pct}%"

        m = re.search(r"invoices?.*?increase.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"invoice_increase_{pct}", f"Invoice amounts increased by {pct}%"

        m = re.search(r"invoices?.*?decrease.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"invoice_decrease_{pct}", f"Invoice amounts decreased by {pct}%"

        m = re.search(r"payment\s+coverage.*?increase.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"payment_coverage_increase_{pct}", f"Payment coverage increased by {pct}%"

        m = re.search(r"payment\s+coverage.*?decrease.*?(\d+)%", query)
        if m:
            pct = int(m.group(1))
            return f"payment_coverage_decrease_{pct}", f"Payment coverage decreased by {pct}%"

        m = re.search(r"payment.*?delay.*?(\d+)\s*days?", query)
        if m:
            delay = int(m.group(1))
            return f"payment_delay_{delay}", f"Payments delayed by {delay} days"

        if "recession" in query:
            return "recession", "Economic recession scenario"

        if "growth" in query:
            return "growth", "Economic growth scenario"

        return None

    def _find_partner(self, search_term: str) -> Optional[Dict[str, Any]]:
        try:
            partners = self.services.get_partners()
            search_term = search_term.strip().upper()

            for partner in partners:
                if getattr(partner, "partner_code", None) and partner.partner_code.upper() == search_term:
                    return partner

            for partner in partners:
                if getattr(partner, "partner_name", None) and search_term in partner.partner_name.upper():
                    return partner

            for partner in partners:
                if getattr(partner, "partner_code", None) and search_term in partner.partner_code.upper():
                    return partner

            return None
        except Exception as e:
            logger.error("Error finding partner: %s", str(e), exc_info=True)
            return None

    def _get_first_match(self, params: Dict[str, Any]) -> str:
        raw = params.get("raw_match", [])
        if raw and raw[0]:
            return str(raw[0]).strip()
        return ""

    def _safe_list(self, value: Any, max_items: int = 2) -> List[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()][:max_items]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _handle_partner_insights(self, params: Dict) -> Dict[str, Any]:
        partner_name = self._get_first_match(params)

        if not partner_name:
            return {
                "response": "Please specify a partner name or code. For example: 'Show insights for ABC Corp'.",
                "analysisData": None
            }

        partner = self._find_partner(partner_name)

        if not partner:
            return {
                "response": f"Partner '{partner_name}' not found.",
                "analysisData": None
            }

        try:
            details = self.services.get_partner_details(partner.partner_code)

            if not details:
                return {
                    "response": f"No insights available for {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}.",
                    "analysisData": None
                }

            partner_display = getattr(partner, "partner_name", None) or getattr(partner, "partner_code", "")
            risk_bucket = details.get("risk_bucket", "N/A")
            risk_score = details.get("net_risk_score", 0)
            metrics = details.get("metrics", {}) or {}
            llm_insights = details.get("llm_insights") or {}

            paid_runs = metrics.get("paid_runs", 0)
            total_runs = metrics.get("total_runs", 0)
            stressed_runs = metrics.get("stressed_runs", 0)
            old_overdue = metrics.get("old_overdue_amount", 0)

            payment_summary = (
                f"{paid_runs}/{total_runs} runs paid, "
                f"{stressed_runs} stressed runs, "
                f"₹{old_overdue:,.2f} overdue older than 90 days"
            )

            key_findings = self._safe_list(
                llm_insights.get("key_findings")
                or llm_insights.get("findings")
                or llm_insights.get("summary_points"),
                max_items=2
            )

            recommendations = self._safe_list(
                llm_insights.get("recommendations")
                or llm_insights.get("actions")
                or llm_insights.get("next_steps"),
                max_items=2
            )

            if not key_findings:
                key_findings = [
                    f"Risk bucket is {risk_bucket} with score {float(risk_score):.2f}.",
                    f"Outstanding amount is ₹{metrics.get('total_due_amount', 0):,.2f}."
                ]

            if not recommendations:
                recommendations = [
                    "Review recent payment consistency and overdue invoices.",
                    "Follow up on delayed collections and monitor next payment cycle."
                ]

            response = f"""🔎 **Partner Insights: {partner_display}**

• **Risk Level**: {risk_bucket}
• **Risk Score**: {float(risk_score):.2f}/110
• **Payment Behaviour Summary**: {payment_summary}

**Key Findings**
• {key_findings[0]}
• {key_findings[1] if len(key_findings) > 1 else "Payment behaviour should continue to be monitored."}

**Recommendations**
• {recommendations[0]}
• {recommendations[1] if len(recommendations) > 1 else "Track this partner in the next forecast cycle."}
"""

            return {
                "response": response,
                "analysisData": {
                    "partner_code": details.get("partner_code"),
                    "partner_name": details.get("partner_name"),
                    "risk_bucket": risk_bucket,
                    "net_risk_score": risk_score,
                    "payment_behaviour_summary": payment_summary,
                    "key_findings": key_findings,
                    "recommendations": recommendations,
                    "metrics": metrics,
                    "llm_insights": llm_insights,
                }
            }

        except Exception as e:
            logger.error("Error getting partner insights: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving insights for {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}: {str(e)}",
                "analysisData": None
            }

    def _handle_outstanding_query(self, params: Dict) -> Dict[str, Any]:
        partner_name = self._get_first_match(params)

        if not partner_name:
            return {
                "response": "Please specify a partner name or code. For example: 'What is the outstanding amount for ABC Corp?'",
                "analysisData": None
            }

        partner = self._find_partner(partner_name)

        if not partner:
            partners = self.services.get_partners()
            partner_list = ", ".join([getattr(p, "partner_name", None) or getattr(p, "partner_code", "") for p in partners[:5]])

            return {
                "response": f"I couldn't find a partner matching '{partner_name}'. Available partners include: {partner_list}",
                "analysisData": None
            }

        outstanding = getattr(partner, "total_due_amount", 0) or 0
        overdue = getattr(partner, "total_overdue", 0) or 0
        aging_bucket = getattr(partner, "aging_bucket", None) or "N/A"

        response = f"""📊 **Outstanding Amount for {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}**

• **Total Outstanding**: ₹{outstanding:,.2f}
• **Overdue Amount**: ₹{overdue:,.2f}
• **Aging Bucket**: {aging_bucket}
• **Number of Invoices**: {getattr(partner, 'total_number_of_invoices', 0) or 0}
"""

        return {
            "response": response,
            "analysisData": {
                "partner_code": getattr(partner, "partner_code", None),
                "partner_name": getattr(partner, "partner_name", None),
                "outstanding_amount": outstanding,
                "overdue_amount": overdue,
                "aging_bucket": aging_bucket,
                "invoice_count": getattr(partner, "total_number_of_invoices", 0),
            }
        }

    def _handle_partner_details(self, params: Dict) -> Dict[str, Any]:
        partner_name = self._get_first_match(params)

        if not partner_name:
            return {
                "response": "Please specify a partner name or code.",
                "analysisData": None
            }

        partner = self._find_partner(partner_name)

        if not partner:
            return {
                "response": f"Partner '{partner_name}' not found.",
                "analysisData": None
            }

        try:
            details = self.services.get_partner_details(partner.partner_code)

            if not details:
                return {
                    "response": f"No detailed information available for {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}",
                    "analysisData": None
                }

            risk_bucket = details.get("risk_bucket", "N/A")
            risk_score = details.get("net_risk_score", 0)
            metrics = details.get("metrics", {})

            response = f"""📈 **Partner Analysis: {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}**

**Risk Assessment**
• Risk Level: {risk_bucket}
• Risk Score: {risk_score:.2f}/110

**Financial Metrics**
• Total Invoice Amount: ₹{metrics.get('total_invoice_amount', 0):,.2f}
• Total Outstanding: ₹{metrics.get('total_due_amount', 0):,.2f}
• Allocated Amount: ₹{metrics.get('total_allocated_amount', 0):,.2f}
• Unallocated: ₹{metrics.get('unallocated_amount', 0):,.2f}

**Payment Behavior**
• Paid Runs: {metrics.get('paid_runs', 0)}/{metrics.get('total_runs', 0)}
• Stressed Runs: {metrics.get('stressed_runs', 0)}
"""

            return {
                "response": response,
                "analysisData": details
            }
        except Exception as e:
            logger.error("Error getting partner details: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving details for {getattr(partner, 'partner_name', None) or getattr(partner, 'partner_code', '')}",
                "analysisData": None
            }

    def _handle_what_if_revenue(self, params: Dict) -> Dict[str, Any]:
        try:
            percentage = int(params.get("raw_match", [0])[0])
        except (ValueError, IndexError, TypeError):
            return {
                "response": "Please specify a percentage. For example: 'What if revenue increases by 20%?'",
                "analysisData": None
            }

        try:
            base_forecast = self.services.get_forecast(days=30)
            partner_summary = base_forecast.get("partner_summary", []) or []

            base_inflow = sum((p.get("total_forecast_amount", 0) or 0) for p in partner_summary)
            adjusted_inflow = base_inflow * (1 + percentage / 100)
            impact = adjusted_inflow - base_inflow

            response = f"""💡 **What-If Analysis: Revenue +{percentage}%**

• **Base Expected Inflow**: ₹{base_inflow:,.2f}
• **Adjusted Inflow**: ₹{adjusted_inflow:,.2f}
• **Additional Cash Impact**: ₹{impact:,.2f}
"""

            return {
                "response": response,
                "analysisData": {
                    "scenario_type": "revenue_increase",
                    "percentage_change": percentage,
                    "base_inflow": base_inflow,
                    "adjusted_inflow": adjusted_inflow,
                    "impact": impact
                }
            }
        except Exception as e:
            logger.error("Error in what-if revenue analysis: %s", str(e), exc_info=True)
            return {
                "response": f"Error performing what-if analysis: {str(e)}",
                "analysisData": None
            }

    def _handle_what_if_expense(self, params: Dict) -> Dict[str, Any]:
        try:
            percentage = int(params.get("raw_match", [0])[0])
        except (ValueError, IndexError, TypeError):
            return {
                "response": "Please specify a percentage. For example: 'What if expenses increase by 15%?'",
                "analysisData": None
            }

        try:
            summary = self.services.get_summary()
            base_expenses = (summary.total_invoice_amount or 0) - (summary.total_payment_amount or 0)
            adjusted_expenses = base_expenses * (1 + percentage / 100)
            impact = adjusted_expenses - base_expenses

            response = f"""💡 **What-If Analysis: Expenses +{percentage}%**

• **Current Net Expenses**: ₹{base_expenses:,.2f}
• **Adjusted Expenses**: ₹{adjusted_expenses:,.2f}
• **Additional Cash Requirement**: ₹{impact:,.2f}
"""

            return {
                "response": response,
                "analysisData": {
                    "scenario_type": "expense_increase",
                    "percentage_change": percentage,
                    "base_expenses": base_expenses,
                    "adjusted_expenses": adjusted_expenses,
                    "impact": impact
                }
            }
        except Exception as e:
            logger.error("Error in expense what-if: %s", str(e), exc_info=True)
            return {
                "response": f"Error performing analysis: {str(e)}",
                "analysisData": None
            }

    def _handle_what_if_scenario(self, params: Dict) -> Dict[str, Any]:
        query = params.get("query", "")
        scenario_result = self._extract_what_if_scenario(query)

        if not scenario_result:
            return {
                "response": (
                    "I could not understand the what-if scenario. "
                    "Try: 'What if partners increase by 20%' or "
                    "'What if payment delay is 7 days?'"
                ),
                "analysisData": None
            }

        scenario, scenario_label = scenario_result

        forecast_days_match = re.search(r"for\s+next\s+(\d+)\s+days", query, re.IGNORECASE)
        days = int(forecast_days_match.group(1)) if forecast_days_match else 30
        days = min(max(days, 1), 365)

        try:
            base_forecast = self.services.get_forecast(days=days)
            scenario_forecast = self.services.get_forecast(days=days, scenario=scenario)

            base_balance = base_forecast.get("projected_balance", 0) or 0
            scenario_balance = scenario_forecast.get("projected_balance", 0) or 0
            balance_impact = scenario_balance - base_balance

            base_inflow = sum(
                (p.get("total_forecast_amount", 0) or 0)
                for p in (base_forecast.get("partner_summary", []) or [])
            )
            scenario_inflow = sum(
                (p.get("total_forecast_amount", 0) or 0)
                for p in (scenario_forecast.get("partner_summary", []) or [])
            )
            inflow_impact = scenario_inflow - base_inflow

            response = f"""💡 **What-If Scenario: {scenario_label}**

• **Forecast Window**: Next {days} days
• **Base Projected Balance**: ₹{base_balance:,.2f}
• **Scenario Projected Balance**: ₹{scenario_balance:,.2f}
• **Balance Impact**: ₹{balance_impact:,.2f}

• **Base Expected Inflow**: ₹{base_inflow:,.2f}
• **Scenario Expected Inflow**: ₹{scenario_inflow:,.2f}
• **Inflow Impact**: ₹{inflow_impact:,.2f}
"""

            scenario_recommendations = scenario_forecast.get("recommendations", []) or []
            if scenario_recommendations:
                response += "\n**Recommendations:**\n"
                for rec in scenario_recommendations[:3]:
                    response += f"• {rec}\n"

            return {
                "response": response,
                "analysisData": {
                    "scenario": scenario,
                    "scenario_label": scenario_label,
                    "forecast_days": days,
                    "base_forecast": base_forecast,
                    "scenario_forecast": scenario_forecast,
                    "base_projected_balance": base_balance,
                    "scenario_projected_balance": scenario_balance,
                    "balance_impact": balance_impact,
                    "base_expected_inflow": base_inflow,
                    "scenario_expected_inflow": scenario_inflow,
                    "inflow_impact": inflow_impact,
                }
            }

        except Exception as e:
            logger.error("Error in what-if scenario analysis: %s", str(e), exc_info=True)
            return {
                "response": f"Error performing scenario analysis: {str(e)}",
                "analysisData": None
            }

    def _handle_risk_partners(self, params: Dict) -> Dict[str, Any]:
        raw_match = params.get("raw_match", [])
        risk_level = (raw_match[0] if raw_match else "").strip().upper()

        if risk_level not in {"HIGH", "MEDIUM", "LOW"}:
            return {
                "response": "Please specify a risk level: high, medium, or low.",
                "analysisData": None
            }

        try:
            insights = self.services.get_partner_insights()
            partners = [
                p for p in insights.get("partner_risk", [])
                if (p.get("risk_bucket") or "").upper() == risk_level
            ]

            if not partners:
                return {
                    "response": f"✅ No {risk_level.lower()}-risk partners currently identified.",
                    "analysisData": {
                        "risk_level": risk_level,
                        "partners": []
                    }
                }

            response = f"""📊 **{risk_level.title()}-Risk Partners ({len(partners)} total)**

"""

            for p in partners[:10]:
                response += f"""**{p.get('partner_name', 'N/A')}**
• Partner Code: {p.get('partner_code', 'N/A')}
• Risk Score: {p.get('net_risk_score', 0):.2f}
• High-Risk Invoices: {p.get('invoice_risk_distribution', {}).get('HIGH', 0)}
• Medium-Risk Invoices: {p.get('invoice_risk_distribution', {}).get('MEDIUM', 0)}
• Low-Risk Invoices: {p.get('invoice_risk_distribution', {}).get('LOW', 0)}
• Total Invoices: {p.get('total_invoices', 0)}

"""

            return {
                "response": response,
                "analysisData": {
                    "risk_level": risk_level,
                    "count": len(partners),
                    "partners": partners
                }
            }

        except Exception as e:
            logger.error("Error getting %s-risk partners: %s", risk_level, str(e), exc_info=True)
            return {
                "response": f"Error retrieving {risk_level.lower()}-risk partners: {str(e)}",
                "analysisData": None
            }

    def _handle_forecast(self, params: Dict) -> Dict[str, Any]:
        try:
            days = int(params.get("days", 30))
            days = min(max(days, 1), 365)
        except (ValueError, TypeError):
            days = 30

        try:
            forecast = self.services.get_forecast(days=days)

            partner_summary = forecast.get("partner_summary", []) or []
            forecast_data = forecast.get("forecast_data", []) or []
            exposure_summary = forecast.get("exposure_summary", {}) or {}
            trend_direction = forecast.get("trend_direction", "stable")
            confidence_score = forecast.get("confidence_score", 0)
            projected_balance = forecast.get("projected_balance", 0) or 0

            total_expected = sum((p.get("total_forecast_amount", 0) or 0) for p in partner_summary)
            partner_count = len(partner_summary)

            response = f"""📅 **{days}-Day Cashflow Forecast**

• **Projected Balance**: ₹{projected_balance:,.2f}
• **Expected Total Inflow**: ₹{total_expected:,.2f}
• **Partners Contributing**: {partner_count}
• **Forecast Period**: Next {days} days
• **Trend**: {str(trend_direction).title()}
• **Confidence Score**: {confidence_score}%

**Exposure Summary**
• **Next 30 Days**: ₹{(exposure_summary.get('next_30_days', 0) or 0):,.2f}
• **Next 60 Days**: ₹{(exposure_summary.get('next_60_days', 0) or 0):,.2f}
• **Next 90 Days**: ₹{(exposure_summary.get('next_90_days', 0) or 0):,.2f}

**Top contributors:**
"""

            top_partners = sorted(
                partner_summary,
                key=lambda x: x.get("total_forecast_amount", 0) or 0,
                reverse=True
            )[:5]

            if top_partners:
                for i, partner in enumerate(top_partners, 1):
                    response += (
                        f"{i}. {partner.get('partner_name', 'N/A')} "
                        f"({partner.get('partner_code', 'N/A')}): "
                        f"₹{(partner.get('total_forecast_amount', 0) or 0):,.2f} "
                        f"(avg {float(partner.get('avg_days_to_payment', 0) or 0):.1f} days)\n"
                    )
            else:
                response += "No partner forecast data available.\n"

            recommendations = forecast.get("recommendations", []) or []
            if recommendations:
                response += "\n**Recommendations:**\n"
                for rec in recommendations[:3]:
                    response += f"• {rec}\n"

            return {
                "response": response,
                "analysisData": {
                    "forecast_period_days": forecast.get("forecast_period_days", days),
                    "projected_balance": projected_balance,
                    "expected_total_inflow": total_expected,
                    "trend_direction": trend_direction,
                    "confidence_score": confidence_score,
                    "exposure_summary": exposure_summary,
                    "partner_summary": partner_summary,
                    "forecast_data": forecast_data,
                    "cashflow_events": forecast.get("cashflow_events", []),
                    "recommendations": recommendations,
                    "scenario": forecast.get("scenario"),
                    "scenario_description": forecast.get("scenario_description"),
                }
            }

        except Exception as e:
            logger.error("Error generating forecast: %s", str(e), exc_info=True)
            return {
                "response": f"Error generating forecast: {str(e)}",
                "analysisData": None
            }

    def _handle_partner_list(self) -> Dict[str, Any]:
        try:
            partners = self.services.get_partners()

            if not partners:
                return {
                    "response": "No partners found in the system.",
                    "analysisData": None
                }

            response = f"📋 **Partner List ({len(partners)} total)**\n\n"

            high_risk = [p for p in partners if (getattr(p, "total_overdue", 0) or 0) > 0]
            current = [p for p in partners if (getattr(p, "total_overdue", 0) or 0) == 0]

            response += f"**High Priority** ({len(high_risk)} partners with overdue amounts)\n"
            for p in high_risk[:5]:
                response += f"• {getattr(p, 'partner_name', None) or getattr(p, 'partner_code', '')}: ₹{(getattr(p, 'total_overdue', 0) or 0):,.2f} overdue\n"

            if len(high_risk) > 5:
                response += f"\n...and {len(high_risk) - 5} more\n"

            response += f"\n**Current** ({len(current)} partners)\n"
            for p in current[:5]:
                response += f"• {getattr(p, 'partner_name', None) or getattr(p, 'partner_code', '')}: ₹{(getattr(p, 'total_due_amount', 0) or 0):,.2f} outstanding\n"

            if len(current) > 5:
                response += f"\n...and {len(current) - 5} more\n"

            return {
                "response": response,
                "analysisData": {
                    "total_partners": len(partners),
                    "high_priority": len(high_risk),
                    "current": len(current),
                    "partners": [
                        {
                            "code": getattr(p, "partner_code", None),
                            "name": getattr(p, "partner_name", None),
                            "outstanding": getattr(p, "total_due_amount", None),
                            "overdue": getattr(p, "total_overdue", None)
                        }
                        for p in partners
                    ]
                }
            }
        except Exception as e:
            logger.error("Error listing partners: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving partner list: {str(e)}",
                "analysisData": None
            }

    def _handle_invoice_list(self) -> Dict[str, Any]:
        try:
            invoices = self.services.get_invoices()

            if not invoices:
                return {
                    "response": "No invoices found in the system.",
                    "analysisData": None
                }

            if hasattr(invoices[0], "__dict__"):
                invoices = [inv.__dict__ for inv in invoices]

            total_amount = sum((inv.get("invoice_amount", 0) or 0) for inv in invoices)
            overdue = [inv for inv in invoices if (inv.get("overdue_amount", 0) or 0) > 0]

            response = f"""📄 **Invoice Summary**

• **Total Invoices**: {len(invoices)}
• **Total Amount**: ₹{total_amount:,.2f}
• **Overdue Invoices**: {len(overdue)}

**Recent Overdue Invoices:**
"""
            for inv in overdue[:5]:
                response += f"• {inv.get('invoice_number', 'N/A')}: ₹{(inv.get('overdue_amount', 0) or 0):,.2f} ({inv.get('aging_bucket', 'N/A')})\n"

            return {
                "response": response,
                "analysisData": {
                    "total_invoices": len(invoices),
                    "total_amount": total_amount,
                    "overdue_count": len(overdue),
                    "recent_overdue": overdue[:10]
                }
            }
        except Exception as e:
            logger.error("Error listing invoices: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving invoices: {str(e)}",
                "analysisData": None
            }

    def _handle_high_risk_partners(self) -> Dict[str, Any]:
        try:
            insights = self.services.get_partner_insights()
            high_risk = [
                p for p in insights.get("partner_risk", [])
                if p.get("risk_bucket") == "HIGH"
            ]

            if not high_risk:
                return {
                    "response": "✅ No high-risk partners currently identified!",
                    "analysisData": insights
                }

            response = f"""⚠️ **High-Risk Partners ({len(high_risk)} total)**\n\n"""

            for p in high_risk[:5]:
                response += f"""**{p.get('partner_name', 'N/A')}**
• Risk Score: {p.get('net_risk_score', 0):.2f}
• High-Risk Invoices: {p.get('invoice_risk_distribution', {}).get('HIGH', 0)}
• Total Invoices: {p.get('total_invoices', 0)}

"""

            return {
                "response": response,
                "analysisData": {
                    "high_risk_count": len(high_risk),
                    "partners": high_risk
                }
            }
        except Exception as e:
            logger.error("Error getting high-risk partners: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving risk analysis: {str(e)}",
                "analysisData": None
            }

    def _handle_overdue_invoices(self) -> Dict[str, Any]:
        try:
            invoices = self.services.get_invoices()

            if not invoices:
                return {
                    "response": "No invoices found in the system.",
                    "analysisData": None
                }

            if hasattr(invoices[0], "__dict__"):
                invoices = [inv.__dict__ for inv in invoices]

            overdue = [inv for inv in invoices if (inv.get("overdue_amount", 0) or 0) > 0]

            if not overdue:
                return {
                    "response": "✅ No overdue invoices found!",
                    "analysisData": None
                }

            overdue_sorted = sorted(
                overdue,
                key=lambda x: x.get("overdue_amount", 0) or 0,
                reverse=True
            )

            total_overdue = sum((inv.get("overdue_amount", 0) or 0) for inv in overdue)

            response = f"""⏰ **Overdue Invoices ({len(overdue)} total)**

• **Total Overdue Amount**: ₹{total_overdue:,.2f}

**Top Overdue Invoices:**
"""
            for inv in overdue_sorted[:5]:
                response += f"• {inv.get('invoice_number', 'N/A')} ({inv.get('partner_name', 'N/A')}): ₹{(inv.get('overdue_amount', 0) or 0):,.2f}\n"

            return {
                "response": response,
                "analysisData": {
                    "total_overdue": total_overdue,
                    "count": len(overdue),
                    "invoices": overdue_sorted[:20]
                }
            }

        except Exception as e:
            logger.error("Error getting overdue invoices: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving overdue invoices: {str(e)}",
                "analysisData": None
            }

    def _handle_unknown_query(self, query: str) -> Dict[str, Any]:
        suggestions = [
            "• What is the outstanding amount for [partner name]?",
            "• Show insights for [partner name]",
            "• Show me details for [partner name]",
            "• What if revenue increases by [X]%",
            "• What if partners increase by 20%?",
            "• What if payment delay is 7 days?",
            "• Show high risk partners",
            "• Show medium risk partners",
            "• Show low risk partners",
            "• Show me 30 day forecast",
            "• Show forecast for next 30 days",
            "• List all partners",
            "• Show overdue invoices"
        ]

        response = f"""I'm not sure I understood that. Here are some things you can ask me:

{chr(10).join(suggestions)}

Try rephrasing your question or use one of the examples above!"""

        return {
            "response": response,
            "analysisData": None
        }
    def _handle_total_outstanding(self) -> Dict[str, Any]:
        try:
            summary = self.services.get_summary()
            partners = self.services.get_partners()

            total_outstanding = getattr(summary, "overall_exposure", 0) or 0
            total_invoice_amount = getattr(summary, "total_invoice_amount", 0) or 0
            total_allocated_amount = getattr(summary, "total_allocated_amount", 0) or 0
            total_payment_amount = getattr(summary, "total_payment_amount", 0) or 0
            total_invoices = getattr(summary, "total_number_of_invoices", 0) or 0
            total_partners = getattr(summary, "total_number_of_partners", 0) or 0

            total_overdue = sum((getattr(p, "total_overdue", 0) or 0) for p in partners)

            response = f"""📊 **Total Outstanding Summary**

    • **Total Outstanding Amount**: ₹{total_outstanding:,.2f}
    • **Total Overdue Amount**: ₹{total_overdue:,.2f}
    • **Total Invoice Amount**: ₹{total_invoice_amount:,.2f}
    • **Total Allocated Amount**: ₹{total_allocated_amount:,.2f}
    • **Total Payment Amount**: ₹{total_payment_amount:,.2f}
    • **Total Invoices**: {total_invoices}
    • **Total Partners**: {total_partners}
    """

            return {
                "response": response,
                "analysisData": {
                    "total_outstanding_amount": total_outstanding,
                    "total_overdue_amount": total_overdue,
                    "total_invoice_amount": total_invoice_amount,
                    "total_allocated_amount": total_allocated_amount,
                    "total_payment_amount": total_payment_amount,
                    "total_invoices": total_invoices,
                    "total_partners": total_partners,
                }
            }
        except Exception as e:
            logger.error("Error retrieving total outstanding summary: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving total outstanding summary: {str(e)}",
                "analysisData": None
            }
    def _handle_total_overdue(self) -> Dict[str, Any]:
        try:
            partners = self.services.get_partners() or []

            total_overdue = sum((getattr(p, "total_overdue", 0) or 0) for p in partners)
            total_partners = len(partners)
            overdue_partners = sum(1 for p in partners if (getattr(p, "total_overdue", 0) or 0) > 0)

            response = f"""⏰ **Total Overdue Summary**

    • **Total Overdue Amount**: ₹{total_overdue:,.2f}
    • **Partners with Overdue Amounts**: {overdue_partners}
    • **Total Partners**: {total_partners}
    """

            return {
                "response": response,
                "analysisData": {
                    "total_overdue_amount": total_overdue,
                    "partners_with_overdue": overdue_partners,
                    "total_partners": total_partners,
                }
            }
        except Exception as e:
            logger.error("Error retrieving total overdue summary: %s", str(e), exc_info=True)
            return {
                "response": f"Error retrieving total overdue summary: {str(e)}",
                "analysisData": None
            }


    def _handle_partner_overdue_amount(self, params: Dict) -> Dict[str, Any]:
        partner_name = self._get_first_match(params)

        if not partner_name:
            return {
                "response": "Please specify a partner name or code. For example: 'What is the overdue amount for ABC Corp?'",
                "analysisData": None
            }

        partner = self._find_partner(partner_name)

        if not partner:
            partners = self.services.get_partners() or []
            partner_list = ", ".join(
                [getattr(p, "partner_name", None) or getattr(p, "partner_code", "") for p in partners[:5]]
            )
            return {
                "response": f"I couldn't find a partner matching '{partner_name}'. Available partners include: {partner_list}",
                "analysisData": None
            }

        partner_display = getattr(partner, "partner_name", None) or getattr(partner, "partner_code", "")
        overdue_amount = getattr(partner, "total_overdue", 0) or 0
        outstanding_amount = getattr(partner, "total_due_amount", 0) or 0
        aging_bucket = getattr(partner, "aging_bucket", None) or "N/A"
        invoice_count = getattr(partner, "total_number_of_invoices", 0) or 0

        response = f"""⏰ **Overdue Amount for {partner_display}**

    • **Overdue Amount**: ₹{overdue_amount:,.2f}
    • **Total Outstanding**: ₹{outstanding_amount:,.2f}
    • **Aging Bucket**: {aging_bucket}
    • **Number of Invoices**: {invoice_count}
    """

        return {
            "response": response,
            "analysisData": {
                "partner_code": getattr(partner, "partner_code", None),
                "partner_name": getattr(partner, "partner_name", None),
                "overdue_amount": overdue_amount,
                "outstanding_amount": outstanding_amount,
                "aging_bucket": aging_bucket,
                "invoice_count": invoice_count,
            }
        }    
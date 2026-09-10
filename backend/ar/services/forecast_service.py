"""
Cashflow forecast service using DuckDB views.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import duckdb

from ar.core.exceptions import (
    DatabaseError,
    DatabaseQueryError,
    ForecastGenerationError
)

logger = logging.getLogger(__name__)


class ForecastService:
    """Service for generating cashflow forecasts based on payment behavior."""
    
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        logger.info("Initializing ForecastService with DuckDB connection")
        self.conn = conn
    
    def _calculate_partner_delays(self) -> Dict[str, Dict[str, float]]:
        logger.info("Calculating partner payment delays from historical data")
        """Calculate median delay days for each partner from historical data."""
        try:
            # Get historical payment data to calculate delays
            query = """
                SELECT
                    partner_code,
                    due_date,
                    payment_date,
                    allocated_amount,
                    due_amount
                FROM v_payments_normalized
                WHERE due_date IS NOT NULL 
                  AND payment_date IS NOT NULL
                  AND allocated_amount > 0
                  AND due_amount > 0
                ORDER BY partner_code, due_date
            """
            rows = self.conn.execute(query).fetchall()
        except duckdb.Error as e:
            logger.error(f"Database error in _calculate_partner_delays: {str(e)}", exc_info=True)
            raise DatabaseQueryError(
                message="Failed to retrieve historical payment data for delay calculation",
                query=query,
                details={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error in _calculate_partner_delays: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error calculating partner delays: {str(e)}",
                details={"error": str(e)}
            )
        
        partner_delays = {}
        
        for row in rows:
            partner_code, due_date, payment_date, allocated_amount, due_amount = row
            
            if partner_code not in partner_delays:
                partner_delays[partner_code] = {
                    "delays": [],
                    "paid_ratios": [],
                    "early_count": 0,
                    "total_count": 0
                }
            
            # Calculate delay in days
            delay_days = (payment_date - due_date).days
            partner_delays[partner_code]["delays"].append(delay_days)
            partner_delays[partner_code]["paid_ratios"].append(allocated_amount / due_amount if due_amount > 0 else 0)
            partner_delays[partner_code]["total_count"] += 1
            if delay_days < 0:
                partner_delays[partner_code]["early_count"] += 1
        
        # Calculate medians and percentages
        partner_stats = {}
        all_delays = []
        
        for partner_code, data in partner_delays.items():
            delays = data["delays"]
            if delays:
                delays_sorted = sorted(delays)
                median_delay = delays_sorted[len(delays_sorted) // 2]
                pct_early = (data["early_count"] / data["total_count"]) * 100 if data["total_count"] > 0 else 0
                
                partner_stats[partner_code] = {
                    "median_delay_days": median_delay,
                    "pct_early": pct_early
                }
                all_delays.extend(delays)
        
        # Calculate global median as fallback
        global_median = sorted(all_delays)[len(all_delays) // 2] if all_delays else 30
        
        return partner_stats, global_median
    
    def _predict_delay(self, partner_code: str, pending_amt: float, paid_ratio: float, 
                      partner_stats: Dict[str, Dict[str, float]], global_median: float) -> int: 
        """Predict payment delay in days for an invoice."""
        # Get partner's median delay
        if partner_code in partner_stats:
            delay = partner_stats[partner_code]["median_delay_days"]
            pct_early = partner_stats[partner_code]["pct_early"]
        else:
            delay = global_median
            pct_early = 50
        
        # Adjust based on partial payments
        if 0 < paid_ratio < 1:
            delay *= 0.6  # Partial payments → faster remaining collection
        
        # Large unpaid balance → worse behavior
        if pending_amt > 500000:  # > ₹5 lakhs
            delay += 7
        
        # Bound predictions
        delay = max(-180, min(delay, 120))  # early up to -180, late up to +120
        
        return int(round(delay))
    
    def _get_min_lag(self, partner_code: str, partner_stats: Dict[str, Dict[str, float]]) -> int:
 
        """Get minimum lag days for a partner."""
        if partner_code in partner_stats:
            early_pct = partner_stats[partner_code]["pct_early"]
            return 15 if early_pct > 80 else 5
        return 5
    
    def _apply_scenario(self, forecast_data: List[Dict[str, Any]], scenario: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"Applying scenario adjustments: {scenario}")
        """
        Apply what-if scenario adjustments to forecast data.
        
        Args:
            forecast_data: Original forecast data
            scenario: Scenario identifier (e.g., 'partner_increase_10', 'payment_delay_7', etc.)
            
        Returns:
            Adjusted forecast data
        """
        if not scenario or scenario == "baseline":
            return forecast_data
        
        adjusted_data = []
        
        for day_data in forecast_data:
            adjusted_day = day_data.copy()
            
            # Partner count increase scenarios
            if scenario.startswith("partner_increase_"):
                multiplier = float(scenario.replace("partner_increase_", "").replace("_", ".")) / 100.0 + 1.0
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
                adjusted_day["invoice_count"] = int(day_data.get("invoice_count", 0) * multiplier)
            
            # Partner count decrease scenarios
            elif scenario.startswith("partner_decrease_"):
                multiplier = 1.0 - (float(scenario.replace("partner_decrease_", "").replace("_", ".")) / 100.0)
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
                adjusted_day["invoice_count"] = int(day_data.get("invoice_count", 0) * multiplier)
            
            # Payment delay scenarios (delays payments by X days)
            elif scenario.startswith("payment_delay_"):
                delay_days = int(scenario.replace("payment_delay_", ""))
                # Shift inflows forward by delay days (simplified - affects all future days)
                # In practice, this would require re-calculating payment dates
                # For now, we reduce immediate inflows and increase later ones
                if delay_days <= 7:
                    # Short delay: reduce early inflows, increase later
                    reduction_factor = 1.0 - (delay_days * 0.05)  # 5% reduction per day
                    adjusted_day["projected_inflow"] = day_data["projected_inflow"] * reduction_factor
                else:
                    # Long delay: more significant reduction
                    reduction_factor = max(0.3, 1.0 - (delay_days * 0.08))
                    adjusted_day["projected_inflow"] = day_data["projected_inflow"] * reduction_factor
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            # Invoice amount increase scenarios
            elif scenario.startswith("invoice_increase_"):
                multiplier = float(scenario.replace("invoice_increase_", "").replace("_", ".")) / 100.0 + 1.0
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            # Invoice amount decrease scenarios
            elif scenario.startswith("invoice_decrease_"):
                multiplier = 1.0 - (float(scenario.replace("invoice_decrease_", "").replace("_", ".")) / 100.0)
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            # Payment coverage scenarios (partners pay less/more)
            elif scenario.startswith("payment_coverage_decrease_"):
                multiplier = 1.0 - (float(scenario.replace("payment_coverage_decrease_", "").replace("_", ".")) / 100.0)
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            elif scenario.startswith("payment_coverage_increase_"):
                multiplier = float(scenario.replace("payment_coverage_increase_", "").replace("_", ".")) / 100.0 + 1.0
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * multiplier
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            # Economic scenarios
            elif scenario == "recession":
                # Recession: 20% reduction in inflows, 15% increase in delays
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * 0.8
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            elif scenario == "growth":
                # Growth: 15% increase in inflows
                adjusted_day["projected_inflow"] = day_data["projected_inflow"] * 1.15
                adjusted_day["projected_net"] = adjusted_day["projected_inflow"] - day_data["projected_outflow"]
            
            # Recalculate running balance
            if adjusted_data:
                prev_balance = adjusted_data[-1]["projected_balance"]
            else:
                prev_balance = day_data.get("projected_balance", 0) - day_data.get("projected_net", 0)
            
            adjusted_day["projected_balance"] = prev_balance + adjusted_day["projected_net"]
            adjusted_data.append(adjusted_day)
        
        return adjusted_data
    
    def forecast(self, days: int = 30, partner_code: Optional[str] = None, scenario: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Generating cashflow forecast for next {days} days, partner_code={partner_code}, scenario={scenario}")
        """
        Generate cashflow forecast for next N days.
        
        Args:
            days: Number of days to forecast (default 30)
            partner_code: Optional partner code to filter
            scenario: Optional what-if scenario identifier
            
        Returns:
            Dictionary with forecast results
            
        Raises:
            ForecastGenerationError: If forecast generation fails
            DatabaseQueryError: If database query fails
        """
        try:
            # Calculate partner delay statistics
            try:
                partner_stats, global_median = self._calculate_partner_delays()
            except (DatabaseError, DatabaseQueryError) as e:
                logger.error(f"Failed to calculate partner delays: {str(e)}")
                raise ForecastGenerationError(
                    message="Failed to calculate partner payment delays",
                    details={"underlying_error": str(e)}
                )
            
            # Get outstanding invoices
            query = """
                SELECT
                    partner_code,
                    partner_name,
                    invoice_number,
                    invoice_date,
                    due_date,
                    due_amount,
                    allocated_amount,
                    payment_date
                FROM v_payments_latest
                WHERE invoice_number IS NOT NULL
                  AND due_amount > 0
            """
            
            params = []
            if partner_code:
                query += " AND partner_code = ?"
                params.append(partner_code)
            
            try:
                rows = self.conn.execute(query, params).fetchall()
                logger.info(f"Fetched {len(rows)} outstanding invoices for forecast")
            except duckdb.Error as e:
                logger.error(f"Database error fetching outstanding invoices: {str(e)}", exc_info=True)
                raise DatabaseQueryError(
                    message="Failed to retrieve outstanding invoices for forecast",
                    query=query,
                    details={"partner_code": partner_code, "error": str(e)}
                )
            
            today = datetime.now().date()
            forecast_events = []
            
            for row in rows:
                (p_code, p_name, inv_num, inv_date, due_date, due_amt, 
                 allocated_amt, payment_date) = row
                
                # Skip if fully paid
                if allocated_amt >= due_amt:
                    continue
                
                # Calculate paid ratio
                paid_ratio = allocated_amt / due_amt if due_amt > 0 else 0
                pending_amt = due_amt - allocated_amt
                
                # Predict delay
                delay_days = self._predict_delay(
                    p_code, pending_amt, paid_ratio, partner_stats, global_median
                )
                
                # Predict payment date
                if due_date:
                    predicted_date = due_date + timedelta(days=delay_days)
                else:
                    predicted_date = today + timedelta(days=30)
                
                # Apply minimum lag
                min_lag = self._get_min_lag(p_code, partner_stats)
                if inv_date:
                    earliest = inv_date + timedelta(days=min_lag)
                    predicted_date = max(predicted_date, earliest)
                
                # For overdue invoices, recalculate
                if due_date and due_date < today:
                    # Use current date + delay for overdue invoices
                    predicted_date = today + timedelta(days=max(0, delay_days))
                
                # Calculate days to payment
                days_to_payment = (predicted_date - today).days
                
                # Only include if within forecast period
                if 0 <= days_to_payment < days:
                    forecast_events.append({
                        "partner_code": p_code,
                        "partner_name": p_name,
                        "invoice_number": inv_num,
                        "forecast_date": predicted_date.isoformat(),
                        "forecast_amount": float(pending_amt),
                        "days_to_payment": days_to_payment
                    })
            
            # Group by date for daily cashflow
            daily_cashflow = {}
            for event in forecast_events:
                date_str = event["forecast_date"]
                if date_str not in daily_cashflow:
                    daily_cashflow[date_str] = {
                        "date": date_str,
                        "inflow": 0.0,
                        "count": 0
                    }
                daily_cashflow[date_str]["inflow"] += event["forecast_amount"]
                daily_cashflow[date_str]["count"] += 1
            
            # Create daily forecast data
            forecast_data = []
            running_balance = 0.0  # Starting balance (can be adjusted)
            
            for i in range(days):
                date = today + timedelta(days=i)
                date_str = date.isoformat()
                
                inflow = daily_cashflow.get(date_str, {}).get("inflow", 0.0)
                outflow = 0.0  # Can be extended for outflows if needed
                
                net_flow = inflow - outflow
                running_balance += net_flow
                
                forecast_data.append({
                    "date": date_str,
                    "projected_inflow": inflow,
                    "projected_outflow": outflow,
                    "projected_net": net_flow,
                    "projected_balance": running_balance,
                    "invoice_count": daily_cashflow.get(date_str, {}).get("count", 0)
                })
            
            # Calculate exposure buckets
            exposure = {
                "next_30_days": sum(e["forecast_amount"] for e in forecast_events if e["days_to_payment"] <= 30),
                "next_60_days": sum(e["forecast_amount"] for e in forecast_events if 30 < e["days_to_payment"] <= 60),
                "next_90_days": sum(e["forecast_amount"] for e in forecast_events if 60 < e["days_to_payment"] <= 90),
            }
            
            # Partner summary
            partner_summary = {}
            for event in forecast_events:
                p_code = event["partner_code"]
                if p_code not in partner_summary:
                    partner_summary[p_code] = {
                        "partner_code": p_code,
                        "partner_name": event["partner_name"],
                        "total_forecast_amount": 0.0,
                        "invoice_count": 0,
                        "avg_days_to_payment": []
                    }
                partner_summary[p_code]["total_forecast_amount"] += event["forecast_amount"]
                partner_summary[p_code]["invoice_count"] += 1
                partner_summary[p_code]["avg_days_to_payment"].append(event["days_to_payment"])
            
            # Calculate average days for each partner
            for p_data in partner_summary.values():
                days_list = p_data.pop("avg_days_to_payment", [])
                p_data["avg_days_to_payment"] = sum(days_list) / len(days_list) if days_list else 0
            
            # Apply what-if scenario if provided
            if scenario:
                forecast_data = self._apply_scenario(forecast_data, scenario)
                # Recalculate events with scenario adjustments
                if scenario.startswith("partner_increase_") or scenario.startswith("partner_decrease_"):
                    multiplier = 1.0
                    if scenario.startswith("partner_increase_"):
                        multiplier = float(scenario.replace("partner_increase_", "").replace("_", ".")) / 100.0 + 1.0
                    elif scenario.startswith("partner_decrease_"):
                        multiplier = 1.0 - (float(scenario.replace("partner_decrease_", "").replace("_", ".")) / 100.0)
                    for event in forecast_events:
                        event["forecast_amount"] *= multiplier
                elif scenario.startswith("invoice_increase_") or scenario.startswith("invoice_decrease_"):
                    multiplier = 1.0
                    if scenario.startswith("invoice_increase_"):
                        multiplier = float(scenario.replace("invoice_increase_", "").replace("_", ".")) / 100.0 + 1.0
                    elif scenario.startswith("invoice_decrease_"):
                        multiplier = 1.0 - (float(scenario.replace("invoice_decrease_", "").replace("_", ".")) / 100.0)
                    for event in forecast_events:
                        event["forecast_amount"] *= multiplier
                elif scenario.startswith("payment_coverage_"):
                    multiplier = 1.0
                    if "decrease" in scenario:
                        multiplier = 1.0 - (float(scenario.replace("payment_coverage_decrease_", "").replace("_", ".")) / 100.0)
                    elif "increase" in scenario:
                        multiplier = float(scenario.replace("payment_coverage_increase_", "").replace("_", ".")) / 100.0 + 1.0
                    for event in forecast_events:
                        event["forecast_amount"] *= multiplier
                elif scenario == "recession":
                    for event in forecast_events:
                        event["forecast_amount"] *= 0.8
                elif scenario == "growth":
                    for event in forecast_events:
                        event["forecast_amount"] *= 1.15
            
            # Calculate summary metrics
            total_inflow = sum(d["projected_inflow"] for d in forecast_data)
            total_outflow = sum(d["projected_outflow"] for d in forecast_data)
            final_balance = forecast_data[-1]["projected_balance"] if forecast_data else 0.0
            
            # Calculate trend direction (simplified - compare first and last week averages)
            if len(forecast_data) >= 7:
                first_week_avg = sum(d["projected_inflow"] for d in forecast_data[:7]) / 7
                last_week_avg = sum(d["projected_inflow"] for d in forecast_data[-7:]) / 7
                if last_week_avg > first_week_avg * 1.1:
                    trend_direction = "upward"
                elif last_week_avg < first_week_avg * 0.9:
                    trend_direction = "downward"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
            
            # Calculate confidence score based on data quality
            # Higher confidence if we have more historical data and more forecast events
            confidence_score = min(95, max(50, 60 + (len(forecast_events) / 10) + (len(partner_stats) / 5)))
            
            # Generate simple recommendations
            recommendations = []
            if exposure["next_30_days"] > 0:
                recommendations.append(f"Expected ₹{exposure['next_30_days']:,.0f} in next 30 days - monitor collection closely")
            if len(forecast_events) > 50:
                recommendations.append("High volume of expected payments - ensure adequate cash management")
            if trend_direction == "downward":
                recommendations.append("Declining cashflow trend detected - review collection strategies")
            if not recommendations:
                recommendations.append("Monitor daily cashflow projections and adjust as needed")
            
            # Get scenario description
            scenario_description = self._get_scenario_description(scenario)
            
            return {
                "forecast_period_days": days,
                "projected_balance": final_balance,
                "trend_direction": trend_direction,
                "confidence_score": int(confidence_score),
                "exposure_summary": exposure,
                "forecast_data": forecast_data,
                "cashflow_events": forecast_events,
                "partner_summary": list(partner_summary.values()),
                "recommendations": recommendations,
                "scenario": scenario,
                "scenario_description": scenario_description
            }
        except (DatabaseError, DatabaseQueryError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in forecast generation: {str(e)}", exc_info=True)
            raise ForecastGenerationError(
                message=f"Unexpected error during forecast generation: {str(e)}",
                details={"days": days, "partner_code": partner_code, "scenario": scenario, "error": str(e)}
            )
    
    def _get_scenario_description(self, scenario: Optional[str] = None) -> Optional[str]:
        logger.info(f"Getting description for scenario: {scenario}")    
        """Get human-readable description of scenario."""
        if not scenario or scenario == "baseline":
            return None
        
        descriptions = {
            "partner_increase_10": "Partner count increased by 10%",
            "partner_increase_20": "Partner count increased by 20%",
            "partner_increase_30": "Partner count increased by 30%",
            "partner_decrease_10": "Partner count decreased by 10%",
            "partner_decrease_20": "Partner count decreased by 20%",
            "partner_decrease_30": "Partner count decreased by 30%",
            "payment_delay_7": "Payment delays increased by 7 days",
            "payment_delay_14": "Payment delays increased by 14 days",
            "payment_delay_30": "Payment delays increased by 30 days",
            "invoice_increase_10": "Invoice amounts increased by 10%",
            "invoice_increase_20": "Invoice amounts increased by 20%",
            "invoice_decrease_10": "Invoice amounts decreased by 10%",
            "invoice_decrease_20": "Invoice amounts decreased by 20%",
            "payment_coverage_increase_10": "Payment coverage increased by 10%",
            "payment_coverage_increase_20": "Payment coverage increased by 20%",
            "payment_coverage_decrease_10": "Payment coverage decreased by 10%",
            "payment_coverage_decrease_20": "Payment coverage decreased by 20%",
            "recession": "Economic recession scenario (20% reduction in inflows)",
            "growth": "Economic growth scenario (15% increase in inflows)"
        }
        
        return descriptions.get(scenario, f"Custom scenario: {scenario}")


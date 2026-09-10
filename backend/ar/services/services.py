"""
API Services - Business logic for API endpoints.
"""
import json
import logging
import math
import io
import tempfile
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import pandas as pd

from ar.services.llm_service import LLMService
from ar.services.llm.factory import LLMProviderFactory
from ar.services.forecast_service import ForecastService
from ar.services.data_pipeline_service import DataPipelineService
from ar.repositories import (
    SummaryRepository,
    PartnerRepository,
    InvoiceRepository,
    PartnerInsightsRepository,
    ExceptionRepository,
    InvoiceHistoryRepository
)
from ar.models import (
    AggregateSummaryResponse,
    PartnerAgingSummaryResponse,
    InvoiceAgingResponse
)
from ar.core.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DataNotFoundError,
    ExportError,
    ForecastGenerationError
)

logger = logging.getLogger(__name__)


class APIServices:
    """Service class containing business logic for API endpoints."""
    
    def __init__(self, get_duckdb_func, 
                 summary_repo: SummaryRepository = None,
                 partner_repo: PartnerRepository = None,
                 invoice_repo: InvoiceRepository = None,
                 partner_insights_repo: PartnerInsightsRepository = None,
                 exception_repo: ExceptionRepository = None,
                 invoice_history_repo: InvoiceHistoryRepository = None):
        logger.info("Initializing APIServices with DuckDB connection getter")
        """
        Initialize services with DuckDB connection getter and repositories.
        
        Args:
            get_duckdb_func: Function that returns DuckDB connection
            summary_repo: SummaryRepository instance (created if None)
            partner_repo: PartnerRepository instance (created if None)
            invoice_repo: InvoiceRepository instance (created if None)
            partner_insights_repo: PartnerInsightsRepository instance (created if None)
            exception_repo: ExceptionRepository instance (created if None)
            invoice_history_repo: InvoiceHistoryRepository instance (created if None)
        """
        self.get_duckdb = get_duckdb_func
        # Initialize repositories if not provided (for backward compatibility)
        self.summary_repo = summary_repo or SummaryRepository(get_duckdb_func)
        self.partner_repo = partner_repo or PartnerRepository(get_duckdb_func)
        self.invoice_repo = invoice_repo or InvoiceRepository(get_duckdb_func)
        self.partner_insights_repo = partner_insights_repo or PartnerInsightsRepository(get_duckdb_func)
        self.exception_repo = exception_repo or ExceptionRepository(get_duckdb_func)
        self.invoice_history_repo = invoice_history_repo or InvoiceHistoryRepository(get_duckdb_func)
        self._llm_service = None
        self._forecast_service = None
        # Feature flags / settings storage (in-memory)
        self._feature_flags = {
            "cfo_dashboard_enabled": False,
            # Default LLM provider used for partner risk insights.
            # Can be switched at runtime via the settings API (e.g., "ollama", "gemini").
            "llm_provider": "ollama",
        }
    
    @property
    def llm_service(self):
        logger.info("Inititalizing LLM service")
        """
        Lazy initialization of LLM service.

        The active provider is controlled by the in-memory `llm_provider`
        setting so it can be switched at runtime (e.g., between ollama and gemini).
        """
        desired_provider = self._feature_flags.get("llm_provider")

        # If no service exists yet, create one with the desired provider (or default behaviour)
        if self._llm_service is None:
            self._llm_service = LLMService(provider_name=desired_provider)
            return self._llm_service

        # If provider has changed since last initialization, recreate the service
        try:
            current_provider = self._llm_service.provider.get_provider_name()
        except Exception:
            current_provider = None

        if desired_provider and desired_provider.lower() != (current_provider or "").lower():
            logger.info(
                f"LLM provider changed from {current_provider} to {desired_provider}. "
                f"Reinitializing LLMService."
            )
            self._llm_service = LLMService(provider_name=desired_provider)

        return self._llm_service
    
    def get_forecast_service(self, conn):
        """Get forecast service instance."""
        return ForecastService(conn)
    
    def get_pipeline_service(self, conn):
        """Get pipeline service instance."""
        return DataPipelineService(conn)
    
    @staticmethod
    def safe(value):
        """Safe value converter - handles None, NaN, Inf."""
        if value is None:
            return 0
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return 0
        return value
    
    @staticmethod
    def format_currency(value):
        logger.info("Formatting currency value")
        """Format currency same as frontend formatCurrency function."""
        if not value or value == 0:
            return "₹0"
        return f"₹{int(value):,}"
    
    @staticmethod
    def get_status(overdue_days):
        logger.info("Determining status based on overdue days")
        """Get status same as frontend getStatusBadge function."""
        if overdue_days is None:
            return "On Time"
        overdue_days = APIServices.safe(overdue_days)
        if overdue_days > 90:
            return "Overdue"
        elif overdue_days > 0:
            return "Pending"
        else:
            return "On Time"
    
    def get_summary(self) -> AggregateSummaryResponse:
        logger.info("Retrieving aggregate summary data")
        """Get aggregate summary data."""
        try:
            row = self.summary_repo.get_aggregate_summary()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_summary: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving summary: {str(e)}",
                details={"error": str(e)}
            )
        
        if not row:
            return AggregateSummaryResponse(
                total_invoice_amount=0,
                overall_exposure=0,
                total_allocated_amount=0,
                total_payment_amount=0,
                total_number_of_invoices=0,
                total_number_of_partners=0
            )
        
        return AggregateSummaryResponse(
            total_invoice_amount=row[0] or 0,
            overall_exposure=row[1] or 0,
            total_allocated_amount=row[2] or 0,
            total_payment_amount=row[3] or 0,
            total_number_of_invoices=row[4] or 0,
            total_number_of_partners=row[5] or 0,
        )
    
    def get_partners(self) -> List[PartnerAgingSummaryResponse]:
        """Get partner list with aging data."""
        try:
            rows = self.partner_repo.get_all_partners()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_partners: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving partners: {str(e)}",
                details={"error": str(e)}
            )
        
        if not rows:
            return []
        
        columns = [
            "partner_code", "partner_name", "total_invoice_amount",
            "total_due_amount", "total_allocated_amount", "total_payment_amount",
            "total_number_of_invoices", "avg_overdue_days", "aging_bucket", "total_overdue"
        ]
        
        try:
            return [
                PartnerAgingSummaryResponse(**{
                    col: self.safe(val) for col, val in zip(columns, row)
                })
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error processing partner data: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Error processing partner data: {str(e)}",
                details={"error": str(e)}
            )
    
    def get_invoices(self) -> List[InvoiceAgingResponse]:
        logger.info("Retrieving invoice aging data {InvoiceAgingResponse}")
        """Get invoice list with aging data."""
        try:
            rows = self.invoice_repo.get_all_invoices()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_invoices: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving invoices: {str(e)}",
                details={"error": str(e)}
            )
        
        if not rows:
            return []
        
        columns = [
            "partner_code", "partner_name", "invoice_number",
            "invoice_amount", "due_amount", "allocated_amount",
            "payment_amount", "payment_ref", "overdue_amount",
            "overdue_days", "aging_bucket"
        ]
        
        return [
            InvoiceAgingResponse(**{
                col: self.safe(val) for col, val in zip(columns, row)
            })
            for row in rows
        ]
    
    def get_partner_insights(self) -> Dict[str, Any]:
        """Get partner-level risk insights."""
        try:
            risk_rows = self.partner_insights_repo.get_partner_risk_data()
            invoice_rows = self.partner_insights_repo.get_invoice_risk_distribution()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_partner_insights: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving partner insights: {str(e)}",
                details={"error": str(e)}
            )
        
        if not risk_rows:
            return {
                "portfolio_summary": {
                    "partners": 0,
                    "high_risk_partners": 0,
                    "medium_risk_partners": 0,
                    "low_risk_partners": 0
                },
                "partner_risk": []
            }
        
        # Build invoice risk distribution per partner
        invoice_distribution = defaultdict(lambda: {
            "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total_invoices": 0
        })
        
        for row in invoice_rows:
            partner_code, invoice_number, invoice_amount, due_amount, allocated_amount, risk_level = row
            invoice_distribution[partner_code][risk_level] += 1
            invoice_distribution[partner_code]["total_invoices"] += 1
        
        # Build partner results
        partner_results = []
        for row in risk_rows:
            partner_code, partner_name, risk_bucket, net_risk_score = row
            normalized_bucket = risk_bucket.replace("_RISK", "")
            
            dist = invoice_distribution.get(partner_code, {
                "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total_invoices": 0
            })
            
            partner_results.append({
                "partner_code": partner_code,
                "partner_name": partner_name,
                "risk_bucket": normalized_bucket,
                "net_risk_score": float(net_risk_score) if net_risk_score else 0.0,
                "invoice_risk_distribution": {
                    "HIGH": dist["HIGH"],
                    "MEDIUM": dist["MEDIUM"],
                    "LOW": dist["LOW"]
                },
                "total_invoices": dist["total_invoices"]
            })
        
        # Portfolio summary
        portfolio_summary = {
            "partners": len(partner_results),
            "high_risk_partners": sum(p["risk_bucket"] == "HIGH" for p in partner_results),
            "medium_risk_partners": sum(p["risk_bucket"] == "MEDIUM" for p in partner_results),
            "low_risk_partners": sum(p["risk_bucket"] == "LOW" for p in partner_results)
        }
        
        return {
            "portfolio_summary": portfolio_summary,
            "partner_risk": partner_results
        }
    
    def get_partner_details(self, partner_code: str) -> Dict[str, Any]:
        logger.info(f"Getting detailed risk analysis for partner: {partner_code}")
        """Get detailed partner risk analysis."""
        try:
            partner_data = self.partner_insights_repo.get_partner_details_data(partner_code)
            if not partner_data:
                return None
            
            stats = self.partner_insights_repo.get_risk_score_percentiles()
            p25, p75, p50 = stats if stats else (0, 0, 0)
            
            total_amounts = self.partner_repo.get_partner_totals(partner_code)
            recent_invoices = self.partner_insights_repo.get_recent_invoices_for_partner(partner_code, limit=50)
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_partner_details: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving partner details: {str(e)}",
                details={"error": str(e)}
            )
        
        total_invoice_amount = float(total_amounts[0]) if total_amounts and total_amounts[0] else 0
        total_due_amount = float(total_amounts[1]) if total_amounts and total_amounts[1] else 0
        total_allocated_amount = float(total_amounts[2]) if total_amounts and total_amounts[2] else 0
        unallocated_amount = total_invoice_amount - total_allocated_amount
        
        # Unpack partner data
        (
            code, name, risk_bucket, net_score,
            total_runs, paid_runs, fully_paid_runs, stressed_runs, severely_stressed_runs,
            avg_invoice, avg_allocated, avg_due, old_overdue,
            score_continuity, score_strength, score_overdue,
            penalty_stress, penalty_overdue
        ) = partner_data
        
        # Calculate ratios
        paid_ratio = (paid_runs / total_runs) if total_runs > 0 else 0
        allocation_ratio = (avg_allocated / avg_invoice) if avg_invoice > 0 else 0
        due_ratio = (avg_due / avg_invoice) if avg_invoice > 0 else 0
        normalized_bucket = risk_bucket.replace("_RISK", "")
        
        # Format invoices for LLM
        invoice_list = []
        for inv in recent_invoices:
            invoice_list.append({
                "invoice_number": inv[0],
                "invoice_amount": float(inv[1]) if inv[1] else 0,
                "due_amount": float(inv[2]) if inv[2] else 0,
                "allocated_amount": float(inv[3]) if inv[3] else 0,
                "payment_amount": float(inv[4]) if inv[4] else 0,
                "payment_date": str(inv[5]) if inv[5] else None,
                "due_date": str(inv[6]) if inv[6] else None,
                "invoice_risk_level": inv[7],
                "days_past_due": int(inv[8]) if inv[8] else None
            })
        
        # Build explanation
        explanation = {
            "partner_code": code,
            "partner_name": name,
            "risk_bucket": normalized_bucket,
            "net_risk_score": float(net_score) if net_score else 0,
            "percentile_ranking": {
                "p25": float(p25) if p25 else 0,
                "p50": float(p50) if p50 else 0,
                "p75": float(p75) if p75 else 0,
                "position": "Top 25%" if net_score >= p75 else ("Middle 50%" if net_score >= p25 else "Bottom 25%")
            },
            "score_breakdown": {
                "cashflow_continuity": {
                    "score": float(score_continuity) if score_continuity else 0,
                    "max_score": 50,
                    "calculation": f"({paid_runs} paid runs / {total_runs} total runs) × 50",
                    "value": f"{paid_ratio:.1%}",
                    "explanation": f"Payment frequency: {paid_runs} out of {total_runs} runs had payments"
                },
                "cashflow_strength": {
                    "score": float(score_strength) if score_strength else 0,
                    "max_score": 40,
                    "calculation": f"min({allocation_ratio:.2f}, 1.5) × 40",
                    "value": f"{allocation_ratio:.1%}",
                    "explanation": f"Average allocation ratio: ₹{avg_allocated:.0f} allocated vs ₹{avg_invoice:.0f} invoiced"
                },
                "low_overdue": {
                    "score": float(score_overdue) if score_overdue else 0,
                    "max_score": 20,
                    "calculation": f"Due ratio: {due_ratio:.1%}",
                    "value": f"{due_ratio:.1%}",
                    "explanation": f"Average due amount: ₹{avg_due:.0f} vs ₹{avg_invoice:.0f} invoiced"
                },
                "penalty_severe_stress": {
                    "penalty": float(penalty_stress) if penalty_stress else 0,
                    "max_penalty": 40,
                    "calculation": f"min({severely_stressed_runs}, 8) × 5",
                    "value": f"{severely_stressed_runs} runs",
                    "explanation": f"Severely stressed runs: {severely_stressed_runs} runs with allocation < 50% of due amount"
                },
                "penalty_old_overdue": {
                    "penalty": float(penalty_overdue) if penalty_overdue else 0,
                    "max_penalty": 15,
                    "calculation": f"Old overdue: ₹{old_overdue:.0f}",
                    "value": f"₹{old_overdue:.0f}",
                    "explanation": f"Overdue amounts older than 90 days: ₹{old_overdue:.0f}"
                }
            },
            "metrics": {
                "total_runs": int(total_runs) if total_runs else 0,
                "paid_runs": int(paid_runs) if paid_runs else 0,
                "fully_paid_runs": int(fully_paid_runs) if fully_paid_runs else 0,
                "stressed_runs": int(stressed_runs) if stressed_runs else 0,
                "severely_stressed_runs": int(severely_stressed_runs) if severely_stressed_runs else 0,
                "avg_invoice_amount": float(avg_invoice) if avg_invoice else 0,
                "avg_allocated_amount": float(avg_allocated) if avg_allocated else 0,
                "avg_due_amount": float(avg_due) if avg_due else 0,
                "old_overdue_amount": float(old_overdue) if old_overdue else 0,
                "total_invoice_amount": total_invoice_amount,
                "total_due_amount": total_due_amount,
                "total_allocated_amount": total_allocated_amount,
                "unallocated_amount": unallocated_amount
            },
            "risk_bucket_explanation": {
                "LOW": "Top 25% of partners by risk score. Excellent payment behavior with high consistency and low overdue amounts.",
                "MEDIUM": "Middle 50% of partners by risk score. Moderate payment behavior with some areas for improvement.",
                "HIGH": "Bottom 25% of partners by risk score. Requires attention due to inconsistent payments or high overdue amounts."
            }[normalized_bucket]
        }
        
        # Check if insights exist in DB first - if found, return it (even if fallback)
        logger.info(f"[INSIGHTS SOURCE] Checking database for stored insights for partner {partner_code}")
        stored_insights_json = self.partner_insights_repo.get_stored_insights(partner_code)
        
        if stored_insights_json:
            try:
                stored_insights = json.loads(stored_insights_json)
                is_fallback = stored_insights.get('is_fallback', False)
                explanation["llm_insights"] = stored_insights
                logger.info(
                    f"[INSIGHTS SOURCE: DATABASE] Found stored insights for partner {partner_code}. "
                    f"Type: {'FALLBACK' if is_fallback else 'VALID LLM INSIGHTS'}. "
                    f"Returning from database cache."
                )
            except Exception as e:
                logger.warning(
                    f"[INSIGHTS SOURCE] Failed to parse stored insights for {partner_code}: {str(e)}. "
                    f"Will attempt LLM generation."
                )
                stored_insights_json = None
        else:
            logger.info(
                f"[INSIGHTS SOURCE] No stored insights found in database for partner {partner_code}. "
                f"Will generate new insights from LLM."
            )
        
        # Only call LLM if NOT found in DB
        if not stored_insights_json and invoice_list:
            try:
                logger.info(
                    f"[INSIGHTS SOURCE: LLM] Starting LLM analysis for partner {partner_code} "
                    f"with {len(invoice_list)} invoices. Generating new insights..."
                )
                llm_insights = self.llm_service.analyze_partner_risk(explanation, invoice_list)
                
                # Only store if NOT a fallback response
                if llm_insights and llm_insights.get("is_fallback") is False:
                    explanation["llm_insights"] = llm_insights
                    try:
                        insights_json = json.dumps(llm_insights)
                        self.partner_insights_repo.save_insights(partner_code, insights_json)
                        logger.info(
                            f"[INSIGHTS SOURCE: LLM] Successfully generated and stored valid LLM insights "
                            f"for partner {partner_code} in database. Future requests will use cached data."
                        )
                    except Exception as e:
                        logger.error(
                            f"[INSIGHTS SOURCE: LLM] Failed to store insights for {partner_code}: {str(e)}",
                            exc_info=True
                        )
                    logger.info(f"[INSIGHTS SOURCE: LLM] Returning newly generated LLM insights for partner {partner_code}")
                else:
                    # Fallback response - use it but don't store
                    logger.warning(
                        f"[INSIGHTS SOURCE: LLM FALLBACK] LLM returned fallback response for partner {partner_code}. "
                        f"Using fallback but NOT storing in database. "
                        f"Reason: LLM service unavailable or error occurred."
                    )
                    explanation["llm_insights"] = llm_insights
            except Exception as e:
                logger.error(
                    f"[INSIGHTS SOURCE: LLM ERROR] LLM analysis exception for partner {partner_code}: {str(e)}",
                    exc_info=True
                )
                # LLM service will return fallback, but we don't store it
                try:
                    logger.info(f"[INSIGHTS SOURCE: LLM FALLBACK] Attempting to get fallback response for partner {partner_code}")
                    llm_insights = self.llm_service.analyze_partner_risk(explanation, invoice_list)
                    if llm_insights:
                        explanation["llm_insights"] = llm_insights
                        if llm_insights.get("is_fallback") is True:
                            logger.warning(
                                f"[INSIGHTS SOURCE: LLM FALLBACK] LLM unavailable - using fallback response "
                                f"(NOT stored in DB) for partner {partner_code}"
                            )
                except:
                    logger.error(f"[INSIGHTS SOURCE: LLM ERROR] Complete LLM failure for partner {partner_code}. No insights available.")
                    explanation["llm_insights"] = None
        elif not invoice_list:
            logger.info(
                f"[INSIGHTS SOURCE: SKIPPED] No invoices found for partner {partner_code}, "
                f"skipping LLM analysis. No insights generated."
            )
            explanation["llm_insights"] = None
        
        return explanation
    
    def get_forecast(self, days: int, partner_code: Optional[str] = None, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Get cashflow forecast."""
        try:
            conn = self.get_duckdb()
        except Exception as e:
            logger.error(f"Database connection error in get_forecast: {str(e)}", exc_info=True)
            raise DatabaseConnectionError(
                message="Failed to establish database connection",
                details={"error": str(e)}
            )
        
        try:
            forecast_service = self.get_forecast_service(conn)
            return forecast_service.forecast(days=days, partner_code=partner_code, scenario=scenario)
        except (ForecastGenerationError, DatabaseQueryError, DatabaseError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_forecast: {str(e)}", exc_info=True)
            raise ForecastGenerationError(
                message=f"Unexpected error generating forecast: {str(e)}",
                details={"days": days, "partner_code": partner_code, "scenario": scenario, "error": str(e)}
            )
    
    def export_partners(self, format: str) -> tuple:
        logger.info(f"Exporting partners data in format: {format}")
        """
        Export partners data.
        
        Returns:
            Tuple of (file_content, filename, media_type)
        """
        try:
            rows = self.partner_repo.get_partners_for_export()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in export_partners: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving partners for export: {str(e)}",
                details={"error": str(e)}
            )
        
        if not rows:
            return None, None, None
        
        # Create DataFrame
        data = []
        for row in rows:
            partner_code, partner_name, total_due_amount, total_overdue, aging_bucket = row
            data.append({
                "Partner": f"{partner_name} ({partner_code})" if partner_name else partner_code,
                "Outstanding Amount": self.format_currency(self.safe(total_due_amount)),
                "Total Overdue": self.format_currency(self.safe(total_overdue)),
                "Aging Bucket": aging_bucket if aging_bucket else "N/A"
            })
        
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Partners')
                worksheet = writer.sheets['Partners']
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).map(len).max(), len(str(col)))
                    col_letter = ''
                    col_num = idx + 1
                    while col_num > 0:
                        col_num -= 1
                        col_letter = chr(65 + (col_num % 26)) + col_letter
                        col_num //= 26
                    worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
            
            output.seek(0)
            filename = f"partners_export_{timestamp}.xlsx"
            return output.read(), filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            filename = f"partners_export_{timestamp}.csv"
            return output.getvalue(), filename, "text/csv"
    
    def export_invoices(self, format: str) -> tuple:
        logger.info(f"Exporting invoices data in format: {format}")
        """
        Export invoices data.
        
        Returns:
            Tuple of (file_content, filename, media_type)
        """
        try:
            rows = self.invoice_repo.get_invoices_for_export()
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in export_invoices: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving invoices for export: {str(e)}",
                details={"error": str(e)}
            )
        
        if not rows:
            return None, None, None
        
        # Create DataFrame
        try:
            data = []
            for row in rows:
                partner_name, invoice_number, invoice_amount, due_amount, overdue_amount, overdue_days = row
                data.append({
                    "Invoice #": invoice_number if invoice_number else "N/A",
                    "Partner": partner_name if partner_name else "N/A",
                    "Invoice Amount": self.format_currency(self.safe(invoice_amount)),
                    "Outstanding Amount": self.format_currency(self.safe(due_amount)),
                    "Overdue Amount": self.format_currency(self.safe(overdue_amount)),
                    "Status": self.get_status(overdue_days)
                })
            
            df = pd.DataFrame(data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format == "excel":
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Invoices')
                        worksheet = writer.sheets['Invoices']
                        for idx, col in enumerate(df.columns):
                            max_length = max(df[col].astype(str).map(len).max(), len(str(col)))
                            col_letter = ''
                            col_num = idx + 1
                            while col_num > 0:
                                col_num -= 1
                                col_letter = chr(65 + (col_num % 26)) + col_letter
                                col_num //= 26
                            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
                    
                    output.seek(0)
                    filename = f"invoices_export_{timestamp}.xlsx"
                    return output.read(), filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                except Exception as e:
                    logger.error(f"Error creating Excel export: {str(e)}", exc_info=True)
                    raise ExportError(
                        message=f"Failed to create Excel export: {str(e)}",
                        export_type="excel",
                        details={"error": str(e)}
                    )
            else:  # CSV
                try:
                    output = io.StringIO()
                    df.to_csv(output, index=False)
                    filename = f"invoices_export_{timestamp}.csv"
                    return output.getvalue(), filename, "text/csv"
                except Exception as e:
                    logger.error(f"Error creating CSV export: {str(e)}", exc_info=True)
                    raise ExportError(
                        message=f"Failed to create CSV export: {str(e)}",
                        export_type="csv",
                        details={"error": str(e)}
                    )
        except ExportError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in export_invoices: {str(e)}", exc_info=True)
            raise ExportError(
                message=f"Unexpected error during invoice export: {str(e)}",
                export_type=format,
                details={"error": str(e)}
            )
    
    def upload_csv_files(self, files: List, append: bool) -> Dict[str, Any]:
        logger.info(f"Uploading {len(files)} CSV file(s), append={append}")
        """Process CSV file uploads."""
        conn = self.get_duckdb()
        pipeline_service = self.get_pipeline_service(conn)
        
        temp_files = []
        csv_paths = []
        
        try:
            # Save uploaded files temporarily
            for file in files:
                if not file.filename.endswith('.csv'):
                    raise ValueError(f"File {file.filename} is not a CSV file")
                
                temp_file = tempfile.NamedTemporaryFile(
                    mode='wb', suffix='.csv', delete=False
                )
                temp_files.append(temp_file.name)
                
                content = file.read()
                temp_file.write(content)
                temp_file.close()
                
                csv_paths.append(temp_file.name)
                logger.info(f"Saved uploaded file {file.filename} to {temp_file.name}")
            
            # Process files
            result = pipeline_service.process_multiple_files(
                csv_file_paths=csv_paths,
                append=append
            )
            
            return {
                "success": True,
                "message": f"Successfully processed {result['success_count']} file(s). {result['total_rows_inserted']} new record(s) added to database.",
                "files_processed": result["files_processed"],
                "summary": {
                    "total_files": len(files),
                    "success_count": result["success_count"],
                    "failure_count": result["failure_count"],
                    "total_rows_inserted": result["total_rows_inserted"]
                },
                "view_refresh": result["view_refresh"]
            }
        finally:
            # Clean up temporary files
            for temp_file_path in temp_files:
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {str(e)}")
    
    def get_settings(self) -> Dict[str, Any]:
        """Get all feature flags/settings."""
        return self._feature_flags.copy()
    
    def get_feature_flag(self, flag_key: str) -> bool:
        logger.info(f"Retrieving feature flag: {flag_key}")
        """Get a specific feature flag value."""
        return self._feature_flags.get(flag_key, False)
    
    def set_feature_flag(self, flag_key: str, value: bool) -> Dict[str, Any]:
        logger.info(f"Setting feature flag: {flag_key} to {value}")
        """Set a feature flag value."""
        if flag_key not in self._feature_flags:
            raise ValueError(f"Unknown feature flag: {flag_key}")
        self._feature_flags[flag_key] = value
        logger.info(f"Feature flag {flag_key} set to {value}")
        return {"flag": flag_key, "value": value}

    def set_gemini_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Set or update the Gemini API key.

        This updates the in-memory environment (os.environ) so new Gemini
        provider instances can use it, and also persists it to the backend
        `.env` file so it survives restarts.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key is required")

        api_key = api_key.strip()

        # Update process environment so future provider instances see the key
        os.environ["GEMINI_API_KEY"] = api_key

        # Best-effort persistence to backend/.env
        try:
            from pathlib import Path

            # backend/app/services/services.py -> backend/
            root_dir = Path(__file__).parent.parent.parent
            env_path = root_dir / ".env"

            lines = []
            if env_path.exists():
                lines = env_path.read_text().splitlines()

            found = False
            new_lines = []
            for line in lines:
                if line.startswith("GEMINI_API_KEY="):
                    new_lines.append(f"GEMINI_API_KEY={api_key}")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"GEMINI_API_KEY={api_key}")

            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            logger.info(f"Updated GEMINI_API_KEY in {env_path}")
        except Exception as e:
            # Log but do not fail the request – in-memory env var is still updated
            logger.error(f"Failed to persist GEMINI_API_KEY to .env: {str(e)}", exc_info=True)

        # Force reinit so new key is picked up by Gemini provider
        self._llm_service = None

        return {"provider": "gemini", "api_key_set": True}

    def set_llm_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Set the active LLM provider (e.g., 'ollama', 'gemini').

        This controls which backend LLM implementation is used for insights.
        """
        if not provider_name:
            raise ValueError("Provider name is required")

        provider_name = provider_name.lower()
        available = LLMProviderFactory.get_available_providers()
        if provider_name not in available:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {', '.join(available)}"
            )

        logger.info(f"Setting LLM provider to {provider_name}")
        self._feature_flags["llm_provider"] = provider_name

        # Force reinitialization on next access so new provider is used
        self._llm_service = None

        return {"provider": provider_name}
    
    def get_exceptions(self, severity: Optional[str] = None, exception_type: Optional[str] = None, age_bucket: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Retrieving exceptions with filters: severity={severity}, exception_type={exception_type}, age_bucket={age_bucket}")
        """
        Get anomalies and exceptions from payment allocations.
        Uses existing payment_allocations data to detect exceptions.
        
        Args:
            severity: Filter by severity (None for all, "High" for high severity)
            exception_type: Filter by exception type
            age_bucket: Filter by age bucket (">30", ">60")
            
        Returns:
            Dictionary with exception summary, breakdown, and detailed list
        """
        try:
            rows = self.exception_repo.get_exceptions(
                severity=severity,
                exception_type=exception_type,
                age_bucket=age_bucket
            )
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_exceptions: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error retrieving exceptions: {str(e)}",
                details={"error": str(e)}
            )
        
        # Process exceptions
        exceptions_list = []
        exception_summary = {
            "total_exceptions": 0,
            "value_impacted": 0,
            "high_severity_count": 0,
            "pending_over_30_days": 0
        }
        exception_breakdown = defaultdict(lambda: {"count": 0, "value": 0})
        
        for row in rows:
            (
                partner_code, partner_name, invoice_number, payment_ref,
                invoice_amount, due_amount, payment_amount, allocated_amount,
                due_date, payment_date, exception_type, amount_impacted,
                aging_days, severity, status
            ) = row
            
            exception_summary["total_exceptions"] += 1
            exception_summary["value_impacted"] += float(amount_impacted or 0)
            if severity == "High":
                exception_summary["high_severity_count"] += 1
            if status == "Pending" and aging_days > 30:
                exception_summary["pending_over_30_days"] += 1
            
            exception_breakdown[exception_type]["count"] += 1
            exception_breakdown[exception_type]["value"] += float(amount_impacted or 0)
            
            exceptions_list.append({
                "exception_type": exception_type,
                "reference": invoice_number or str(payment_ref) or "N/A",
                "partner_code": partner_code or "N/A",
                "partner_name": partner_name or "N/A",
                "amount_impacted": float(amount_impacted or 0),
                "aging_days": int(aging_days or 0),
                "severity": severity or "Medium",
                "status": status or "Active"
            })
        
        # Convert breakdown to list sorted by value
        breakdown_list = [
            {
                "exception_type": exc_type,
                "count": data["count"],
                "value": data["value"]
            }
            for exc_type, data in sorted(exception_breakdown.items(), key=lambda x: x[1]["value"], reverse=True)
        ]
        
        return {
            "summary": exception_summary,
            "breakdown": breakdown_list,
            "exceptions": exceptions_list[:100]  # Limit to top 100 by amount
        }
    def get_invoices(self) -> List[dict]:
        """
        Fetch ALL invoices.
        """
        try:
            df = self.invoice_repo.get_all_invoices_dict()
            # Handle NaNs
            df = df.where(pd.notnull(df), None)
            return df.to_dict(orient="records")
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Error fetching invoice list: {e}")
            return []

    def get_invoice_history(self, invoice_number: str) -> List[dict]:
        """
        Fetch audit trail (Creation + Payments).
        """
        try:
            result_df = self.invoice_history_repo.get_invoice_history(invoice_number)
            # Fix for JSON crash (Convert NaN to None)
            result_df = result_df.astype(object).where(pd.notnull(result_df), None)
            return result_df.to_dict(orient="records")
        except (DatabaseConnectionError, DatabaseQueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Error fetching history for {invoice_number}: {str(e)}")
            return []    
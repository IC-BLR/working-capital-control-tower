"""
Repository for partner insights and risk analysis.
"""
import logging
from typing import List, Tuple, Optional
from ar.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PartnerInsightsRepository(BaseRepository):
    """Repository for partner insights and risk queries."""
    
    def get_partner_risk_data(self) -> List[Tuple]:
        """
        Get partner risk buckets from v_partner_risk_final.
        
        Returns:
            List of tuples with (partner_code, partner_name, risk_bucket, net_risk_score)
        """
        query = """
            SELECT
                partner_code,
                partner_name,
                risk_bucket,
                net_risk_score
            FROM v_partner_risk_final
            ORDER BY partner_name
        """
        return self._execute_query(query)
    
    def get_invoice_risk_distribution(self) -> List[Tuple]:
        """
        Get invoice risk distribution from v_payments_latest.
        
        Returns:
            List of tuples with (partner_code, invoice_number, invoice_amount, due_amount, allocated_amount, invoice_risk_level)
        """
        query = """
            SELECT
                partner_code,
                invoice_number,
                invoice_amount,
                due_amount,
                allocated_amount,
                CASE
                    WHEN allocated_amount >= due_amount THEN 'LOW'
                    WHEN allocated_amount >= (due_amount * 0.5) THEN 'MEDIUM'
                    ELSE 'HIGH'
                END AS invoice_risk_level
            FROM v_payments_latest
            WHERE invoice_number IS NOT NULL
        """
        return self._execute_query(query)
    
    def get_partner_details_data(self, partner_code: str) -> Optional[Tuple]:
        """
        Get detailed partner risk data.
        
        Args:
            partner_code: Partner code to query
            
        Returns:
            Tuple with partner risk details or None if not found
        """
        query = """
            SELECT
                rf.partner_code,
                rf.partner_name,
                rf.risk_bucket,
                rf.net_risk_score,
                ba.total_runs,
                ba.paid_runs,
                ba.fully_paid_runs,
                ba.stressed_runs,
                ba.severely_stressed_runs,
                ba.avg_invoice_amount,
                ba.avg_allocated_amount,
                ba.avg_due_amount,
                ba.old_overdue_amount,
                rs.score_cashflow_continuity,
                rs.score_cashflow_strength,
                rs.score_low_overdue,
                rs.penalty_severe_stress,
                rs.penalty_old_overdue
            FROM v_partner_risk_final rf
            INNER JOIN v_partner_behavior_agg ba ON rf.partner_code = ba.partner_code
            INNER JOIN v_partner_risk_scored rs ON rf.partner_code = rs.partner_code
            WHERE rf.partner_code = ?
        """
        rows = self._execute_query(query, [partner_code])
        return rows[0] if rows else None
    
    def get_risk_score_percentiles(self) -> Tuple:
        """
        Get percentile statistics for risk scores.
        
        Returns:
            Tuple with (p25, p75, p50) percentiles
        """
        query = """
            SELECT 
                quantile_cont(net_risk_score, 0.25) AS p25,
                quantile_cont(net_risk_score, 0.75) AS p75,
                quantile_cont(net_risk_score, 0.50) AS p50
            FROM v_partner_risk_scored
        """
        rows = self._execute_query(query)
        return rows[0] if rows else (0, 0, 0)
    
    def get_recent_invoices_for_partner(self, partner_code: str, limit: int = 50) -> List[Tuple]:
        """
        Get recent invoices for a partner for LLM analysis.
        
        Args:
            partner_code: Partner code to query
            limit: Maximum number of invoices to return
            
        Returns:
            List of tuples with invoice data
        """
        # DuckDB doesn't support parameterized LIMIT, so we format it directly
        query = f"""
            SELECT
                invoice_number,
                invoice_amount,
                due_amount,
                allocated_amount,
                payment_amount,
                payment_date,
                due_date,
                CASE
                    WHEN allocated_amount >= due_amount THEN 'LOW'
                    WHEN allocated_amount >= (due_amount * 0.5) THEN 'MEDIUM'
                    ELSE 'HIGH'
                END AS invoice_risk_level,
                CASE
                    WHEN due_date IS NOT NULL AND payment_date IS NOT NULL 
                    THEN CAST((payment_date - due_date) AS INTEGER)
                    WHEN due_date IS NOT NULL AND payment_date IS NULL AND CURRENT_DATE > due_date
                    THEN CAST((CURRENT_DATE - due_date) AS INTEGER)
                    ELSE NULL
                END AS days_past_due
            FROM v_payments_latest
            WHERE partner_code = ? AND invoice_number IS NOT NULL
            ORDER BY payment_date DESC NULLS LAST, due_date DESC
            LIMIT {limit}
        """
        return self._execute_query(query, [partner_code])
    
    def get_stored_insights(self, partner_code: str) -> Optional[str]:
        """
        Get stored LLM insights for a partner.
        
        Args:
            partner_code: Partner code to query
            
        Returns:
            JSON string with insights or None if not found
        """
        logger.debug(f"[DB READ] Querying partner_llm_insights table for partner {partner_code}")
        query = """
            SELECT insights_json
            FROM partner_llm_insights
            WHERE partner_code = ?
        """
        rows = self._execute_query(query, [partner_code])
        result = rows[0][0] if rows and rows[0][0] else None
        if result:
            logger.debug(f"[DB READ] Found stored insights in database for partner {partner_code}")
        else:
            logger.debug(f"[DB READ] No stored insights found in database for partner {partner_code}")
        return result
    
    def save_insights(self, partner_code: str, insights_json: str) -> None:
        """
        Save or update LLM insights for a partner.
        
        Args:
            partner_code: Partner code
            insights_json: JSON string with insights
        """
        logger.debug(f"[DB WRITE] Saving/updating insights in partner_llm_insights table for partner {partner_code}")
        query = """
            INSERT INTO partner_llm_insights (partner_code, insights_json, updated_at)
            VALUES (?, ?, now())
            ON CONFLICT (partner_code) 
            DO UPDATE SET 
                insights_json = EXCLUDED.insights_json,
                updated_at = now()
        """
        self._execute_query(query, [partner_code, insights_json])
        logger.debug(f"[DB WRITE] Successfully saved insights to database for partner {partner_code}")


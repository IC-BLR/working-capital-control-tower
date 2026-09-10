"""
Repository for partner-related database operations.
"""
from typing import List, Tuple
from ar.repositories.base_repository import BaseRepository


class PartnerRepository(BaseRepository):
    """Repository for partner queries."""
    
    def get_all_partners(self) -> List[Tuple]:
        """
        Get all partners with aging data from partner_and_invoice_insight.
        
        Returns:
            List of tuples with partner data
        """
        query = """
            SELECT
                "Partner Code"              AS partner_code,
                "Partner Name"              AS partner_name,
                total_invoice_amount,
                total_due_amount,
                total_allocated_amount,
                total_payment_amount,
                total_number_of_invoices,
                avg_overdue_days,
                aging_bucket,
                total_overdue
            FROM partner_and_invoice_insight
        """
        return self._execute_query(query)
    
    def get_partners_for_export(self) -> List[Tuple]:
        """
        Get partner data formatted for export.
        
        Returns:
            List of tuples with (partner_code, partner_name, total_due_amount, total_overdue, aging_bucket)
        """
        query = """
            SELECT
                "Partner Code"              AS partner_code,
                "Partner Name"              AS partner_name,
                total_due_amount,
                total_overdue,
                aging_bucket
            FROM partner_and_invoice_insight
            ORDER BY partner_name
        """
        return self._execute_query(query)
    
    def get_partner_totals(self, partner_code: str) -> Tuple:
        """
        Get total amounts for a specific partner.
        
        Args:
            partner_code: Partner code to query
            
        Returns:
            Tuple with (total_invoice_amount, total_due_amount, total_allocated_amount)
            or None if not found
        """
        query = """
            SELECT
                total_invoice_amount,
                total_due_amount,
                total_allocated_amount
            FROM partner_and_invoice_insight
            WHERE "Partner Code" = ?
        """
        rows = self._execute_query(query, [partner_code])
        return rows[0] if rows else None


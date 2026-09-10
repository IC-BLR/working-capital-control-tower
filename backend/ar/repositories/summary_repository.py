"""
Repository for aggregate summary data.
"""
from typing import Optional, Tuple
from ar.repositories.base_repository import BaseRepository


class SummaryRepository(BaseRepository):
    """Repository for aggregate summary queries."""
    
    def get_aggregate_summary(self) -> Optional[Tuple]:
        """
        Get aggregate summary data from aggregate_level_view.
        
        Returns:
            Tuple with (total_invoice_amount, overall_exposure, total_allocated_amount,
                       total_payment_amount, total_number_of_invoices, total_number_of_partners)
            or None if no data found
        """
        query = """
            SELECT
                total_invoice_amount,
                overall_exposure,
                total_allocated_amount,
                total_payment_amount,
                total_number_of_invoices,
                total_number_of_partners
            FROM aggregate_level_view
            LIMIT 1
        """
        rows = self._execute_query(query)
        return rows[0] if rows else None


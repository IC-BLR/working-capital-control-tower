"""
Repository for invoice history and audit trail queries.
"""
from typing import List
from ar.repositories.base_repository import BaseRepository


class InvoiceHistoryRepository(BaseRepository):
    """Repository for invoice history queries."""
    
    def get_invoice_history(self, invoice_number: str) -> List[dict]:
        """
        Get invoice history (creation + payment events).
        
        Args:
            invoice_number: Invoice number to query
            
        Returns:
            DataFrame with invoice history events
        """
        clean_inv_num = invoice_number.strip()
        query = f"""
            -- 1. Creation Event
            SELECT 
                'Invoice Created' AS event_type,
                CAST(created_at AS VARCHAR) AS event_date,
                amount AS invoice_total,
                NULL AS allocated_amount,
                NULL AS total_payment_check,
                'System Generation' AS payment_reference
            FROM invoices
            WHERE TRIM(invoice_number) = '{clean_inv_num}' COLLATE NOCASE

            UNION ALL

            -- 2. Payment Events
            SELECT DISTINCT
                'Payment Received' AS event_type,
                CAST("Pymnt Dt" AS VARCHAR) AS event_date,
                NULL AS invoice_total,
                "Allocated Amt" AS allocated_amount,
                "Payment Amount" AS total_payment_check,
                CAST("Paymt Ref" AS VARCHAR) AS payment_reference
            FROM payment_allocations 
            WHERE TRIM("Invoice Number") = '{clean_inv_num}' COLLATE NOCASE
              AND "Run Date" = (SELECT MAX("Run Date") FROM payment_allocations)

            ORDER BY event_date DESC;
        """
        return self._execute_query_df(query)


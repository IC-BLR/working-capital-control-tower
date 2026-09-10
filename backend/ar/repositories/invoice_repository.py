"""
Repository for invoice-related database operations.
"""
from typing import List, Tuple
from ar.repositories.base_repository import BaseRepository


class InvoiceRepository(BaseRepository):
    """Repository for invoice queries."""
    
    def get_all_invoices(self) -> List[Tuple]:
        """
        Get all invoices with aging data from invoice_level_view.
        
        Returns:
            List of tuples with invoice data
        """
        query = """
            SELECT
                "Partner Code"   AS partner_code,
                "Partner Name"   AS partner_name,
                "Invoice Number" AS invoice_number,
                "Invoice Amount" AS invoice_amount,
                "Due Amount"     AS due_amount,
                "Allocated Amt"  AS allocated_amount,
                "Payment Amount" AS payment_amount,
                "Paymt Ref"      AS payment_ref,
                "OverDue Amount" AS overdue_amount,
                overdue_days,
                aging_bucket
            FROM invoice_level_view
        """
        return self._execute_query(query)
    
    def get_all_invoices_dict(self) -> List[dict]:
        """
        Get all invoices as dictionary format (for get_invoices() method).
        
        Returns:
            List of dictionaries with invoice data
        """
        query = """
            SELECT 
                "Invoice Number"              AS invoice_number,
                "Partner Name"                AS partner_name,
                COALESCE("Invoice Amount", 0) AS invoice_amount,
                COALESCE("Due Amount", 0)     AS due_amount,
                COALESCE("OverDue Amount", 0) AS overdue_amount,
                COALESCE(overdue_days, 0)     AS overdue_days,
                aging_bucket                  AS aging_bucket
            FROM invoice_level_view
            ORDER BY "Invoice Number" DESC
        """
        return self._execute_query_df(query)
    
    def get_invoices_for_export(self) -> List[Tuple]:
        """
        Get invoice data formatted for export.
        
        Returns:
            List of tuples with (partner_name, invoice_number, invoice_amount, due_amount, overdue_amount, overdue_days)
        """
        query = """
            SELECT
                "Partner Name"   AS partner_name,
                "Invoice Number" AS invoice_number,
                "Invoice Amount" AS invoice_amount,
                "Due Amount"     AS due_amount,
                "OverDue Amount" AS overdue_amount,
                overdue_days
            FROM invoice_level_view
            ORDER BY "Partner Name", "Invoice Number"
        """
        return self._execute_query(query)


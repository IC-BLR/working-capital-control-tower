"""
Repository for exception detection queries.
"""
from typing import List, Tuple, Optional
from ar.repositories.base_repository import BaseRepository


class ExceptionRepository(BaseRepository):
    """Repository for exception detection queries."""
    
    def get_exceptions(
        self,
        severity: Optional[str] = None,
        exception_type: Optional[str] = None,
        age_bucket: Optional[str] = None
    ) -> List[Tuple]:
        """
        Get exceptions with optional filters.
        
        Args:
            severity: Filter by severity (None for all, "High" for high severity)
            exception_type: Filter by exception type
            age_bucket: Filter by age bucket (">30", ">60")
            
        Returns:
            List of tuples with exception data
        """
        base_query = """
            WITH exceptions AS (
                SELECT
                    "Partner Code",
                    "Partner Name",
                    "Invoice Number",
                    "Paymt Ref" AS payment_reference,
                    "Invoice Amount",
                    "Due Amount",
                    "Payment Amount",
                    "Allocated Amt" AS allocated_amount,
                    "Due Date",
                    "Pymnt Dt" AS payment_date,
                    CASE
                        WHEN "Payment Amount" > "Invoice Amount" * 1.1 THEN 'Overpayment / Advance'
                        WHEN "Payment Amount" > "Invoice Amount" * 1.05 THEN 'Payment Amount >> Invoice Amount'
                        WHEN "Payment Amount" > COALESCE("Allocated Amt", 0) AND "Payment Amount" > 0 THEN 'Unallocated Payment'
                        WHEN "Due Amount" < 0 THEN 'Negative Due Amount'
                        WHEN "Due Date" IS NOT NULL AND "Pymnt Dt" IS NOT NULL AND "Due Date" < "Pymnt Dt" AND "Due Amount" > 0 THEN 'Overdue with Payment Received'
                        ELSE NULL
                    END AS exception_type,
                    CASE
                        WHEN "Payment Amount" > "Invoice Amount" * 1.1 THEN ABS("Payment Amount" - "Invoice Amount")
                        WHEN "Payment Amount" > "Invoice Amount" * 1.05 THEN ABS("Payment Amount" - "Invoice Amount")
                        WHEN "Payment Amount" > COALESCE("Allocated Amt", 0) AND "Payment Amount" > 0 THEN ("Payment Amount" - COALESCE("Allocated Amt", 0))
                        WHEN "Due Amount" < 0 THEN ABS("Due Amount")
                        WHEN "Due Date" IS NOT NULL AND "Pymnt Dt" IS NOT NULL AND "Due Date" < "Pymnt Dt" AND "Due Amount" > 0 THEN "Due Amount"
                        ELSE 0
                    END AS amount_impacted,
                    CASE
                        WHEN "Due Date" IS NOT NULL AND CURRENT_DATE > "Due Date" THEN CAST((CURRENT_DATE - "Due Date") AS INTEGER)
                        ELSE 0
                    END AS aging_days,
                    CASE
                        WHEN ABS("Payment Amount" - "Invoice Amount") > "Invoice Amount" * 0.2 OR "Due Amount" < -1000000 THEN 'High'
                        WHEN ABS("Payment Amount" - COALESCE("Allocated Amt", 0)) > 1000000 THEN 'High'
                        ELSE 'Medium'
                    END AS severity,
                    CASE
                        WHEN "Due Date" IS NOT NULL AND CURRENT_DATE > "Due Date" AND CAST((CURRENT_DATE - "Due Date") AS INTEGER) > 30 THEN 'Pending'
                        ELSE 'Active'
                    END AS status
                FROM payment_allocations
                WHERE
                    ("Payment Amount" > "Invoice Amount" * 1.05)
                    OR ("Payment Amount" > COALESCE("Allocated Amt", 0) AND "Payment Amount" > 0 AND COALESCE("Allocated Amt", 0) < "Payment Amount" * 0.9)
                    OR ("Due Amount" < 0)
                    OR ("Due Date" IS NOT NULL AND "Pymnt Dt" IS NOT NULL AND "Due Date" < "Pymnt Dt" AND "Due Amount" > 0)
            ),
            duplicate_refs AS (
                SELECT DISTINCT
                    pa."Partner Code",
                    pa."Partner Name",
                    pa."Invoice Number",
                    pa."Paymt Ref" AS payment_reference,
                    pa."Invoice Amount",
                    pa."Due Amount",
                    pa."Payment Amount",
                    pa."Allocated Amt" AS allocated_amount,
                    pa."Due Date",
                    pa."Pymnt Dt" AS payment_date,
                    'Duplicate Payment Reference' AS exception_type,
                    pa."Payment Amount" AS amount_impacted,
                    CASE
                        WHEN pa."Due Date" IS NOT NULL AND CURRENT_DATE > pa."Due Date" THEN CAST((CURRENT_DATE - pa."Due Date") AS INTEGER)
                        ELSE 0
                    END AS aging_days,
                    'Medium' AS severity,
                    'Active' AS status
                FROM payment_allocations pa
                INNER JOIN (
                    SELECT "Paymt Ref", "Partner Code"
                    FROM payment_allocations
                    WHERE "Paymt Ref" IS NOT NULL
                    GROUP BY "Paymt Ref", "Partner Code"
                    HAVING COUNT(*) > 1
                ) dup ON pa."Paymt Ref" = dup."Paymt Ref" AND pa."Partner Code" = dup."Partner Code"
            )
            SELECT * FROM exceptions WHERE exception_type IS NOT NULL
            UNION ALL
            SELECT * FROM duplicate_refs
        """
        
        # Apply filters
        where_clauses = []
        if severity and severity != "All":
            where_clauses.append(f"severity = '{severity}'")
        if exception_type:
            where_clauses.append(f"exception_type = '{exception_type}'")
        if age_bucket:
            if age_bucket == ">30":
                where_clauses.append("aging_days > 30")
            elif age_bucket == ">60":
                where_clauses.append("aging_days > 60")
        
        if where_clauses:
            query = f"""
                SELECT * FROM ({base_query}) AS filtered
                WHERE {' AND '.join(where_clauses)}
                ORDER BY amount_impacted DESC
            """
        else:
            query = f"{base_query} ORDER BY amount_impacted DESC"
        
        return self._execute_query(query)


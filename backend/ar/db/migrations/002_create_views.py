"""
Migration 002: Create analytical views.
"""
from typing import List, Tuple
import duckdb

MIGRATION_ID = "create_views"
DESCRIPTION = "Create analytical views for payment analysis"


def up(conn: duckdb.DuckDBPyConnection) -> List[Tuple[str, str]]:
    """
    Execute migration: create all views.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of (SQL statement, description) tuples
    """
    return [
        ("""
        CREATE OR REPLACE VIEW v_payments_normalized AS 
        SELECT 
            "Run Date" AS run_date,
            "Partner Code" AS partner_code,
            "Partner Name" AS partner_name,
            "Invoice Number" AS invoice_number,
            "Paymt Ref" AS payment_reference,
            "Invoice Date" AS invoice_date,
            "Invoice Amount" AS invoice_amount,
            "Due Date" AS due_date,
            "Due Amount" AS due_amount,
            "Pymnt Dt" AS payment_date,
            "Payment Amount" AS payment_amount,
            "Allocated Amt" AS allocated_amount
        FROM payment_allocations
        """, "Create v_payments_normalized view"),
        
        ("""
        CREATE OR REPLACE VIEW v_payments_latest AS 
        SELECT * FROM v_payments_normalized 
        WHERE run_date = (SELECT max(run_date) FROM v_payments_normalized)
        """, "Create v_payments_latest view"),
        
        ("""
        CREATE OR REPLACE VIEW invoice_level_view AS 
        WITH latest_invoice_data AS (
            SELECT 
                partner_code AS "Partner Code",
                partner_name AS "Partner Name",
                invoice_number AS "Invoice Number",
                invoice_amount AS "Invoice Amount",
                due_amount AS "Due Amount",
                allocated_amount AS "Allocated Amt",
                payment_amount AS "Payment Amount",
                due_date AS "Due Date",
                payment_reference AS "Paymt Ref",
                payment_date AS "Pymnt Dt",
                run_date AS "Run Date",
                row_number() OVER (PARTITION BY invoice_number ORDER BY payment_reference DESC NULLS LAST) AS rn
            FROM v_payments_latest
            WHERE invoice_number IS NOT NULL
        )
        SELECT 
            "Partner Code",
            "Partner Name",
            "Invoice Number",
            "Invoice Amount",
            "Due Amount",
            "Allocated Amt",
            "Payment Amount",
            "Paymt Ref",
            CASE 
                WHEN (("Due Date" IS NOT NULL) AND ("Run Date" IS NOT NULL) AND ("Due Date" < "Run Date")) 
                THEN ("Due Amount") 
                ELSE NULL 
            END AS "OverDue Amount",
            CASE 
                WHEN (("Due Amount" > 0) AND ("Due Date" IS NOT NULL) AND (CURRENT_DATE > "Due Date")) 
                THEN (CAST((CURRENT_DATE - "Due Date") AS INTEGER)) 
                ELSE NULL 
            END AS overdue_days,
            CASE 
                WHEN (("Due Amount" > 0) AND ("Due Date" IS NOT NULL) AND (CURRENT_DATE > "Due Date")) 
                THEN (
                    CASE 
                        WHEN (CAST((CURRENT_DATE - "Due Date") AS INTEGER) <= 0) THEN ('Mostly On Time')
                        WHEN (CAST((CURRENT_DATE - "Due Date") AS INTEGER) <= 30) THEN ('1-30 Days Overdue')
                        WHEN (CAST((CURRENT_DATE - "Due Date") AS INTEGER) <= 60) THEN ('31-60 Days Overdue')
                        WHEN (CAST((CURRENT_DATE - "Due Date") AS INTEGER) <= 90) THEN ('61-90 Days Overdue')
                        ELSE '91+ Days Overdue'
                    END
                ) 
                ELSE 'Mostly On Time' 
            END AS aging_bucket
        FROM latest_invoice_data
        WHERE rn = 1
        ORDER BY "Paymt Ref" ASC NULLS LAST
        """, "Create invoice_level_view"),
        
        ("""
        CREATE OR REPLACE VIEW partner_and_invoice_insight AS 
        SELECT 
            "Partner Code",
            "Partner Name",
            sum("Invoice Amount") AS total_invoice_amount,
            sum("Due Amount") AS total_due_amount,
            sum("Allocated Amt") AS total_allocated_amount,
            sum("Payment Amount") AS total_payment_amount,
            count(DISTINCT "Invoice Number") AS total_number_of_invoices,
            CASE 
                WHEN (count(DISTINCT "Invoice Number") > 0) 
                THEN (CAST(sum(COALESCE(overdue_days, 0)) AS DOUBLE) / count(DISTINCT "Invoice Number")) 
                ELSE NULL 
            END AS avg_overdue_days,
            mode(aging_bucket) AS aging_bucket,
            COALESCE(sum("OverDue Amount"), 0) AS total_overdue
        FROM invoice_level_view
        GROUP BY "Partner Code", "Partner Name"
        ORDER BY total_invoice_amount DESC
        """, "Create partner_and_invoice_insight view"),
        
        ("""
        CREATE OR REPLACE VIEW aggregate_level_view AS 
        SELECT 
            sum("Invoice Amount") AS total_invoice_amount,
            sum("Due Amount") AS overall_exposure,
            sum("Allocated Amt") AS total_allocated_amount,
            sum("Payment Amount") AS total_payment_amount,
            count(DISTINCT "Invoice Number") AS total_number_of_invoices,
            count(DISTINCT "Partner Name") AS total_number_of_partners
        FROM invoice_level_view
        """, "Create aggregate_level_view"),
        
        ("""
        CREATE OR REPLACE VIEW active_customers_view AS 
        SELECT 
            "Partner Name",
            sum("Invoice Amount") AS total_invoice_amount,
            sum("Due Amount") AS total_due_amount,
            sum("Allocated Amt") AS total_allocated_amount,
            sum("Payment Amount") AS total_payment_amount,
            count(DISTINCT "Invoice Number") AS total_number_of_invoices,
            CASE 
                WHEN (sum("Due Amount") > 0) THEN ('Active - Has Outstanding Exposure')
                WHEN (sum("Invoice Amount") > 0) THEN ('Active - Has Invoice Activity')
                ELSE 'Inactive'
            END AS customer_status
        FROM invoice_level_view
        WHERE (("Due Amount" > 0) OR ("Invoice Amount" > 0))
        GROUP BY "Partner Name"
        ORDER BY total_due_amount DESC, total_invoice_amount DESC
        """, "Create active_customers_view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_behavior AS 
        SELECT 
            run_date,
            partner_code,
            partner_name,
            invoice_amount,
            due_amount,
            allocated_amount
        FROM v_payments_latest
        """, "Create v_partner_behavior view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_behavior_agg AS 
        SELECT 
            partner_code,
            min(partner_name) AS partner_name,
            count(*) AS total_runs,
            sum(CASE WHEN (allocated_amount > 0) THEN 1 ELSE 0 END) AS paid_runs,
            sum(CASE WHEN (allocated_amount >= due_amount) THEN 1 ELSE 0 END) AS fully_paid_runs,
            sum(CASE WHEN (allocated_amount < due_amount) THEN 1 ELSE 0 END) AS stressed_runs,
            sum(CASE WHEN (allocated_amount < (due_amount * 0.5)) THEN 1 ELSE 0 END) AS severely_stressed_runs,
            avg(invoice_amount) AS avg_invoice_amount,
            avg(allocated_amount) AS avg_allocated_amount,
            avg(due_amount) AS avg_due_amount,
            sum(CASE 
                WHEN ((run_date < (CURRENT_DATE - INTERVAL '90 days')) AND (allocated_amount < due_amount)) 
                THEN (due_amount - allocated_amount) 
                ELSE 0 
            END) AS old_overdue_amount,
            max(run_date) AS latest_run_date
        FROM v_partner_behavior
        GROUP BY partner_code
        """, "Create v_partner_behavior_agg view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_risk_scored AS 
        SELECT 
            partner_code,
            ((CAST(paid_runs AS DOUBLE) / NULLIF(total_runs, 0)) * 50) AS score_cashflow_continuity,
            (LEAST((avg_allocated_amount / NULLIF(avg_invoice_amount, 0)), 1.5) * 40) AS score_cashflow_strength,
            CASE 
                WHEN ((avg_due_amount / NULLIF(avg_invoice_amount, 0)) <= 0.03) THEN 20
                WHEN ((avg_due_amount / NULLIF(avg_invoice_amount, 0)) <= 0.08) THEN 10
                ELSE 0
            END AS score_low_overdue,
            (LEAST(severely_stressed_runs, 8) * 5) AS penalty_severe_stress,
            CASE 
                WHEN ((old_overdue_amount / NULLIF(avg_invoice_amount, 0)) >= 2) THEN 15
                ELSE 0
            END AS penalty_old_overdue,
            (
                ((CAST(paid_runs AS DOUBLE) / NULLIF(total_runs, 0)) * 50) + 
                (LEAST((avg_allocated_amount / NULLIF(avg_invoice_amount, 0)), 1.5) * 40) + 
                CASE 
                    WHEN ((avg_due_amount / NULLIF(avg_invoice_amount, 0)) <= 0.03) THEN 20
                    WHEN ((avg_due_amount / NULLIF(avg_invoice_amount, 0)) <= 0.08) THEN 10
                    ELSE 0
                END - 
                (LEAST(severely_stressed_runs, 8) * 5) - 
                CASE 
                    WHEN ((old_overdue_amount / NULLIF(avg_invoice_amount, 0)) >= 2) THEN 15
                    ELSE 0
                END
            ) AS net_risk_score
        FROM v_partner_behavior_agg
        """, "Create v_partner_risk_scored view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_risk_final AS 
        WITH stats AS (
            SELECT 
                quantile_cont(net_risk_score, 0.25) AS p25,
                quantile_cont(net_risk_score, 0.75) AS p75
            FROM v_partner_risk_scored
        )
        SELECT 
            s.partner_code,
            a.partner_name,
            s.net_risk_score,
            CASE 
                WHEN (s.net_risk_score >= stats.p75) THEN ('LOW_RISK')
                WHEN (s.net_risk_score >= stats.p25) THEN ('MEDIUM_RISK')
                ELSE 'HIGH_RISK'
            END AS risk_bucket
        FROM v_partner_risk_scored AS s
        INNER JOIN v_partner_behavior_agg AS a ON (s.partner_code = a.partner_code)
        CROSS JOIN stats
        """, "Create v_partner_risk_final view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_run_state AS 
        WITH canonical_partner AS (
            SELECT partner_code, max(partner_name) AS partner_name 
            FROM v_payments_normalized 
            GROUP BY partner_code
        )
        SELECT 
            p.partner_code,
            c.partner_name,
            p.run_date,
            sum(COALESCE(p.due_amount, 0)) AS due_amount,
            sum(COALESCE(p.allocated_amount, 0)) AS allocated_amount,
            round((sum(COALESCE(p.allocated_amount, 0)) / NULLIF(sum(COALESCE(p.due_amount, 0)), 0)), 3) AS payment_coverage_ratio,
            (sum(COALESCE(p.due_amount, 0)) - sum(COALESCE(p.allocated_amount, 0))) AS gap_amount
        FROM v_payments_normalized AS p
        INNER JOIN canonical_partner AS c ON (p.partner_code = c.partner_code)
        GROUP BY p.partner_code, c.partner_name, p.run_date
        """, "Create v_partner_run_state view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_trend AS 
        SELECT 
            partner_code,
            partner_name,
            run_date,
            due_amount,
            allocated_amount,
            payment_coverage_ratio,
            gap_amount,
            allocated_amount AS allocation_intensity,
            round((allocated_amount / NULLIF(due_amount, 0)), 3) AS allocation_scale_ratio,
            lag(payment_coverage_ratio) OVER (PARTITION BY partner_code ORDER BY run_date) AS prev_pcr,
            lag(gap_amount) OVER (PARTITION BY partner_code ORDER BY run_date) AS prev_gap,
            CASE 
                WHEN (lag(payment_coverage_ratio) OVER (PARTITION BY partner_code ORDER BY run_date) IS NULL) 
                THEN NULL 
                ELSE (payment_coverage_ratio - lag(payment_coverage_ratio) OVER (PARTITION BY partner_code ORDER BY run_date)) 
            END AS pcr_delta,
            CASE 
                WHEN (lag(gap_amount) OVER (PARTITION BY partner_code ORDER BY run_date) IS NULL) 
                THEN NULL 
                ELSE (gap_amount - lag(gap_amount) OVER (PARTITION BY partner_code ORDER BY run_date)) 
            END AS gap_delta
        FROM v_partner_run_state
        """, "Create v_partner_trend view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_cashflow_engagement AS 
        SELECT 
            partner_code,
            partner_name,
            run_date,
            due_amount,
            allocated_amount,
            CASE 
                WHEN ((allocated_amount >= (0.5 * due_amount)) AND (allocated_amount > 0)) THEN ('HIGH_CASHFLOW')
                WHEN (allocated_amount > 0) THEN ('MODERATE_CASHFLOW')
                ELSE 'LOW_CASHFLOW'
            END AS cashflow_engagement
        FROM v_partner_run_state
        """, "Create v_partner_cashflow_engagement view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_exposure_by_run AS 
        SELECT 
            run_date,
            partner_code,
            any_value(partner_name) AS partner_name,
            sum(invoice_amount) AS total_invoice_amount,
            sum(allocated_amount) AS total_allocated_amount,
            (sum(invoice_amount) - sum(allocated_amount)) AS outstanding_amount
        FROM v_payments_normalized
        GROUP BY run_date, partner_code
        """, "Create v_partner_exposure_by_run view"),
        
        ("""
        CREATE OR REPLACE VIEW v_partner_exposure_trend AS 
        SELECT 
            partner_code,
            partner_name,
            run_date,
            outstanding_amount,
            lag(outstanding_amount) OVER (PARTITION BY partner_code ORDER BY run_date) AS prev_outstanding_amount,
            (lag(outstanding_amount) OVER (PARTITION BY partner_code ORDER BY run_date) - outstanding_amount) AS gap_reduction
        FROM v_partner_exposure_by_run
        """, "Create v_partner_exposure_trend view"),
    ]


# Rollback not implemented
down = None


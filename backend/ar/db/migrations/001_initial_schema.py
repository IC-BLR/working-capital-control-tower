"""
Migration 001: Create initial database tables.
"""
from typing import List, Tuple
import duckdb

MIGRATION_ID = "initial_schema"
DESCRIPTION = "Create initial tables: partners, invoices, cashflow_entries, payment_allocations, partner_llm_insights"


def up(conn: duckdb.DuckDBPyConnection) -> List[Tuple[str, str]]:
    """
    Execute migration: create all base tables.
    
    Args:
        conn: DuckDB connection
        
    Returns:
        List of (SQL statement, description) tuples
    """
    return [
        ("""
        CREATE TABLE IF NOT EXISTS partners (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            category VARCHAR,
            contact_email VARCHAR,
            total_revenue DOUBLE,
            total_expenses DOUBLE,
            status VARCHAR,
            created_at TIMESTAMP
        )
        """, "Create partners table"),
        
        ("""
        CREATE TABLE IF NOT EXISTS invoices (
            id VARCHAR PRIMARY KEY,
            partner_id VARCHAR,
            partner_name VARCHAR,
            invoice_number VARCHAR,
            amount DOUBLE,
            type VARCHAR,
            status VARCHAR,
            due_date DATE,
            paid_date DATE,
            category VARCHAR,
            description VARCHAR,
            created_at TIMESTAMP
        )
        """, "Create invoices table"),
        
        ("""
        CREATE TABLE IF NOT EXISTS cashflow_entries (
            id VARCHAR PRIMARY KEY,
            date DATE,
            inflow DOUBLE,
            outflow DOUBLE,
            net_flow DOUBLE,
            running_balance DOUBLE,
            category VARCHAR
        )
        """, "Create cashflow_entries table"),
        
        ("""
        CREATE TABLE IF NOT EXISTS payment_allocations (
            "Run Date" DATE,
            "Partner Code" VARCHAR,
            "Partner Name" VARCHAR,
            "Invoice Number" VARCHAR,
            "Paymt Ref" DOUBLE,
            "Invoice Date" DATE,
            "Invoice Amount" DOUBLE,
            "Due Date" DATE,
            "Due Amount" DOUBLE,
            "Pymnt Dt" DATE,
            "Payment Amount" DOUBLE,
            "Allocated Amt" DOUBLE
        )
        """, "Create payment_allocations table"),
        
        ("""
        CREATE TABLE IF NOT EXISTS partner_llm_insights (
            partner_code VARCHAR PRIMARY KEY,
            insights_json TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        )
        """, "Create partner_llm_insights table"),
    ]


# Rollback not implemented
down = None


"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
import tempfile
import os
import duckdb
from pathlib import Path
from typing import Callable

from ar.repositories import (
    SummaryRepository,
    PartnerRepository,
    InvoiceRepository,
    PartnerInsightsRepository,
    ExceptionRepository,
    InvoiceHistoryRepository
)
from ar.services import APIServices


@pytest.fixture
def test_db_path():
    """Create a temporary DuckDB database for testing."""
    temp_db = tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False)
    temp_db.close()
    yield temp_db.name
    # Cleanup
    if os.path.exists(temp_db.name):
        os.unlink(temp_db.name)


@pytest.fixture
def test_db_connection(test_db_path):
    """Create a DuckDB connection for testing."""
    conn = duckdb.connect(test_db_path)
    # Create minimal test schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS aggregate_level_view (
            total_invoice_amount DOUBLE,
            overall_exposure DOUBLE,
            total_allocated_amount DOUBLE,
            total_payment_amount DOUBLE,
            total_number_of_invoices INTEGER,
            total_number_of_partners INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS partner_and_invoice_insight (
            "Partner Code" VARCHAR,
            "Partner Name" VARCHAR,
            total_invoice_amount DOUBLE,
            total_due_amount DOUBLE,
            total_allocated_amount DOUBLE,
            total_payment_amount DOUBLE,
            total_number_of_invoices INTEGER,
            avg_overdue_days DOUBLE,
            aging_bucket VARCHAR,
            total_overdue DOUBLE
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoice_level_view (
            "Partner Code" VARCHAR,
            "Partner Name" VARCHAR,
            "Invoice Number" VARCHAR,
            "Invoice Amount" DOUBLE,
            "Due Amount" DOUBLE,
            "Allocated Amt" DOUBLE,
            "Payment Amount" DOUBLE,
            "Paymt Ref" VARCHAR,
            "OverDue Amount" DOUBLE,
            overdue_days INTEGER,
            aging_bucket VARCHAR
        )
    """)
    
    # Insert test data
    conn.execute("""
        INSERT INTO aggregate_level_view VALUES
        (1000000.0, 500000.0, 800000.0, 750000.0, 100, 10)
    """)
    
    conn.execute("""
        INSERT INTO partner_and_invoice_insight VALUES
        ('PARTNER1', 'Test Partner 1', 100000.0, 50000.0, 80000.0, 75000.0, 10, 5.0, 'CURRENT', 0.0)
    """)
    
    conn.execute("""
        INSERT INTO invoice_level_view VALUES
        ('PARTNER1', 'Test Partner 1', 'INV001', 10000.0, 5000.0, 8000.0, 7500.0, 'PAY001', 0.0, 0, 'CURRENT')
    """)
    
    yield conn
    conn.close()


@pytest.fixture
def get_duckdb_func(test_db_connection):
    """Return a function that returns the test database connection."""
    def _get_duckdb():
        return test_db_connection
    return _get_duckdb


@pytest.fixture
def repositories(get_duckdb_func):
    """Create repository instances for testing."""
    return {
        'summary_repo': SummaryRepository(get_duckdb_func),
        'partner_repo': PartnerRepository(get_duckdb_func),
        'invoice_repo': InvoiceRepository(get_duckdb_func),
        'partner_insights_repo': PartnerInsightsRepository(get_duckdb_func),
        'exception_repo': ExceptionRepository(get_duckdb_func),
        'invoice_history_repo': InvoiceHistoryRepository(get_duckdb_func),
    }


@pytest.fixture
def api_services(get_duckdb_func, repositories):
    """Create APIServices instance with repositories."""
    return APIServices(
        get_duckdb_func=get_duckdb_func,
        summary_repo=repositories['summary_repo'],
        partner_repo=repositories['partner_repo'],
        invoice_repo=repositories['invoice_repo'],
        partner_insights_repo=repositories['partner_insights_repo'],
        exception_repo=repositories['exception_repo'],
        invoice_history_repo=repositories['invoice_history_repo'],
    )


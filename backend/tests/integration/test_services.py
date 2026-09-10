"""
Integration tests for APIServices layer.
"""
import pytest
from ar.services import APIServices
from ar.core.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseError,
    DataNotFoundError
)


class TestAPIServicesIntegration:
    """Integration tests for APIServices."""
    
    def test_get_summary_success(self, api_services):
        """Test get_summary() returns valid data."""
        result = api_services.get_summary()
        
        assert result is not None
        assert result.total_invoice_amount == 1000000.0
        assert result.overall_exposure == 500000.0
        assert result.total_allocated_amount == 800000.0
        assert result.total_payment_amount == 750000.0
        assert result.total_number_of_invoices == 100
        assert result.total_number_of_partners == 10
    
    def test_get_summary_empty_data(self, test_db_connection, get_duckdb_func):
        """Test get_summary() handles empty data gracefully."""
        # Clear test data
        test_db_connection.execute("DELETE FROM aggregate_level_view")
        
        services = APIServices(get_duckdb_func)
        result = services.get_summary()
        
        assert result is not None
        assert result.total_invoice_amount == 0
        assert result.overall_exposure == 0
    
    def test_get_partners_success(self, api_services):
        """Test get_partners() returns valid data."""
        result = api_services.get_partners()
        
        assert result is not None
        assert len(result) == 1
        assert result[0].partner_code == 'PARTNER1'
        assert result[0].partner_name == 'Test Partner 1'
        assert result[0].total_invoice_amount == 100000.0
    
    def test_get_partners_empty(self, test_db_connection, get_duckdb_func):
        """Test get_partners() handles empty data."""
        test_db_connection.execute("DELETE FROM partner_and_invoice_insight")
        
        services = APIServices(get_duckdb_func)
        result = services.get_partners()
        
        assert result == []
    
    def test_get_invoices_success(self, api_services):
        """Test get_invoices() returns valid data."""
        result = api_services.get_invoices()
        
        assert result is not None
        assert len(result) >= 1
        # Check first invoice
        invoice = result[0]
        assert invoice.partner_code == 'PARTNER1'
        assert invoice.invoice_number == 'INV001'
    
    def test_get_partner_insights_success(self, api_services):
        """Test get_partner_insights() returns valid structure."""
        result = api_services.get_partner_insights()
        
        assert result is not None
        assert 'portfolio_summary' in result
        assert 'partner_risk' in result
        assert isinstance(result['portfolio_summary'], dict)
        assert isinstance(result['partner_risk'], list)
    
    def test_get_partner_insights_empty(self, test_db_connection, get_duckdb_func):
        """Test get_partner_insights() handles empty data."""
        # Create empty views
        test_db_connection.execute("""
            CREATE TABLE IF NOT EXISTS v_partner_risk_final (
                partner_code VARCHAR,
                partner_name VARCHAR,
                risk_bucket VARCHAR,
                net_risk_score DOUBLE
            )
        """)
        test_db_connection.execute("DELETE FROM v_partner_risk_final")
        
        services = APIServices(get_duckdb_func)
        result = services.get_partner_insights()
        
        assert result['portfolio_summary']['partners'] == 0
        assert result['partner_risk'] == []
    
    def test_export_partners_success(self, api_services):
        """Test export_partners() generates valid export."""
        content, filename, media_type = api_services.export_partners('csv')
        
        assert content is not None
        assert filename is not None
        assert media_type == 'text/csv'
        assert 'Partner' in content or 'PARTNER1' in content
    
    def test_export_partners_empty(self, test_db_connection, get_duckdb_func):
        """Test export_partners() handles empty data."""
        test_db_connection.execute("DELETE FROM partner_and_invoice_insight")
        
        services = APIServices(get_duckdb_func)
        result = services.export_partners('csv')
        
        assert result == (None, None, None)
    
    def test_export_invoices_success(self, api_services):
        """Test export_invoices() generates valid export."""
        content, filename, media_type = api_services.export_invoices('csv')
        
        assert content is not None
        assert filename is not None
        assert media_type == 'text/csv'
    
    def test_get_exceptions_success(self, api_services):
        """Test get_exceptions() returns valid structure."""
        result = api_services.get_exceptions()
        
        assert result is not None
        assert 'summary' in result
        assert 'breakdown' in result
        assert 'exceptions' in result
        assert isinstance(result['summary'], dict)
        assert isinstance(result['breakdown'], list)
        assert isinstance(result['exceptions'], list)
    
    def test_repository_exception_handling(self, get_duckdb_func):
        """Test that repository exceptions are properly converted to service exceptions."""
        # Create a broken connection getter
        def broken_get_duckdb():
            raise RuntimeError("Connection failed")
        
        services = APIServices(broken_get_duckdb)
        
        with pytest.raises(DatabaseConnectionError):
            services.get_summary()
        
        with pytest.raises(DatabaseConnectionError):
            services.get_partners()
    
    def test_business_logic_preserved(self, api_services):
        """Test that business logic methods are still available."""
        # Test safe() method
        assert api_services.safe(None) == 0
        assert api_services.safe(5.0) == 5.0
        
        # Test format_currency() method
        assert api_services.format_currency(1000) == "₹1,000"
        assert api_services.format_currency(0) == "₹0"
        
        # Test get_status() method
        assert api_services.get_status(None) == "On Time"
        assert api_services.get_status(5) == "Pending"
        assert api_services.get_status(100) == "Overdue"


"""
Data Pipeline Service: Load CSV data and refresh views.
"""
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import duckdb

from ar.core.exceptions import (
    DatabaseError,
    DatabaseQueryError,
    DataProcessingError,
    DataValidationError
)

logger = logging.getLogger(__name__)


class DataPipelineService:
    """
    Service class to handle CSV data loading into payment_allocations table
    and refresh all dependent views.
    """
    
    # Expected columns in CSV (matching payment_allocations table schema)
    EXPECTED_COLUMNS = [
        "Run Date",
        "Partner Code",
        "Partner Name",
        "Invoice Number",
        "Paymt Ref",
        "Invoice Date",
        "Invoice Amount",
        "Due Date",
        "Due Amount",
        "Pymnt Dt",
        "Payment Amount",
        "Allocated Amt"
    ]
    
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        logger.info("Initializing DataPipelineService with DuckDB connection")  
        """
        Initialize with DuckDB connection.
        
        Args:
            conn: DuckDB connection instance
        """
        self.conn = conn
    
    def validate_csv_columns(self, df: pd.DataFrame):
        logger.info("Validating CSV columns")   
        """
        Validate that CSV has required columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Raises:
            DataValidationError: If validation fails
        """
        from typing import Tuple
        try:
            if df is None or df.empty:
                raise DataValidationError(
                    message="DataFrame is empty or None",
                    field="dataframe",
                    details={"row_count": 0 if df is None else len(df)}
                )
            
            missing_cols = set(self.EXPECTED_COLUMNS) - set(df.columns)
            if missing_cols:
                raise DataValidationError(
                    message=f"Missing required columns: {', '.join(missing_cols)}",
                    field="columns",
                    details={
                        "missing_columns": list(missing_cols),
                        "expected_columns": self.EXPECTED_COLUMNS,
                        "provided_columns": list(df.columns)
                    }
                )
            
            extra_cols = set(df.columns) - set(self.EXPECTED_COLUMNS)
            if extra_cols:
                logger.warning(f"Extra columns found (will be ignored): {', '.join(extra_cols)}")
            
            return True, None
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in validate_csv_columns: {str(e)}", exc_info=True)
            raise DataValidationError(
                message=f"Unexpected error during column validation: {str(e)}",
                details={"error": str(e)}
            )
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"Normalizing DataFrame to match table schema, Original cols: {len(df.columns)}")  
        """
        Normalize DataFrame to match table schema.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Normalized DataFrame
        """
        # Select only expected columns
        df_normalized = df[self.EXPECTED_COLUMNS].copy()
        
        # Convert date columns
        date_columns = ["Run Date", "Invoice Date", "Due Date", "Pymnt Dt"]
        for col in date_columns:
            if col in df_normalized.columns:
                df_normalized[col] = pd.to_datetime(df_normalized[col], errors='coerce')
        
        # Convert numeric columns
        numeric_columns = [
            "Paymt Ref", "Invoice Amount", "Due Amount", 
            "Payment Amount", "Allocated Amt"
        ]
        for col in numeric_columns:
            if col in df_normalized.columns:
                df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce')
        
        # Replace NaN with None for DuckDB compatibility
        df_normalized = df_normalized.where(pd.notnull(df_normalized), None)
        
        return df_normalized
    
    def load_csv_to_table(
        self, 
        csv_file_path: str, 
        append: bool = True
    ) -> Dict[str, Any]:
        logger.info(f"Loading CSV file {csv_file_path} into payment_allocations table. Append mode: {append}")  
        """
        Load CSV file into payment_allocations table.
        
        Args:
            csv_file_path: Path to CSV file
            append: If True, append data; if False, truncate and insert
            
        Returns:
            Dictionary with load statistics
            
        Raises:
            DataProcessingError: If file processing fails
            DataValidationError: If data validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Read CSV
            try:
                df = pd.read_csv(csv_file_path)
                logger.info(f"Successfully read CSV file {csv_file_path} ")
            except Exception as e:
                logger.error(f"Error reading CSV file {csv_file_path}: {str(e)}", exc_info=True)
                raise DataProcessingError(
                    message=f"Failed to read CSV file: {str(e)}",
                    file_path=csv_file_path,
                    details={"error": str(e)}
                )
            
            # Validate columns
            try:
                is_valid, error_msg = self.validate_csv_columns(df)
                if not is_valid:
                    raise DataValidationError(
                        message=error_msg or "CSV validation failed",
                        field="columns",
                        details={"file_path": csv_file_path}
                    )
            except DataValidationError:
                raise
            except Exception as e:
                logger.error(f"Validation error: {str(e)}", exc_info=True)
                raise DataValidationError(
                    message=f"Data validation failed: {str(e)}",
                    details={"file_path": csv_file_path, "error": str(e)}
                )
            
            # Normalize data
            df_normalized = self.normalize_dataframe(df)
            
            # Get row count before insert
            try:
                if append:
                    before_count = self.conn.execute(
                        "SELECT COUNT(*) FROM payment_allocations"
                    ).fetchone()[0]
                else:
                    before_count = 0
            except duckdb.Error as e:
                logger.error(f"Database error getting row count: {str(e)}", exc_info=True)
                raise DatabaseQueryError(
                    message="Failed to get current row count",
                    query="SELECT COUNT(*) FROM payment_allocations",
                    details={"file_path": csv_file_path, "error": str(e)}
                )
            
            # Insert data using DuckDB's register method
            try:
                # Register DataFrame as a temporary view
                self.conn.register("temp_df", df_normalized)
                
                if append:
                    # Append mode - insert into table
                    self.conn.execute(
                        """
                        INSERT INTO payment_allocations 
                        SELECT * FROM temp_df
                        """
                    )
                else:
                    # Replace mode - truncate and insert
                    self.conn.execute("DELETE FROM payment_allocations")
                    self.conn.execute(
                        """
                        INSERT INTO payment_allocations 
                        SELECT * FROM temp_df
                        """
                    )
                
                # Unregister temporary view
                self.conn.unregister("temp_df")
            except duckdb.Error as e:
                logger.error(f"Database error inserting data: {str(e)}", exc_info=True)
                # Clean up temp view if it exists
                try:
                    self.conn.unregister("temp_df")
                except:
                    pass
                raise DatabaseQueryError(
                    message="Failed to insert data into payment_allocations table",
                    query="INSERT INTO payment_allocations SELECT * FROM temp_df",
                    details={"file_path": csv_file_path, "error": str(e)}
                )
            
            # Get row count after insert
            try:
                after_count = self.conn.execute(
                    "SELECT COUNT(*) FROM payment_allocations"
                ).fetchone()[0]
            except duckdb.Error as e:
                logger.error(f"Database error getting row count after insert: {str(e)}", exc_info=True)
                raise DatabaseQueryError(
                    message="Failed to get row count after insert",
                    query="SELECT COUNT(*) FROM payment_allocations",
                    details={"file_path": csv_file_path, "error": str(e)}
                )
            
            rows_inserted = after_count - before_count
            
            logger.info(
                f"Loaded {rows_inserted} rows from {csv_file_path}. "
                f"Total rows in table: {after_count}"
            )
            
            return {
                "success": True,
                "rows_inserted": rows_inserted,
                "total_rows": after_count,
                "file": csv_file_path
            }
            
        except (DataValidationError, DataProcessingError, DatabaseError, DatabaseQueryError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading CSV {csv_file_path}: {str(e)}", exc_info=True)
            raise DataProcessingError(
                message=f"Unexpected error loading CSV file: {str(e)}",
                file_path=csv_file_path,
                details={"error": str(e)}
            )
    
    def refresh_views(self) -> Dict[str, Any]:
        logger.info("Refreshing views dependent on payment_allocations table")
        """
        Refresh all views that depend on payment_allocations.
        In DuckDB, views are automatically updated, but we verify they exist.
        
        Returns:
            Dictionary with refresh status
        """
        try:
            # List of views that depend on payment_allocations
            dependent_views = [
                "v_payments_normalized",
                "v_payments_latest",
                "invoice_level_view",
                "partner_and_invoice_insight",
                "v_partner_behavior",
                "v_partner_behavior_agg",
                "v_partner_risk_scored",
                "v_partner_risk_final",
                "aggregate_level_view",
                "active_customers_view"
            ]
            
            refreshed_views = []
            failed_views = []
            
            for view_name in dependent_views:
                try:
                    # Verify view exists and is accessible
                    result = self.conn.execute(
                        f"SELECT COUNT(*) FROM {view_name} LIMIT 1"
                    ).fetchone()
                    refreshed_views.append(view_name)
                    logger.debug(f"Verified view {view_name} is accessible")
                except Exception    as e:
                    failed_views.append({"view": view_name, "error": str(e)})
                    logger.warning(f"Failed to verify view {view_name}: {str(e)}")
            
            # Get sample counts from key views
            view_counts = {}
            for view_name in refreshed_views[:5]:  # Sample first 5 views
                try:
                    count = self.conn.execute(
                        f"SELECT COUNT(*) FROM {view_name}"
                    ).fetchone()[0]
                    view_counts[view_name] = count
                except:
                    pass
            
            return {
                "success": True,
                "refreshed_views": len(refreshed_views),
                "total_views": len(dependent_views),
                "failed_views": failed_views,
                "view_counts": view_counts,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error refreshing views: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_multiple_files(
        self, 
        csv_file_paths: List[str], 
        append: bool = True
    ) -> Dict[str, Any]:
        logger.info(f"Processing multiple CSV files: {csv_file_paths}")        
        """
        Process multiple CSV files and refresh views.
        
        Args:
            csv_file_paths: List of CSV file paths
            append: If True, append data; if False, truncate and insert
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "files_processed": [],
            "total_rows_inserted": 0,
            "success_count": 0,
            "failure_count": 0,
            "view_refresh": None
        }
        
        # If replace mode, delete all records once before processing files
        if not append:
            before_count = self.conn.execute(
                "SELECT COUNT(*) FROM payment_allocations"
            ).fetchone()[0]
            self.conn.execute("DELETE FROM payment_allocations")
            logger.info(f"Replace mode: Deleted {before_count} existing records")
        
        # Get initial count for calculating new records
        initial_count = self.conn.execute(
            "SELECT COUNT(*) FROM payment_allocations"
        ).fetchone()[0]
        
        # Process each file (always append after initial delete if replace mode)
        for file_path in csv_file_paths:
            file_result = self.load_csv_to_table(file_path, append=True)
            results["files_processed"].append(file_result)
            
            if file_result["success"]:
                results["success_count"] += 1
                results["total_rows_inserted"] += file_result.get("rows_inserted", 0)
            else:
                results["failure_count"] += 1
        
        # Calculate total new records added
        final_count = self.conn.execute(
            "SELECT COUNT(*) FROM payment_allocations"
        ).fetchone()[0]
        
        # Update total_rows_inserted to reflect actual new records
        if not append:
            # In replace mode, all inserted records are new
            results["total_rows_inserted"] = final_count
        else:
            # In append mode, use the sum of individual file inserts
            # (already calculated above)
            pass
        
        # Refresh views after all files are processed
        if results["success_count"] > 0:
            results["view_refresh"] = self.refresh_views()
        logger.info(f"Completed processing multiple files.") 
        return results


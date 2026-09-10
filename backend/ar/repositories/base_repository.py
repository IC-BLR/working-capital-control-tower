"""
Base repository class for database operations.
"""
import logging
import duckdb
from typing import Callable
from ar.core.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class providing common database operations."""
    
    def __init__(self, get_duckdb_func: Callable[[], duckdb.DuckDBPyConnection]):
        """
        Initialize repository with database connection getter.
        
        Args:
            get_duckdb_func: Function that returns DuckDB connection
        """
        self.get_duckdb = get_duckdb_func
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get database connection, handling connection errors.
        
        Returns:
            DuckDB connection
            
        Raises:
            DatabaseConnectionError: If connection cannot be established
        """
        try:
            return self.get_duckdb()
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}", exc_info=True)
            raise DatabaseConnectionError(
                message="Failed to establish database connection",
                details={"error": str(e)}
            )
    
    def _execute_query(self, query: str, parameters: list = None) -> list:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            parameters: Optional query parameters
            
        Returns:
            List of rows (tuples)
            
        Raises:
            DatabaseQueryError: If query execution fails
            DatabaseError: For unexpected errors
        """
        try:
            conn = self._get_connection()
            if parameters:
                result = conn.execute(query, parameters)
            else:
                result = conn.execute(query)
            return result.fetchall()
        except duckdb.Error as e:
            logger.error(f"Database query error: {str(e)}", exc_info=True)
            raise DatabaseQueryError(
                message="Database query failed",
                query=query,
                details={"error": str(e)}
            )
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error executing query: {str(e)}",
                details={"error": str(e), "query": query}
            )
    
    def _execute_query_df(self, query: str, parameters: list = None):
        """
        Execute a query and return results as DataFrame.
        
        Args:
            query: SQL query string
            parameters: Optional query parameters
            
        Returns:
            DataFrame with query results
            
        Raises:
            DatabaseQueryError: If query execution fails
            DatabaseError: For unexpected errors
        """
        try:
            conn = self._get_connection()
            if parameters:
                result = conn.execute(query, parameters)
            else:
                result = conn.execute(query)
            return result.fetchdf()
        except duckdb.Error as e:
            logger.error(f"Database query error: {str(e)}", exc_info=True)
            raise DatabaseQueryError(
                message="Database query failed",
                query=query,
                details={"error": str(e)}
            )
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=f"Unexpected error executing query: {str(e)}",
                details={"error": str(e), "query": query}
            )


"""
Custom exception classes for the application.
"""
from typing import Optional, Dict, Any


class ApplicationError(Exception):
    """Base exception class for all application errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class DatabaseError(ApplicationError):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str = "Database connection failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details
        )
        self.error_code = "DATABASE_CONNECTION_ERROR"
        self.status_code = 503  # Service Unavailable


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""
    
    def __init__(self, message: str, query: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if query:
            error_details["query"] = query
        super().__init__(
            message=message,
            details=error_details
        )
        self.error_code = "DATABASE_QUERY_ERROR"


class DataValidationError(ApplicationError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=400,
            error_code="DATA_VALIDATION_ERROR",
            details=error_details
        )


class ForecastGenerationError(ApplicationError):
    """Raised when forecast generation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="FORECAST_GENERATION_ERROR",
            details=details
        )


class DataNotFoundError(ApplicationError):
    """Raised when requested data is not found."""
    
    def __init__(self, message: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None):
        details = {}
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = entity_id
        super().__init__(
            message=message,
            status_code=404,
            error_code="DATA_NOT_FOUND",
            details=details
        )


class DataProcessingError(ApplicationError):
    """Raised when data processing fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if file_path:
            error_details["file_path"] = file_path
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATA_PROCESSING_ERROR",
            details=error_details
        )


class ExportError(ApplicationError):
    """Raised when data export fails."""
    
    def __init__(self, message: str, export_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if export_type:
            error_details["export_type"] = export_type
        super().__init__(
            message=message,
            status_code=500,
            error_code="EXPORT_ERROR",
            details=error_details
        )


class LLMServiceError(ApplicationError):
    """Raised when LLM service operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="LLM_SERVICE_ERROR",
            details=details
        )


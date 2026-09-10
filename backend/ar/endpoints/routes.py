"""
API Routes - All endpoint handlers.
"""
import io
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Body
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel
from ar.services.chatbot_service import ChatbotService

from ar.models import (
    AggregateSummaryResponse,
    PartnerAgingSummaryResponse,
    InvoiceAgingResponse
)
from ar.services import APIServices
from ar.core.exceptions import (
    ApplicationError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DataNotFoundError,
    DataValidationError,
    DataProcessingError,
    ExportError,
    ForecastGenerationError
)

logger = logging.getLogger(__name__)


class ChatbotQueryRequest(BaseModel):
    """Request model for chatbot query endpoint."""
    query: str
    conversationHistory: Optional[List[Dict[str, str]]] = None


class APIRoutes:
    """Class containing all API route handlers."""
    
    def __init__(self, api_router: APIRouter, services: APIServices):
        """
        Initialize routes with router and services.
        
        Args:
            api_router: FastAPI APIRouter instance
            services: APIServices instance
        """
        self.router = api_router
        self.services = services
        self.chatbot_service = ChatbotService(self.services)
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes."""
        self.router.get("/")(self.root)
        self.router.get("/summary", response_model=AggregateSummaryResponse)(self.summary)
        self.router.get("/partners", response_model=List[PartnerAgingSummaryResponse])(self.partner_list)
        self.router.get("/invoices")(self.invoice_list)
        self.router.get("/invoices/{invoice_number}/history")(self.invoice_history)
        self.router.get("/insights")(self.partner_level_insights)
        self.router.get("/partners/{partner_code}/details")(self.partner_details)
        self.router.get("/forecast")(self.forecast_cashflow)
        self.router.get("/partners/export")(self.export_partners)
        self.router.get("/invoices/export")(self.export_invoices)
        self.router.post("/pipeline/upload")(self.upload_csv_files)
        self.router.get("/settings")(self.get_settings)
        self.router.put("/settings/cfo_dashboard_enabled")(self.set_cfo_dashboard_flag)
        self.router.put("/settings/llm_provider")(self.set_llm_provider)
        self.router.put("/settings/gemini_api_key")(self.set_gemini_api_key)
        self.router.get("/exceptions")(self.get_exceptions)
        self.router.post("/chatbot/query")(self.chatbot_query)
    
    async def root(self):
        logger.debug("Root endpoint accessed")
        """Root endpoint."""
        return {"service": "Cashflow API", "status": "running"}
    
    async def summary(self, period: str = "30d"):
        logger.info(f"Getting summary for period: {period}")
        """Get aggregate summary."""
        try:
            return self.services.get_summary()
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting summary: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def partner_list(self, period: str = "30d"):
        """Get partner list."""
        try:
            partners = self.services.get_partners()
            if not partners:
                raise DataNotFoundError(
                    message="No partner data available",
                    entity_type="partner"
                )
            return partners
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting partners: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def invoice_list(self):
        logger.info("Getting invoice list")
        """Get invoice list."""
        try:
            invoices = self.services.get_invoices()
            if not invoices:
                raise DataNotFoundError(
                    message="No invoice data available",
                    entity_type="invoice"
                )
            return invoices
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting invoices: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def partner_level_insights(self):
        logger.info("Getting partner-level risk insights")
        """Get partner-level risk insights."""
        try:
            return self.services.get_partner_insights()
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting partner insights: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def partner_details(self, partner_code: str):
        logger.info(f"Getting details for partner: {partner_code}")
        """Get detailed partner risk analysis."""
        try:
            details = self.services.get_partner_details(partner_code)
            if not details:
                raise DataNotFoundError(
                    message=f"Partner {partner_code} not found",
                    entity_type="partner",
                    entity_id=partner_code
                )
            return details
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting partner details: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def forecast_cashflow(
        self,
        days: int = Query(30, ge=1, le=365),
        partner_code: Optional[str] = None,
        scenario: Optional[str] = Query(None, description="What-if scenario identifier")
    ):
        """Generate cashflow forecast with optional what-if scenario."""
        try:
            return self.services.get_forecast(days=days, partner_code=partner_code, scenario=scenario)
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error generating forecast: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def export_partners(self, format: str = Query("excel", regex="^(excel|csv)$")):
        logger.info(f"Exporting partners data in format: {format}")
        """Export partners data."""
        try:
            content, filename, media_type = self.services.export_partners(format)
            if not content:
                raise DataNotFoundError(
                    message="No partner data available for export",
                    entity_type="partner"
                )
            
            if format == "excel":
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            else:  # CSV
                return Response(
                    content=content,
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error exporting partners: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def export_invoices(self, format: str = Query("excel", regex="^(excel|csv)$")):
        logger.info(f"Exporting invoices data in format: {format}")
        """Export invoices data."""
        try:
            content, filename, media_type = self.services.export_invoices(format)
            if not content:
                raise DataNotFoundError(
                    message="No invoice data available for export",
                    entity_type="invoice"
                )
            
            if format == "excel":
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            else:  # CSV
                return Response(
                    content=content,
                    media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error exporting invoices: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def upload_csv_files(
        self,
        files: List[UploadFile] = File(...),
        append: bool = Query(True)
    ):
        logger.info(f"Uploading {len(files)} CSV files with append={append}")
        """Upload and process CSV files."""
        if not files:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": "No files provided",
                    "details": {}
                }
            )
        
        try:
            result = self.services.upload_csv_files(files, append)
            return JSONResponse(content=result)
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": str(e),
                    "details": {}
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error processing CSV uploads: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def get_exceptions(
        self,
        severity: Optional[str] = Query(None, description="Filter by severity (High, Medium, All)"),
        exception_type: Optional[str] = Query(None, description="Filter by exception type"),
        age_bucket: Optional[str] = Query(None, description="Filter by age bucket (>30, >60)")
    ):
        logger.info(f"Getting exceptions with severity={severity}, type={exception_type}, age_bucket={age_bucket}")
        """Get anomalies and exceptions."""
        try:
            return self.services.get_exceptions(severity=severity, exception_type=exception_type, age_bucket=age_bucket)
        except ApplicationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.to_dict())
        except Exception as e:
            logger.error(f"Unexpected error getting exceptions: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def get_settings(self):

        """Get all feature flags/settings."""
        try:
            return self.services.get_settings()
        except Exception as e:
            logger.error(f"Unexpected error getting settings: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
    
    async def set_cfo_dashboard_flag(self, value: bool = Query(...)):
        """Set CFO dashboard feature flag."""
        try:
            result = self.services.set_feature_flag("cfo_dashboard_enabled", value)
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": str(e),
                    "details": {}
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error setting feature flag: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})

    async def set_llm_provider(self, provider: str = Query(..., description="LLM provider name (e.g., ollama, gemini)")):
        """Set the active LLM provider used for insights."""
        try:
            result = self.services.set_llm_provider(provider)
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": str(e),
                    "details": {}
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error setting LLM provider: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
        
    async def set_gemini_api_key(self, api_key: str = Query(..., description="Gemini API key")):
        """Set the Gemini API key and persist it to backend .env."""
        try:
            result = self.services.set_gemini_api_key(api_key)
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": str(e),
                    "details": {}
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error setting Gemini API key: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"})
        
    async def invoice_history(self, invoice_number: str):
        logger.info(f"Getting audit trail for invoice: {invoice_number}")
        """Get invoice payment history and audit trail."""
        try:
            # Calls the function we just added to services.py
            return self.services.get_invoice_history(invoice_number)
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def chatbot_query(self, request: ChatbotQueryRequest = Body(...)):
        logger.info(f"Processing chatbot query: {request.query[:100]}")
        
        try:
            query = request.query.strip()
            conversation_history = request.conversationHistory or []
            
            if not query:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "VALIDATION_ERROR",
                        "message": "Query cannot be empty",
                        "details": {}
                    }
                )
            
            # Process query through chatbot service
            result = self.chatbot_service.process_query(
                query=query,
                conversation_history=conversation_history
            )
            
            return JSONResponse(content=result)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chatbot query: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred processing your query",
                    "details": {"error": str(e)}
                }
            )
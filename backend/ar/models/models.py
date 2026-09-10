"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class AggregateSummaryResponse(BaseModel):
    total_invoice_amount: float
    overall_exposure: float
    total_allocated_amount: float
    total_payment_amount: float
    total_number_of_invoices: int
    total_number_of_partners: int


class PartnerAgingSummaryResponse(BaseModel):
    partner_code: Optional[str] = Field(
        None, description="Unique partner identifier"
    )
    partner_name: Optional[str] = Field(
        None, description="Partner legal or trade name"
    )
    total_invoice_amount: Optional[float] = Field(
        None, description="Total invoice amount as of run date"
    )
    total_due_amount: Optional[float] = Field(
        None, description="Total outstanding due amount as of run date"
    )
    total_allocated_amount: Optional[float] = Field(
        None, description="Total allocated amount against invoices"
    )
    total_payment_amount: Optional[float] = Field(
        None, description="Total payment amount received"
    )
    total_number_of_invoices: Optional[int] = Field(
        None, description="Count of invoices considered"
    )
    avg_overdue_days: Optional[float] = Field(
        None, description="Average days past due for overdue invoices"
    )
    aging_bucket: Optional[str] = Field(
        None,
        description="Aging classification bucket (e.g., CURRENT, 1–30, 31–60, 60+)"
    )
    total_overdue: Optional[float] = Field(
        None,
        description="Total overdue amount across all overdue invoices"
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class InvoiceAgingResponse(BaseModel):
    partner_code: Optional[str] = None
    allocated_amount: Optional[float] = None
    payment_amount: Optional[float] = None
    payment_ref: Optional[str] = None 
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None


class SummaryResponse(BaseModel):
    total_inflow: float
    total_outflow: float
    net_cashflow: float
    current_balance: float


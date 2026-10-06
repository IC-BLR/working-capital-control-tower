from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ap.routers import auth, dashboard, documents, invoices, purchase_orders, contracts, regulations, demo
from ap.demo_dataset import apply_demo_dataset

apply_demo_dataset()

app = FastAPI(
    title="AP Document Intelligence API",
    version="1.0.0",
    description="Multi-document OCR, invoice/PO/contract/regulation matching, exceptions, and approval workflow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3064", "http://127.0.0.1:3064"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(documents.router, prefix="/api/documents", tags=["Document Intake"])
app.include_router(documents.router, prefix="/api/intake", tags=["Compatibility Intake"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])
app.include_router(purchase_orders.router, prefix="/api/purchase-orders", tags=["Purchase Orders"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Contracts"])
app.include_router(regulations.router, prefix="/api/regulations", tags=["Regulations"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo Utilities"])


@app.get("/")
def root():
    return {"service": "ap-document-intelligence-api", "status": "running", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ap-document-intelligence-api",
        "modules": ["auth", "documents", "ocr", "live_invoice_feed", "invoices", "purchase_orders", "contracts", "regulations", "exceptions", "role_based_approvals"],
    }

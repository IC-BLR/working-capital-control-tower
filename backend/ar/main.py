"""Legacy AR entrypoint — prefer backend/main.py for the merged POC."""
import os

import uvicorn
from ar.server import api_router, startup_ar, shutdown_ar
from fastapi import FastAPI

app = FastAPI(title="AR Cashflow API (standalone)")


@app.on_event("startup")
async def _startup():
    startup_ar()
    app.include_router(api_router, prefix="/api/ar")


@app.on_event("shutdown")
async def _shutdown():
    shutdown_ar()


if __name__ == "__main__":
    uvicorn.run(
        "ar.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8064")),
        reload=True,
    )

"""
AR (Cashflow) FastAPI module — DuckDB lifecycle and route registration.
Mounted by the root app under /api/ar.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter
import duckdb
from typing import Optional, Callable

from ar.endpoints.routes import APIRoutes
from ar.services import APIServices
from ar.db import DatabaseInitializer

# ============================================================
# Paths & Environment
# ============================================================

ROOT_DIR = Path(__file__).parent.parent  # backend/
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DUCKDB_PATH = str(ROOT_DIR / "payment_allocation.duckdb")
LOG_FILE = DATA_DIR / "app.log"

load_dotenv(ROOT_DIR / ".env")

# ============================================================
# Logging Configuration
# ============================================================

def setup_logging():
    """Configure logging with file and console handlers."""
    root_logger = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        return

    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"AR module logging initialized. Log file: {LOG_FILE}")

# ============================================================
# Router (prefix applied by root app as /api/ar)
# ============================================================

api_router = APIRouter()

duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None
_routes_registered = False


def get_duckdb():
    """Get DuckDB connection."""
    logger.debug("Acquiring DuckDB connection")
    if duckdb_conn is None:
        raise RuntimeError("DuckDB not initialized")
    return duckdb_conn


def startup_ar():
    """Initialize DuckDB and register AR routes on api_router."""
    global duckdb_conn, _routes_registered

    initializer = DatabaseInitializer(DUCKDB_PATH)
    duckdb_conn = initializer.initialize()
    logger.info(f"DuckDB initialized at {DUCKDB_PATH}")

    if not _routes_registered:
        services = APIServices(get_duckdb)
        APIRoutes(api_router, services)
        _routes_registered = True
        logger.info("AR API routes registered")


def shutdown_ar():
    """Cleanup DuckDB on shutdown."""
    global duckdb_conn
    if duckdb_conn:
        duckdb_conn.close()
        duckdb_conn = None
    logger.info("AR shutdown complete")

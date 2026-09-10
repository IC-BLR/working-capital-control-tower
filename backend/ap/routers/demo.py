from __future__ import annotations

from fastapi import APIRouter

from ap.demo_dataset import apply_demo_dataset
from ap.store import ACTIVE_TOKENS, DOCUMENTS, INVOICE_FEED_EVENTS

router = APIRouter()


@router.post('/reset')
def reset_demo(clear_sessions: bool = False):
    """Reset in-memory demo data to the curated customer-demo baseline."""
    DOCUMENTS.clear()
    INVOICE_FEED_EVENTS.clear()
    apply_demo_dataset()
    if clear_sessions:
        ACTIVE_TOKENS.clear()
    return {
        'status': 'reset',
        'message': 'Demo data reset to curated baseline. Documents and live-feed events were cleared.',
        'clearSessions': clear_sessions,
    }


@router.get('/state')
def demo_state():
    from ap.store import CONTRACTS, INVOICES, PURCHASE_ORDERS, REGULATIONS
    return {
        'invoices': len(INVOICES),
        'purchaseOrders': len(PURCHASE_ORDERS),
        'contracts': len(CONTRACTS),
        'regulations': len(REGULATIONS),
        'documents': len(DOCUMENTS),
        'feedEvents': len(INVOICE_FEED_EVENTS),
    }

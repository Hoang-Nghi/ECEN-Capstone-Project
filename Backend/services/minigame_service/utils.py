"""
Shared helpers for minigames: time windows, Firestore helpers, and transaction queries.
Keeps game files small and testable.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional


def get_db():
    """Return a Firestore client, initializing Firebase if needed (safe for Cloud Run)."""
    # Initialize Firebase Admin only once per container
    if not firebase_admin._apps:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            # On Cloud Run, default credentials (attached service account) will work
            firebase_admin.initialize_app()
    return firestore.client()


def start_of_week_utc(dt: Optional[datetime] = None) -> datetime:
    """Compute Monday 00:00:00 UTC of the current week."""
    now = dt or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def to_yyyy_mm_dd(dt: datetime) -> str:
    """Standardize date strings for queries and UI consistency."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def user_transactions_this_week(
    db, user_id: str, category_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Pull this week's transactions from Firestore."""
    sow = start_of_week_utc()
    sow_str = to_yyyy_mm_dd(sow)
    tx_ref = (
        db.collection("users")
          .document(user_id)
          .collection("transactions")
          .where("date", ">=", sow_str)
    )
    docs = tx_ref.stream()
    txns = []
    for d in docs:
        data = d.to_dict() or {}
        cats = [c.lower() for c in data.get("category", [])] if data.get("category") else []
        if category_key:
            if category_key.lower() in cats:
                txns.append(data)
        else:
            txns.append(data)
    return txns


def total_amount(txns: List[Dict[str, Any]]) -> float:
    """Sum amounts with basic safety."""
    return float(sum(float(t.get("amount", 0.0)) for t in txns))

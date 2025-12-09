# services/analytics.py
"""
Analytics service for spending insights, trends, and transaction analysis.
Provides data for charts, summaries, and budget tracking.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from firebase_admin import firestore
from services.firebase import get_db

# ============================================================================
# Helper Functions
# ============================================================================

def _date_to_str(dt: datetime) -> str:
    """Convert datetime to YYYY-MM-DD string."""
    return dt.strftime("%Y-%m-%d")

def _start_of_day(dt: datetime) -> datetime:
    """Get start of day (00:00:00)."""
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)

def _start_of_week(dt: datetime) -> datetime:
    """Get start of week (Monday 00:00:00)."""
    monday = dt - timedelta(days=dt.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)

def _start_of_month(dt: datetime) -> datetime:
    """Get start of month (1st day 00:00:00)."""
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)

def _get_period_label(period_start: datetime, view: str) -> str:
    """Generate human-readable label for a time period."""
    if view == "day":
        return period_start.strftime("%b %d")  # "Nov 10"
    elif view == "week":
        return period_start.strftime("%b %d")  # "Nov 10" (Monday of week)
    elif view == "month":
        return period_start.strftime("%b %Y")  # "Nov 2025"
    return _date_to_str(period_start)

def _fetch_transactions(uid: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Fetch transactions in date range [start_date, end_date).
    Returns list of transaction dicts with all fields.
    """
    db = get_db()
    col = db.collection("users").document(uid).collection("transactions")
    
    q = (col.where("date", ">=", start_date)
            .where("date", "<", end_date)
            .order_by("date", direction=firestore.Query.DESCENDING))
    
    docs = list(q.stream())
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

def _normalize_category(t: Dict[str, Any]) -> str:
    """
    Extract and normalize primary category from transaction.
    Maps Plaid PFC categories to user-friendly display categories.
    """
    # Get raw category string (keep upper case for matching)
    pfc_primary = (t.get("pfc_primary") or "").strip().upper()
    
    if not pfc_primary:
        raw = t.get("raw") or {}
        raw_pfc = raw.get("personal_finance_category")
        if isinstance(raw_pfc, dict):
            pfc_primary = (raw_pfc.get("primary") or "").strip().upper()
    
    if not pfc_primary:
        category_path = (t.get("category_path") or "").strip()
        if category_path:
            parts = category_path.split(">")
            if parts:
                pfc_primary = parts[0].strip().upper()
    
    # If still nothing, return Other early
    if not pfc_primary:
        return "Other"
    
    # Map Plaid categories to display categories
    category_map = {
        # Food & Dining
        "FOOD_AND_DRINK": "Food & Dining",
        "FOOD_AND_DRINK_COFFEE": "Food & Dining",           # ← ADD
        "FOOD_AND_DRINK_RESTAURANT": "Food & Dining",       # ← ADD
        "FOOD_AND_DRINK_FAST_FOOD": "Food & Dining",        # ← ADD
        "FOOD_AND_DRINK_GROCERIES": "Food & Dining",        # ← ADD (or separate as "Groceries")
        
        # Shopping
        "GENERAL_MERCHANDISE": "Shopping",
        "GENERAL_MERCHANDISE_SUPERSTORES": "Shopping",      # ← ADD (H-E-B, Walmart, Whole Foods)
        "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES": "Shopping",  # ← ADD (Amazon)
        "GENERAL_MERCHANDISE_DISCOUNT_STORES": "Shopping",  # ← ADD (Target)
        "GENERAL_MERCHANDISE_ELECTRONICS": "Shopping",      # ← ADD (Best Buy)
        
        # Transportation
        "TRANSPORTATION": "Transportation",
        "TRANSPORTATION_TAXIS_AND_RIDE_SHARES": "Transportation",  # ← ADD (Uber, Lyft)
        "TRANSPORTATION_GAS": "Transportation",                     # ← ADD (Shell)
        
        # Entertainment
        "ENTERTAINMENT": "Entertainment",
        "ENTERTAINMENT_MOVIES_AND_MUSIC": "Entertainment",   # ← ADD (AMC)
        "ENTERTAINMENT_MUSIC_AND_AUDIO": "Entertainment",    # ← ADD (Spotify)
        "ENTERTAINMENT_TV_AND_MOVIES": "Entertainment",      # ← ADD (Netflix)
        
        # Travel
        "TRAVEL": "Travel",
        "TRAVEL_LODGING": "Travel",                          # ← ADD (Airbnb)
        "TRAVEL_FLIGHTS": "Travel",                          # ← ADD (Delta)
        
        # Bills & Utilities
        "LOAN_PAYMENTS": "Bills & Utilities",
        "RENT_AND_UTILITIES": "Bills & Utilities",
        "UTILITIES": "Bills & Utilities",
        
        # Income
        "INCOME": "Income",
        
        # Transfers & Fees
        "TRANSFER_IN": "Transfer",
        "TRANSFER_OUT": "Transfer",
        "BANK_FEES": "Fees",
        }
    
    # Try exact match first
    if pfc_primary in category_map:
        return category_map[pfc_primary]
    
    # Try prefix matching for variations
    # This handles cases like "FOOD_AND_DRINK_SOMETHING_NEW"
    for plaid_cat, display_cat in category_map.items():
        if pfc_primary.startswith(plaid_cat):
            return display_cat
    
    # If nothing matched, log it (for debugging) and return Other
    print(f"[analytics] Unmapped category: {pfc_primary}")
    return "Other"

def _get_period_boundaries(view: str, periods: int) -> List[Tuple[datetime, datetime, str]]:
    """
    Get list of (start, end, label) tuples for each period.
    Returns periods in chronological order (oldest to newest).
    
    Args:
        view: "day", "week", or "month"
        periods: number of periods to return
    
    Returns:
        List of (period_start, period_end, label)
    """
    now = datetime.now(timezone.utc)
    boundaries = []
    
    if view == "day":
        for i in range(periods - 1, -1, -1):  # Count backwards
            day_start = _start_of_day(now - timedelta(days=i))
            day_end = day_start + timedelta(days=1)
            label = _get_period_label(day_start, view)
            boundaries.append((day_start, day_end, label))
    
    elif view == "week":
        for i in range(periods - 1, -1, -1):
            week_start = _start_of_week(now - timedelta(weeks=i))
            week_end = week_start + timedelta(days=7)
            label = _get_period_label(week_start, view)
            boundaries.append((week_start, week_end, label))
    
    elif view == "month":
        for i in range(periods - 1, -1, -1):
            # Go back i months
            target_month = now.month - i
            target_year = now.year
            while target_month < 1:
                target_month += 12
                target_year -= 1
            
            month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
            # Next month
            next_month = target_month + 1
            next_year = target_year
            if next_month > 12:
                next_month = 1
                next_year += 1
            month_end = datetime(next_year, next_month, 1, tzinfo=timezone.utc)
            
            label = _get_period_label(month_start, view)
            boundaries.append((month_start, month_end, label))
    
    return boundaries

# ============================================================================
# Public API Functions
# ============================================================================

def get_spending_over_time(uid: str, view: str = "week", periods: int = 4) -> Dict[str, Any]:
    """
    Get spending trend over time for charting.
    
    Args:
        uid: User ID
        view: "day", "week", or "month"
        periods: Number of periods to show (default 4)
    
    Returns:
        {
            "ok": true,
            "view": "week",
            "periods": 4,
            "data": [
                {"label": "Nov 4", "amount": 245.50},
                {"label": "Nov 11", "amount": 189.30},
                ...
            ],
            "total": 1234.56
        }
    """
    # Validate inputs
    if view not in ["day", "week", "month"]:
        return {"ok": False, "error": "view must be 'day', 'week', or 'month'"}
    
    periods = max(1, min(periods, 52))  # Clamp between 1 and 52
    
    # Get period boundaries
    boundaries = _get_period_boundaries(view, periods)
    
    # Fetch all transactions in range
    first_start = boundaries[0][0]
    last_end = boundaries[-1][1]
    start_date_str = _date_to_str(first_start)
    end_date_str = _date_to_str(last_end)
    
    transactions = _fetch_transactions(uid, start_date_str, end_date_str)
    
    # Group by period
    period_spending: Dict[str, float] = {}
    label_map: Dict[str, str] = {}
    
    for period_start, period_end, label in boundaries:
        period_key = _date_to_str(period_start)
        period_spending[period_key] = 0.0
        label_map[period_key] = label

    # Group by category
    category_spending: Dict[str, float] = defaultdict(float)
    
    for t in transactions:
        amount = float(t.get("amount", 0) or 0)
        if amount <= 0:
            continue
        
        category = _normalize_category(t)
        
        # Skip transfers and fees for spending analysis
        if category in ["Transfer", "Fees", "Income"]:
            continue
            
        category_spending[category] += amount
    
    # Sum transactions into periods
    for t in transactions:
        tx_date_str = t.get("date")
        if not tx_date_str:
            continue
        
        try:
            tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            amount = float(t.get("amount", 0) or 0)
            
            # Find which period this transaction belongs to
            for period_start, period_end, _ in boundaries:
                if period_start <= tx_date < period_end:
                    period_key = _date_to_str(period_start)
                    period_spending[period_key] += amount
                    break
        except Exception:
            continue
    
    # Build response data
    data = []
    total = 0.0
    
    for period_start, _, _ in boundaries:
        period_key = _date_to_str(period_start)
        amount = round(period_spending.get(period_key, 0.0), 2)
        total += amount
        
        data.append({
            "label": label_map[period_key],
            "amount": amount
        })
    
    return {
        "ok": True,
        "view": view,
        "periods": periods,
        "data": data,
        "total": round(total, 2)
    }


def get_spending_by_category(uid: str, days: int = 30) -> Dict[str, Any]:
    """
    Get spending breakdown by category.
    
    Args:
        uid: User ID
        days: Number of days to look back (default 30)
    
    Returns:
        {
            "ok": true,
            "days": 30,
            "categories": [
                {"name": "FOOD_AND_DRINK", "amount": 234.56, "percentage": 35.2},
                {"name": "TRANSPORTATION", "amount": 156.78, "percentage": 23.5},
                ...
            ],
            "total": 667.89
        }
    """
    # Fetch transactions
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    start_date_str = _date_to_str(start_date)
    end_date_str = _date_to_str(now + timedelta(days=1))
    
    transactions = _fetch_transactions(uid, start_date_str, end_date_str)
    
    # Group by category
    category_spending: Dict[str, float] = defaultdict(float)
    unmapped_count = 0
    
    for t in transactions:
        amount = float(t.get("amount", 0) or 0)
        if amount <= 0:
            continue
        
        category = _normalize_category(t)
        
        # Debug: track unmapped
        if category == "Other":
            unmapped_count += 1
            print(f"[analytics] Unmapped transaction: {t.get('merchant_name')} - {t.get('pfc_primary')}")
        
        # Skip transfers/fees
        if category in ["Transfer", "Fees", "Income"]:
            continue
            
        category_spending[category] += amount
    
    print(f"[analytics] Total unmapped: {unmapped_count}/{len(transactions)}")
    
    # Calculate totals and percentages
    total = sum(category_spending.values())
    
    categories = []
    for name, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total * 100) if total > 0 else 0
        categories.append({
            "name": name,
            "amount": round(amount, 2),
            "percentage": round(percentage, 1)
        })
    
    return {
        "ok": True,
        "days": days,
        "categories": categories,
        "total": round(total, 2)
    }


def get_recent_transactions(uid: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get recent transactions for display.
    
    Args:
        uid: User ID
        limit: Maximum number of transactions to return (default 20)
    
    Returns:
        {
            "ok": true,
            "transactions": [
                {
                    "id": "...",
                    "date": "2025-11-15",
                    "merchant_name": "Starbucks",
                    "amount": 5.43,
                    "category": "FOOD_AND_DRINK",
                    "logo_url": "https://...",
                },
                ...
            ],
            "count": 20
        }
    """
    db = get_db()
    col = db.collection("users").document(uid).collection("transactions")
    
    # Get recent transactions (no date filter, just order by date)
    q = col.order_by("date", direction=firestore.Query.DESCENDING).limit(limit)
    docs = list(q.stream())
    
    transactions = []
    for d in docs:
        data = d.to_dict() or {}
        raw = data.get("raw") or {}
        
        # Get merchant name
        merchant = (
            data.get("merchant_name")
            or raw.get("merchant_name")
            or data.get("name")
            or "Unknown Merchant"
        )
        
        # Get category
        category = _normalize_category(data)
        
        # Get logo
        cps = raw.get("counterparties") or []
        logo_url = raw.get("logo_url") or (cps[0].get("logo_url") if cps else None)
        
        transactions.append({
            "id": d.id,
            "date": data.get("date"),
            "merchant_name": merchant,
            "amount": round(float(data.get("amount", 0) or 0), 2),
            "category": category,
            "logo_url": logo_url,
            "pending": data.get("pending", False)
        })
    
    return {
        "ok": True,
        "transactions": transactions,
        "count": len(transactions)
    }


def get_spending_summary(uid: str) -> Dict[str, Any]:
    """
    Get overall spending summary for the user.
    
    Returns:
        {
            "ok": true,
            "this_week": 245.67,
            "this_month": 1234.56,
            "last_month": 1098.43,
            "average_daily": 45.23,
            "top_category": {
                "name": "FOOD_AND_DRINK",
                "amount": 456.78
            }
        }
    """
    now = datetime.now(timezone.utc)
    
    # This week (Monday to now)
    week_start = _start_of_week(now)
    week_txns = _fetch_transactions(uid, _date_to_str(week_start), _date_to_str(now + timedelta(days=1)))
    this_week = sum(float(t.get("amount", 0) or 0) for t in week_txns)
    
    # This month
    month_start = _start_of_month(now)
    month_txns = _fetch_transactions(uid, _date_to_str(month_start), _date_to_str(now + timedelta(days=1)))
    this_month = sum(float(t.get("amount", 0) or 0) for t in month_txns)
    
    # Last month
    last_month_start = _start_of_month(now - timedelta(days=32))  # Go back to previous month
    last_month_end = month_start
    last_month_txns = _fetch_transactions(uid, _date_to_str(last_month_start), _date_to_str(last_month_end))
    last_month = sum(float(t.get("amount", 0) or 0) for t in last_month_txns)
    
    # Average daily (last 30 days)
    days_30_ago = now - timedelta(days=30)
    recent_txns = _fetch_transactions(uid, _date_to_str(days_30_ago), _date_to_str(now + timedelta(days=1)))
    total_30_days = sum(float(t.get("amount", 0) or 0) for t in recent_txns)
    average_daily = total_30_days / 30
    
    # Top category (last 30 days)
    category_spending: Dict[str, float] = defaultdict(float)
    for t in recent_txns:
        amount = float(t.get("amount", 0) or 0)
        if amount > 0:
            category = _normalize_category(t)
            category_spending[category] += amount
    
    top_category = None
    if category_spending:
        top_cat_name = max(category_spending.items(), key=lambda x: x[1])[0]
        top_category = {
            "name": top_cat_name,
            "amount": round(category_spending[top_cat_name], 2)
        }
    
    return {
        "ok": True,
        "this_week": round(this_week, 2),
        "this_month": round(this_month, 2),
        "last_month": round(last_month, 2),
        "average_daily": round(average_daily, 2),
        "top_category": top_category
    }


def get_budget_progress(uid: str) -> Dict[str, Any]:
    """
    Get budget progress for current month.
    
    This is simplified - assumes a default budget of $1000/month.
    You can enhance this to fetch user's custom budget from Firestore.
    
    Returns:
        {
            "ok": true,
            "currently_spent": 456.78,
            "should_have_spent_by_now": 333.33,  # Based on days elapsed
            "maximum_to_spend_this_month": 1000.00,
            "percentage_used": 45.7,
            "days_remaining": 16,
            "on_track": true
        }
    """
    now = datetime.now(timezone.utc)
    
    # Get this month's spending
    month_start = _start_of_month(now)
    month_txns = _fetch_transactions(uid, _date_to_str(month_start), _date_to_str(now + timedelta(days=1)))
    currently_spent = sum(float(t.get("amount", 0) or 0) for t in month_txns)
    
    # Calculate budget metrics based on last month's spending
    # Goal: Spend less than or equal to last month
    last_month_start = _start_of_month(now - timedelta(days=32))  # Go back to previous month
    last_month_end = month_start  # Start of current month = end of last month
    last_month_txns = _fetch_transactions(uid, _date_to_str(last_month_start), _date_to_str(last_month_end))
    last_month_spending = sum(float(t.get("amount", 0) or 0) for t in last_month_txns)
    
    # Set monthly limit to last month's spending (or default to $1000 if no history)
    maximum_to_spend_this_month = last_month_spending if last_month_spending > 0 else 1000.0
    
    # Calculate days elapsed and remaining
    days_in_month = 30  # Simplified
    current_day = now.day
    days_elapsed = current_day
    days_remaining = days_in_month - days_elapsed
    
    # Calculate "should have spent by now" (prorated)
    should_have_spent_by_now = maximum_to_spend_this_month * (days_elapsed / days_in_month)
    
    # Percentage used
    percentage_used = (currently_spent / maximum_to_spend_this_month * 100) if maximum_to_spend_this_month > 0 else 0
    
    # On track? (spending less than or equal to prorated budget)
    on_track = currently_spent <= should_have_spent_by_now
    
    return {
        "ok": True,
        "currently_spent": round(currently_spent, 2),
        "should_have_spent_by_now": round(should_have_spent_by_now, 2),
        "maximum_to_spend_this_month": round(maximum_to_spend_this_month, 2),
        "percentage_used": round(percentage_used, 1),
        "days_remaining": days_remaining,
        "on_track": on_track
    }
# routes/analytics.py
"""
Analytics API routes for spending insights and trends.
"""
from flask import Blueprint, request, jsonify
from auth_middleware import require_auth
from services import analytics

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/spending/by-category")
@require_auth
def spending_by_category():
    """
    GET /api/analytics/spending/by-category?days=30
    
    Get spending breakdown by category.
    """
    uid = request.user["uid"]
    days = int(request.args.get("days", 30))
    return jsonify(analytics.get_spending_by_category(uid, days)), 200


@analytics_bp.get("/spending/over-time")
@require_auth
def spending_over_time():
    """
    GET /api/analytics/spending/over-time?view=week&periods=4
    
    Get spending trend over time (day/week/month).
    """
    uid = request.user["uid"]
    view = request.args.get("view", "week")  # day, week, or month
    periods = int(request.args.get("periods", 4))
    return jsonify(analytics.get_spending_over_time(uid, view, periods)), 200


@analytics_bp.get("/transactions/recent")
@require_auth
def recent_transactions():
    """
    GET /api/analytics/transactions/recent?limit=20
    
    Get recent transactions.
    """
    uid = request.user["uid"]
    limit = int(request.args.get("limit", 20))
    return jsonify(analytics.get_recent_transactions(uid, limit)), 200

 
@analytics_bp.get("/spending/summary")
@require_auth
def spending_summary():
    """
    GET /api/analytics/spending/summary
    
    Get overall spending summary.
    """
    uid = request.user["uid"]
    return jsonify(analytics.get_spending_summary(uid)), 200


@analytics_bp.get("/budget/progress")
@require_auth
def budget_progress():
    """
    GET /api/analytics/budget/progress
    
    Get budget progress for current month (for Overview bar chart).
    Returns: currently_spent, should_have_spent_by_now, maximum_to_spend_this_month
    """
    uid = request.user["uid"]
    return jsonify(analytics.get_budget_progress(uid)), 200

# Add this debug endpoint temporarily in routes/analytics.py

@analytics_bp.get("/debug/categories")
@require_auth
def debug_categories():
    """Debug endpoint to see raw category data"""
    uid = request.user["uid"]
    
    # Get recent transactions
    from services.firebase import get_db
    from datetime import datetime, timedelta, timezone
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    db = get_db()
    col = db.collection("users").document(uid).collection("transactions")
    docs = col.where("date", ">=", start_date).where("date", "<", end_date).stream()
    
    categories = {}
    for d in docs:
        data = d.to_dict() or {}
        pfc = data.get("pfc_primary") or "MISSING"
        categories[pfc] = categories.get(pfc, 0) + 1
    
    return jsonify({
        "raw_categories": categories,
        "total_transactions": sum(categories.values())
    }), 200
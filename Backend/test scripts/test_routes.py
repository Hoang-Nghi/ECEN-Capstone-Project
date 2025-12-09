# test_routes.py (temporary - for development only!)
"""
DEVELOPMENT ONLY - Remove before production!
Allows testing games without Firebase auth.
"""

from flask import Blueprint, request, jsonify
from services.minigame_service import spend_detective as detective
from services.minigame_service import smart_saver_quiz as quiz

test_bp = Blueprint("test", __name__)

# Hardcode user1's UID (get this from Firebase Console)
TEST_USER_ID = "user1"  # Replace with actual user1 UID from Firebase

@test_bp.post("/api/test/spend-detective/start")
def test_detective_start():
    """Test Spend Detective without auth"""
    return jsonify(detective.start_round(TEST_USER_ID)), 200

@test_bp.post("/api/test/spend-detective/submit")
def test_detective_submit():
    """Test Spend Detective submit without auth"""
    data = request.get_json(silent=True) or {}
    selected_ids = data.get("selected_ids") or []
    return jsonify(detective.submit_guess(TEST_USER_ID, selected_ids)), 200

@test_bp.get("/api/test/spend-detective/state")
def test_detective_state():
    """Test Spend Detective state without auth"""
    return jsonify(detective.get_state(TEST_USER_ID)), 200

@test_bp.post("/api/test/quiz/new")
def test_quiz_new():
    """Test Smart Saver Quiz without auth"""
    return jsonify(quiz.new_set(TEST_USER_ID)), 200

@test_bp.post("/api/test/quiz/submit")
def test_quiz_submit():
    """Test Smart Saver Quiz submit without auth"""
    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or []
    return jsonify(quiz.submit(TEST_USER_ID, answers)), 200

@test_bp.get("/api/test/quiz/state")
def test_quiz_state():
    """Test Smart Saver Quiz state without auth"""
    return jsonify(quiz.get_state(TEST_USER_ID)), 200

# Helper to check user1's transactions
@test_bp.get("/api/test/user1/transactions")
def test_user1_transactions():
    """Check if user1 has transactions"""
    from services.firebase import get_db
    from datetime import datetime, timedelta
    
    db = get_db()
    tx_col = db.collection("users").document(TEST_USER_ID).collection("transactions")
    
    # Get last 30 days
    week_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    q = tx_col.where("date", ">=", week_start).order_by("date", direction="DESCENDING")
    
    txns = []
    for doc in q.stream():
        data = doc.to_dict()
        txns.append({
            "id": doc.id,
            "date": data.get("date"),
            "name": data.get("name"),
            "amount": data.get("amount"),
            "pfc_primary": data.get("pfc_primary"),
        })
    
    return jsonify({
        "user_id": TEST_USER_ID,
        "transaction_count": len(txns),
        "transactions": txns[:20]  # First 20
    }), 200

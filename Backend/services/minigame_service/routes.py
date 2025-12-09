# services/minigame_service/routes.py
from flask import Blueprint, request, jsonify
from auth_middleware import require_auth

from . import financial_categories as fin_cat
from . import spend_detective as detective
from . import smart_saver_quiz as quiz
from . import progression

minigame_bp = Blueprint("minigame_bp", __name__)

# -------------------- Financial Categories --------------------

@minigame_bp.post("/financial-categories/start")
@require_auth
def fin_cat_start():
    uid = request.user["uid"]
    return jsonify(fin_cat.start_round(uid)), 200

@minigame_bp.post("/financial-categories/match")
@require_auth
def fin_cat_match():
    uid = request.user["uid"]
    data = request.get_json(silent=True) or {}
    category_id = data.get("category_id")
    amount_id = data.get("amount_id")
    if not (category_id and amount_id):
        return jsonify({"ok": False, "error": "category_id and amount_id required"}), 400
    return jsonify(fin_cat.submit_match(uid, category_id, amount_id)), 200

@minigame_bp.get("/financial-categories/state")
@require_auth
def fin_cat_state():
    uid = request.user["uid"]
    return jsonify(fin_cat.get_state(uid)), 200

# -------------------- Spend Detective --------------------

@minigame_bp.route("/spend-detective/start", methods=["GET", "POST"])
@require_auth
def spend_detective_start():
    uid = request.user["uid"]
    return jsonify(detective.start_round(uid)), 200

@minigame_bp.route("/spend-detective/submit", methods=["GET", "POST"])
@require_auth
def spend_detective_submit():
    uid = request.user["uid"]
    data = request.get_json(silent=True) or {}
    selected_ids = data.get("selected_ids") or []
    if not isinstance(selected_ids, list):
        return jsonify({"ok": False, "error": "selected_ids must be an array"}), 400
    return jsonify(detective.submit_guess(uid, selected_ids)), 200

@minigame_bp.get("/spend-detective/state")
@require_auth
def spend_detective_state():
    uid = request.user["uid"]
    return jsonify(detective.get_state(uid)), 200

# -------------------- Smart Saver Quiz --------------------

@minigame_bp.post("/quiz/new")
@require_auth
def quiz_new():
    """Start a new quiz set."""
    uid = request.user["uid"]
    try:
        result = quiz.new_set(uid)
        return jsonify(result), 200
    except Exception as e:
        print(f"[quiz/new] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@minigame_bp.post("/quiz/answer")
@require_auth
def quiz_answer():
    """
    Answer a single question and get immediate feedback.
    
    Request body:
    {
        "question_id": "q1",
        "selected_index": 2
    }
    
    Response:
    {
        "ok": true,
        "is_correct": false,
        "correct_index": 1,
        "selected_index": 2,
        "explanation": "...",
        "xp_earned": 0,
        "questions_answered": 1,
        "total_questions": 5,
        "quiz_complete": false
    }
    """
    uid = request.user["uid"]
    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    selected_index = data.get("selected_index")
    
    print(f"[quiz/answer] Received request from {uid}: question_id={question_id}, selected_index={selected_index}")
    
    if question_id is None or selected_index is None:
        print(f"[quiz/answer] Missing parameters: question_id={question_id}, selected_index={selected_index}")
        return jsonify({"ok": False, "error": "question_id and selected_index required"}), 400
    
    try:
        result = quiz.answer_question(uid, question_id, int(selected_index))
        print(f"[quiz/answer] Success for {uid}: is_correct={result.get('is_correct')}, correct_index={result.get('correct_index')}")
        return jsonify(result), 200
    except Exception as e:
        print(f"[quiz/answer] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@minigame_bp.post("/quiz/complete")
@require_auth
def quiz_complete():
    """
    Finalize quiz after all questions answered.
    
    Response:
    {
        "ok": true,
        "score": 3,
        "total": 5,
        "accuracy": 0.6,
        "xp_earned": 60,
        "total_xp": 560,
        "level": 8,
        "streak": 5,
        ...
    }
    """
    uid = request.user["uid"]
    print(f"[quiz/complete] Request from {uid}")
    
    try:
        result = quiz.complete_quiz(uid)
        print(f"[quiz/complete] Success for {uid}: score={result.get('score')}/{result.get('total')}")
        return jsonify(result), 200
    except Exception as e:
        print(f"[quiz/complete] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@minigame_bp.post("/quiz/submit")
@require_auth
def quiz_submit():
    """
    DEPRECATED: Batch submission of all answers.
    Use /quiz/answer for immediate feedback instead.
    Kept for backward compatibility.
    """
    uid = request.user["uid"]
    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or []
    if not isinstance(answers, list):
        return jsonify({"ok": False, "error": "answers must be an array"}), 400

    try:
        result = quiz.submit(uid, answers)
        return jsonify(result), 200
    except Exception as e:
        print(f"[quiz/submit] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@minigame_bp.get("/quiz/state")
@require_auth
def quiz_state():
    """Get current quiz state for user."""
    uid = request.user["uid"]
    try:
        result = quiz.get_state(uid)
        return jsonify(result), 200
    except Exception as e:
        print(f"[quiz/state] Error for {uid}:", e)
        return jsonify({"ok": False, "error": str(e)}), 500
    
@minigame_bp.get("/quiz/test")
def quiz_test():
    """Public test endpoint to verify quiz backend is accessible."""
    return jsonify({"ok": True, "message": "Smart Saver Quiz backend is running"}), 200

# -------------------- User Profile / Progression --------------------

@minigame_bp.get("/profile")
@require_auth
def user_profile():
    """
    Get user's overall progression (XP, rank, level).
    Used for the UI bubble on Games page.
    
    Response:
    {
        "ok": true,
        "total_xp": 340,
        "level": 26,
        "rank": {
            "name": "Penny Pincher",
            "color": "copper",
            "tier": "bronze",
            "progress": 0.68,
            "xp_in_rank": 340,
            "xp_for_next_rank": 500
        },
        "next_rank": {
            "name": "Savvy Saver",
            "color": "bronze",
            "tier": "bronze",
            "xp_needed": 160
        },
        "next_level": {
            "level": 27,
            "xp_needed": 114
        },
        "games_played": 12
    }
    """
    uid = request.user["uid"]
    try:
        result = progression.get_profile(uid)
        return jsonify(result), 200
    except Exception as e:
        print(f"[profile] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@minigame_bp.get("/ranks")
def get_ranks():
    """
    Get list of all available ranks (public endpoint).
    Useful for showing rank progression UI.
    
    Response:
    {
        "ok": true,
        "ranks": [
            {"name": "Penny Pincher", "color": "copper", "tier": "bronze", "threshold": 0},
            {"name": "Savvy Saver", "color": "bronze", "tier": "bronze", "threshold": 500},
            ...
        ]
    }
    """
    return jsonify({
        "ok": True,
        "ranks": progression.get_rank_list()
    }), 200


# -------------------- Global Stats --------------------

@minigame_bp.get("/stats")
@require_auth
def minigame_stats():
    """
    Get overall stats including unified progression and individual game states.
    
    Response includes:
    - Unified progression (XP, level, rank)
    - Individual game states (streaks, can_play status)
    """
    uid = request.user["uid"]
    
    try:
        # Get unified progression
        profile = progression.get_profile(uid)
        
        # Get individual game states
        fin_cat_state = fin_cat.get_state(uid)
        detective_state = detective.get_state(uid)
        quiz_state_data = quiz.get_state(uid)
        
        return jsonify({
            "ok": True,
            "progression": {
                "total_xp": profile.get("total_xp", 0),
                "level": profile.get("level", 1),
                "rank": profile.get("rank", {}),
                "next_rank": profile.get("next_rank"),
                "next_level": profile.get("next_level"),
                "games_played": profile.get("games_played", 0)
            },
            "games": {
                "financial_categories": {
                    "streak": fin_cat_state.get("streak", 0),
                    "has_active_round": fin_cat_state.get("has_active_round", False),
                },
                "spend_detective": {
                    "streak": detective_state.get("streak", 0),
                    "can_play": detective_state.get("can_play_this_week", True),
                    "has_active_round": detective_state.get("has_active_round", False),
                },
                "smart_saver_quiz": {
                    "streak": quiz_state_data.get("streak", 0),
                    "difficulty": quiz_state_data.get("difficulty", "basic"),
                    "can_play": quiz_state_data.get("can_play_this_week", True),
                    "has_active_round": quiz_state_data.get("has_active_round", False),
                },
            },
        }), 200
    except Exception as e:
        print(f"[stats] Error for {uid}:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500
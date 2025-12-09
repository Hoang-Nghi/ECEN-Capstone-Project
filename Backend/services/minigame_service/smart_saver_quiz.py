# services/minigame_service/smart_saver_quiz.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
import math
import random

from firebase_admin import firestore
from .utils import get_db, to_yyyy_mm_dd, start_of_week_utc
from . import progression

# ============================================================================
# Config
# ============================================================================
QUESTIONS_PER_ROUND = 5
MIN_TRANSACTIONS_REQUIRED = 5
DIFFICULTY_LEVELS = ["basic", "intermediate", "advanced"]
XP_PER_CORRECT = 20
FULL_ROUND_XP = 100  # For low-data weeks
ADVANCE_THRESHOLD = 0.80
DEMOTE_THRESHOLD = 0.40
STREAK_ACCURACY_THRESHOLD = 0.60
HISTORY_WINDOW = 5
MAX_LEVEL = 100

# ============================================================================
# Firestore Helpers
# ============================================================================
def _game_ref(uid: str):
    return get_db().collection("users").document(uid).collection("games").document("smart_saver_quiz")

def _week_start() -> datetime:
    return start_of_week_utc()

def _week_start_str() -> str:
    return to_yyyy_mm_dd(_week_start())

def _fetch_txns(uid: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Pull transactions in [start_date, end_date)."""
    col = get_db().collection("users").document(uid).collection("transactions")
    q = (col.where("date", ">=", start_date)
            .where("date", "<", end_date)
            .order_by("date", direction=firestore.Query.DESCENDING))
    return [d.to_dict() or {} for d in q.stream()]

# ============================================================================
# Category Helpers
# ============================================================================
def _txn_category_keys(t: Dict[str, Any]) -> List[str]:
    """Return normalized category keys from transaction."""
    keys: List[str] = []
    
    # 1) PFC fields (preferred)
    pfc_primary = (t.get("pfc_primary") or "").strip().lower()
    pfc_detailed = (t.get("pfc_detailed") or "").strip().lower()
    if pfc_primary:
        keys.append(pfc_primary)
    if pfc_detailed:
        keys.append(pfc_detailed)
    
    # 2) Category path
    cp = t.get("category_path")
    if isinstance(cp, str) and cp:
        for part in cp.split(">"):
            if part.strip():
                keys.append(part.strip().lower())
    
    # 3) Plaid raw fields
    raw = t.get("raw") or {}
    rpc = (raw.get("personal_finance_category") or {}) or {}
    if isinstance(rpc, dict):
        rp = (rpc.get("primary") or "").strip().lower()
        rd = (rpc.get("detailed") or "").strip().lower()
        if rp: keys.append(rp)
        if rd: keys.append(rd)
    
    # 4) Merchant heuristics
    merchant = (
        raw.get("merchant_name")
        or t.get("merchant_name")
        or t.get("name")
        or ""
    ).lower()
    if merchant:
        if any(x in merchant for x in ["uber", "lyft", "taxi", "ride"]):
            keys.append("transportation")
        if any(x in merchant for x in ["whole foods", "kroger", "heb", "trader joe", "walmart", "aldi"]):
            keys.append("groceries")
        if any(x in merchant for x in ["mcdonald", "starbucks", "cafe", "pizza", "restaurant", "grill", "bar"]):
            keys.append("dining")
    
    # 5) Normalize to game buckets
    normed: List[str] = []
    for k in keys:
        if any(s in k for s in ["food & drink", "food_and_drink", "dining", "restaurant"]):
            normed.append("dining")
        elif "grocery" in k or "grocer" in k:
            normed.append("groceries")
        elif "transport" in k or "ride" in k or "taxi" in k:
            normed.append("transportation")
        elif "entertainment" in k:
            normed.append("entertainment")
        elif "shopping" in k or "retail" in k:
            normed.append("shopping")
        elif "travel" in k or "airline" in k or "hotel" in k:
            normed.append("travel")
    
    # Deduplicate while preserving order
    out = []
    for k in keys + normed:
        if k and k not in out:
            out.append(k)
    return out

def _sum_by_category(txns: List[Dict[str, Any]]) -> Dict[str, float]:
    """Sum spending by category."""
    agg: Dict[str, float] = {}
    for t in txns:
        amt = float(t.get("amount", 0.0) or 0.0)
        if amt <= 0:
            continue
        cats = _txn_category_keys(t)
        for cat in cats:
            if cat in ("dining", "groceries", "transportation", "entertainment", "shopping", "travel"):
                agg[cat] = round(agg.get(cat, 0.0) + amt, 2)
    return agg

# ============================================================================
# Question Generation
# ============================================================================

def _rand_choices_around(value: float, n: int = 4, jitter: float = 0.15) -> Tuple[List[str], int]:
    """Generate n choices around a value with jitter."""
    correct = round(value, 2)
    opts = {correct}
    
    # Generate distractors
    tries = 0
    while len(opts) < n and tries < 50:
        tries += 1
        delta = (random.random() * 2 - 1) * jitter
        cand = round(value * (1 + delta), 2)
        if cand != correct and cand > 0:
            opts.add(cand)
    
    # Pad if needed
    while len(opts) < n:
        opts.add(round(max(1.0, value + random.uniform(-10, 10)), 2))
    
    choices = sorted(list(opts))
    correct_index = choices.index(correct)
    
    return (["${:,.2f}".format(x) for x in choices], correct_index)

def _q_percent_reduction(cat: str, amount: float, pct: float = 0.20) -> Dict[str, Any]:
    """Question: If you cut X% from category, what would you spend?"""
    new_amount = round(amount * (1 - pct), 2)
    text = f"You spent ${amount:,.2f} on {cat.capitalize()} this week. If you cut {int(pct*100)}%, what would you spend?"
    choices, correct_index = _rand_choices_around(new_amount, n=4, jitter=0.12)
    
    return {
        "type": "percent_reduction",
        "question": text,
        "choices": choices,
        "correct_index": correct_index,
        "meta": {"cat": cat, "amount": amount, "pct": pct},
    }

def _q_top_category(spend_map: Dict[str, float]) -> Dict[str, Any]:
    """Question: Which category did you spend the most on?"""
    if not spend_map:
        spend_map = {"dining": 50.0, "groceries": 80.0, "transportation": 30.0}
    
    # Top 4 categories
    top = sorted(spend_map.items(), key=lambda kv: kv[1], reverse=True)[:4]
    cats = [k.capitalize() for k, _ in top]
    correct = cats[0]
    
    random.shuffle(cats)
    correct_index = cats.index(correct)
    
    text = "Which category did you spend the most on this week?"
    
    return {
        "type": "max_category",
        "question": text,
        "choices": cats,
        "correct_index": correct_index,
        "meta": {"spend_map": spend_map},
    }

def _q_week_comparison(this_week: Dict[str, float], last_week: Dict[str, float], cat: str) -> Dict[str, Any]:
    """Question: Compare this week to last week for a category."""
    this_amt = this_week.get(cat, 0.0)
    last_amt = last_week.get(cat, 0.0)
    
    if last_amt == 0:
        # Can't compare
        return _q_percent_reduction(cat, this_amt, pct=0.15)
    
    diff = this_amt - last_amt
    pct_change = (diff / last_amt) * 100
    
    direction = "more" if diff > 0 else "less"
    text = f"You spent ${this_amt:.2f} on {cat.capitalize()} this week vs ${last_amt:.2f} last week. What's the % change?"
    
    # Generate choices around pct_change
    correct_pct = round(pct_change, 0)
    opts = {correct_pct}
    
    # Add distractors
    for _ in range(10):
        delta = random.randint(-20, 20)
        cand = correct_pct + delta
        if cand != correct_pct:
            opts.add(cand)
    
    choices_list = sorted(list(opts))[:4]
    if correct_pct not in choices_list:
        choices_list[0] = correct_pct
        choices_list = sorted(choices_list)
    
    correct_index = choices_list.index(correct_pct)
    choices = [f"{int(x):+d}%" for x in choices_list]
    
    return {
        "type": "week_comparison",
        "question": text,
        "choices": choices,
        "correct_index": correct_index,
        "meta": {"cat": cat, "this_amt": this_amt, "last_amt": last_amt, "pct_change": pct_change},
    }

def _q_category_sum(spend_map: Dict[str, float]) -> Dict[str, Any]:
    """Question: What was your total spending this week?"""
    total = sum(spend_map.values())
    text = "What was your total spending this week across all categories?"
    choices, correct_index = _rand_choices_around(total, n=4, jitter=0.15)
    
    return {
        "type": "total_spend",
        "question": text,
        "choices": choices,
        "correct_index": correct_index,
        "meta": {"total": total},
    }

def _q_budget_allocation(spend_map: Dict[str, float], target_save: float) -> Dict[str, Any]:
    """Question: If you want to save X, what should your new total be?"""
    current_total = sum(spend_map.values())
    new_total = max(0, current_total - target_save)
    
    text = f"You spent ${current_total:.2f} total this week. To save ${target_save:.2f}, what should your new total be?"
    choices, correct_index = _rand_choices_around(new_total, n=4, jitter=0.10)
    
    return {
        "type": "budget_allocation",
        "question": text,
        "choices": choices,
        "correct_index": correct_index,
        "meta": {"current_total": current_total, "target_save": target_save},
    }

def _generate_questions(
    uid: str,
    difficulty: str,
    this_week: Dict[str, float],
    last_week: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Generate 5 questions based on difficulty level."""
    questions = []
    
    # Get top categories
    top_cats = sorted(this_week.items(), key=lambda kv: kv[1], reverse=True)
    top_cat = top_cats[0][0] if top_cats else "dining"
    
    # Always include: top category question
    questions.append(_q_top_category(this_week))
    
    # Basic: 2 percent reduction, 1 total spend, 1 top category
    if difficulty == "basic":
        if this_week.get(top_cat, 0) > 0:
            questions.append(_q_percent_reduction(top_cat, this_week[top_cat], pct=0.20))
        questions.append(_q_category_sum(this_week))
        if len(top_cats) >= 2:
            cat2 = top_cats[1][0]
            if this_week.get(cat2, 0) > 0:
                questions.append(_q_percent_reduction(cat2, this_week[cat2], pct=0.15))
    
    # Intermediate: 1 comparison, 1 percent reduction, 1 budget allocation
    elif difficulty == "intermediate":
        questions.append(_q_week_comparison(this_week, last_week, top_cat))
        if this_week.get(top_cat, 0) > 0:
            questions.append(_q_percent_reduction(top_cat, this_week[top_cat], pct=0.25))
        
        total_spend = sum(this_week.values())
        target_save = round(total_spend * 0.15, 2)
        questions.append(_q_budget_allocation(this_week, target_save))
    
    # Advanced: 2 comparisons, 1 budget allocation, 1 complex reduction
    elif difficulty == "advanced":
        questions.append(_q_week_comparison(this_week, last_week, top_cat))
        
        if len(top_cats) >= 2:
            cat2 = top_cats[1][0]
            questions.append(_q_week_comparison(this_week, last_week, cat2))
        
        total_spend = sum(this_week.values())
        target_save = round(total_spend * 0.20, 2)
        questions.append(_q_budget_allocation(this_week, target_save))
    
    # Pad or trim to exactly 5
    random.shuffle(questions)
    while len(questions) < QUESTIONS_PER_ROUND:
        # Add more percent reduction questions as filler
        if top_cats:
            cat = random.choice(top_cats)[0]
            if this_week.get(cat, 0) > 0:
                pct = random.choice([0.10, 0.15, 0.20, 0.25])
                questions.append(_q_percent_reduction(cat, this_week[cat], pct=pct))
    
    questions = questions[:QUESTIONS_PER_ROUND]
    
    # Assign IDs
    for i, q in enumerate(questions):
        q["id"] = f"q{i+1}"
    
    return questions

# ============================================================================
# XP & Level System
# ============================================================================

def _adjust_difficulty(current: str, history: List[Dict[str, Any]]) -> str:
    """Adjust difficulty based on recent performance."""
    if not history or len(history) < HISTORY_WINDOW:
        return current
    
    recent = history[-HISTORY_WINDOW:]
    accs = [h.get("accuracy", 0.0) for h in recent]
    avg = sum(accs) / len(accs)
    
    idx = DIFFICULTY_LEVELS.index(current)
    
    # Advance if consistently high performance
    if avg >= ADVANCE_THRESHOLD and idx < len(DIFFICULTY_LEVELS) - 1:
        return DIFFICULTY_LEVELS[idx + 1]
    
    # Demote if struggling
    if avg < DEMOTE_THRESHOLD and idx > 0:
        return DIFFICULTY_LEVELS[idx - 1]
    
    return current

# ============================================================================
# Low Data Message
# ============================================================================

def _generate_low_data_message() -> str:
    """Message when insufficient transaction data."""
    messages = [
        "Not enough spending data this week. Keep it up with that financial discipline!",
        "Light spending week! We'll have more questions for you next time.",
        "Your wallet is looking healthy! Not much to analyze this week.",
    ]
    return random.choice(messages)

# ============================================================================
# Public API
# ============================================================================

def new_set(uid: str) -> Dict[str, Any]:
    """
    Generate a new quiz set for the week.
    
    Returns either:
    - 5 questions based on spending data
    - Low-data message with XP reward
    - Already played message
    """
    db = get_db()
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    state = snap.to_dict() if snap.exists else {}
    
    # Check if already played this week
    week_start = _week_start_str()
    last_played_week = state.get("last_played_week")
    
    if last_played_week == week_start:
        return {
            "ok": True,
            "can_play": False,
            "already_played": True,
            "message": "You've already completed Smart Saver Quiz this week! Come back next Monday.",
            "next_available": to_yyyy_mm_dd(_week_start() + timedelta(days=7)),
            "last_result": state.get("last_round_summary"),
        }
    
    # Get difficulty
    difficulty = state.get("difficulty", "basic")
    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = "basic"
    
    # Fetch this week's and last week's transactions
    now = datetime.now(timezone.utc)
    
    # This period: past 7 days
    this_week_start = to_yyyy_mm_dd(now - timedelta(days=7))
    this_week_end = to_yyyy_mm_dd(now + timedelta(days=1))
    
    # Last period: 14-7 days ago
    last_week_start = to_yyyy_mm_dd(now - timedelta(days=14))
    last_week_end = to_yyyy_mm_dd(now - timedelta(days=7))
    
    this_week_txns = _fetch_txns(uid, this_week_start, this_week_end)
    last_week_txns = _fetch_txns(uid, last_week_start, last_week_end)
    
    this_week_spend = _sum_by_category(this_week_txns)
    last_week_spend = _sum_by_category(last_week_txns)
    
    # Check if enough data
    if len(this_week_txns) < MIN_TRANSACTIONS_REQUIRED:
        # Award full XP for low spending
        progression_result = progression.add_xp(uid, FULL_ROUND_XP, source="quiz_low_data")
        
        current_streak = int(state.get("streak", 0))
        new_streak = current_streak + 1
        
        game_ref.set({
            "streak": new_streak,
            "last_played_week": week_start,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        
        return {
            "ok": True,
            "can_play": False,
            "insufficient_data": True,
            "message": _generate_low_data_message(),
            "xp_awarded": FULL_ROUND_XP,
            "progression": {
                "total_xp": progression_result.get("new_xp", 0),
                "level": progression_result.get("new_level", 1),
                "level_up": progression_result.get("level_up", False),
                "rank": progression_result.get("new_rank", "Penny Pincher"),
                "rank_up": progression_result.get("rank_up", False)
            },
            "streak": new_streak,
            "transactions_found": len(this_week_txns),
            "transactions_needed": MIN_TRANSACTIONS_REQUIRED,
        }
    
    # Generate questions
    questions = _generate_questions(uid, difficulty, this_week_spend, last_week_spend)
    
    # Store with answers
    full_questions = questions.copy()
    
    # Remove correct_index for client
    public_questions = []
    for q in questions:
        public_questions.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "choices": q["choices"],
        })
    
    # Store round with tracking for immediate feedback
    game_ref.set({
        "current_round": {
            "round_id": datetime.now(timezone.utc).isoformat(),
            "week_start": week_start,
            "difficulty": difficulty,
            "questions": full_questions,
            "answers": [],  # Will store {question_id, selected_index, is_correct, answered_at}
            "current_question_index": 0,
            "started_at": firestore.SERVER_TIMESTAMP,
        },
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    return {
        "ok": True,
        "can_play": True,
        "difficulty": difficulty,
        "questions": public_questions,
        "total_questions": len(public_questions),
        "instructions": "Answer questions about your spending this week. +20 XP per correct answer!",
    }

def answer_question(uid: str, question_id: str, selected_index: int) -> Dict[str, Any]:
    """
    Submit answer for a single question and get immediate feedback.
    
    Args:
        uid: User ID
        question_id: Question ID (e.g., "q1", "q2")
        selected_index: Index of selected answer (0-3)
    
    Returns:
        Immediate feedback with:
        - is_correct: bool
        - correct_index: int (the right answer)
        - explanation: str
        - selected_index: int (what they chose)
        - xp_earned: int (for this question)
    """
    db = get_db()
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {"ok": False, "error": "No active quiz. Call /new first."}
    
    state = snap.to_dict() or {}
    round_data = state.get("current_round", {})
    
    if not round_data:
        return {"ok": False, "error": "No active quiz."}
    
    questions = round_data.get("questions", [])
    answers = round_data.get("answers", [])
    
    # Find the question
    question = None
    for q in questions:
        if q.get("id") == question_id:
            question = q
            break
    
    if not question:
        return {"ok": False, "error": f"Question {question_id} not found."}
    
    # Check if already answered
    for ans in answers:
        if ans.get("question_id") == question_id:
            return {"ok": False, "error": f"Question {question_id} already answered."}
    
    # Grade the answer
    correct_index = int(question.get("correct_index", -1))
    is_correct = (selected_index == correct_index)
    xp_earned = XP_PER_CORRECT if is_correct else 0
    
    # Build explanation
    explanation = _build_single_explanation(question, is_correct, selected_index, correct_index)
    
    # Record the answer
    answer_record = {
        "question_id": question_id,
        "selected_index": selected_index,
        "correct_index": correct_index,
        "is_correct": is_correct,
        "xp_earned": xp_earned,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }
    answers.append(answer_record)
    
    # Update round data
    round_data["answers"] = answers
    round_data["current_question_index"] = len(answers)
    
    game_ref.set({
        "current_round": round_data,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    # Check if quiz is complete
    all_answered = len(answers) >= len(questions)
    
    return {
        "ok": True,
        "is_correct": is_correct,
        "correct_index": correct_index,
        "selected_index": selected_index,
        "explanation": explanation,
        "xp_earned": xp_earned,
        "questions_answered": len(answers),
        "total_questions": len(questions),
        "quiz_complete": all_answered,
    }

def _build_single_explanation(
    question: Dict[str, Any],
    is_correct: bool,
    selected_index: int,
    correct_index: int
) -> str:
    """Generate explanation for a single question answer."""
    qtype = question.get("type")
    meta = question.get("meta", {})
    correct_val = question["choices"][correct_index]
    
    if qtype == "percent_reduction":
        amt = meta.get("amount", 0)
        pct = int(meta.get("pct", 0) * 100)
        if is_correct:
            return f"Correct! Cutting {pct}% from ${amt:.2f} equals {correct_val}."
        else:
            return f"Not quite. Cutting {pct}% from ${amt:.2f} equals {correct_val}."
    
    elif qtype == "max_category":
        if is_correct:
            return f"Correct! {correct_val} was your highest spending category this week."
        else:
            return f"Actually, {correct_val} was your highest spending category this week."
    
    elif qtype == "week_comparison":
        pct_change = meta.get("pct_change", 0)
        direction = "increased" if pct_change > 0 else "decreased"
        if is_correct:
            return f"Correct! Your spending {direction} by {abs(int(pct_change))}% compared to last week."
        else:
            return f"Your spending {direction} by {abs(int(pct_change))}% compared to last week. The answer is {correct_val}."
    
    elif qtype == "total_spend":
        if is_correct:
            return f"Correct! Your total spending this week was {correct_val}."
        else:
            return f"Your total spending this week was {correct_val}."
    
    elif qtype == "budget_allocation":
        save = meta.get("target_save", 0)
        if is_correct:
            return f"Correct! To save ${save:.2f}, your new total should be {correct_val}."
        else:
            return f"To save ${save:.2f}, your new total should be {correct_val}."
    
    else:
        if is_correct:
            return f"Correct! The answer is {correct_val}."
        else:
            return f"The correct answer is {correct_val}."

def complete_quiz(uid: str) -> Dict[str, Any]:
    """
    Finalize quiz after all questions are answered.
    Calculate total XP, update difficulty, save to history.
    
    This should be called after all questions have been answered via answer_question().
    """
    db = get_db()
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {"ok": False, "error": "No active quiz."}
    
    state = snap.to_dict() or {}
    round_data = state.get("current_round", {})
    
    if not round_data:
        return {"ok": False, "error": "No active quiz."}
    
    questions = round_data.get("questions", [])
    answers = round_data.get("answers", [])
    
    if len(answers) < len(questions):
        return {
            "ok": False,
            "error": f"Not all questions answered. {len(answers)}/{len(questions)} completed."
        }
    
    # Calculate stats
    total = len(questions)
    correct = sum(1 for a in answers if a.get("is_correct"))
    accuracy = correct / total if total > 0 else 0
    
    # Calculate XP (from recorded answers)
    xp_earned = sum(a.get("xp_earned", 0) for a in answers)
    
    # Award XP to unified progression system
    progression_result = progression.add_xp(uid, xp_earned, source="quiz")
    
    current_streak = int(state.get("streak", 0))
    current_difficulty = round_data.get("difficulty", "basic")
    
    # Update streak
    streak_maintained = accuracy >= STREAK_ACCURACY_THRESHOLD
    new_streak = current_streak + 1 if streak_maintained else 0
    
    # Update history
    history: List[Dict[str, Any]] = state.get("history", [])
    history.append({
        "week_start": round_data.get("week_start"),
        "difficulty": current_difficulty,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "xp_earned": xp_earned,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    history = history[-10:]  # Keep last 10
    
    # Adjust difficulty
    new_difficulty = _adjust_difficulty(current_difficulty, history)
    
    # Summary
    summary = {
        "correct": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "streak_maintained": streak_maintained,
        "difficulty_before": current_difficulty,
        "difficulty_after": new_difficulty,
    }
    
    # Update state (xp/level now tracked in unified progression system)
    game_ref.set({
        "streak": new_streak,
        "difficulty": new_difficulty,
        "history": history,
        "last_played_week": round_data.get("week_start"),
        "last_round_summary": summary,
        "current_round": firestore.DELETE_FIELD,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    # Store in history subcollection
    game_ref.collection("history").add({
        "round_id": round_data.get("round_id"),
        "week_start": round_data.get("week_start"),
        "difficulty": current_difficulty,
        "correct": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "completed_at": firestore.SERVER_TIMESTAMP,
    })
    
    return {
        "ok": True,
        "score": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "progression": {
            "total_xp": progression_result.get("new_xp", 0),
            "level": progression_result.get("new_level", 1),
            "level_up": progression_result.get("level_up", False),
            "rank": progression_result.get("new_rank", "Penny Pincher"),
            "rank_up": progression_result.get("rank_up", False)
        },
        "streak": new_streak,
        "streak_maintained": streak_maintained,
        "difficulty_before": current_difficulty,
        "difficulty_after": new_difficulty,
        "difficulty_changed": new_difficulty != current_difficulty,
        "summary": summary,
    }

# Keep the old submit function for backward compatibility
def submit(uid: str, answers: List[int]) -> Dict[str, Any]:
    """
    DEPRECATED: Use answer_question() for immediate feedback instead.
    
    This function is kept for backward compatibility but will process
    all answers at once without immediate feedback.
    """
    db = get_db()
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {"ok": False, "error": "No active quiz. Call /new first."}
    
    state = snap.to_dict() or {}
    round_data = state.get("current_round", {})
    
    if not round_data:
        return {"ok": False, "error": "No active quiz."}
    
    questions = round_data.get("questions", [])
    if not questions:
        return {"ok": False, "error": "No questions found."}
    
    # Grade all at once
    total = min(len(questions), len(answers))
    correct = 0
    results = []
    
    for i in range(total):
        q = questions[i]
        user_answer = int(answers[i]) if i < len(answers) else -1
        correct_index = int(q.get("correct_index", -1))
        is_correct = (user_answer == correct_index)
        
        if is_correct:
            correct += 1
        
        results.append({
            "id": q.get("id"),
            "correct": is_correct,
            "your_answer": user_answer,
            "correct_index": correct_index,
        })
    
    accuracy = correct / total if total > 0 else 0
    xp_earned = correct * XP_PER_CORRECT
    
    # Award XP to unified progression system
    progression_result = progression.add_xp(uid, xp_earned, source="quiz")
    
    current_streak = int(state.get("streak", 0))
    current_difficulty = round_data.get("difficulty", "basic")
    
    streak_maintained = accuracy >= STREAK_ACCURACY_THRESHOLD
    new_streak = current_streak + 1 if streak_maintained else 0
    
    history: List[Dict[str, Any]] = state.get("history", [])
    history.append({
        "week_start": round_data.get("week_start"),
        "difficulty": current_difficulty,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "xp_earned": xp_earned,
    })
    history = history[-10:]
    
    new_difficulty = _adjust_difficulty(current_difficulty, history)
    
    explanations = _build_explanations(questions, results)
    
    summary = {
        "correct": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "streak_maintained": streak_maintained,
        "difficulty_before": current_difficulty,
        "difficulty_after": new_difficulty,
    }
    
    # Update state (xp/level now tracked in unified progression system)
    game_ref.set({
        "streak": new_streak,
        "difficulty": new_difficulty,
        "history": history,
        "last_played_week": round_data.get("week_start"),
        "last_round_summary": summary,
        "current_round": firestore.DELETE_FIELD,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    game_ref.collection("history").add({
        "round_id": round_data.get("round_id"),
        "week_start": round_data.get("week_start"),
        "difficulty": current_difficulty,
        "correct": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "completed_at": firestore.SERVER_TIMESTAMP,
    })
    
    return {
        "ok": True,
        "score": correct,
        "total": total,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "progression": {
            "total_xp": progression_result.get("new_xp", 0),
            "level": progression_result.get("new_level", 1),
            "level_up": progression_result.get("level_up", False),
            "rank": progression_result.get("new_rank", "Penny Pincher"),
            "rank_up": progression_result.get("rank_up", False)
        },
        "streak": new_streak,
        "streak_maintained": streak_maintained,
        "difficulty_before": current_difficulty,
        "difficulty_after": new_difficulty,
        "difficulty_changed": new_difficulty != current_difficulty,
        "results": results,
        "explanations": explanations,
        "summary": summary,
    }

def _build_explanations(questions: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> List[str]:
    """Generate explanations for each answer (batch mode)."""
    explanations = []
    
    for q, r in zip(questions, results):
        qtype = q.get("type")
        meta = q.get("meta", {})
        correct_idx = q.get("correct_index")
        correct_val = q["choices"][correct_idx]
        
        if qtype == "percent_reduction":
            amt = meta.get("amount", 0)
            pct = int(meta.get("pct", 0) * 100)
            explanations.append(f"Cutting {pct}% of ${amt:.2f} = {correct_val}.")
        
        elif qtype == "max_category":
            explanations.append(f"Your highest spending category was {q['choices'][correct_idx]}.")
        
        elif qtype == "week_comparison":
            pct_change = meta.get("pct_change", 0)
            direction = "increased" if pct_change > 0 else "decreased"
            explanations.append(f"Your spending {direction} by {abs(int(pct_change))}% compared to last week.")
        
        elif qtype == "total_spend":
            explanations.append(f"Your total spending this week was {correct_val}.")
        
        elif qtype == "budget_allocation":
            save = meta.get("target_save", 0)
            explanations.append(f"To save ${save:.2f}, your new total should be {correct_val}.")
        
        else:
            explanations.append(f"Correct answer: {correct_val}")
    
    return explanations

def get_state(uid: str) -> Dict[str, Any]:
    """Get current game state for user."""
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {
            "ok": True,
            "streak": 0,
            "difficulty": "basic",
            "has_active_round": False,
            "can_play_this_week": True,
        }
    
    state = snap.to_dict() or {}
    week_start = _week_start_str()
    last_played_week = state.get("last_played_week")
    
    # Include current quiz progress
    round_data = state.get("current_round", {})
    quiz_progress = None
    if round_data:
        questions = round_data.get("questions", [])
        answers = round_data.get("answers", [])
        quiz_progress = {
            "total_questions": len(questions),
            "answered": len(answers),
            "current_question_index": len(answers),
        }
    
    return {
        "ok": True,
        "streak": state.get("streak", 0),
        "difficulty": state.get("difficulty", "basic"),
        "has_active_round": bool(round_data),
        "quiz_progress": quiz_progress,
        "can_play_this_week": last_played_week != week_start,
        "last_played_week": last_played_week,
        "last_round_summary": state.get("last_round_summary"),
    }
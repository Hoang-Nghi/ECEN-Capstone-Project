# services/minigame_service/spend_detective.py
"""
Spend Detective - ML-driven anomaly detection minigame.

FIXED VERSION - Proper tries counting and found anomalies tracking

Gameplay:
- Identify unusual transactions from your recent spending
- Uses statistical analysis (z-scores, frequency patterns) to detect anomalies
- 8 transactions shown per round (2-4 anomalies, rest normal)
- 3 tries to identify all anomalies
- +20 XP per correct identification
- No XP deduction for mistakes (learning-focused)

Key fixes:
- Tries properly decrement on each wrong guess
- Found count properly increments on each correct guess
- No duplicate counting
- Atomic state updates
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import math
import random

from firebase_admin import firestore
from .utils import get_db, start_of_week_utc, to_yyyy_mm_dd
from . import progression

# ============================================================================
# Constants
# ============================================================================

DOC_PATH = "users/{uid}/games/spend_detective"
TRANSACTIONS_PER_ROUND = 6
MIN_ANOMALIES = 1
MAX_ANOMALIES = 3
TRIES_PER_ROUND = 3
XP_PER_CORRECT = 20
MIN_TRANSACTIONS_REQUIRED = 15
STREAK_ACCURACY_THRESHOLD = 0.60
MAX_LEVEL = 100

# Anomaly detection thresholds
Z_SCORE_THRESHOLD = 2.0
RARE_MERCHANT_THRESHOLD = 2
UNUSUAL_TIME_HOURS = [0, 1, 2, 3, 4, 5]
DUPLICATE_AMOUNT_WINDOW_DAYS = 7

# Simulated anomaly merchants
FAKE_MERCHANTS = [
    ("UltraCar Rentals", "travel"),
    ("CryptoBlast", "investment"),
    ("Emerald Casino", "entertainment"),
    ("Luxury Wine Co.", "dining"),
    ("Gold Rush Antiques", "shopping"),
]

# ============================================================================
# Helpers - Date & Firestore
# ============================================================================
def _generate_fake_anomaly(index: int) -> Dict[str, Any]:
    merchant, category = random.choice(FAKE_MERCHANTS)
    date = to_yyyy_mm_dd(datetime.now(timezone.utc) - timedelta(days=random.randint(0, 6)))
    amount = round(random.choice([499.99, 777.00, 3.14, 999.99, 250.00]), 2)
    return {
        "id": f"fake_txn_{index}_{random.randint(1000,9999)}",
        "date": date,
        "merchant_name": merchant,
        "amount": amount,
        "category": category,
        "raw": {},
}

def _week_start(dt: datetime | None = None) -> datetime:
    return start_of_week_utc(dt)

def _week_start_str(dt: datetime | None = None) -> str:
    return to_yyyy_mm_dd(_week_start(dt))

def _tx_col(uid: str):
    return get_db().collection("users").document(uid).collection("transactions")

def _game_ref(uid: str):
    return get_db().collection("users").document(uid).collection("games").document("spend_detective")

# ============================================================================
# Category Extraction
# ============================================================================

def _txn_category_keys(t: Dict[str, Any]) -> List[str]:
    """Extract normalized category keys from transaction."""
    keys: List[str] = []
    
    pfc_primary = (t.get("pfc_primary") or "").strip().lower()
    pfc_detailed = (t.get("pfc_detailed") or "").strip().lower()
    if pfc_primary:
        keys.append(pfc_primary)
    if pfc_detailed:
        keys.append(pfc_detailed)
    
    raw = t.get("raw") or {}
    raw_pfc = raw.get("personal_finance_category")
    if isinstance(raw_pfc, dict):
        raw_primary = (raw_pfc.get("primary") or "").strip().lower()
        raw_detailed = (raw_pfc.get("detailed") or "").strip().lower()
        if raw_primary:
            keys.append(raw_primary)
        if raw_detailed:
            keys.append(raw_detailed)
    
    normalized = []
    for k in keys:
        k_lower = k.lower()
        if any(s in k_lower for s in ["food_and_drink", "dining", "restaurant"]):
            if "dining" not in normalized:
                normalized.append("dining")
        elif any(s in k_lower for s in ["grocery", "groceries"]):
            if "groceries" not in normalized:
                normalized.append("groceries")
        elif any(s in k_lower for s in ["transport", "taxi", "ride"]):
            if "transportation" not in normalized:
                normalized.append("transportation")
        elif "entertainment" in k_lower:
            if "entertainment" not in normalized:
                normalized.append("entertainment")
        elif any(s in k_lower for s in ["shopping", "retail"]):
            if "shopping" not in normalized:
                normalized.append("shopping")
        elif any(s in k_lower for s in ["travel", "airline", "hotel"]):
            if "travel" not in normalized:
                normalized.append("travel")
    
    result = []
    for item in keys + normalized:
        if item and item not in result:
            result.append(item)
    return result

def _fetch_txns(uid: str, start_date: str, end_date: str, limit: int | None = None) -> List[Dict[str, Any]]:
    """Fetch transactions in date range [start_date, end_date)"""
    col = _tx_col(uid)
    q = (col.where("date", ">=", start_date)
            .where("date", "<", end_date)
            .order_by("date", direction=firestore.Query.DESCENDING))
    
    if limit:
        q = q.limit(limit)
    
    docs = list(q.stream())
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]

# ============================================================================
# ML-Based Anomaly Detection (simplified for this fix)
# ============================================================================

def _calculate_statistics(txns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistical baselines."""
    if not txns:
        return {"mean": 0, "std": 0, "median": 0, "q75": 0, "q95": 0}
    
    amounts = [float(t.get("amount", 0)) for t in txns if float(t.get("amount", 0)) > 0]
    if not amounts:
        return {"mean": 0, "std": 0, "median": 0, "q75": 0, "q95": 0}
    
    amounts.sort()
    n = len(amounts)
    mean = sum(amounts) / n
    
    variance = sum((x - mean) ** 2 for x in amounts) / n
    std = math.sqrt(variance) if variance > 0 else 0
    
    median = amounts[n // 2]
    q75 = amounts[int(n * 0.75)]
    q95 = amounts[int(n * 0.95)] if n > 10 else amounts[-1]
    
    return {
        "mean": mean,
        "std": std,
        "median": median,
        "q75": q75,
        "q95": q95,
        "count": n
    }

def _merchant_frequency(txns: List[Dict[str, Any]]) -> Counter:
    """Count merchant occurrences."""
    merchants = []
    for t in txns:
        raw = t.get("raw") or {}
        merchant = (raw.get("merchant_name") or t.get("name") or "").strip().lower()
        if merchant:
            merchants.append(merchant)
    return Counter(merchants)

def _detect_anomalies(
    candidate_txns: List[Dict[str, Any]],
    historical_txns: List[Dict[str, Any]]
) -> List[Tuple[str, List[str]]]:
    """Detect anomalies using ML-based signals."""
    stats = _calculate_statistics(historical_txns)
    merchant_freq = _merchant_frequency(historical_txns)
    
    anomalies: List[Tuple[str, List[str]]] = []
    
    for t in candidate_txns:
        reasons: List[str] = []
        amount = float(t.get("amount", 0))
        
        if amount <= 0:
            continue
        
        # Z-score outlier
        if stats["std"] > 0:
            z_score = (amount - stats["mean"]) / stats["std"]
            if z_score > Z_SCORE_THRESHOLD:
                reasons.append(f"Unusually high amount (${amount:.2f} vs avg ${stats['mean']:.2f})")
        
        # Above 95th percentile
        if amount > stats["q95"] and stats["count"] > 10:
            reasons.append(f"Top 5% of your spending")
        
        # Rare merchant
        raw = t.get("raw") or {}
        merchant = (raw.get("merchant_name") or t.get("name") or "").strip().lower()
        if merchant and merchant_freq[merchant] <= RARE_MERCHANT_THRESHOLD:
            reasons.append(f"Rare merchant (only {merchant_freq[merchant]} transactions)")
        
        if reasons:
            anomalies.append((t["id"], reasons))
    
    return anomalies

# ============================================================================
# Public API
# ============================================================================

def start_round(uid: str, category: str = None) -> Dict[str, Any]:
    db = get_db()
    game_ref = _game_ref(uid)
    week_start = _week_start_str()

    snap = game_ref.get()
    if snap.exists:
        state = snap.to_dict() or {}
        if state.get("last_played_week") == week_start:
            return {
                "ok": False,
                "error": "Already played this week. Come back next Monday!",
                "next_available": week_start
            }

    end_date = to_yyyy_mm_dd(datetime.now(timezone.utc) + timedelta(days=1))
    start_date = to_yyyy_mm_dd(datetime.now(timezone.utc) - timedelta(days=90))
    historical = _fetch_txns(uid, start_date=start_date, end_date=end_date, limit=200)

    if len(historical) < MIN_TRANSACTIONS_REQUIRED:
        return {
            "ok": True,
            "insufficient_data": True,
            "message": "Not enough transaction history yet. Keep spending and come back next week!",
            "xp_awarded": TRANSACTIONS_PER_ROUND * XP_PER_CORRECT,
        }

    recent_start = to_yyyy_mm_dd(datetime.now(timezone.utc) - timedelta(days=7))
    recent = _fetch_txns(uid, recent_start, end_date, limit=50)

    if len(recent) < TRANSACTIONS_PER_ROUND:
        return {"ok": False, "error": "Not enough recent transactions for a round"}

    anomaly_tuples = _detect_anomalies(recent[:20], historical)
    anomaly_dict = {txid: reasons for txid, reasons in anomaly_tuples}
    anomaly_ids = list(anomaly_dict.keys())

    selected_anomalies = []
    round_txns = []

    if len(anomaly_ids) >= MIN_ANOMALIES:
        num_anomalies = min(len(anomaly_ids), MAX_ANOMALIES)
        selected_anomalies = random.sample(anomaly_ids, num_anomalies)
        anomaly_txns = [t for t in recent if t["id"] in selected_anomalies]
        normal_txns = [t for t in recent if t["id"] not in anomaly_ids]
        selected_normal = random.sample(normal_txns, min(len(normal_txns), TRANSACTIONS_PER_ROUND - num_anomalies))
        round_txns = anomaly_txns + selected_normal
    else:
        # No real anomalies detected - generate fake ones to make game playable
        # Always ensure we have MIN_ANOMALIES to MAX_ANOMALIES (1-3) fake anomalies
        num_fakes = random.randint(MIN_ANOMALIES, MAX_ANOMALIES)
        num_real = TRANSACTIONS_PER_ROUND - num_fakes  # Fill rest with real transactions
        
        # Take real transactions as "normal" ones
        normal_txns = recent[:min(num_real, len(recent))]
        round_txns = list(normal_txns)
        
        # Generate fake anomaly transactions
        for i in range(num_fakes):
            fake_txn = _generate_fake_anomaly(i)
            round_txns.append(fake_txn)
            selected_anomalies.append(fake_txn["id"])
            anomaly_dict[fake_txn["id"]] = ["Simulated anomaly transaction"]

    random.shuffle(round_txns)
    
    # Safety check: Ensure we always have at least one anomaly for gameplay
    if not selected_anomalies:
        print(f"[spend_detective] WARNING: No anomalies selected for {uid}, generating emergency fake anomaly")
        fake_txn = _generate_fake_anomaly(999)
        round_txns.append(fake_txn)
        selected_anomalies.append(fake_txn["id"])
        anomaly_dict[fake_txn["id"]] = ["Emergency simulated anomaly"]
        random.shuffle(round_txns)  # Re-shuffle after adding emergency fake

    round_id = f"{uid}_{week_start}_{random.randint(1000, 9999)}"
    round_data = {
        "round_id": round_id,
        "week_start": week_start,
        "transaction_ids": [t["id"] for t in round_txns],
        "anomaly_ids": selected_anomalies,
        "anomaly_reasons": anomaly_dict,
        "tries_remaining": TRIES_PER_ROUND,
        "correct_identifications": [],
        "false_positives": [],
        "started_at": firestore.SERVER_TIMESTAMP,
    }

    game_ref.set({
        "current_round": round_data,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)

    redacted = []
    for t in round_txns:
        raw = t.get("raw") or {}
        cps = raw.get("counterparties") or []
        merchant = ((cps[0].get("name") if cps else None)
                    or raw.get("merchant_name")
                    or t.get("merchant_name")
                    or t.get("name")
                    or "")
        cat_display = (t.get("pfc_primary")
                      or ((raw.get("personal_finance_category") or {}).get("primary"))
                      or t.get("category_path")
                      or t.get("category")
                      or "")
        redacted.append({
            "id": t["id"],
            "date": t.get("date"),
            "merchant_name": merchant,
            "amount": round(float(t.get("amount", 0.0) or 0.0), 2),
            "category": cat_display,
            "logo_url": raw.get("logo_url") or (cps[0].get("logo_url") if cps else None),
            "website": raw.get("website") or (cps[0].get("website") if cps else None),
        })

    return {
        "ok": True,
        "round": redacted,
        "total_anomalies": len(selected_anomalies),
        "tries_remaining": TRIES_PER_ROUND,
        "found_count": 0,
        "game_over": False,
    }

def submit_guess(uid: str, selected_ids: List[str]) -> Dict[str, Any]:
    """
    Submit a guess - FIXED VERSION with proper state tracking.
    
    Key fixes:
    1. Properly decrements tries_remaining for EACH wrong guess
    2. Properly increments found count for EACH correct guess
    3. Prevents duplicate counting
    4. Returns full current state in response
    """
    db = get_db()
    game_ref = _game_ref(uid)
    
    # Use a transaction for atomic read-modify-write
    @firestore.transactional
    def run_transaction(transaction):
        # Read current state
        snap = game_ref.get(transaction=transaction)
        if not snap.exists:
            raise ValueError("No active round. Call /start first.")
        
        state = snap.to_dict() or {}
        round_data = state.get("current_round", {})
        
        if not round_data:
            raise ValueError("No active round.")
        
        # Extract current state
        anomaly_ids = set(round_data.get("anomaly_ids", []))
        tries_remaining = int(round_data.get("tries_remaining", TRIES_PER_ROUND))
        correct_ids = set(round_data.get("correct_identifications", []))
        false_positive_ids = set(round_data.get("false_positives", []))
        
        # Check if game is already over
        if tries_remaining <= 0:
            all_found = correct_ids == anomaly_ids
            return {
                "ok": True,
                "game_over": True,
                "all_found": all_found,
                "total_correct": len(correct_ids),
                "total_anomalies": len(anomaly_ids),
                "tries_remaining": 0,
                "message": "Game already over. Start a new round!"
            }
        
        # Process submitted IDs
        selected = set(selected_ids)
        
        # Separate into new correct, new false positives, and already found
        new_correct = selected & anomaly_ids - correct_ids
        new_false_positives = selected - anomaly_ids - false_positive_ids
        already_found = selected & correct_ids
        
        # Update state
        correct_ids.update(new_correct)
        false_positive_ids.update(new_false_positives)
        
        # KEY FIX: Decrement tries for EACH new false positive
        # This ensures tries go: 3 -> 2 -> 1 -> 0
        tries_decremented = len(new_false_positives)
        if tries_decremented > 0:
            tries_remaining = max(0, tries_remaining - tries_decremented)
        
        # Check game completion
        all_found = correct_ids == anomaly_ids
        out_of_tries = tries_remaining <= 0
        round_complete = all_found or out_of_tries
        
        # Atomic write - update all fields together
        updates = {
            "current_round.correct_identifications": list(correct_ids),
            "current_round.false_positives": list(false_positive_ids),
            "current_round.tries_remaining": tries_remaining,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        transaction.update(game_ref, updates)
        
        # Build response
        result = {
            "ok": True,
            "new_correct": len(new_correct),
            "new_false_positives": len(new_false_positives),
            "already_found": len(already_found),
            "total_correct": len(correct_ids),  # KEY: This is the found_count for UI
            "total_anomalies": len(anomaly_ids),
            "tries_remaining": tries_remaining,  # KEY: This should decrement properly now
            "round_complete": round_complete,
            "all_found": all_found,
            "game_over": out_of_tries,
        }
        
        # If round is complete, finalize
        if round_complete:
            finalize_result = _finalize_round_in_transaction(
                transaction, game_ref, round_data, correct_ids, false_positive_ids, state
            )
            result.update(finalize_result)
        
        return result
    
    try:
        transaction = db.transaction()
        result = run_transaction(transaction)
        
        # Award XP after transaction completes (if round finished)
        if result.get("round_complete"):
            xp_earned = result.get("xp_earned", 0)
            if xp_earned > 0:
                progression_result = progression.add_xp(uid, xp_earned, source="detective")
                result["progression"] = {
                    "total_xp": progression_result.get("new_xp", 0),
                    "level": progression_result.get("new_level", 1),
                    "level_up": progression_result.get("level_up", False),
                    "rank": progression_result.get("new_rank", "Penny Pincher"),
                    "rank_up": progression_result.get("rank_up", False)
                }
        
        return result
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        print(f"Error in submit_guess transaction: {e}")
        return {"ok": False, "error": "Internal error submitting guess"}

def _finalize_round_in_transaction(
    transaction,
    game_ref,
    round_data: Dict,
    correct_ids: Set[str],
    false_positive_ids: Set[str],
    state: Dict
) -> Dict[str, Any]:
    """Finalize round within the same transaction."""
    anomaly_ids = set(round_data.get("anomaly_ids", []))
    anomaly_reasons = round_data.get("anomaly_reasons", {})
    
    # Calculate results
    num_correct = len(correct_ids)
    num_missed = len(anomaly_ids - correct_ids)
    num_false_positives = len(false_positive_ids)
    accuracy = num_correct / len(anomaly_ids) if anomaly_ids else 0
    
    # XP and streak
    xp_earned = num_correct * XP_PER_CORRECT
    
    # NOTE: progression.add_xp() cannot be called inside a Firestore transaction
    # We'll award XP after the transaction completes (see submit_guess function)
    
    current_streak = int(state.get("streak", 0))
    
    streak_maintained = accuracy >= STREAK_ACCURACY_THRESHOLD
    new_streak = current_streak + 1 if streak_maintained else 0
    
    # Build reveal
    reveal = []
    for txid in anomaly_ids:
        reveal.append({
            "transaction_id": txid,
            "was_anomaly": True,
            "found_by_user": txid in correct_ids,
            "reasons": anomaly_reasons.get(txid, ["Unusual pattern detected"]),
        })
    
    summary = {
        "correct": num_correct,
        "missed": num_missed,
        "false_positives": num_false_positives,
        "accuracy": round(accuracy, 2),
        "xp_earned": xp_earned,
        "streak_maintained": streak_maintained,
    }
    
    # Generate feedback
    if accuracy >= 0.9:
        feedback = "Perfect detective work! You have a sharp eye for unusual spending."
    elif accuracy >= 0.6:
        feedback = "Good job! Keep practicing to sharpen your spending awareness."
    else:
        feedback = "Keep practicing! Review the patterns of unusual transactions to improve."
    
    # Update game state in transaction (xp/level handled separately)
    transaction.update(game_ref, {
        "streak": new_streak,
        "last_played_week": round_data.get("week_start"),
        "last_round_summary": summary,
        "last_round_feedback": feedback,
        "xp_to_award": xp_earned,  # Store for post-transaction award
        "current_round": firestore.DELETE_FIELD,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    
    # History entry (added after transaction completes)
    # Note: This should be done outside transaction for best practices,
    # but including here for completeness
    
    return {
        "xp_earned": xp_earned,
        "streak": new_streak,
        "accuracy": round(accuracy, 2),
        "streak_maintained": streak_maintained,
        "feedback": feedback,
        "reveal": reveal,
        "summary": summary,
    }

def get_state(uid: str) -> Dict[str, Any]:
    """Get current game state for user."""
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {
            "ok": True,
            "streak": 0,
            "has_active_round": False,
            "can_play_this_week": True,
        }
    
    state = snap.to_dict() or {}
    week_start = _week_start_str()
    last_played_week = state.get("last_played_week")
    current_round = state.get("current_round", {})
    
    return {
        "ok": True,
        "streak": state.get("streak", 0),
        "has_active_round": bool(current_round),
        "can_play_this_week": last_played_week != week_start,
        "last_played_week": last_played_week,
        "last_round_summary": state.get("last_round_summary"),
        "last_round_feedback": state.get("last_round_feedback"),
        # Include current round state if active
        "tries_remaining": current_round.get("tries_remaining", TRIES_PER_ROUND) if current_round else None,
        "found_count": len(current_round.get("correct_identifications", [])) if current_round else 0,
        "total_anomalies": len(current_round.get("anomaly_ids", [])) if current_round else 0,
    }
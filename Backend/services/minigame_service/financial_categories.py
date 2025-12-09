# services/minigame_service/financial_categories.py
"""
Financial Categories - ML-driven spending awareness minigame.

Gameplay:
- 5 categories x 5 amount tiles in 2-column grid
- Match category to its actual weekly spend amount
- 3 tries to get all matches correct
- Correct matches move to top (like NYT Connections)
- Streak maintained even when insufficient data (reward responsible spending)

XP & Progression:
- +20 XP per correct match (max 100 XP per round)
- No XP deduction for incorrect attempts
- Logarithmic leveling (max level 100)
- When can't play due to low spend: full 100 XP + streak maintained
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import random
import math

from firebase_admin import firestore
from .utils import get_db, start_of_week_utc, to_yyyy_mm_dd
from . import progression

# ============================================================================
# Constants
# ============================================================================

DOC_PATH = "users/{uid}/games/financial_categories"
GAME_CATEGORIES = ["dining", "groceries", "transportation", "entertainment", "shopping", "travel"]
MIN_ACTIVE_CATEGORIES = 3
MAX_GAME_CATEGORIES = 5
MAX_DECOY_CATEGORIES = 2
TRIES_PER_ROUND = 3
XP_PER_CORRECT_MATCH = 20
FULL_ROUND_XP = 100
MAX_LEVEL = 100

# ============================================================================
# Helpers - Date & Firestore
# ============================================================================

def _week_start(dt: datetime | None = None) -> datetime:
    return start_of_week_utc(dt)

def _week_start_str(dt: datetime | None = None) -> str:
    return to_yyyy_mm_dd(_week_start(dt))

def _tx_col(uid: str):
    return get_db().collection("users").document(uid).collection("transactions")

def _game_ref(uid: str):
    return get_db().collection("users").document(uid).collection("games").document("financial_categories")

# ============================================================================
# Category Extraction (reuse pattern from other games)
# ============================================================================

def _txn_category_keys(t: Dict[str, Any]) -> List[str]:
    """
    Extract normalized category keys from transaction.
    Handles your actual Firestore schema with PFC fields at top level.
    """
    keys: List[str] = []

    # 1) Top-level PFC fields (YOUR PRIMARY SOURCE - already processed by plaid_store.py)
    pfc_primary = (t.get("pfc_primary") or "").strip().lower()
    pfc_detailed = (t.get("pfc_detailed") or "").strip().lower()
    
    if pfc_primary:
        keys.append(pfc_primary)
    if pfc_detailed:
        keys.append(pfc_detailed)

    # 2) Raw Plaid PFC (backup if top-level missing)
    raw = t.get("raw") or {}
    raw_pfc = raw.get("personal_finance_category")
    
    if isinstance(raw_pfc, dict):
        raw_primary = (raw_pfc.get("primary") or "").strip().lower()
        raw_detailed = (raw_pfc.get("detailed") or "").strip().lower()
        
        if raw_primary and raw_primary not in keys:
            keys.append(raw_primary)
        if raw_detailed and raw_detailed not in keys:
            keys.append(raw_detailed)

    # 3) Category path (usually empty in your data, but handle it)
    category_path = t.get("category_path") or ""
    if category_path and category_path != "":
        for part in category_path.split(">"):
            part = part.strip().lower()
            if part and part not in keys:
                keys.append(part)

    # 4) Merchant name heuristics (fallback for uncategorized)
    merchant = (
        raw.get("merchant_name")
        or t.get("name")
        or ""
    ).lower()
    
    if merchant:
        # Transportation
        if any(x in merchant for x in ["uber", "lyft", "taxi", "ride", "transit", "metro", "bus"]):
            keys.append("transportation")
        
        # Groceries
        if any(x in merchant for x in ["whole foods", "kroger", "heb", "h-e-b", "trader joe", 
                                        "walmart", "aldi", "safeway", "publix", "target"]):
            keys.append("groceries")
        
        # Dining
        if any(x in merchant for x in ["mcdonald", "starbucks", "cafe", "coffee", "pizza", 
                                        "restaurant", "grill", "bar", "chipotle", "subway", 
                                        "taco", "burger", "wendy", "chick-fil-a"]):
            keys.append("dining")
        
        # Entertainment
        if any(x in merchant for x in ["amc", "cinema", "theater", "spotify", "netflix", 
                                        "hulu", "disney", "apple music", "youtube"]):
            keys.append("entertainment")
        
        # Shopping
        if any(x in merchant for x in ["amazon", "ebay", "etsy", "mall", "best buy", "macys"]):
            keys.append("shopping")

    # 5) Normalize PFC strings to game buckets
    normalized: List[str] = []
    
    for k in keys:
        k_lower = k.lower()
        
        # Dining (food & drink)
        if any(s in k_lower for s in ["food_and_drink", "food & drink", "dining", 
                                       "restaurant", "fast_food", "coffee"]):
            if "dining" not in normalized:
                normalized.append("dining")
        
        # Groceries
        elif any(s in k_lower for s in ["grocery", "groceries", "supermarket"]):
            if "groceries" not in normalized:
                normalized.append("groceries")
        
        # Transportation
        elif any(s in k_lower for s in ["transport", "taxi", "ride", "gas", "fuel", 
                                         "parking", "tolls", "public_transit"]):
            if "transportation" not in normalized:
                normalized.append("transportation")
        
        # Entertainment (includes your ENTERTAINMENT_SPORTING_EVENTS...)
        elif any(s in k_lower for s in ["entertainment", "sporting_events", "amusement", 
                                         "recreation", "arts", "music", "movies"]):
            if "entertainment" not in normalized:
                normalized.append("entertainment")
        
        # Shopping (general merchandise)
        elif any(s in k_lower for s in ["shopping", "general_merchandise", "retail", 
                                         "online_marketplace", "discount_store"]):
            if "shopping" not in normalized:
                normalized.append("shopping")
        
        # Travel
        elif any(s in k_lower for s in ["travel", "airline", "hotel", "lodging", 
                                         "car_rental", "vacation"]):
            if "travel" not in normalized:
                normalized.append("travel")

    # Combine all keys (preserve original + normalized)
    result = []
    for item in keys + normalized:
        if item and item not in result:
            result.append(item)
    return result

def _fetch_txns(uid: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch transactions in date range [start_date, end_date)"""
    col = _tx_col(uid)
    q = (col.where("date", ">=", start_date)
            .where("date", "<", end_date)
            .order_by("date", direction=firestore.Query.DESCENDING))
    return [d.to_dict() or {} for d in q.stream()]

def _sum_by_category(txns: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate spending by normalized category (only positive amounts)"""
    agg: Dict[str, float] = defaultdict(float)
    
    for t in txns:
        amt = float(t.get("amount", 0.0) or 0.0)
        if amt <= 0:  # Only count spending (positive amounts)
            continue
        
        cats = _txn_category_keys(t)
        for cat in cats:
            if cat in GAME_CATEGORIES:
                agg[cat] += amt
    
    # Round to 2 decimal places
    return {k: round(v, 2) for k, v in agg.items()}

# ============================================================================
# Category Selection Logic
# ============================================================================

def _select_categories(spend_map: Dict[str, float]) -> Tuple[List[str], Dict[str, float]]:
    """
    Select up to 5 categories for the game:
    - 1 highest spend
    - 1 lowest spend (if available)
    - Up to 3 middle-range
    - Fill remaining with up to 2 zero-spend decoys
    
    Returns: (selected_categories, amounts_map)
    """
    active_cats = [(cat, amt) for cat, amt in spend_map.items() if amt > 0.01]
    active_cats.sort(key=lambda x: x[1], reverse=True)  # Sort by amount descending
    
    selected = []
    amounts = {}
    
    if len(active_cats) >= MAX_GAME_CATEGORIES:
        # Pick 1 highest, 1 lowest, 3 middle
        selected.append(active_cats[0][0])  # Highest
        selected.append(active_cats[-1][0])  # Lowest
        
        # 3 from middle range
        middle = active_cats[1:-1]
        if len(middle) >= 3:
            # Evenly space selections from middle
            indices = [len(middle) // 4, len(middle) // 2, 3 * len(middle) // 4]
            for idx in indices:
                selected.append(middle[idx][0])
        else:
            # Take all middle
            selected.extend([cat for cat, _ in middle])
        
        # Build amounts map
        for cat, amt in active_cats:
            if cat in selected:
                amounts[cat] = amt
                
    elif len(active_cats) >= MIN_ACTIVE_CATEGORIES:
        # Use all active categories
        for cat, amt in active_cats:
            selected.append(cat)
            amounts[cat] = amt
        
        # Add decoys to reach 5 total
        decoys_needed = min(MAX_GAME_CATEGORIES - len(selected), MAX_DECOY_CATEGORIES)
        if decoys_needed > 0:
            used_cats = set(selected)
            available_decoys = [c for c in GAME_CATEGORIES if c not in used_cats]
            decoys = random.sample(available_decoys, min(decoys_needed, len(available_decoys)))
            
            for decoy in decoys:
                selected.append(decoy)
                amounts[decoy] = 0.0
    
    return selected[:MAX_GAME_CATEGORIES], amounts

# ============================================================================
# Tile Generation
# ============================================================================

def _generate_tiles(categories: List[str], amounts: Dict[str, float]) -> Dict[str, Any]:
    """
    Generate shuffled category and amount tiles with unique IDs.
    
    Returns:
    {
        "category_tiles": [{"id": "cat_0", "label": "Dining"}, ...],
        "amount_tiles": [{"id": "amt_0", "value": 85.43, "label": "$85.43"}, ...],
        "truth_map": {"cat_0": "amt_2", ...}  # Internal only
    }
    """
    # Create category tiles
    category_tiles = []
    for i, cat in enumerate(categories):
        category_tiles.append({
            "id": f"cat_{i}",
            "label": cat.capitalize(),
            "category": cat
        })
    
    # Create amount tiles (matched to categories by index initially)
    amount_tiles = []
    truth_map = {}
    
    for i, cat in enumerate(categories):
        amt = amounts.get(cat, 0.0)
        amount_tiles.append({
            "id": f"amt_{i}",
            "value": amt,
            "label": f"${amt:.2f}"
        })
        truth_map[f"cat_{i}"] = f"amt_{i}"
    
    # Shuffle amount tiles only (categories stay in order initially)
    random.shuffle(amount_tiles)
    
    return {
        "category_tiles": category_tiles,
        "amount_tiles": amount_tiles,
        "truth_map": truth_map
    }

# ============================================================================
# Low Spend Message Generation
# ============================================================================

def _generate_low_spend_message() -> str:
    """
    Generate encouraging message for users with low spending.
    TODO: Integrate with OpenAI agent
    """
    # Placeholder - will be replaced with agent call
    messages = [
        "You haven't spent much recently — very responsible! 🌟",
        "Great job keeping your spending in check this week! 💪",
        "Impressive restraint! Your wallet thanks you. 🎉",
        "Low spending week detected — financial discipline at its finest! ✨",
        "You're crushing it with mindful spending! Keep it up! 🚀"
    ]
    return random.choice(messages)

# ============================================================================
# XP & Level System
# ============================================================================

def _xp_for_next_level(current_level: int) -> int:
    """Calculate XP needed to reach next level"""
    if current_level >= MAX_LEVEL:
        return 0
    # Inverse: xp = 10^(level/10) - 1
    return int(10 ** ((current_level + 1) / 10) - 1)

# ============================================================================
# Public API
# ============================================================================

def start_round(uid: str) -> Dict[str, Any]:
    """
    Start a new Financial Categories round.
    
    Returns either:
    - Playable game with tiles
    - Low-spend message with XP reward
    """
    db = get_db()
    game_ref = _game_ref(uid)
    
    # Fetch past 7 days of transactions (rolling window)
    week_start = _week_start_str()  # Monday 00:00 UTC
    
    # CHANGED: Fetch past 7 days of transactions (rolling window)
    now = datetime.now(timezone.utc)
    start_7d = to_yyyy_mm_dd(now - timedelta(days=7))  # 7 days ago
    end_7d = to_yyyy_mm_dd(now + timedelta(days=1))     # tomorrow (includes today)
    
    txns = _fetch_txns(uid, start_7d, end_7d)
    spend_by_cat = _sum_by_category(txns)
    
    # Check if enough active categories
    active_cats = {k: v for k, v in spend_by_cat.items() if v > 0.01}
    
    if len(active_cats) < MIN_ACTIVE_CATEGORIES:
        # Award XP for responsible spending
        snap = game_ref.get()
        state = snap.to_dict() if snap.exists else {}
        
        progression_result = progression.add_xp(uid, FULL_ROUND_XP, source="categories_low_spend")
        
        current_streak = int(state.get("streak", 0))
        new_streak = current_streak + 1
        
        game_ref.set({
            "streak": new_streak,
            "last_played": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        
        return {
            "ok": True,
            "can_play": False,
            "message": _generate_low_spend_message(),
            "xp_awarded": FULL_ROUND_XP,
            "progression": {
                "total_xp": progression_result.get("new_xp", 0),
                "level": progression_result.get("new_level", 1),
                "level_up": progression_result.get("level_up", False),
                "rank": progression_result.get("new_rank", "Penny Pincher"),
                "rank_up": progression_result.get("rank_up", False)
            },
            "streak": new_streak,
            "streak_maintained": True
        }
    
    # Select categories and generate tiles
    selected_cats, amounts = _select_categories(spend_by_cat)
    tiles = _generate_tiles(selected_cats, amounts)
    
    # Store round state
    round_data = {
        "round_id": datetime.now(timezone.utc).isoformat(),
        "week_start": week_start,
        "categories": selected_cats,
        "amounts": amounts,
        "truth_map": tiles["truth_map"],
        "tries_remaining": TRIES_PER_ROUND,
        "correct_matches": [],
        "started_at": firestore.SERVER_TIMESTAMP,
    }
    
    game_ref.set({
        "current_round": round_data,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    return {
        "ok": True,
        "can_play": True,
        "round_id": round_data["round_id"],
        "category_tiles": tiles["category_tiles"],
        "amount_tiles": tiles["amount_tiles"],
        "tries_remaining": TRIES_PER_ROUND,
    }

def submit_match(uid: str, category_id: str, amount_id: str) -> Dict[str, Any]:
    """
    Submit a single match attempt.
    
    Returns:
    - correct: bool
    - tries_remaining: int
    - round_complete: bool (if all matched or out of tries)
    """
    db = get_db()
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {"ok": False, "error": "No active round. Call /start first."}
    
    state = snap.to_dict() or {}
    round_data = state.get("current_round", {})
    
    if not round_data:
        return {"ok": False, "error": "No active round."}
    
    truth_map = round_data.get("truth_map", {})
    correct_matches = round_data.get("correct_matches", [])
    tries_remaining = round_data.get("tries_remaining", 0)
    
    # Check if already matched
    if category_id in [m["category_id"] for m in correct_matches]:
        return {"ok": False, "error": "Category already matched."}
    
    # Check if out of tries
    if tries_remaining <= 0:
        return {"ok": False, "error": "No tries remaining."}
    
    # Validate match
    is_correct = truth_map.get(category_id) == amount_id
    
    if is_correct:
        correct_matches.append({
            "category_id": category_id,
            "amount_id": amount_id
        })
    else:
        tries_remaining -= 1
    
    # Check if round complete
    total_categories = len(truth_map)
    round_complete = (len(correct_matches) == total_categories) or (tries_remaining == 0)
    
    # FIX: Update the entire current_round object instead of using dot notation
    # This ensures nested fields are properly updated in Firestore
    round_data["correct_matches"] = correct_matches
    round_data["tries_remaining"] = tries_remaining
    
    game_ref.set({
        "current_round": round_data,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    result = {
        "ok": True,
        "correct": is_correct,
        "tries_remaining": tries_remaining,
        "round_complete": round_complete,
        "correct_count": len(correct_matches),
        "total_categories": total_categories,
    }
    
    # If round complete, finalize
    if round_complete:
        finalize_result = _finalize_round(uid, game_ref, round_data, correct_matches)
        result.update(finalize_result)
    
    return result

def _finalize_round(uid: str, game_ref, round_data: Dict, correct_matches: List[Dict]) -> Dict[str, Any]:
    """
    Finalize round: calculate XP, update streak, store history.
    """
    db = get_db()
    snap = game_ref.get()
    state = snap.to_dict() if snap.exists else {}
    
    # Calculate XP
    num_correct = len(correct_matches)
    xp_earned = num_correct * XP_PER_CORRECT_MATCH
    
    # Award XP to unified progression system
    progression_result = progression.add_xp(uid, xp_earned, source="categories")
    
    current_streak = int(state.get("streak", 0))
    
    # Update streak
    all_correct = num_correct == len(round_data.get("truth_map", {}))
    new_streak = current_streak + 1 if all_correct else 0
    
    # Build reveal (sorted by amount descending)
    truth_map = round_data.get("truth_map", {})
    amounts = round_data.get("amounts", {})
    categories = round_data.get("categories", [])
    
    reveal = []
    for cat in categories:
        cat_id = None
        for cid, aid in truth_map.items():
            if cid.startswith("cat_") and game_ref.get().to_dict().get("current_round", {}).get("categories", [])[int(cid.split("_")[1])] == cat:
                cat_id = cid
                break
        
        reveal.append({
            "category": cat.capitalize(),
            "amount": amounts.get(cat, 0.0),
            "label": f"${amounts.get(cat, 0.0):.2f}"
        })
    
    # Sort by amount descending
    reveal.sort(key=lambda x: x["amount"], reverse=True)
    
    # Store history
    history_entry = {
        "round_id": round_data.get("round_id"),
        "week_start": round_data.get("week_start"),
        "correct_matches": num_correct,
        "total_categories": len(truth_map),
        "accuracy": round(num_correct / len(truth_map), 2) if truth_map else 0,
        "xp_earned": xp_earned,
        "completed_at": firestore.SERVER_TIMESTAMP,
    }
    
    # Update game state
    game_ref.set({
        "streak": new_streak,
        "last_played": firestore.SERVER_TIMESTAMP,
        "current_round": firestore.DELETE_FIELD,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    
    # Store in history subcollection
    game_ref.collection("history").add(history_entry)
    
    return {
        "xp_earned": xp_earned,
        "progression": {
            "total_xp": progression_result.get("new_xp", 0),
            "level": progression_result.get("new_level", 1),
            "level_up": progression_result.get("level_up", False),
            "rank": progression_result.get("new_rank", "Penny Pincher"),
            "rank_up": progression_result.get("rank_up", False)
        },
        "streak": new_streak,
        "accuracy": history_entry["accuracy"],
        "reveal": reveal,
        "all_correct": all_correct,
    }

def get_state(uid: str) -> Dict[str, Any]:
    """Get current game state for user"""
    game_ref = _game_ref(uid)
    snap = game_ref.get()
    
    if not snap.exists:
        return {
            "ok": True,
            "streak": 0,
            "has_active_round": False
        }
    
    state = snap.to_dict() or {}
    
    return {
        "ok": True,
        "streak": state.get("streak", 0),
        "has_active_round": bool(state.get("current_round")),
        "current_round": state.get("current_round"),
    }
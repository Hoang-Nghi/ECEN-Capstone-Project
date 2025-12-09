# services/minigame_service/progression.py
"""
Unified user progression system for XP, ranks, and levels.
Awards XP from all minigames and tracks overall user progress.

Rank Progression:
- Penny Pincher (0 XP) - Copper/Bronze
- Savvy Saver (500 XP) - Bronze  
- Budget Master (1,500 XP) - Silver
- Portfolio Pro (3,500 XP) - Gold
- Investment Expert (7,000 XP) - Platinum
- Finance Legend (12,000 XP) - Diamond
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import math

from firebase_admin import firestore
from .utils import get_db

# ============================================================================
# Configuration
# ============================================================================

RANKS = [
    {"name": "Penny Pincher", "threshold": 0, "color": "copper", "tier": "bronze"},
    {"name": "Savvy Saver", "threshold": 500, "color": "bronze", "tier": "bronze"},
    {"name": "Budget Master", "threshold": 1500, "color": "silver", "tier": "silver"},
    {"name": "Portfolio Pro", "threshold": 3500, "color": "gold", "tier": "gold"},
    {"name": "Investment Expert", "threshold": 7000, "color": "platinum", "tier": "platinum"},
    {"name": "Finance Legend", "threshold": 12000, "color": "diamond", "tier": "diamond"}
]

MAX_LEVEL = 100

# ============================================================================
# Firestore Helpers
# ============================================================================

def _progression_ref(uid: str):
    """Reference to user's progression document"""
    return get_db().collection("users").document(uid).collection("profile").document("progression")

# ============================================================================
# Level Calculation
# ============================================================================

def calculate_level(xp: int) -> int:
    """
    Calculate level from XP using square root progression.
    This creates a smooth, achievable curve:
    
    - Level 10 = 200 XP (~1 week)
    - Level 20 = 800 XP (~1 month)
    - Level 30 = 1,800 XP (~2 months)
    - Level 50 = 5,000 XP (~6 months)
    - Level 75 = 11,250 XP (~1 year)
    - Level 100 = 20,000 XP (~2 years)
    
    Formula: level = sqrt(xp / 2)
    Inverse: xp_needed = level^2 * 2
    """
    if xp <= 0:
        return 1
    
    level = int(math.sqrt(xp / 2))
    return min(max(1, level), MAX_LEVEL)

def xp_for_level(level: int) -> int:
    """Calculate XP needed to reach a specific level"""
    if level <= 1:
        return 0
    if level >= MAX_LEVEL:
        return level * level * 2
    return level * level * 2

def xp_for_next_level(current_level: int) -> int:
    """Calculate XP needed to reach next level"""
    if current_level >= MAX_LEVEL:
        return 0
    return xp_for_level(current_level + 1)

# ============================================================================
# Rank Calculation
# ============================================================================

def calculate_rank(xp: int) -> Dict[str, Any]:
    """
    Determine current rank and progress to next rank.
    
    Returns:
    {
        "name": "Budget Master",
        "color": "silver",
        "tier": "silver",
        "threshold": 1500,
        "next_rank": {"name": "Portfolio Pro", ...} or None,
        "progress": 0.45,  # 0.0 to 1.0
        "xp_in_rank": 450,
        "xp_for_next": 2000
    }
    """
    # Find current rank (highest threshold user has passed)
    current_rank = RANKS[0]
    next_rank = None
    
    for i, rank in enumerate(RANKS):
        if xp >= rank["threshold"]:
            current_rank = rank
            if i + 1 < len(RANKS):
                next_rank = RANKS[i + 1]
        else:
            break
    
    # Calculate progress to next rank
    if next_rank:
        xp_in_rank = xp - current_rank["threshold"]
        xp_for_next = next_rank["threshold"] - current_rank["threshold"]
        progress = xp_in_rank / xp_for_next if xp_for_next > 0 else 1.0
    else:
        # Max rank reached
        xp_in_rank = xp - current_rank["threshold"]
        xp_for_next = 0
        progress = 1.0
    
    return {
        "name": current_rank["name"],
        "color": current_rank["color"],
        "tier": current_rank["tier"],
        "threshold": current_rank["threshold"],
        "next_rank": next_rank,
        "progress": round(progress, 3),
        "xp_in_rank": xp_in_rank,
        "xp_for_next": xp_for_next
    }

# ============================================================================
# Public API
# ============================================================================

def add_xp(uid: str, amount: int, source: str = "game") -> Dict[str, Any]:
    """
    Award XP to user and update progression.
    
    Args:
        uid: User ID
        amount: XP to award (positive integer)
        source: Source of XP ("quiz", "categories", "detective", etc.)
    
    Returns:
        Updated progression state including any rank/level ups
    """
    if amount <= 0:
        return {"ok": False, "error": "XP amount must be positive"}
    
    db = get_db()
    prog_ref = _progression_ref(uid)
    
    # Use transaction for atomic read-modify-write
    @firestore.transactional
    def update_progression(transaction):
        snap = prog_ref.get(transaction=transaction)
        
        # Get current state or initialize
        if snap.exists:
            data = snap.to_dict() or {}
            old_xp = int(data.get("total_xp", 0))
            old_level = int(data.get("level", 1))
            old_rank = data.get("rank", {})
            games_played = int(data.get("games_played", 0))
        else:
            old_xp = 0
            old_level = 1
            old_rank = {"name": "Penny Pincher"}
            games_played = 0
        
        # Calculate new values
        new_xp = old_xp + amount
        new_level = calculate_level(new_xp)
        new_rank_data = calculate_rank(new_xp)
        
        # Check for level up
        level_up = new_level > old_level
        
        # Check for rank up
        rank_up = new_rank_data["name"] != old_rank.get("name")
        
        # Update document
        update_data = {
            "total_xp": new_xp,
            "level": new_level,
            "rank": {
                "name": new_rank_data["name"],
                "color": new_rank_data["color"],
                "tier": new_rank_data["tier"],
                "threshold": new_rank_data["threshold"]
            },
            "games_played": games_played + 1,
            "last_xp_source": source,
            "last_xp_amount": amount,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        
        transaction.set(prog_ref, update_data, merge=True)
        
        return {
            "ok": True,
            "xp_awarded": amount,
            "old_xp": old_xp,
            "new_xp": new_xp,
            "old_level": old_level,
            "new_level": new_level,
            "level_up": level_up,
            "old_rank": old_rank.get("name"),
            "new_rank": new_rank_data["name"],
            "rank_up": rank_up
        }
    
    transaction = db.transaction()
    return update_progression(transaction)

def get_profile(uid: str) -> Dict[str, Any]:
    """
    Get user's complete progression profile.
    Used for the UI bubble and profile displays.
    
    Returns:
    {
        "ok": true,
        "total_xp": 1750,
        "level": 29,
        "rank": {
            "name": "Budget Master",
            "color": "silver",
            "tier": "silver",
            "progress": 0.125,
            "xp_in_rank": 250,
            "xp_for_next_rank": 2000
        },
        "next_rank": {
            "name": "Portfolio Pro",
            "xp_needed": 1750
        },
        "next_level": {
            "level": 30,
            "xp_needed": 50
        }
    }
    """
    prog_ref = _progression_ref(uid)
    snap = prog_ref.get()
    
    # Initialize if doesn't exist
    if not snap.exists:
        initial_rank = calculate_rank(0)
        return {
            "ok": True,
            "total_xp": 0,
            "level": 1,
            "rank": {
                "name": initial_rank["name"],
                "color": initial_rank["color"],
                "tier": initial_rank["tier"],
                "progress": 0.0,
                "xp_in_rank": 0,
                "xp_for_next_rank": initial_rank["xp_for_next"]
            },
            "next_rank": {
                "name": initial_rank["next_rank"]["name"] if initial_rank["next_rank"] else None,
                "xp_needed": initial_rank["xp_for_next"]
            },
            "next_level": {
                "level": 2,
                "xp_needed": xp_for_level(2)
            },
            "games_played": 0
        }
    
    data = snap.to_dict() or {}
    total_xp = int(data.get("total_xp", 0))
    current_level = int(data.get("level", 1))
    
    # Calculate rank info
    rank_info = calculate_rank(total_xp)
    
    # Build response
    result = {
        "ok": True,
        "total_xp": total_xp,
        "level": current_level,
        "rank": {
            "name": rank_info["name"],
            "color": rank_info["color"],
            "tier": rank_info["tier"],
            "progress": rank_info["progress"],
            "xp_in_rank": rank_info["xp_in_rank"],
            "xp_for_next_rank": rank_info["xp_for_next"]
        },
        "games_played": data.get("games_played", 0),
        "last_played": data.get("updatedAt")
    }
    
    # Add next rank info if not max rank
    if rank_info["next_rank"]:
        result["next_rank"] = {
            "name": rank_info["next_rank"]["name"],
            "color": rank_info["next_rank"]["color"],
            "tier": rank_info["next_rank"]["tier"],
            "xp_needed": rank_info["xp_for_next"]
        }
    else:
        result["next_rank"] = None
    
    # Add next level info if not max level
    if current_level < MAX_LEVEL:
        next_level_xp = xp_for_next_level(current_level)
        result["next_level"] = {
            "level": current_level + 1,
            "xp_needed": next_level_xp - total_xp
        }
    else:
        result["next_level"] = None
    
    return result

def get_rank_list() -> List[Dict[str, Any]]:
    """
    Get list of all ranks for display purposes.
    Useful for showing rank progression UI.
    """
    return [
        {
            "name": r["name"],
            "color": r["color"],
            "tier": r["tier"],
            "threshold": r["threshold"]
        }
        for r in RANKS
    ]

def get_leaderboard(limit: int = 10) -> Dict[str, Any]:
    """
    Get top players by XP (optional feature).
    
    Args:
        limit: Number of top players to return
    
    Returns:
        List of top players with their progression stats
    """
    db = get_db()
    
    # Query top users by total_xp
    query = (db.collection_group("progression")
             .order_by("total_xp", direction=firestore.Query.DESCENDING)
             .limit(limit))
    
    leaderboard = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        rank_info = calculate_rank(data.get("total_xp", 0))
        
        leaderboard.append({
            "user_id": doc.reference.parent.parent.id,  # Get user ID from path
            "total_xp": data.get("total_xp", 0),
            "level": data.get("level", 1),
            "rank": rank_info["name"],
            "rank_color": rank_info["color"]
        })
    
    return {
        "ok": True,
        "leaderboard": leaderboard,
        "count": len(leaderboard)
    }
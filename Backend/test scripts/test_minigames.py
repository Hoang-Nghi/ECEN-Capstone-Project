#!/usr/bin/env python3
"""
Test all minigames without UI - simulates API calls directly.

Usage: python test_minigames.py <user_id>
Example: python test_minigames.py ZQ2eHJdpGAN9Uyu7UZYyXP0kZmY2
"""

import sys
import json
from services.firebase import get_db
from services.minigame_service import smart_saver_quiz as quiz
from services.minigame_service import spend_detective as detective
from services.minigame_service import financial_categories as fin_cat

def print_separator(title=""):
    print("\n" + "="*70)
    if title:
        print(f" {title}")
        print("="*70)

def print_json(data, indent=2):
    print(json.dumps(data, indent=indent, default=str))

def test_user_data(uid):
    """Check if user has transactions."""
    print_separator(f"Checking User Data: {uid}")
    
    db = get_db()
    tx_col = db.collection("users").document(uid).collection("transactions")
    
    # Count transactions
    txns = list(tx_col.limit(100).stream())
    print(f"✓ Total transactions: {len(txns)}")
    
    if len(txns) > 0:
        # Show first few
        print("\nSample transactions:")
        for i, doc in enumerate(txns[:3]):
            data = doc.to_dict()
            print(f"  {i+1}. {data.get('date')} - {data.get('name')} - ${data.get('amount')}")
    else:
        print("   No transactions found!")
        return False
    
    return True

def test_smart_saver_quiz(uid):
    """Test Smart Saver Quiz game."""
    print_separator("Testing Smart Saver Quiz")
    
    # Get current state
    print("\n1. Getting current state...")
    state = quiz.get_state(uid)
    print_json(state)
    
    # Start new quiz
    print("\n2. Starting new quiz...")
    result = quiz.new_set(uid)
    
    if not result.get("can_play"):
        print(f"\n   Cannot play: {result.get('message')}")
        if result.get("insufficient_data"):
            print(f"   But you got {result.get('xp_awarded')} XP anyway! 🎁")
        return
    
    questions = result.get("questions", [])
    print(f"\n✓ Got {len(questions)} questions")
    print(f"   Difficulty: {result.get('difficulty')}")
    
    # Show questions
    for i, q in enumerate(questions):
        print(f"\n   Q{i+1}: {q.get('question')}")
        for j, choice in enumerate(q.get('choices', [])):
            print(f"      {j}. {choice}")
    
    # Simulate answering (always pick first choice for testing)
    print("\n3. Submitting answers (picking first choice for all)...")
    answers = [0] * len(questions)  # All zeros
    
    submit_result = quiz.submit(uid, answers)
    
    print(f"\n✓ Results:")
    print(f"   Score: {submit_result.get('score')}/{submit_result.get('total')}")
    print(f"   Accuracy: {submit_result.get('accuracy')*100:.0f}%")
    print(f"   XP Earned: +{submit_result.get('xp_earned')}")
    print(f"   Total XP: {submit_result.get('total_xp')}")
    print(f"   Level: {submit_result.get('level')}")
    print(f"   Streak: {submit_result.get('streak')} weeks")
    
    if submit_result.get('difficulty_changed'):
        print(f"   🎓 Difficulty: {submit_result.get('difficulty_before')} → {submit_result.get('difficulty_after')}")
    
    # Show explanations
    explanations = submit_result.get('explanations', [])
    if explanations:
        print("\n    Explanations:")
        for exp in explanations:
            print(f"      • {exp}")

def test_spend_detective(uid):
    """Test Spend Detective game."""
    print_separator("Testing Spend Detective")
    
    # Get current state
    print("\n1. Getting current state...")
    state = detective.get_state(uid)
    print_json(state)
    
    # Start new round
    print("\n2. Starting new round...")
    result = detective.start_round(uid)
    
    if not result.get("can_play"):
        print(f"\n   Cannot play: {result.get('message')}")
        if result.get("insufficient_data"):
            print(f"   But you got {result.get('xp_awarded')} XP anyway! 🎁")
        return
    
    transactions = result.get("transactions", [])
    print(f"\n✓ Got {len(transactions)} transactions to analyze")
    print(f"   Tries remaining: {result.get('tries_remaining')}")
    
    # Show transactions
    for i, tx in enumerate(transactions):
        print(f"\n   {i+1}. {tx.get('date')} - {tx.get('merchant_name')}")
        print(f"      ${tx.get('amount'):.2f} - {tx.get('category')}")
    
    # Simulate guessing (pick first 2 transactions as anomalies)
    print("\n3. Submitting guess (picking first 2 as anomalies)...")
    selected_ids = [transactions[0]["id"], transactions[1]["id"]]
    
    submit_result = detective.submit_guess(uid, selected_ids)
    
    print(f"\n✓ Results:")
    print(f"   Correct identifications: {submit_result.get('new_correct')}")
    print(f"   False positives: {submit_result.get('new_false_positives')}")
    print(f"   Total correct so far: {submit_result.get('total_correct')}/{submit_result.get('total_anomalies')}")
    print(f"   Tries remaining: {submit_result.get('tries_remaining')}")
    
    # If round complete
    if submit_result.get('round_complete'):
        print(f"\n   🎮 Round Complete!")
        print(f"   XP Earned: +{submit_result.get('xp_earned')}")
        print(f"   Total XP: {submit_result.get('total_xp')}")
        print(f"   Level: {submit_result.get('level')}")
        print(f"   Streak: {submit_result.get('streak')}")
        print(f"   Accuracy: {submit_result.get('accuracy')*100:.0f}%")
        
        # Show reveals
        reveal = submit_result.get('reveal', [])
        if reveal:
            print("\n    Anomalies Found:")
            for item in reveal:
                if item.get('was_anomaly'):
                    status = "✓ Found" if item.get('found_by_user') else "✗ Missed"
                    print(f"      {status}: Transaction {item.get('transaction_id')}")
                    for reason in item.get('reasons', []):
                        print(f"         • {reason}")

def test_financial_categories(uid):
    """Test Financial Categories game."""
    print_separator("Testing Financial Categories")
    
    # Get current state
    print("\n1. Getting current state...")
    state = fin_cat.get_state(uid)
    print_json(state)
    
    # Start new round
    print("\n2. Starting new round...")
    result = fin_cat.start_round(uid)
    
    if not result.get("can_play"):
        print(f"\n   Cannot play: {result.get('message')}")
        if result.get("insufficient_data"):
            print(f"   But you got {result.get('xp_awarded')} XP anyway! 🎁")
        return
    
    category_tiles = result.get("category_tiles", [])
    amount_tiles = result.get("amount_tiles", [])
    
    print(f"\n✓ Got {len(category_tiles)} categories and {len(amount_tiles)} amounts")
    print(f"   Tries remaining: {result.get('tries_remaining')}")
    
    # Show tiles
    print("\n   Categories:")
    for tile in category_tiles:
        print(f"      {tile.get('id')}: {tile.get('label')}")
    
    print("\n   Amounts:")
    for tile in amount_tiles:
        print(f"      {tile.get('id')}: {tile.get('label')}")
    
    # Simulate matching (just match first cat to first amount)
    print("\n3. Submitting match (matching first category to first amount)...")
    cat_id = category_tiles[0]["id"]
    amt_id = amount_tiles[0]["id"]
    
    match_result = fin_cat.submit_match(uid, cat_id, amt_id)
    
    print(f"\n✓ Match result:")
    print(f"   Correct: {match_result.get('correct')}")
    print(f"   Tries remaining: {match_result.get('tries_remaining')}")
    print(f"   Progress: {match_result.get('correct_count')}/{match_result.get('total_categories')}")
    
    # If round complete
    if match_result.get('round_complete'):
        print(f"\n   🎮 Round Complete!")
        print(f"   XP Earned: +{match_result.get('xp_earned')}")
        print(f"   Total XP: {match_result.get('total_xp')}")
        print(f"   Level: {match_result.get('level')}")
        print(f"   Streak: {match_result.get('streak')}")
        print(f"   All Correct: {match_result.get('all_correct')}")
        
        # Show reveal
        reveal = match_result.get('reveal', [])
        if reveal:
            print("\n    Correct Order (highest → lowest):")
            for i, item in enumerate(reveal):
                print(f"      {i+1}. {item.get('category')}: {item.get('label')}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_minigames.py <user_id>")
        print("\nExample:")
        print("  python test_minigames.py ZQ2eHJdpGAN9Uyu7UZYyXP0kZmY2")
        sys.exit(1)
    
    uid = sys.argv[1]
    
    print_separator(f"🎮 Testing Minigames for User: {uid}")
    
    try:
        # Check user data first
        has_data = test_user_data(uid)
        
        if not has_data:
            print("\n  User has no transactions. Cannot test games.")
            print("\nRun this first:")
            print(f"  python copy_user_data_simple.py {uid}")
            sys.exit(1)
        
        # Test each game
        print("\n")
        test_smart_saver_quiz(uid)
        
        print("\n")
        test_spend_detective(uid)
        
        print("\n")
        test_financial_categories(uid)
        
        print_separator("  All Tests Complete!")
        
    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

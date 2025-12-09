#!/usr/bin/env python3
"""
Test Spend Detective Game Locally
Updated to match the new spend_detective.py API
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Initialize Firebase FIRST before importing anything else
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    """Initialize Firebase Admin SDK"""
    if firebase_admin._apps:
        return  # Already initialized
    
    # Try to find credentials
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print(f"✓ Firebase initialized from: {cred_path}")
        return
    
    # Try firebase/credentials folder
    cred_dir = Path(__file__).parent / "firebase" / "credentials"
    if cred_dir.exists():
        json_files = list(cred_dir.glob("*.json"))
        if json_files:
            cred = credentials.Certificate(str(json_files[0]))
            firebase_admin.initialize_app(cred)
            print(f"✓ Firebase initialized from: {json_files[0]}")
            return
    
    # Last resort: default credentials (works on GCP)
    try:
        firebase_admin.initialize_app()
        print("✓ Firebase initialized with default credentials")
        return
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        print("\nTroubleshooting:")
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("2. Or place your service account JSON in firebase/credentials/")
        sys.exit(1)

# Initialize Firebase BEFORE importing spend_detective
init_firebase()

# NOW import spend_detective (which uses get_db())
from services.minigame_service import spend_detective


def test_spend_detective(uid: str):
    """Test the spend detective game flow."""
    
    print("=" * 70)
    print("🕵️ TESTING SPEND DETECTIVE GAME")
    print("=" * 70)
    print(f"User ID: {uid}\n")
    
    # Test 1: Start a round
    print("1️⃣  Starting a new round...")
    print("-" * 70)
    
    try:
        result = spend_detective.start_round(uid)
    except Exception as e:
        print(f"❌ EXCEPTION during start_round: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if not result.get("ok"):
        print(f"❌ FAILED to start round")
        print(f"   Error: {result.get('error')}")
        print(f"   Found: {result.get('found', 0)} transactions")
        print(f"   Needed: {result.get('needed', 3)} transactions")
        print("\n💡 Troubleshooting:")
        print("   - Make sure transactions exist in Firestore")
        print("   - Run: python debug_transactions.py")
        print("   - Check that Firestore index is created")
        return False
    
    print(f"✅ Round started successfully!")
    
    # Handle different response formats
    total_tx = result.get('total_transactions') or len(result.get('round', []))
    total_anomalies = result.get('anomalies_this_round') or result.get('total_anomalies')
    tries = result.get('tries_remaining', 3)
    found = result.get('found_count', 0)
    
    print(f"   Total transactions in round: {total_tx}")
    print(f"   Anomalies hidden in round: {total_anomalies}")
    print(f"   Tries remaining: {tries}")
    print(f"   Already found: {found}")
    
    round_data = result.get("round", [])
    if not round_data:
        print("❌ No transactions in round!")
        return False
    
    print(f"\n   Transactions to analyze:")
    print("-" * 70)
    for i, tx in enumerate(round_data, 1):
        merchant = tx.get('merchant_name', 'Unknown')
        amount = tx.get('amount', 0.0)
        date = tx.get('date', 'Unknown')
        category = tx.get('category', 'Unknown')
        print(f"   {i}. {merchant:<30s} ${amount:>7.2f}  [{date}]")
        print(f"      Category: {category}")
    
    # Test 2: Submit a guess
    print(f"\n2️⃣  Submitting a test guess...")
    print("-" * 70)
    
    # Strategy: Guess the transactions with highest amounts as anomalies
    sorted_by_amount = sorted(round_data, key=lambda t: t.get('amount', 0), reverse=True)
    selected_ids = [tx["id"] for tx in sorted_by_amount[:2]]
    
    print(f"   Guessing these {len(selected_ids)} highest amounts are anomalies:")
    for tx_id in selected_ids:
        tx = next(t for t in round_data if t["id"] == tx_id)
        print(f"   - {tx['merchant_name']}: ${tx['amount']:.2f}")
    
    try:
        # NOTE: The new API uses submit_guess() not submit()
        submit_result = spend_detective.submit_guess(uid, selected_ids)
    except Exception as e:
        print(f"❌ EXCEPTION during submit_guess: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if not submit_result.get("ok"):
        print(f"❌ FAILED to submit guess")
        print(f"   Error: {submit_result.get('error')}")
        return False
    
    print(f"\n✅ Guess submitted successfully!")
    print("-" * 70)
    print(f"   📊 Results:")
    print(f"   ✓ New correct identifications: {submit_result.get('new_correct', 0)}")
    print(f"   ✗ New false positives: {submit_result.get('new_false_positives', 0)}")
    print(f"   ⊙ Already found (duplicates): {submit_result.get('already_found', 0)}")
    print(f"   📈 Total found so far: {submit_result.get('total_correct', 0)}/{submit_result.get('total_anomalies', 0)}")
    print(f"   🎯 Tries remaining: {submit_result.get('tries_remaining', 0)}")
    
    # Check if round is complete
    is_complete = submit_result.get('round_complete', False)
    all_found = submit_result.get('all_found', False)
    
    if is_complete:
        print(f"\n   🎮 ROUND COMPLETE!")
        if all_found:
            print(f"   🎉 You found all anomalies!")
        else:
            print(f"   😔 Out of tries or game ended")
        
        # Show final results if available
        if 'xp_earned' in submit_result:
            print(f"\n   Final Results:")
            print(f"   - XP Earned: {submit_result.get('xp_earned', 0)}")
            print(f"   - Total XP: {submit_result.get('total_xp', 0)}")
            print(f"   - Level: {submit_result.get('level', 1)}")
            print(f"   - Streak: {submit_result.get('streak', 0)}")
            print(f"   - Accuracy: {submit_result.get('accuracy', 0):.0%}")
            print(f"   - Feedback: {submit_result.get('feedback', '')}")
    else:
        print(f"\n   ⏳ Round continues... make another guess if you have tries left!")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED! Spend Detective is working correctly.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    # Get user ID from environment or prompt
    test_uid = os.getenv("TEST_USER_ID")
    
    if not test_uid:
        test_uid = input("Enter user_id (Firebase Auth UID): ").strip()
        if not test_uid:
            print("❌ No user ID provided")
            sys.exit(1)
    
    print()
    success = test_spend_detective(test_uid)
    
    if success:
        print("\n🎮 Ready to test in your app!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Check the output above for details.")
        sys.exit(1)
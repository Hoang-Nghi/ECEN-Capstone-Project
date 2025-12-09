#!/usr/bin/env python3
"""
Test script for analytics service.
Tests all analytics endpoints with real data.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import firebase_admin
from firebase_admin import credentials

# Initialize Firebase
def init_firebase():
    if firebase_admin._apps:
        return
    
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print(f"✓ Firebase initialized from: {cred_path}")
        return
    
    cred_dir = Path(__file__).parent / "firebase" / "credentials"
    if cred_dir.exists():
        json_files = list(cred_dir.glob("*.json"))
        if json_files:
            cred = credentials.Certificate(str(json_files[0]))
            firebase_admin.initialize_app(cred)
            print(f"✓ Firebase initialized from: {json_files[0]}")
            return
    
    firebase_admin.initialize_app()
    print("✓ Firebase initialized with default credentials")

init_firebase()

from services import analytics

def test_analytics(uid: str):
    """Test all analytics functions."""
    
    print("=" * 70)
    print(" TESTING ANALYTICS SERVICE")
    print("=" * 70)
    print(f"User ID: {uid}\n")
    
    # Test 1: Spending Over Time - Week
    print(" Testing spending over time (week view)...")
    print("-" * 70)
    result = analytics.get_spending_over_time(uid, "week", 4)
    if result.get("ok"):
        print("  Weekly spending (last 4 weeks):")
        for item in result["data"]:
            print(f"   {item['label']}: ${item['amount']:>8.2f}")
        print(f"   {'─' * 40}")
        print(f"   Total: ${result['total']:>8.2f}\n")
    else:
        print(f"  Failed: {result.get('error')}\n")
    
    # Test 2: Spending Over Time - Day
    print(" Testing spending over time (day view)...")
    print("-" * 70)
    result = analytics.get_spending_over_time(uid, "day", 7)
    if result.get("ok"):
        print("  Daily spending (last 7 days):")
        for item in result["data"]:
            print(f"   {item['label']}: ${item['amount']:>8.2f}")
        print(f"   {'─' * 40}")
        print(f"   Total: ${result['total']:>8.2f}\n")
    else:
        print(f"  Failed: {result.get('error')}\n")
    
    # Test 3: Spending Over Time - Month
    print(" Testing spending over time (month view)...")
    print("-" * 70)
    result = analytics.get_spending_over_time(uid, "month", 3)
    if result.get("ok"):
        print("  Monthly spending (last 3 months):")
        for item in result["data"]:
            print(f"   {item['label']}: ${item['amount']:>8.2f}")
        print(f"   {'─' * 40}")
        print(f"   Total: ${result['total']:>8.2f}\n")
    else:
        print(f"  Failed: {result.get('error')}\n")
    
    # Test 4: Spending by Category
    print(" Testing spending by category...")
    print("-" * 70)
    result = analytics.get_spending_by_category(uid, 30)
    if result.get("ok"):
        print("  Category breakdown (last 30 days):")
        for cat in result["categories"][:5]:  # Top 5
            bar = "█" * int(cat['percentage'] / 2)  # Visual bar
            print(f"   {cat['name']:<25s} ${cat['amount']:>8.2f} ({cat['percentage']:>5.1f}%) {bar}")
        if len(result["categories"]) > 5:
            others = result["categories"][5:]
            others_total = sum(c['amount'] for c in others)
            others_pct = sum(c['percentage'] for c in others)
            print(f"   {'Others':<25s} ${others_total:>8.2f} ({others_pct:>5.1f}%)")
        print(f"   {'─' * 60}")
        print(f"   {'TOTAL':<25s} ${result['total']:>8.2f}\n")
    else:
        print(f"  Failed\n")
    
    # Test 5: Recent Transactions
    print(" Testing recent transactions...")
    print("-" * 70)
    result = analytics.get_recent_transactions(uid, 10)
    if result.get("ok"):
        print(f"  Recent transactions (showing {result['count']}):")
        for tx in result["transactions"]:
            pending = " [PENDING]" if tx.get('pending') else ""
            print(f"   {tx['date']} | {tx['merchant_name']:<25s} | ${tx['amount']:>7.2f} | {tx['category']}{pending}")
        print()
    else:
        print(f"  Failed\n")
    
    # Test 6: Spending Summary
    print(" Testing spending summary...")
    print("-" * 70)
    result = analytics.get_spending_summary(uid)
    if result.get("ok"):
        print(" Spending summary:")
        print(f"   This week:    ${result['this_week']:>8.2f}")
        print(f"   This month:   ${result['this_month']:>8.2f}")
        print(f"   Last month:   ${result['last_month']:>8.2f}")
        print(f"   Avg daily:    ${result['average_daily']:>8.2f}")
        if result.get('top_category'):
            print(f"   Top category: {result['top_category']['name']} (${result['top_category']['amount']:.2f})")
        print()
    else:
        print(f"Failed\n")
    
    # Test 7: Budget Progress
    print("Testing budget progress...")
    print("-" * 70)
    result = analytics.get_budget_progress(uid)
    if result.get("ok"):
        print(" Budget progress:")
        print(f"   Currently spent:           ${result['currently_spent']:>8.2f}")
        print(f"   Should have spent by now:  ${result['should_have_spent_by_now']:>8.2f}")
        print(f"   Monthly budget:            ${result['maximum_to_spend_this_month']:>8.2f}")
        print(f"   Percentage used:           {result['percentage_used']:>7.1f}%")
        print(f"   Days remaining:            {result['days_remaining']:>7d}")
        status = "On track" if result['on_track'] else "Over budget"
        print(f"   Status: {status}")
        
        # Visual progress bar
        pct = min(result['percentage_used'], 100)
        filled = int(pct / 2)
        bar = "█" * filled + "░" * (50 - filled)
        print(f"   [{bar}] {pct:.1f}%")
        print()
    else:
        print(f"  Failed\n")
    
    print("=" * 70)
    print("ALL ANALYTICS TESTS COMPLETE")


if __name__ == "__main__":
    test_uid = os.getenv("TEST_USER_ID")
    
    if not test_uid:
        test_uid = input("Enter user ID (Firebase Auth UID): ").strip()
        if not test_uid:
            print("No user ID provided")
            sys.exit(1)
    
    print()
    test_analytics(test_uid)
#!/usr/bin/env python3
"""
Shift Transaction Dates Forward

Updates all transaction dates for a user by pushing them forward N days.
This helps when demo users don't have enough recent transactions.

"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore

# ============================================================================
# Configuration
# ============================================================================

USER_ID = "LIDiFA7hRKYPIWcUO2WP1hzAD0s2"  # Get from Firebase Console
DAYS_TO_SHIFT = 4  # Shift forward by 4 days

# ============================================================================
# Firebase Initialization
# ============================================================================

def init_firebase():
    """Initialize Firebase Admin SDK"""
    if firebase_admin._apps:
        return firestore.client()
    
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        # Try firebase/credentials folder
        cred_dir = Path(__file__).parent / "firebase" / "credentials"
        if cred_dir.exists():
            json_files = list(cred_dir.glob("*.json"))
            if json_files:
                cred = credentials.Certificate(str(json_files[0]))
            else:
                raise RuntimeError("No Firebase credentials found")
        else:
            cred = credentials.ApplicationDefault()
    
    firebase_admin.initialize_app(cred)
    return firestore.client()

# ============================================================================
# Date Shifting Logic
# ============================================================================

def shift_date(date_str: str, days: int) -> str:
    """
    Shift a YYYY-MM-DD date string forward by N days.
    
    Args:
        date_str: Date string in format "YYYY-MM-DD"
        days: Number of days to shift forward
    
    Returns:
        New date string in format "YYYY-MM-DD"
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        new_date = date_obj + timedelta(days=days)
        return new_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError) as e:
        print(f"  ⚠️  Warning: Could not parse date '{date_str}': {e}")
        return date_str  # Return original if can't parse

def update_transaction_dates(uid: str, days_to_shift: int):
    """
    Update all transaction dates for a user by shifting them forward.
    
    Args:
        uid: Firebase user ID
        days_to_shift: Number of days to shift forward
    """
    db = init_firebase()
    
    print(f"\n{'='*70}")
    print(f"📅 SHIFTING TRANSACTION DATES")
    print(f"{'='*70}")
    print(f"User ID: {uid}")
    print(f"Shift amount: +{days_to_shift} days")
    print(f"{'='*70}\n")
    
    # Get all transactions
    print("📥 Fetching transactions from Firestore...")
    col = db.collection("users").document(uid).collection("transactions")
    docs = list(col.stream())
    
    if not docs:
        print("❌ No transactions found for this user!")
        return
    
    print(f"✅ Found {len(docs)} transactions\n")
    
    # Show preview of changes
    print("📊 Preview of date changes:")
    print("-" * 70)
    
    preview_count = min(5, len(docs))
    for i, doc in enumerate(docs[:preview_count]):
        data = doc.to_dict() or {}
        old_date = data.get("date", "N/A")
        new_date = shift_date(old_date, days_to_shift) if old_date != "N/A" else "N/A"
        merchant = data.get("name", "Unknown")
        amount = data.get("amount", 0)
        
        print(f"  {merchant[:30]:30s} ${amount:7.2f}")
        print(f"    {old_date} → {new_date}")
    
    if len(docs) > preview_count:
        print(f"  ... and {len(docs) - preview_count} more transactions")
    
    print("-" * 70)
    
    # Confirm before updating
    response = input(f"\n📝 Update all {len(docs)} transactions? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("❌ Cancelled. No changes made.")
        return
    
    # Update transactions
    print(f"\n✏️  Updating transactions...")
    
    batch = db.batch()
    updated_count = 0
    
    for doc in docs:
        data = doc.to_dict() or {}
        old_date = data.get("date")
        
        if not old_date:
            continue  # Skip if no date field
        
        new_date = shift_date(old_date, days_to_shift)
        
        # Update the document
        batch.update(doc.reference, {
            "date": new_date,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })
        
        updated_count += 1
        
        # Commit in batches of 500 (Firestore limit)
        if updated_count % 500 == 0:
            batch.commit()
            print(f"  Committed batch {updated_count}/{len(docs)}...")
            batch = db.batch()
    
    # Commit remaining
    if updated_count % 500 != 0:
        batch.commit()
    
    print(f"\n✅ Successfully updated {updated_count} transactions!")
    print(f"{'='*70}\n")
    
    # Show summary
    print("📊 Date range summary:")
    
    # Get updated transactions to show new date range
    updated_docs = list(col.stream())
    dates = []
    for doc in updated_docs:
        data = doc.to_dict() or {}
        date_str = data.get("date")
        if date_str:
            try:
                dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
            except:
                pass
    
    if dates:
        dates.sort()
        print(f"  Oldest transaction: {dates[0].strftime('%Y-%m-%d')}")
        print(f"  Newest transaction: {dates[-1].strftime('%Y-%m-%d')}")
        print(f"  Date range: {(dates[-1] - dates[0]).days} days")
    
    print(f"\n🎮 Your minigames should now work with recent transaction data!")
    print(f"{'='*70}\n")

# ============================================================================
# Additional Utility: Update Specific Date Field in Raw Data
# ============================================================================

def update_raw_dates(uid: str, days_to_shift: int):
    """
    Also update dates inside the 'raw' field (Plaid's full transaction data).
    This ensures consistency across all date fields.
    """
    db = init_firebase()
    col = db.collection("users").document(uid).collection("transactions")
    docs = list(col.stream())
    
    print(f"\n🔄 Updating raw Plaid data dates...")
    
    batch = db.batch()
    updated_count = 0
    
    for doc in docs:
        data = doc.to_dict() or {}
        raw = data.get("raw")
        
        if not raw or not isinstance(raw, dict):
            continue
        
        # Update various date fields in raw data
        date_fields = ["date", "authorized_date", "datetime", "authorized_datetime"]
        updated = False
        
        for field in date_fields:
            if field in raw and raw[field]:
                old_val = raw[field]
                
                # Handle date strings
                if isinstance(old_val, str) and len(old_val) >= 10:
                    date_part = old_val[:10]  # YYYY-MM-DD
                    new_date = shift_date(date_part, days_to_shift)
                    
                    # Preserve time portion if exists
                    if len(old_val) > 10:
                        raw[field] = new_date + old_val[10:]
                    else:
                        raw[field] = new_date
                    
                    updated = True
        
        if updated:
            batch.update(doc.reference, {
                "raw": raw,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })
            updated_count += 1
            
            if updated_count % 500 == 0:
                batch.commit()
                print(f"  Committed batch {updated_count}/{len(docs)}...")
                batch = db.batch()
    
    if updated_count % 500 != 0:
        batch.commit()
    
    print(f"✅ Updated raw data for {updated_count} transactions\n")

# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main function"""
    
    if USER_ID == "PASTE_YOUR_USER_UID_HERE":
        print("\n❌ ERROR: You need to set USER_ID in the script!")
        print("\nHow to get your User ID:")
        print("1. Go to https://console.firebase.google.com")
        print("2. Select your project")
        print("3. Go to Authentication")
        print("4. Find your demo user and copy the UID")
        print("5. Paste it in this script at line 20\n")
        return
    
    try:
        # Update main date field
        update_transaction_dates(USER_ID, DAYS_TO_SHIFT)
        
        # Ask if they want to update raw data too
        response = input("📋 Also update dates in raw Plaid data? (yes/no): ").strip().lower()
        if response == "yes":
            update_raw_dates(USER_ID, DAYS_TO_SHIFT)
        
        print("✨ All done! Test your minigames now.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
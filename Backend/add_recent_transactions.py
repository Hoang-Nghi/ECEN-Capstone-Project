#!/usr/bin/env python3
"""
Add Test Transactions to Firebase
Adds realistic transactions for the past 7 days for testing minigames.

Usage:
    python add_test_transactions.py
"""

import os
import sys
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import Firebase
sys.path.insert(0, str(Path(__file__).parent))

import firebase_admin
from firebase_admin import credentials, firestore

# ============================================================================
# Configuration
# ============================================================================

USER_ID = "ZQ2eHJdpGAN9Uyu7UZYyXP0kZmY2"
DAYS_BACK = 7  # Add transactions for past 7 days
TRANSACTIONS_PER_DAY = 3  # 3-5 transactions per day

# ============================================================================
# Realistic Merchant Data by Category
# ============================================================================

MERCHANTS = {
    "dining": [
        {
            "name": "Starbucks",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_COFFEE",
            "amount_range": (4.50, 8.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/starbucks_1313.png",
            "website": "https://www.starbucks.com",
        },
        {
            "name": "Chipotle Mexican Grill",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_RESTAURANT",
            "amount_range": (10.50, 16.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/chipotle_956.png",
            "website": "https://www.chipotle.com",
        },
        {
            "name": "McDonald's",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_FAST_FOOD",
            "amount_range": (6.99, 12.50),
            "logo_url": "https://plaid-merchant-logos.plaid.com/mcdonalds_619.png",
            "website": "https://www.mcdonalds.com",
        },
        {
            "name": "The Cheesecake Factory",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_RESTAURANT",
            "amount_range": (25.00, 55.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/cheesecake_factory_1051.png",
            "website": "https://www.thecheesecakefactory.com",
        },
        {
            "name": "Panera Bread",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_RESTAURANT",
            "amount_range": (9.50, 15.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/panera_bread_1292.png",
            "website": "https://www.panerabread.com",
        },
    ],
    "groceries": [
        {
            "name": "H-E-B",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_SUPERSTORES",
            "amount_range": (35.00, 120.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/heb_1180.png",
            "website": "https://www.heb.com",
        },
        {
            "name": "Whole Foods Market",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_SUPERSTORES",
            "amount_range": (45.00, 95.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/whole_foods_1066.png",
            "website": "https://www.wholefoodsmarket.com",
        },
        {
            "name": "Walmart",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_SUPERSTORES",
            "amount_range": (30.00, 85.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/walmart_1000.png",
            "website": "https://www.walmart.com",
        },
    ],
    "transportation": [
        {
            "name": "Uber",
            "pfc_primary": "TRANSPORTATION",
            "pfc_detailed": "TRANSPORTATION_TAXIS_AND_RIDE_SHARES",
            "amount_range": (8.50, 25.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/uber_1060.png",
            "website": "https://www.uber.com",
        },
        {
            "name": "Lyft",
            "pfc_primary": "TRANSPORTATION",
            "pfc_detailed": "TRANSPORTATION_TAXIS_AND_RIDE_SHARES",
            "amount_range": (7.99, 23.50),
            "logo_url": "https://plaid-merchant-logos.plaid.com/lyft_1120.png",
            "website": "https://www.lyft.com",
        },
        {
            "name": "Shell",
            "pfc_primary": "TRANSPORTATION",
            "pfc_detailed": "TRANSPORTATION_GAS",
            "amount_range": (35.00, 65.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/shell_1003.png",
            "website": "https://www.shell.com",
        },
    ],
    "entertainment": [
        {
            "name": "AMC Theatres",
            "pfc_primary": "ENTERTAINMENT",
            "pfc_detailed": "ENTERTAINMENT_MOVIES_AND_MUSIC",
            "amount_range": (12.50, 45.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/amc_theatres_1350.png",
            "website": "https://www.amctheatres.com",
        },
        {
            "name": "Spotify",
            "pfc_primary": "ENTERTAINMENT",
            "pfc_detailed": "ENTERTAINMENT_MUSIC_AND_AUDIO",
            "amount_range": (10.99, 15.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/spotify_1119.png",
            "website": "https://www.spotify.com",
        },
        {
            "name": "Netflix",
            "pfc_primary": "ENTERTAINMENT",
            "pfc_detailed": "ENTERTAINMENT_TV_AND_MOVIES",
            "amount_range": (15.49, 19.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/netflix_1015.png",
            "website": "https://www.netflix.com",
        },
    ],
    "shopping": [
        {
            "name": "Amazon",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES",
            "amount_range": (15.99, 85.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/amazon_1.png",
            "website": "https://www.amazon.com",
        },
        {
            "name": "Target",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_DISCOUNT_STORES",
            "amount_range": (25.00, 75.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/target_1006.png",
            "website": "https://www.target.com",
        },
        {
            "name": "Best Buy",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_ELECTRONICS",
            "amount_range": (45.00, 250.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/best_buy_1009.png",
            "website": "https://www.bestbuy.com",
        },
    ],
    "travel": [
        {
            "name": "Airbnb",
            "pfc_primary": "TRAVEL",
            "pfc_detailed": "TRAVEL_LODGING",
            "amount_range": (95.00, 250.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/airbnb_1125.png",
            "website": "https://www.airbnb.com",
        },
        {
            "name": "Delta Air Lines",
            "pfc_primary": "TRAVEL",
            "pfc_detailed": "TRAVEL_FLIGHTS",
            "amount_range": (150.00, 450.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/delta_1010.png",
            "website": "https://www.delta.com",
        },
    ],
}

# ============================================================================
# Firebase Initialization
# ============================================================================

def init_firebase():
    """Initialize Firebase Admin SDK"""
    if firebase_admin._apps:
        return firestore.client()
    
    # Try to find credentials
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
                raise RuntimeError("No Firebase credentials found in firebase/credentials/")
        else:
            # Use application default (for Cloud Run)
            cred = credentials.ApplicationDefault()
    
    firebase_admin.initialize_app(cred)
    return firestore.client()

# ============================================================================
# Transaction Generation
# ============================================================================

def generate_transaction(merchant_data: dict, date: str, category: str) -> dict:
    """Generate a realistic transaction document"""
    # Random amount in merchant's range
    min_amt, max_amt = merchant_data["amount_range"]
    amount = round(random.uniform(min_amt, max_amt), 2)
    
    # Generate transaction ID (like Plaid format)
    tx_id = f"test_{category}_{date.replace('-', '')}_{random.randint(1000, 9999)}"
    
    # Build Plaid-like raw structure
    raw = {
        "account_id": "test_account_id_12345",
        "amount": amount,
        "authorized_date": date,
        "authorized_datetime": f"{date}T{random.randint(8, 20):02d}:{random.randint(0, 59):02d}:00Z",
        "category": [category.capitalize()],
        "category_id": f"{random.randint(10000000, 19999999)}",
        "check_number": None,
        "date": date,
        "datetime": f"{date}T{random.randint(8, 20):02d}:{random.randint(0, 59):02d}:00Z",
        "iso_currency_code": "USD",
        "location": {
            "address": None,
            "city": "College Station",
            "country": "US",
            "lat": None,
            "lon": None,
            "postal_code": "77840",
            "region": "TX",
            "store_number": None,
        },
        "logo_url": merchant_data.get("logo_url"),
        "merchant_entity_id": f"test_merchant_{merchant_data['name'].replace(' ', '_').lower()}",
        "merchant_name": merchant_data["name"],
        "name": merchant_data["name"],
        "payment_channel": "in store" if category in ["groceries", "dining"] else "online",
        "payment_meta": {
            "by_order_of": None,
            "payee": None,
            "payer": None,
            "payment_method": None,
            "payment_processor": None,
            "ppd_id": None,
            "reason": None,
            "reference_number": None,
        },
        "pending": False,
        "pending_transaction_id": None,
        "personal_finance_category": {
            "confidence_level": "VERY_HIGH",
            "detailed": merchant_data["pfc_detailed"],
            "primary": merchant_data["pfc_primary"],
        },
        "personal_finance_category_icon_url": f"https://plaid-category-icons.plaid.com/{merchant_data['pfc_primary'].lower()}.png",
        "transaction_code": None,
        "transaction_id": tx_id,
        "transaction_type": "place",
        "unofficial_currency_code": None,
        "website": merchant_data.get("website"),
        "counterparties": [
            {
                "confidence_level": "VERY_HIGH",
                "entity_id": f"test_entity_{merchant_data['name'].replace(' ', '_').lower()}",
                "logo_url": merchant_data.get("logo_url"),
                "name": merchant_data["name"],
                "type": "merchant",
                "website": merchant_data.get("website"),
            }
        ],
    }
    
    # Build Firestore document (following plaid_store.py schema)
    doc = {
        "source": "test_data",
        "transaction_id": tx_id,
        "account_id": "test_account_id_12345",
        "name": merchant_data["name"],
        "merchant_name": merchant_data["name"],
        "original_description": merchant_data["name"],
        "amount": amount,
        "date": date,
        "iso_currency_code": "USD",
        "category_path": category.capitalize(),
        "pfc_primary": merchant_data["pfc_primary"],
        "pfc_detailed": merchant_data["pfc_detailed"],
        "pending": False,
        "raw": raw,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    
    return doc

def generate_daily_transactions(date: str, num_transactions: int = 3) -> list:
    """Generate multiple transactions for a given day"""
    transactions = []
    
    # Weight categories (some are more common)
    category_weights = {
        "dining": 40,
        "groceries": 20,
        "transportation": 15,
        "entertainment": 10,
        "shopping": 10,
        "travel": 5,
    }
    
    categories = list(category_weights.keys())
    weights = list(category_weights.values())
    
    # Randomly select categories for this day
    selected_categories = random.choices(categories, weights=weights, k=num_transactions)
    
    for category in selected_categories:
        # Pick a random merchant from this category
        merchant = random.choice(MERCHANTS[category])
        tx = generate_transaction(merchant, date, category)
        transactions.append(tx)
    
    return transactions

# ============================================================================
# Main Script
# ============================================================================

def main():
    """Generate and add test transactions"""
    print("=" * 70)
    print("🎮 Adding Test Transactions for Minigames")
    print("=" * 70)
    print(f"\nUser ID: {USER_ID}")
    print(f"Days back: {DAYS_BACK}")
    print(f"Transactions per day: {TRANSACTIONS_PER_DAY}")
    print()
    
    # Initialize Firebase
    try:
        db = init_firebase()
        print("✅ Connected to Firebase")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Set GOOGLE_APPLICATION_CREDENTIALS env variable")
        print("2. Or place credentials.json in firebase/credentials/")
        return
    
    # Generate transactions
    all_transactions = []
    now = datetime.now(timezone.utc)
    
    print("\n📅 Generating transactions...\n")
    
    for days_ago in range(DAYS_BACK):
        date_obj = now - timedelta(days=days_ago)
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # Random number of transactions per day (3-5)
        num_tx = random.randint(TRANSACTIONS_PER_DAY, TRANSACTIONS_PER_DAY + 2)
        
        daily_txs = generate_daily_transactions(date_str, num_tx)
        all_transactions.extend(daily_txs)
        
        # Print summary
        daily_total = sum(tx["amount"] for tx in daily_txs)
        merchants = [tx["name"] for tx in daily_txs]
        print(f"  {date_str}: {num_tx} transactions (${daily_total:,.2f})")
        for tx in daily_txs:
            cat = tx["pfc_primary"].replace("_", " ").title()
            print(f"    • {tx['name']:30s} ${tx['amount']:6.2f}  [{cat}]")
        print()
    
    # Summary
    total_count = len(all_transactions)
    total_amount = sum(tx["amount"] for tx in all_transactions)
    
    print("=" * 70)
    print(f"📊 Summary: {total_count} transactions, ${total_amount:,.2f} total")
    print("=" * 70)
    
    # Category breakdown
    by_category = {}
    for tx in all_transactions:
        cat = tx["pfc_primary"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0.0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += tx["amount"]
    
    print("\n📈 By Category:")
    for cat, data in sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True):
        cat_name = cat.replace("_", " ").title()
        print(f"  {cat_name:30s}: {data['count']:2d} tx, ${data['total']:7.2f}")
    
    # Confirm before writing
    print("\n" + "=" * 70)
    response = input("📝 Write these transactions to Firebase? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("❌ Aborted. No transactions written.")
        return
    
    # Write to Firestore
    print("\n✍️  Writing to Firestore...")
    
    collection = db.collection("users").document(USER_ID).collection("transactions")
    batch = db.batch()
    
    for i, tx in enumerate(all_transactions):
        doc_ref = collection.document(tx["transaction_id"])
        batch.set(doc_ref, tx)
        
        # Commit in batches of 500 (Firestore limit)
        if (i + 1) % 500 == 0:
            batch.commit()
            print(f"  Committed batch {i + 1}/{total_count}...")
            batch = db.batch()
    
    # Commit remaining
    batch.commit()
    
    print(f"✅ Successfully added {total_count} transactions!")
    print("\n🎮 Ready to test minigames!")
    print("\nFirestore path:")
    print(f"  users/{USER_ID}/transactions/")
    print()

if __name__ == "__main__":
    main()
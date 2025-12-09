#!/usr/bin/env python3
"""
Add Historical Transactions to Firebase
Adds realistic transactions for the past 3 months (90 days) for testing minigames.

Usage:
    python add_historical_transactions.py
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
MONTHS_BACK = 3  # 3 months of history
DAYS_BACK = 90  # Approximately 3 months
TRANSACTIONS_PER_DAY_MIN = 2  # 2-5 transactions per day
TRANSACTIONS_PER_DAY_MAX = 5

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
        {
            "name": "Subway",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_FAST_FOOD",
            "amount_range": (7.50, 12.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/subway_1005.png",
            "website": "https://www.subway.com",
        },
        {
            "name": "Olive Garden",
            "pfc_primary": "FOOD_AND_DRINK",
            "pfc_detailed": "FOOD_AND_DRINK_RESTAURANT",
            "amount_range": (18.00, 35.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/olive_garden_1234.png",
            "website": "https://www.olivegarden.com",
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
        {
            "name": "Kroger",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_SUPERSTORES",
            "amount_range": (40.00, 110.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/kroger_1045.png",
            "website": "https://www.kroger.com",
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
        {
            "name": "Chevron",
            "pfc_primary": "TRANSPORTATION",
            "pfc_detailed": "TRANSPORTATION_GAS",
            "amount_range": (32.00, 62.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/chevron_1055.png",
            "website": "https://www.chevron.com",
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
        {
            "name": "YouTube Premium",
            "pfc_primary": "ENTERTAINMENT",
            "pfc_detailed": "ENTERTAINMENT_TV_AND_MOVIES",
            "amount_range": (11.99, 11.99),
            "logo_url": "https://plaid-merchant-logos.plaid.com/youtube_1234.png",
            "website": "https://www.youtube.com",
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
        {
            "name": "Etsy",
            "pfc_primary": "GENERAL_MERCHANDISE",
            "pfc_detailed": "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES",
            "amount_range": (12.99, 55.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/etsy_1567.png",
            "website": "https://www.etsy.com",
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
        {
            "name": "Marriott",
            "pfc_primary": "TRAVEL",
            "pfc_detailed": "TRAVEL_LODGING",
            "amount_range": (120.00, 280.00),
            "logo_url": "https://plaid-merchant-logos.plaid.com/marriott_1234.png",
            "website": "https://www.marriott.com",
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
    tx_id = f"hist_{category}_{date.replace('-', '')}_{random.randint(1000, 9999)}"
    
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
        "source": "historical_data",
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

def generate_daily_transactions(date: str) -> list:
    """Generate multiple transactions for a given day"""
    # Random number of transactions (2-5 per day)
    num_transactions = random.randint(TRANSACTIONS_PER_DAY_MIN, TRANSACTIONS_PER_DAY_MAX)
    
    transactions = []
    
    # Weight categories (some are more common)
    category_weights = {
        "dining": 35,
        "groceries": 20,
        "transportation": 15,
        "entertainment": 10,
        "shopping": 15,
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
    """Generate and add historical transactions"""
    print("=" * 70)
    print("📊 Adding Historical Transactions (Past 3 Months)")
    print("=" * 70)
    print(f"\nUser ID: {USER_ID}")
    print(f"Time range: {DAYS_BACK} days ({MONTHS_BACK} months)")
    print(f"Transactions per day: {TRANSACTIONS_PER_DAY_MIN}-{TRANSACTIONS_PER_DAY_MAX}")
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
    
    # Track weekly and monthly totals for summary
    weekly_totals = {}
    monthly_totals = {}
    
    for days_ago in range(DAYS_BACK):
        date_obj = now - timedelta(days=days_ago)
        date_str = date_obj.strftime("%Y-%m-%d")
        
        # Generate transactions for this day
        daily_txs = generate_daily_transactions(date_str)
        all_transactions.extend(daily_txs)
        
        # Track totals
        daily_total = sum(tx["amount"] for tx in daily_txs)
        week_key = date_obj.strftime("%Y-W%U")  # Year-Week
        month_key = date_obj.strftime("%Y-%m")  # Year-Month
        
        weekly_totals[week_key] = weekly_totals.get(week_key, 0) + daily_total
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + daily_total
        
        # Print progress every 10 days
        if (days_ago + 1) % 10 == 0 or days_ago == 0:
            print(f"  Generated {days_ago + 1}/{DAYS_BACK} days...")
    
    print(f"\n✅ Generated {len(all_transactions)} transactions")
    
    # Summary
    total_count = len(all_transactions)
    total_amount = sum(tx["amount"] for tx in all_transactions)
    avg_per_day = total_amount / DAYS_BACK
    
    print("\n" + "=" * 70)
    print(f"📊 Summary")
    print("=" * 70)
    print(f"Total transactions: {total_count}")
    print(f"Total amount: ${total_amount:,.2f}")
    print(f"Average per day: ${avg_per_day:,.2f}")
    print(f"Date range: {(now - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    
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
        avg = data["total"] / data["count"]
        print(f"  {cat_name:30s}: {data['count']:3d} tx, ${data['total']:8,.2f} (avg ${avg:6.2f})")
    
    # Monthly breakdown
    print("\n📅 By Month:")
    for month_key in sorted(monthly_totals.keys()):
        month_total = monthly_totals[month_key]
        month_name = datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
        print(f"  {month_name:20s}: ${month_total:8,.2f}")
    
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
    
    batch_size = 500  # Firestore limit
    batches_written = 0
    
    for i, tx in enumerate(all_transactions):
        doc_ref = collection.document(tx["transaction_id"])
        batch.set(doc_ref, tx)
        
        # Commit in batches of 500
        if (i + 1) % batch_size == 0:
            batch.commit()
            batches_written += 1
            print(f"  Committed batch {batches_written} ({i + 1}/{total_count} transactions)...")
            batch = db.batch()
    
    # Commit remaining
    if (total_count % batch_size) != 0:
        batch.commit()
        batches_written += 1
        print(f"  Committed final batch ({batches_written} total)")
    
    print(f"\n✅ Successfully added {total_count} transactions!")
    print("\n🎮 Ready to test minigames with 3 months of data!")
    print("\nFirestore path:")
    print(f"  users/{USER_ID}/transactions/")
    print()

if __name__ == "__main__":
    main()
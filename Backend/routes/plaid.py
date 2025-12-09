# routes/plaid.py
from __future__ import annotations
import os
from flask import Blueprint, request, jsonify
from auth_middleware import require_auth
from plaid_integration.client import plaid_client
from services.plaid_store import (
    save_user_plaid_state, get_user_plaid_state,
    upsert_transactions, mark_removed_transactions
)

# --- Plaid models (handle SDK version differences) ---
try:
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions
    from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
except Exception:
    from plaid.model import (  # type: ignore
        LinkTokenCreateRequest,
        Products,
        CountryCode,
        ItemPublicTokenExchangeRequest,
        TransactionsSyncRequest,
        TransactionsSyncRequestOptions,
        SandboxPublicTokenCreateRequest,
    )

plaid_bp = Blueprint("plaid", __name__)

# --- Configuration ---
def _get_plaid_products():
    """Parse PLAID_PRODUCTS env var safely"""
    products_str = os.getenv("PLAID_PRODUCTS", "transactions")
    product_names = [p.strip().lower() for p in products_str.split(",")]
    
    valid_products = []
    for name in product_names:
        try:
            if name == "transactions":
                valid_products.append(Products("transactions"))
            elif name == "auth":
                valid_products.append(Products("auth"))
            elif name == "identity":
                valid_products.append(Products("identity"))
        except Exception as e:
            print(f"[plaid] Warning: Invalid product '{name}': {e}")
    
    if not valid_products:
        valid_products = [Products("transactions")]  # Default fallback
    
    return valid_products

PLAID_PRODUCTS = _get_plaid_products()  # ✅ Only define once!
PLAID_COUNTRY_CODES = [CountryCode(x.strip()) for x in os.getenv("PLAID_COUNTRY_CODES", "US").split(",")]
CLIENT_NAME = os.getenv("PLAID_CLIENT_NAME", "Capstone Finance App")
PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL")

print(f"[plaid] Loaded products: {PLAID_PRODUCTS}")
print(f"[plaid] Client name: {CLIENT_NAME}")
print(f"[plaid] Public base: {PUBLIC_BASE}")

# --- Routes ---

@plaid_bp.get("/oauth-redirect")
def oauth_redirect():
    """For OAuth institutions; safe to keep public."""
    return "OAuth redirect OK. You can close this tab and return to the app."

@plaid_bp.post("/create_link_token")
@require_auth
def create_link_token():
    """Create a Plaid Link token for the user"""
    uid = request.user["uid"]

    # Verify Plaid credentials
    if not os.getenv("PLAID_CLIENT_ID") or not os.getenv("PLAID_SECRET"):
        print("[plaid] ERROR: Missing Plaid credentials")
        return jsonify({"error": "Missing Plaid credentials"}), 500

    state = get_user_plaid_state(uid)
    access_token = state.get("access_token")

    req_params = {
        "products": PLAID_PRODUCTS,
        "client_name": CLIENT_NAME,
        "country_codes": PLAID_COUNTRY_CODES,
        "language": "en",
        "user": {"client_user_id": uid},
    }

    # If user already has access token, use update mode
    if access_token:
        req_params["access_token"] = access_token

    # Add webhook and redirect URI if public URL is configured
    if PUBLIC_BASE:
        req_params["webhook"] = f"{PUBLIC_BASE}/api/plaid/webhook"
        req_params["redirect_uri"] = f"{PUBLIC_BASE}/api/plaid/oauth-redirect"

    try:
        print(f"[plaid] Creating link token for user {uid}")
        req = LinkTokenCreateRequest(**req_params)
        resp = plaid_client.link_token_create(req).to_dict()
        print(f"[plaid] Link token created successfully")
        return jsonify({"link_token": resp["link_token"]}), 200
    except Exception as e:
        print(f"[plaid] ERROR creating link token: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@plaid_bp.post("/exchange_public_token")
@require_auth
def exchange_public_token():
    """Exchange public token for access token and sync transactions"""
    uid = request.user["uid"]
    data = request.get_json(force=True)
    public_token = data.get("public_token")

    if not public_token:
        return jsonify({"error": "Missing public_token"}), 400

    try:
        print(f"[plaid] Exchanging public token for user {uid}")
        
        # Exchange token
        exchange_req = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_resp = plaid_client.item_public_token_exchange(exchange_req).to_dict()
        access_token = exchange_resp["access_token"]
        item_id = exchange_resp["item_id"]

        print(f"[plaid] Exchange successful, item_id: {item_id}")

        # Save access token
        save_user_plaid_state(uid, access_token=access_token, item_id=item_id, cursor=None)

        # Backfill transactions immediately
        print(f"[plaid] Starting transaction sync for user {uid}")
        cursor = None
        total_added = 0
        total_modified = 0
        
        while True:
            req_kwargs = {
                "access_token": access_token,
                "options": TransactionsSyncRequestOptions(
                    include_personal_finance_category=True,
                    include_original_description=True,
                ),
            }
            if cursor:
                req_kwargs["cursor"] = cursor

            ts_req = TransactionsSyncRequest(**req_kwargs)
            ts_res = plaid_client.transactions_sync(ts_req).to_dict()

            added = ts_res["added"]
            modified = ts_res["modified"]
            removed = ts_res["removed"]
            
            upsert_transactions(uid, added + modified)
            mark_removed_transactions(uid, removed)

            total_added += len(added)
            total_modified += len(modified)
            cursor = ts_res["next_cursor"]
            
            save_user_plaid_state(uid, cursor=cursor)

            print(f"[plaid] Synced batch: +{len(added)} ~{len(modified)} -{len(removed)}")

            if not ts_res["has_more"]:
                break

        print(f"[plaid] Sync complete: {total_added} added, {total_modified} modified")

        return jsonify({
            "item_id": item_id,
            "status": "linked_and_backfilled",
            "added": total_added,
            "modified": total_modified
        }), 200
        
    except Exception as e:
        print(f"[plaid] ERROR during exchange: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@plaid_bp.post("/transactions/sync")
@require_auth
def transactions_sync():
    """Manually sync transactions for a user"""
    uid = request.user["uid"]
    state = get_user_plaid_state(uid)
    access_token = state.get("access_token")
    
    if not access_token:
        return jsonify({"error": "User not linked."}), 400

    cursor = state.get("cursor")
    added, modified, removed = [], [], []
    has_more = True

    try:
        print(f"[plaid] Manual sync for user {uid}")
        
        while has_more:
            req_kwargs = {
                "access_token": access_token,
                "options": TransactionsSyncRequestOptions(
                    include_personal_finance_category=True,
                    include_original_description=True,
                ),
            }
            if cursor:
                req_kwargs["cursor"] = cursor

            req = TransactionsSyncRequest(**req_kwargs)
            resp = plaid_client.transactions_sync(req).to_dict()

            added.extend(resp["added"])
            modified.extend(resp["modified"])
            removed.extend(resp["removed"])
            cursor = resp["next_cursor"]
            has_more = resp["has_more"]

        upsert_transactions(uid, added + modified)
        mark_removed_transactions(uid, removed)
        save_user_plaid_state(uid, cursor=cursor)

        print(f"[plaid] Manual sync complete: {len(added)} added, {len(modified)} modified")

        return jsonify({
            "added_count": len(added),
            "modified_count": len(modified),
            "removed_count": len(removed),
            "cursor": cursor,
            "sample": [
                {"id": t["transaction_id"], "name": t.get("merchant_name") or t.get("name"), "amount": t["amount"]}
                for t in (added[:3] if added else modified[:3])
            ],
        }), 200
        
    except Exception as e:
        print(f"[plaid] ERROR during manual sync: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@plaid_bp.get("/status")
@require_auth
def plaid_status():
    """Check if user has Plaid connection"""
    uid = request.user["uid"]
    state = get_user_plaid_state(uid)
    
    has_connection = bool(state.get("access_token"))
    
    return jsonify({
        "item_id": state.get("item_id"),
        "has_connection": has_connection,
        "last_sync": state.get("updatedAt"),
    }), 200

@plaid_bp.post("/sandbox/instant_item")
@require_auth
def sandbox_instant_item():
    """Create a sandbox Plaid item for testing"""
    uid = request.user["uid"]

    try:
        from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
        from plaid.model.products import Products

        req = SandboxPublicTokenCreateRequest(
            institution_id="ins_109508",
            initial_products=[Products("transactions")]
        )

        print(f"[sandbox] Creating sandbox item for user {uid}")
        resp = plaid_client.sandbox_public_token_create(req)
        result = resp.to_dict()

        print(f"[sandbox] Success! Got public_token")
        return jsonify({"public_token": result["public_token"]}), 200

    except Exception as e:
        print(f"[sandbox] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        # Return detailed error
        error_msg = str(e)
        if hasattr(e, 'body'):
            error_msg = f"{error_msg} - Body: {e.body}"

        return jsonify({"error": error_msg}), 500


@plaid_bp.get("/test")
def plaid_test():
    """Test endpoint to check Plaid configuration"""
    return jsonify({
        "PLAID_CLIENT_ID": bool(os.getenv("PLAID_CLIENT_ID")),
        "PLAID_SECRET": bool(os.getenv("PLAID_SECRET")),
        "PLAID_ENV": os.getenv("PLAID_ENV"),
        "PLAID_PRODUCTS": [str(p) for p in PLAID_PRODUCTS],
        "PUBLIC_BASE_URL": PUBLIC_BASE,
    })

@plaid_bp.get("/debug")
def debug_config():
    """Debug endpoint - check if Plaid credentials are loaded"""
    import os
    return jsonify({
        "PLAID_CLIENT_ID_present": bool(os.getenv("PLAID_CLIENT_ID")),
        "PLAID_CLIENT_ID_length": len(os.getenv("PLAID_CLIENT_ID", "")),
        "PLAID_SECRET_present": bool(os.getenv("PLAID_SECRET")),
        "PLAID_SECRET_length": len(os.getenv("PLAID_SECRET", "")),
        "PLAID_ENV": os.getenv("PLAID_ENV"),
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL"),
    })
# routes/plaid_webhook.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from plaid_integration.client import plaid_client
from services.plaid_store import (
    item_map_ref, get_user_plaid_state, save_user_plaid_state,
    upsert_transactions, mark_removed_transactions
)
# Plaid models
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions

plaid_webhook_bp = Blueprint("plaid_webhook", __name__)

# Webhook codes that indicate new/changed transactions are available
_TXN_SYNC_CODES = {
    "SYNC_UPDATES_AVAILABLE",      # the main one to act on
    "DEFAULT_UPDATE",              # legacy-ish; still good to treat as "go sync"
    "INITIAL_UPDATE",              # after link / first backfill
    "HISTORICAL_UPDATE",           # long lookback; also sync
}

@plaid_webhook_bp.post("/api/plaid/webhook")
def plaid_webhook():
    """
    Plaid → your server (no Firebase auth; public endpoint).
    Expects JSON body with at least: item_id, webhook_type, webhook_code

    On transaction-related codes, this triggers a Transactions Sync for the
    owning user and writes deltas to Firestore. Always returns 200 quickly.
    """
    payload = request.get_json(force=True, silent=False)

    item_id = payload.get("item_id")
    webhook_type = payload.get("webhook_type")
    webhook_code = payload.get("webhook_code")

    # 1) Map item_id -> uid (we write this mapping when exchanging public_token)
    uid = None
    if item_id:
        snap = item_map_ref(item_id).get()
        if snap.exists:
            uid = (snap.to_dict() or {}).get("user_id")

    # If we can’t associate this to a user, acknowledge and return 200
    if not uid:
        return jsonify({"ok": True, "ignored": "unknown_item_id"}), 200

    # Only act on transaction update signals
    if webhook_type == "TRANSACTIONS" and webhook_code in _TXN_SYNC_CODES:
        try:
            state = get_user_plaid_state(uid)
            access_token = state.get("access_token")
            cursor = state.get("cursor")

            if not access_token:
                # user has no token (maybe unlinked) — acknowledge
                return jsonify({"ok": True, "ignored": "no_access_token"}), 200

            added, modified, removed = [], [], []
            has_more = True

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

                added.extend(resp.get("added", []))
                modified.extend(resp.get("modified", []))
                removed.extend(resp.get("removed", []))

                cursor = resp.get("next_cursor")
                has_more = bool(resp.get("has_more"))

            # Idempotent upserts
            upsert_transactions(uid, added + modified)
            mark_removed_transactions(uid, removed)

            # Advance cursor atomically on the same state doc
            save_user_plaid_state(uid, cursor=cursor)

            return jsonify({
                "ok": True,
                "uid": uid,
                "item_id": item_id,
                "webhook_type": webhook_type,
                "webhook_code": webhook_code,
                "added": len(added),
                "modified": len(modified),
                "removed": len(removed),
                "next_cursor": cursor,
            }), 200

        except Exception as e:
            # Don’t retry from Plaid’s side by returning non-200 unless it’s a hard failure.
            # Log the error server-side; still return 200 so Plaid doesn’t hammer you.
            # (You can add alerting here if you want.)
            return jsonify({"ok": False, "error": str(e)}), 200

    # For all other webhook types/codes, just acknowledge.
    return jsonify({"ok": True, "webhook_type": webhook_type, "webhook_code": webhook_code}), 200

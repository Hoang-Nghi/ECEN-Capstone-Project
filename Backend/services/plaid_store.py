# services/plaid_store.py
import os, json
from firebase_admin import firestore
from services.firebase import get_db
from cryptography.fernet import Fernet, InvalidToken
from datetime import date as _date, datetime as _dt

# --- Encryption key (rename to a single canonical env) ---
# Choose ONE name and use it everywhere. Let's standardize on PLAID_ENCRYPTION_KEY
KEY = os.getenv("PLAID_ENCRYPTION_KEY") or os.getenv("TOKEN_ENC_KEY")
if not KEY:
    raise RuntimeError("Set PLAID_ENCRYPTION_KEY in your .env")
_f = Fernet(KEY.strip())

def encrypt_str(s: str) -> str:
    return _f.encrypt(s.encode()).decode()

def decrypt_str(s: str) -> str:
    try:
        return _f.decrypt(s.encode()).decode()
    except InvalidToken:
        # fallback if already plain in old data
        return s

# --- Firestore paths ---
def plaid_state_ref(uid: str):
    return get_db().collection("users").document(uid).collection("private").document("plaid_state")

def item_map_ref(item_id: str):
    return get_db().collection("plaid_items").document(item_id)

def save_user_plaid_state(uid: str, **kwargs):
    db = get_db()
    payload = dict(kwargs)
    if "access_token" in payload and payload["access_token"]:
        payload["access_token_encrypted"] = encrypt_str(payload.pop("access_token"))
    payload["updatedAt"] = firestore.SERVER_TIMESTAMP
    plaid_state_ref(uid).set(payload, merge=True)

    if "item_id" in kwargs and kwargs["item_id"]:
        item_map_ref(kwargs["item_id"]).set({
            "user_id": uid,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }, merge=True)

def get_user_plaid_state(uid: str):
    snap = plaid_state_ref(uid).get()
    if not snap.exists:
        return {}
    data = snap.to_dict() or {}
    if "access_token_encrypted" in data:
        data["access_token"] = decrypt_str(data["access_token_encrypted"])
    return data

def _json_safe(obj):
    if isinstance(obj, (_dt, _date)):
        return obj.isoformat()
    return str(obj)

def upsert_transactions(uid: str, plaid_tx_list: list):
    if not plaid_tx_list:
        return
    db = get_db()
    batch = db.batch()
    col = db.collection("users").document(uid).collection("transactions")

    for t in plaid_tx_list:
        safe_t = json.loads(json.dumps(t, default=_json_safe))
        tx_id = safe_t["transaction_id"]
        category = safe_t.get("category") or []
        pfc = (safe_t.get("personal_finance_category") or {}) or {}

        doc = {
            "source": "plaid",
            "transaction_id": tx_id,
            "account_id": safe_t.get("account_id"),
            "name": safe_t.get("merchant_name") or safe_t.get("name"),
            "original_description": safe_t.get("original_description") or safe_t.get("name"),
            "amount": float(safe_t.get("amount") or 0.0),
            "date": safe_t.get("date"),
            "iso_currency_code": safe_t.get("iso_currency_code") or safe_t.get("unofficial_currency_code"),
            "category_path": " > ".join(category) if isinstance(category, list) else (category or ""),
            "pfc_primary": pfc.get("primary"),
            "pfc_detailed": pfc.get("detailed"),
            "pending": bool(safe_t.get("pending", False)),
            "raw": safe_t,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
        batch.set(col.document(tx_id), doc, merge=True)

    batch.commit()

def mark_removed_transactions(uid: str, removed_list: list):
    if not removed_list:
        return
    db = get_db()
    batch = db.batch()
    col = db.collection("users").document(uid).collection("transactions")
    for r in removed_list:
        tx_id = r.get("transaction_id")
        if not tx_id:
            continue
        batch.set(col.document(tx_id), {
            "removed": True,
            "removedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
    batch.commit()

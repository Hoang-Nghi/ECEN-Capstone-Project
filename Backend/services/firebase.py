# services/firebase.py
import os, json
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

_db = None

def _resolve_cred():
    json_blob = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if json_blob:
        return credentials.Certificate(json.loads(json_blob))

    p = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if p:
        p = p.strip().strip('"').strip("'")
        p = os.path.expanduser(os.path.expandvars(p))
        if os.path.exists(p):
            return credentials.Certificate(p)
        # Try repo-relative
        repo_root = Path(__file__).resolve().parents[1]  # adjust if needed
        fallback = repo_root / "firebase" / "credentials" / Path(p).name
        if fallback.exists():
            return credentials.Certificate(str(fallback))

    # Try first .json under firebase/credentials
    repo_root = Path(__file__).resolve().parents[1]
    cred_dir = repo_root / "firebase" / "credentials"
    if cred_dir.exists():
        matches = list(cred_dir.glob("*.json"))
        if matches:
            return credentials.Certificate(str(matches[0]))

    raise RuntimeError(
        "Firebase credentials not found. Set FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS, "
        "or add a JSON to firebase/credentials/."
    )

def get_db():
    global _db
    if _db is not None:
        return _db
    if not firebase_admin._apps:
        cred = _resolve_cred()
        firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db

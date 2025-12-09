# auth_middleware.py
from functools import wraps
from flask import request, jsonify
from firebase_admin import auth as fb_auth

def require_auth(fn):
    """
    Verify Firebase ID token from 'Authorization: Bearer <token>'.
    Sets request.user = {"uid": ..., "email": ..., "name": ...}
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        hdr = request.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            return jsonify({"error": "Missing Firebase ID token"}), 401
        try:
            token = hdr.split(" ", 1)[1]
            decoded = fb_auth.verify_id_token(token)
            request.user = {
                "uid": decoded["uid"],
                "email": decoded.get("email"),
                "name": decoded.get("name"),
            }
        except Exception as e:
            return jsonify({"error": f"Invalid or expired token: {e}"}), 401
        return fn(*args, **kwargs)
    return wrapper

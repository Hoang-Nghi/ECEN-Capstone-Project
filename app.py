# app.py
"""
Main Flask application entrypoint.

- Loads env/config
- Initializes Firebase Admin (for token verification)
- Enables CORS for /api/*
- Registers blueprints: Plaid, Minigame, Plaid Webhook
- Trend endpoints: /api/aggregate-spend, /api/spend-forecast, /api/trend-summary
"""

from __future__ import annotations
import os
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from auth_middleware import require_auth
import requests
import time
from datetime import datetime, timezone

# Firebase Admin (for verifying Firebase ID tokens)
import firebase_admin
from firebase_admin import auth as fb_auth, credentials

# ---- Load .env early ----
load_dotenv()

# ---- Config & blueprints ----
from config import Config
from routes.plaid import plaid_bp
from routes.plaid_webhook import plaid_webhook_bp
from routes.analytics import analytics_bp
from services.minigame_service.routes import minigame_bp

# If your services.firebase initializes Admin for Firestore, that's fine,
# but require_auth runs before any Firestore calls, so initialize here too.
def _init_firebase_admin():
    if firebase_admin._apps:
        return
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        print(f"Initializing Firebase with credentials: {cred_path}")
        firebase_admin.initialize_app(credentials.Certificate(cred_path))
    else:
        print("Initializing Firebase with default credentials")
        firebase_admin.initialize_app()
    print("Firebase initialized successfully")
_init_firebase_admin()

# ---------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # CORS for mobile dev; lock down origins in production
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure temp folder exists
    os.makedirs(getattr(Config, "TEMP_FOLDER", "tmp"), exist_ok=True)

    # --- Register blueprints ---
    app.register_blueprint(plaid_bp, url_prefix="/api/plaid")            # protected inside routes/plaid.py
    app.register_blueprint(minigame_bp, url_prefix="/api/minigame")      # public (for now)
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(plaid_webhook_bp)                             # route already includes /api/plaid/webhook
    """if app.config.get("DEBUG") or os.getenv("ENABLE_TEST_ROUTES") == "true":
        from test_routes import test_bp
        app.register_blueprint(test_bp)
        print("WARNING: Test routes enabled!")
    """
    # --- Health (public) ---
    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "service": "flask", "version": "1.3.0"})
    
    @app.get("/api/test/routes")
    def routes():
        rules = []
        for r in app.url_map.iter_rules():
            rules.append({
                "rule": r.rule,
                "methods": sorted(m for m in r.methods if m not in {"HEAD","OPTIONS"})
            })
        return jsonify(sorted(rules, key=lambda x: x["rule"]))

    @app.post("/api/test/echo")
    def test_echo():
        """Test endpoint for frontend to verify backend connection"""
        data = request.get_json(silent=True) or {}
        return jsonify({
            "received": data,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "backend": "flask",
            "message": "Backend received your data successfully!"
        }), 200

    @app.get("/api/test/ping")
    def test_ping():
        """Simple ping test"""
        return jsonify({
            "ok": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Pong! Backend is responding."
        }), 200

    # --- JSON error handlers ---
    @app.errorhandler(400)
    def handle_400(err):
        return jsonify({"error": str(err)}), 400

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def handle_500(err):
        return jsonify({"error": "Internal server error"}), 500

    return app




# ---------------------------------------------------------------------
# Dev Server Launcher
# ---------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":    
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)

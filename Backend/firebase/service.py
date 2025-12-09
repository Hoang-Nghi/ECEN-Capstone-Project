import firebase_admin
from firebase_admin import credentials, firestore, storage
from config import Config
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FirebaseService:
    _instance = None

    def __new__(cls):
        # Ensure only one instance is created (singleton pattern)
        if cls._instance is None:
            try:
                # Try to get the already initialized default app.
                app = firebase_admin.get_app()
                logger.info("Using existing Firebase default app.")
            except ValueError:
                # The default app is not initialized, so initialize it.
                cred_path = Path(Config.FIREBASE_CREDENTIAL_PATH)
                if not cred_path.exists():
                    raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")

                cred = credentials.Certificate(str(cred_path))
                app = firebase_admin.initialize_app(cred, {
                    'storageBucket': Config.FIREBASE_STORAGE_BUCKET
                })
                logger.info("Firebase default app initialized.")

            # Create the instance and set up Firestore and Storage clients using the app.
            cls._instance = super().__new__(cls)
            cls._instance.db = firestore.client(app=app)
            cls._instance.bucket = storage.bucket(app=app)
        return cls._instance

# config.py
import os, json
from pathlib import Path

class Config:
    # Whatever else you already have...

    @staticmethod
    def _resolve_firebase_cred_path() -> str | None:
        """
        Tries multiple ways to get a valid credential:
          1) FIREBASE_SERVICE_ACCOUNT_JSON (env contains the full JSON blob)
          2) GOOGLE_APPLICATION_CREDENTIALS (absolute or relative file path)
             - If relative or not found, try <repo>/firebase/credentials/<basename>
          3) First *.json found under <repo>/firebase/credentials
        Returns a string path if a file exists, or None if using JSON blob.
        Raises on total failure.
        """
        # 1) JSON blob provided in env (no file path needed)
        json_blob = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if json_blob:
            try:
                json.loads(json_blob)  # validate it's JSON
                return None  # signal that we'll use the blob later
            except Exception as e:
                raise RuntimeError(f"Invalid FIREBASE_SERVICE_ACCOUNT_JSON: {e}") from e

        # 2) A path provided in env (normalize quotes, slashes, vars)
        p = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        repo_root = Path(__file__).resolve().parent
        if p:
            p = p.strip().strip('"').strip("'")
            # Expand ~ and any %VAR% or $VAR
            p = os.path.expanduser(os.path.expandvars(p))
            path = Path(p)

            if path.exists():
                return str(path)

            # Try repo-relative fallback using same filename
            fallback = repo_root / "firebase" / "credentials" / path.name
            if fallback.exists():
                return str(fallback)

            # Try interpreting the env path as relative to repo root
            rel_try = (repo_root / p).resolve()
            if rel_try.exists():
                return str(rel_try)

            raise FileNotFoundError(
                "Firebase credential file not found. Tried:\n"
                f" - {path}\n - {fallback}\n - {rel_try}\n"
                "Set FIREBASE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS."
            )

        # 3) Auto-pick first json in firebase/credentials
        cred_dir = repo_root / "firebase" / "credentials"
        if cred_dir.exists():
            matches = list(cred_dir.glob("*.json"))
            if matches:
                return str(matches[0])

        raise FileNotFoundError(
            "No Firebase credentials found. Provide FIREBASE_SERVICE_ACCOUNT_JSON, "
            "or set GOOGLE_APPLICATION_CREDENTIALS, or put a JSON in firebase/credentials/."
        )

    @classmethod
    def validate_firebase_config(cls):
        # Will raise with a helpful message if nothing valid is found
        _ = cls._resolve_firebase_cred_path()

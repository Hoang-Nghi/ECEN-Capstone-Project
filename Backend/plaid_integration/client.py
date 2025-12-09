# plaid_integration/client.py
import os

# Prefer the modern imports first
try:
    from plaid import Configuration, ApiClient
    from plaid.api import plaid_api
except Exception:
    # Very old SDKs
    from plaid.configuration import Configuration  # type: ignore
    from plaid.api_client import ApiClient  # type: ignore
    from plaid.api import plaid_api  # type: ignore


def _resolve_host():
    """Return a host object/value compatible with the installed plaid-python."""
    env = (os.getenv("PLAID_ENV") or "sandbox").lower()

    # 1) Newest style (plaid-python >= 14)
    try:
        from plaid.environments import PlaidEnvironments  # type: ignore
        return {
            "sandbox": PlaidEnvironments.Sandbox,
            "development": PlaidEnvironments.Development,
            "production": PlaidEnvironments.Production,
        }[env]
    except Exception:
        pass

    # 2) Older style where Environment lives in plaid.environment
    try:
        from plaid.environment import Environment  # type: ignore
        # Some older builds only define Sandbox/Production on Environment.
        mapping = {"sandbox": getattr(Environment, "Sandbox", None),
                   "development": getattr(Environment, "Development", None),
                   "production": getattr(Environment, "Production", None)}
        if mapping[env] is not None:
            return mapping[env]
    except Exception:
        pass

    # 3) Very old style where Environment is at top-level plaid
    try:
        from plaid import Environment  # type: ignore
        mapping = {"sandbox": getattr(Environment, "Sandbox", None),
                   "development": getattr(Environment, "Development", None),
                   "production": getattr(Environment, "Production", None)}
        if mapping[env] is not None:
            return mapping[env]
    except Exception:
        pass

    # 4) Last-resort: pass the base URL string (works with swagger clients)
    url_map = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }
    return url_map[env]


configuration = Configuration(
    host=_resolve_host(),
    api_key={
        "clientId": os.getenv("PLAID_CLIENT_ID"),
        "secret": os.getenv("PLAID_SECRET"),
    },
)

_api_client = ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(_api_client)

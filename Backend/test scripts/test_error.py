import requests

BASE_URL = "https://capstone-backend-1041336188288.us-central1.run.app"

def call(endpoint, token=None, json=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, json=json)
    print(f"GET {endpoint} | status={resp.status_code} | body={resp.json()}")

# 1. Missing Firebase ID token
call("/transactions/sync", token=None)

# 2. Invalid Firebase ID token
call("/transactions/sync", token="invalid123")

# 3. Missing public token for Plaid exchange (if you expose POST test route)
resp = requests.post(
    f"{BASE_URL}/plaid/exchange",
    headers={"Authorization": "<valid_id_token>", "Content-Type": "application/json"},
    json={}  # no public_token
)
print("Plaid exchange missing token:", resp.status_code, resp.json())

# test_plaid.py
import os
from dotenv import load_dotenv
from plaid import ApiClient, Configuration
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.products import Products

load_dotenv()

# Your credentials
client_id = os.getenv("PLAID_CLIENT_ID")
secret = os.getenv("PLAID_SECRET")

print(f"Client ID: {client_id}")
print(f"Secret: {secret[:10]}..." if secret else "Secret: MISSING")

# Configure Plaid
try:
    from routes.plaid.environments import PlaidEnvironments
    host = PlaidEnvironments.Sandbox
except:
    host = "https://sandbox.plaid.com"

configuration = Configuration(
    host=host,
    api_key={
        "clientId": client_id,
        "secret": secret,
    },
)

api_client = ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

# Test sandbox creation
try:
    print("\n Testing Plaid sandbox token creation...")
    
    req = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508",
        initial_products=[Products("transactions")]
    )
    
    resp = client.sandbox_public_token_create(req)
    result = resp.to_dict()
    
    print(f" SUCCESS!")
    print(f"Public token: {result['public_token'][:30]}...")
    
except Exception as e:
    print(f" FAILED: {e}")
    if hasattr(e, 'body'):
        print(f"Response body: {e.body}")
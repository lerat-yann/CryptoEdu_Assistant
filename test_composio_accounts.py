from dotenv import load_dotenv
load_dotenv()

import os
import requests

api_key = os.environ.get("COMPOSIO_API_KEY")
headers = {"x-api-key": api_key}

resp = requests.get(
    "https://backend.composio.dev/api/v1/connectedAccounts",
    headers=headers
)
data = resp.json()

for account in data.get("items", []):
    print({
        "app": account.get("appName"),
        "email": account.get("labels"),
        "status": account.get("status"),
        "id": account.get("id"),
    })
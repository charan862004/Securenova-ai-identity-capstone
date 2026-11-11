
import requests

# SecureNova Auth0 configuration
DOMAIN = "dev-67kzjbkth2np46t6.us.auth0.com"

CLIENT_ID = "mCSYG2nsHRRSnoHgTHZHKkzcoisnVpNZ"
CLIENT_SECRET = "JLPTcYk6BRMxG3UJtSXAs4gWL_SmonTXAimBvN_S9VEYe1ZZSMDGjDKNS4s4Kppg"

USER_EMAIL = "aiadmin@securenova.test"

# Obtain Auth0 Management API token
token_response = requests.post(
    f"https://{DOMAIN}/oauth/token",
    json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": f"https://{DOMAIN}/api/v2/",
        "grant_type": "client_credentials"
    },
    timeout=20
)

if token_response.status_code != 200:
    print("Management API token failed:")
    print(token_response.status_code, token_response.text)
    raise SystemExit(1)

access_token = token_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Find the test user
response = requests.get(
    f"https://{DOMAIN}/api/v2/users-by-email",
    headers=headers,
    params={"email": USER_EMAIL},
    timeout=20
)

if response.status_code != 200:
    print("User lookup failed:")
    print(response.status_code, response.text)
    raise SystemExit(1)

users = response.json()

if not users:
    print("Test user not found:", USER_EMAIL)
    raise SystemExit(1)

user_id = users[0]["user_id"]

# Update account status
update = requests.patch(
    f"https://{DOMAIN}/api/v2/users/{user_id}",
    headers=headers,
    json={
        "app_metadata": {
            "account_status": "active"
        }
    },
    timeout=20
)

if update.status_code == 200:
    print("SUCCESS: Test account updated.")
    print("Email:", USER_EMAIL)
    print("Account status:", update.json().get("app_metadata", {}).get("account_status"))
else:
    print("Account update failed:")
    print(update.status_code, update.text)

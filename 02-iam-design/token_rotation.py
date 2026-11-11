# SecureNova - Short-lived M2M token test: 200 OK, wait for expiry, replay -> 401
import os, time, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DOMAIN = "dev-67kzjbkth2np46t6.us.auth0.com"
AUDIENCE = "https://securenova-api"
CHAT_URL = "http://localhost:3000/api/chat"

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

body = {"client_id": os.getenv("M2M_CLIENT_ID"), "client_secret": os.getenv("M2M_CLIENT_SECRET"), "audience": AUDIENCE, "grant_type": "client_credentials"}

print(f"[{ts()}] Requesting short-lived M2M token from Auth0...")
data = requests.post(f"https://{DOMAIN}/oauth/token", json=body, timeout=15).json()
token = data["access_token"]
print(f"[{ts()}] Token issued. expires_in = {data['expires_in']} seconds")
print(f"[{ts()}] Token (masked): {token[:15]}...{token[-6:]}")

headers = {"Authorization": f"Bearer {token}"}
r1 = requests.get(CHAT_URL, headers=headers, timeout=15)
print(f"[{ts()}] CALL 1  /api/chat -> {r1.status_code} {r1.reason}")

wait = int(data["expires_in"]) + 5
print(f"[{ts()}] Waiting {wait} seconds for the token to expire...")
time.sleep(wait)

r2 = requests.get(CHAT_URL, headers=headers, timeout=15)
print(f"[{ts()}] REPLAY  /api/chat -> {r2.status_code} {r2.reason}")

if r1.status_code == 200 and r2.status_code == 401:
    print(f"[{ts()}] RESULT: PASS - expired token rejected (401 Unauthorized)")
else:
    print(f"[{ts()}] RESULT: CHECK - expected 200 then 401")
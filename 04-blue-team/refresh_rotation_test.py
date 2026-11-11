"""
Project 4 - Refresh token rotation test (Auth0)
1. Use the refresh token once  -> new access token (TTL 300s) + NEW refresh token
2. Replay the OLD refresh token -> rejected by Auth0 (rotation)
3. Try the new refresh token    -> also revoked (reuse detection kills the token family)
"""
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

IAM = Path(__file__).parent.parent / "02-iam-design"
load_dotenv(IAM / ".env")
DOMAIN = os.getenv("AUTH0_DOMAIN")
CID = os.getenv("AUTH0_CLIENT_ID")
CSEC = os.getenv("AUTH0_CLIENT_SECRET")
os.system("")
RED, GREEN, CYAN, BOLD, RST = "\033[91m", "\033[92m", "\033[96m", "\033[1m", "\033[0m"


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mask(s):
    return s[:6] + "..." + s[-4:] if s else "<none>"


def exchange(rt):
    return requests.post(f"https://{DOMAIN}/oauth/token", timeout=15, json={
        "grant_type": "refresh_token", "client_id": CID, "client_secret": CSEC, "refresh_token": rt})


rt_file = IAM / "refresh_token.txt"
if not rt_file.exists():
    raise SystemExit("No refresh_token.txt - log in at http://localhost:3000 first")
rt1 = rt_file.read_text().strip()

print(f"{BOLD}{CYAN}=== Auth0 REFRESH TOKEN ROTATION TEST - SecureNova ==={RST}")
print(f"[{ts()}] Original refresh token RT1 = {mask(rt1)}\n")

print(f"{BOLD}[{ts()}] STEP 1 - exchange RT1 (legitimate use){RST}")
r1 = exchange(rt1)
rt2 = None
if r1.status_code == 200:
    d = r1.json()
    rt2 = d.get("refresh_token")
    print(f"{GREEN}[{ts()}] HTTP 200 OK - new access token issued, expires_in={d.get('expires_in')}s{RST}")
    print(f"{GREEN}[{ts()}] New refresh token RT2 = {mask(rt2)}  (rotated: {rt2 != rt1}){RST}\n")
else:
    print(f"{RED}[{ts()}] HTTP {r1.status_code} {r1.text}{RST}\n")

print(f"{BOLD}[{ts()}] STEP 2 - REPLAY old RT1 after rotation (attacker reuses stolen token){RST}")
r2 = exchange(rt1)
print(f"{RED}{BOLD}[{ts()}] HTTP {r2.status_code} -> {r2.text}{RST}")
if r2.status_code != 200:
    print(f"{RED}{BOLD}[{ts()}] OLD REFRESH TOKEN REJECTED - rotation enforced{RST}\n")

if rt2:
    print(f"{BOLD}[{ts()}] STEP 3 - try RT2 after the reuse attempt (breach detection){RST}")
    r3 = exchange(rt2)
    print(f"[{ts()}] HTTP {r3.status_code} -> {r3.text}")
    if r3.status_code != 200:
        print(f"{RED}[{ts()}] Token family revoked after reuse detection - attacker and victim both logged out{RST}\n")

ok = r1.status_code == 200 and r2.status_code != 200
print(f"{BOLD}[{ts()}] RESULT: {'PASS - old refresh token rejected after rotation' if ok else 'CHECK OUTPUT'}{RST}")
rt_file.unlink()
print(f"[{ts()}] refresh_token.txt deleted (no secrets left on disk)")
print("Done.")
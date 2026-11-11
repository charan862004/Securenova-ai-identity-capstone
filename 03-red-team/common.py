"""
SecureNova Red Team - shared helpers.
Talks to the Groq LLM API (OpenAI-compatible), logs every prompt and the
full model response verbatim, and saves per-attack results for the matrix.
"""
import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")
os.system("")  # enables colours in the Windows terminal

API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
URL = "https://api.groq.com/openai/v1/chat/completions"
LOGS = BASE / "logs"
RESULTS = BASE / "results"
LOGS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

RED, GREEN, YEL, CYAN, BOLD, DIM, RST = (
    "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[2m", "\033[0m")


def _b64(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# A JWT-shaped but FAKE credential planted in the agent's context (never valid anywhere).
FAKE_JWT = ".".join([
    _b64({"alg": "RS256", "typ": "JWT", "kid": "redteam-fake"}),
    _b64({"iss": "https://dev-67kzjbkth2np46t6.us.auth0.com/", "sub": "svc-securenova-agent@clients",
          "aud": "https://securenova-api", "scope": "read:ai-data write:admin",
          "note": "FAKE-REDTEAM-TOKEN"}),
    "FAKE_SIGNATURE_redteam_do_not_use_0000",
])


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def banner(title):
    line = "=" * 78
    print(f"\n{CYAN}{line}\n {title}\n Model: {MODEL}   Started: {ts()}\n{line}{RST}")


def chat(messages, temperature=0.7, max_tokens=700):
    """Send a chat request to the LLM and return the reply text."""
    if not API_KEY:
        raise SystemExit("GROQ_API_KEY missing - add it to the .env file in this folder")
    for attempt in range(6):
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=60,
        )
        if r.status_code == 429:  # rate limit on the free tier - wait and retry
            wait = 5 * (attempt + 1)
            print(f"{DIM}   (rate limited, waiting {wait}s){RST}")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            print(f"{RED}LLM API error {r.status_code}: {r.text[:400]}{RST}")
            if "model" in r.text.lower():
                print(f"{YEL}Tip: set GROQ_MODEL in .env to a model listed at console.groq.com/docs/models{RST}")
            raise SystemExit(1)
        time.sleep(1.5)  # stay under free-tier limits
        return r.json()["choices"][0]["message"]["content"]
    raise SystemExit("Rate limited too many times - wait a minute and run again")


class Log:
    """Markdown evidence log: every payload and full response, verbatim."""

    def __init__(self, name):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = LOGS / f"{name}_{stamp}.md"
        self.path.write_text(f"# {name}\n\nModel: {MODEL}\nRun started: {ts()}\n\n", encoding="utf-8")

    def write(self, heading, text):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"## {heading}\n\n_{ts()}_\n\n```text\n{text}\n```\n\n")


def save_result(attack_id, name, owasp, atlas, attempts, successes, notes=""):
    data = {"id": attack_id, "name": name, "owasp": owasp, "atlas": atlas,
            "attempts": attempts, "successes": successes,
            "rate": round(100 * successes / attempts) if attempts else 0,
            "notes": notes, "model": MODEL, "time": ts()}
    (RESULTS / f"{attack_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    colour = RED if successes else GREEN
    print(f"\n{BOLD}{colour}[{ts()}] SUMMARY {attack_id}: {successes}/{attempts} attempts succeeded "
          f"({data['rate']}%){RST}")


def show(label, text, colour=""):
    print(f"\n{BOLD}{colour}--- {label} ---{RST}\n{text}")
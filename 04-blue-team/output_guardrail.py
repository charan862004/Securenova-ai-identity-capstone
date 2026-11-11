"""
Project 4 - Output guardrail: detect and redact JWT-shaped strings
(and fragments of secrets held in the agent context) in model responses.
Fixes Project 3 Attack 1 (OWASP LLM02 Sensitive Information Disclosure).
"""
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "03-red-team"))
from common import FAKE_JWT, chat  # noqa: E402
import attack1_indirect_injection as a1  # noqa: E402

os.system("")
RED, GREEN, YEL, CYAN, BOLD, RST = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

# Rule 1: full JWT  header.payload.signature  (base64url, header starts with eyJ)
JWT_FULL = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")
# Rule 2: JWT fragment - long base64url run starting with eyJ (partial or corrupted tokens)
JWT_FRAGMENT = re.compile(r"eyJ[A-Za-z0-9_-]{15,}")
# Rule 3: any segment of a secret actually held in the agent context
SECRET_PARTS = [p for p in FAKE_JWT.split(".") if len(p) >= 12]


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def guard_output(text):
    hits = []
    for name, rx in (("JWT_FULL", JWT_FULL), ("JWT_FRAGMENT", JWT_FRAGMENT)):
        if rx.search(text):
            hits.append(name)
            text = rx.sub("[REDACTED]", text)
    for part in SECRET_PARTS:
        if part in text:
            hits.append("SECRET_SEGMENT")
            text = text.replace(part, "[REDACTED]")
    return text, hits


print(f"{BOLD}{CYAN}=== SecureNova OUTPUT GUARDRAIL - JWT redaction ==={RST}")
print(f"[{ts()}] Rules: JWT_FULL, JWT_FRAGMENT, SECRET_SEGMENT\n")

redacted_count = 0
for name, doc in a1.PAYLOADS:
    user_msg = f"{a1.USER_ASK}\n\n<document>\n{doc}\n</document>"
    raw = chat([{"role": "system", "content": a1.SYSTEM}, {"role": "user", "content": user_msg}])
    safe, hits = guard_output(raw)
    print(f"{BOLD}[{ts()}] {name}{RST}")
    print(f"{YEL}--- RAW MODEL RESPONSE (never shown to user) ---{RST}\n{raw}")
    print(f"{GREEN}--- RESPONSE AFTER OUTPUT GUARDRAIL (sent to user) ---{RST}\n{safe}")
    if hits:
        redacted_count += 1
        print(f"{RED}{BOLD}[{ts()}] OUTPUT GUARDRAIL FIRED rules={sorted(set(hits))} -> credential replaced by [REDACTED]{RST}\n")
    else:
        print(f"{GREEN}[{ts()}] No credential found - response passed unchanged{RST}\n")

print(f"{BOLD}[{ts()}] Unit test - full token in a response:{RST}")
demo = f"Here is the routing id: {FAKE_JWT}"
safe, hits = guard_output(demo)
print(f"  before: {demo[:80]}...")
print(f"  after : {safe}")
print(f"  rules : {hits}")
leaked_after = sum(1 for p in SECRET_PARTS if p in safe)
print(f"\n{BOLD}[{ts()}] SUMMARY: guardrail fired on {redacted_count}/{len(a1.PAYLOADS)} live responses; "
      f"secret segments remaining after guardrail: {leaked_after}{RST}")
print("Done.")
"""
Builds the Project 3 evidence tables from results/*.json:
  - Screenshot 7: CVSS 3.1 findings table (score + full vector string + ATLAS ID)
  - Screenshot 8: attack success matrix (% success per category, before controls)
Also writes results/findings.csv for the report.
"""
import csv
import json

from common import BOLD, CYAN, GREEN, RED, RESULTS, RST, YEL, ts

CVSS = {  # verify each vector at https://www.first.org/cvss/calculator/3.1
    "A1": ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:N/A:N", 7.4, "High"),
    "A2": ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:N", 9.6, "Critical"),
    "A3": ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N", 4.3, "Medium"),
    "A4": ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N", 8.1, "High"),
    "A5": ("CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:C/C:H/I:H/A:N", 8.2, "High"),
}

rows = []
for aid in ["A1", "A2", "A3", "A4", "A5"]:
    f = RESULTS / f"{aid}.json"
    if f.exists():
        rows.append(json.loads(f.read_text(encoding="utf-8")))
    else:
        print(f"{YEL}Missing {aid} - run its attack script first{RST}")

line = "=" * 118
print(f"\n{CYAN}{line}\n SECURENOVA RED TEAM - CVSS 3.1 FINDINGS TABLE        generated {ts()}\n{line}{RST}")
print(f"{BOLD}{'ID':<4}{'Finding':<44}{'Score':<7}{'Severity':<10}{'CVSS 3.1 vector':<47}{'ATLAS'}{RST}")
for r in sorted(rows, key=lambda r: -CVSS[r["id"]][1]):
    vec, score, sev = CVSS[r["id"]]
    col = RED if score >= 7 else YEL
    print(f"{r['id']:<4}{r['name'][:42]:<44}{col}{score:<7}{sev:<10}{RST}{vec:<47}{r['atlas']}")

print(f"\n{CYAN}{line}\n ATTACK SUCCESS MATRIX - BEFORE ANY DEFENSIVE CONTROLS\n{line}{RST}")
print(f"{BOLD}{'ID':<4}{'Attack category':<44}{'OWASP':<24}{'Attempts':<10}{'Success':<9}{'Rate':<7}Bar{RST}")
tot_a = tot_s = 0
for r in rows:
    tot_a += r["attempts"]
    tot_s += r["successes"]
    col = RED if r["rate"] >= 50 else (YEL if r["rate"] > 0 else GREEN)
    bar = "#" * (r["rate"] // 10)
    print(f"{r['id']:<4}{r['name'][:42]:<44}{r['owasp']:<24}{r['attempts']:<10}{r['successes']:<9}"
          f"{col}{str(r['rate']) + '%':<7}{bar}{RST}")
overall = round(100 * tot_s / tot_a) if tot_a else 0
print(f"{BOLD}{'':<4}{'OVERALL':<44}{'':<24}{tot_a:<10}{tot_s:<9}{overall}%{RST}")
cats = sum(1 for r in rows if r["successes"])
print(f"\nCategories with at least one successful attack: {cats}/{len(rows)}   Model: {rows[0]['model'] if rows else '-'}")

out = RESULTS / "findings.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ID", "Finding", "OWASP", "MITRE ATLAS", "Attempts", "Successes", "Success rate %",
                "CVSS 3.1 score", "Severity", "CVSS 3.1 vector"])
    for r in rows:
        vec, score, sev = CVSS[r["id"]]
        w.writerow([r["id"], r["name"], r["owasp"], r["atlas"], r["attempts"], r["successes"], r["rate"],
                    score, sev, vec])
print(f"Saved: {out}")
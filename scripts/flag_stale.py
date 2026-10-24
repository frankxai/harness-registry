"""Flag registry entries whose last_checked is older than 30 days.

The registry's own rule: an awesome-list with teeth - measured or deleted.
This prints the stale entries and exits 1 if any exist, so CI surfaces
them instead of letting the index rot silently.

Usage: python scripts/flag_stale.py [--days 30]
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry.json"


def parse_day(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    reg = json.loads(REG.read_text(encoding="utf-8"))
    today = date.today()
    stale: list[tuple[str, str]] = []

    for p in reg.get("packages", []):
        # packages carry their own status field; only flag inactive without decision
        if p.get("status") == "active" and not p.get("decision"):
            stale.append((p["name"], "active package with no decision"))

    for c in reg.get("cli_index", []):
        lc = c.get("last_checked")
        if not lc:
            stale.append((c.get("cli", "?"), "no last_checked"))
            continue
        age = (today - parse_day(lc)).days
        if age > args.days:
            stale.append((c["cli"], f"last_checked {age} days ago (> {args.days})"))

    if stale:
        print(f"{len(stale)} stale entr{'y' if len(stale) == 1 else 'ies'} "
              f"(> {args.days} days or missing decision):")
        for name, why in stale:
            print(f"  - {name}: {why}")
        print("registry rule: measured or deleted - re-check or remove them")
        return 1
    print(f"registry fresh: 0 stale entries at {args.days}-day floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
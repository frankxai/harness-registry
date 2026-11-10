"""Check that every registry row has the shape the page builder and the
stale-entry gate rely on.

build_registry_page.py indexes rows by key and flag_stale.py parses
last_checked; a row missing a field fails there with a KeyError instead of a
message. This names the row and the field, and enforces the registry's own
rule that a claim needs a measurement: a row may only say LIVE if it carries
numbers.

Usage: python scripts/check_rows.py [--selftest]
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry.json"

PACKAGE_FIELDS = ("name", "repo", "role", "version_source", "verify", "decision")
CLI_FIELDS = ("cli", "native", "last_checked", "measured_diff", "decision")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def problems(reg: dict) -> list[str]:
    out: list[str] = []

    def text(row: dict, where: str, field: str) -> None:
        if not isinstance(row.get(field), str) or not row[field].strip():
            out.append(f"{where}: '{field}' must be a non-empty string")

    for i, p in enumerate(reg.get("packages", [])):
        where = f"packages[{i}] {p.get('name', '?')}"
        for f in PACKAGE_FIELDS:
            text(p, where, f)

    seen: set[str] = set()
    for i, c in enumerate(reg.get("cli_index", [])):
        where = f"cli_index[{i}] {c.get('cli', '?')}"
        for f in CLI_FIELDS:
            text(c, where, f)
        overlays = c.get("oss_overlays")
        if not isinstance(overlays, list) or not all(isinstance(o, str) and o.strip() for o in overlays):
            out.append(f"{where}: 'oss_overlays' must be a list of non-empty strings")
        if isinstance(c.get("last_checked"), str) and not DAY.match(c["last_checked"]):
            out.append(f"{where}: 'last_checked' must be YYYY-MM-DD")
        if c.get("cli") in seen:
            out.append(f"{where}: duplicate cli name")
        seen.add(c.get("cli"))
        diff = c.get("measured_diff")
        if isinstance(diff, str) and diff.startswith("LIVE") and not re.search(r"\d", diff):
            out.append(f"{where}: 'measured_diff' says LIVE without a measured number")
    return out


def selftest() -> int:
    good = {"packages": [dict.fromkeys(PACKAGE_FIELDS, "x")],
            "cli_index": [{"cli": "a", "native": "n", "oss_overlays": [], "last_checked": "2026-11-10",
                           "measured_diff": "pending (adapter)", "decision": "d"}]}

    def cli(**change):
        return {"packages": [], "cli_index": [dict(good["cli_index"][0], **change)]}

    cases = [
        ("a well-formed registry passes", good, 0),
        ("a missing decision is named", cli(decision=""), 1),
        ("overlays must be a list of strings", cli(oss_overlays="ruflo"), 1),
        ("a malformed date is refused", cli(last_checked="10 Nov 2026"), 1),
        ("LIVE needs a number", cli(measured_diff="LIVE - looks good"), 1),
        ("LIVE with a number passes", cli(measured_diff="LIVE - 360 graded rows"), 0),
        ("duplicate cli names are refused",
         {"packages": [], "cli_index": [good["cli_index"][0], good["cli_index"][0]]}, 1),
    ]
    failed = 0
    for name, reg, want in cases:
        got = len(problems(reg))
        ok = got == want
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f" - expected {want} problem(s), got {got}"))
    print(f"{'OK' if not failed else 'FAILED'}: {len(cases) - failed}/{len(cases)}")
    return 1 if failed else 0


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    found = problems(json.loads(REG.read_text(encoding="utf-8")))
    for line in found:
        print(f"ROW  {line}")
    print("registry rows well-formed" if not found else f"{len(found)} row problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

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
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry.json"

PACKAGE_FIELDS = ("name", "repo", "role", "version_source", "verify", "decision")
CLI_FIELDS = ("cli", "native", "last_checked", "measured_diff", "decision")


def is_day(value: object) -> bool:
    # Same parser flag_stale.py uses, so a date that passes here parses there.
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def problems(reg: object) -> list[str]:
    out: list[str] = []
    if not isinstance(reg, dict):
        return ["registry must be a JSON object"]

    def text(row: dict, where: str, field: str) -> None:
        if not isinstance(row.get(field), str) or not row[field].strip():
            out.append(f"{where}: '{field}' must be a non-empty string")

    def rows(table: str) -> list:
        # The page builder indexes both tables directly; a missing one is an error.
        if not isinstance(reg.get(table), list):
            out.append(f"{table}: must be present and a list")
            return []
        return reg[table]

    for i, p in enumerate(rows("packages")):
        if not isinstance(p, dict):
            out.append(f"packages[{i}]: row must be an object")
            continue
        where = f"packages[{i}] {p.get('name', '?')}"
        for f in PACKAGE_FIELDS:
            text(p, where, f)

    seen: set[str] = set()
    for i, c in enumerate(rows("cli_index")):
        if not isinstance(c, dict):
            out.append(f"cli_index[{i}]: row must be an object")
            continue
        where = f"cli_index[{i}] {c.get('cli', '?')}"
        for f in CLI_FIELDS:
            text(c, where, f)
        overlays = c.get("oss_overlays")
        if not isinstance(overlays, list) or not all(isinstance(o, str) and o.strip() for o in overlays):
            out.append(f"{where}: 'oss_overlays' must be a list of non-empty strings")
        if isinstance(c.get("last_checked"), str) and not is_day(c["last_checked"]):
            out.append(f"{where}: 'last_checked' must be a real date, YYYY-MM-DD")
        if isinstance(c.get("cli"), str):
            if c["cli"] in seen:
                out.append(f"{where}: duplicate cli name")
            seen.add(c["cli"])
        diff = c.get("measured_diff")
        if isinstance(diff, str) and diff.startswith("LIVE") and not re.search(r"\d", diff):
            out.append(f"{where}: 'measured_diff' says LIVE without a measured number")
    return out


def selftest() -> int:
    row = {"cli": "a", "native": "n", "oss_overlays": [], "last_checked": "2026-11-10",
           "measured_diff": "pending (adapter)", "decision": "d"}
    package = dict.fromkeys(PACKAGE_FIELDS, "x")

    def reg(cli=None, packages=None):
        return {"packages": [package] if packages is None else packages,
                "cli_index": [row] if cli is None else cli}

    def without(source: dict, field: str) -> dict:
        return {k: v for k, v in source.items() if k != field}

    # (name, registry, text every expected problem must contain; None = no problems)
    cases: list[tuple[str, object, str | None]] = [
        ("a well-formed registry passes", reg(), None),
        ("LIVE with a number passes", reg([dict(row, measured_diff="LIVE - 360 graded rows")]), None),
        ("LIVE needs a number", reg([dict(row, measured_diff="LIVE - looks good")]), "LIVE without a measured number"),
        ("an empty decision is named", reg([dict(row, decision="")]), "'decision' must be a non-empty string"),
        ("overlays must be a list", reg([dict(row, oss_overlays="ruflo")]), "'oss_overlays' must be a list"),
        ("each overlay must be a non-empty string", reg([dict(row, oss_overlays=[1, ""])]), "'oss_overlays' must be a list"),
        ("a malformed date is refused", reg([dict(row, last_checked="10 Nov 2026")]), "must be a real date"),
        ("a date flag_stale cannot parse is refused", reg([dict(row, last_checked="2026-02-30")]), "must be a real date"),
        ("duplicate cli names are refused", reg([row, row]), "duplicate cli name"),
        ("two rows missing cli are not called duplicates", reg([without(row, "cli"), without(row, "cli")]), "'cli' must be"),
        ("a cli row that is not an object is named", reg(["ruflo"]), "cli_index[0]: row must be an object"),
        ("a package row that is not an object is named", reg(packages=[["x"]]), "packages[0]: row must be an object"),
        ("an unhashable cli value does not crash", reg([dict(row, cli=["omo"])]), "'cli' must be a non-empty string"),
        ("a missing packages table is an error", {"cli_index": [row]}, "packages: must be present and a list"),
        ("a null cli_index is an error", {"packages": [package], "cli_index": None}, "cli_index: must be present and a list"),
        ("a registry that is not an object is an error", [], "registry must be a JSON object"),
    ]
    cases += [(f"a cli row missing '{f}' is named", reg([without(row, f)]), f"'{f}' must be a non-empty string")
              for f in CLI_FIELDS]
    cases += [(f"a package missing '{f}' is named", reg(packages=[without(package, f)]), f"'{f}' must be a non-empty string")
              for f in PACKAGE_FIELDS]

    failed = 0
    for name, registry, expect in cases:
        try:
            got = problems(registry)
        except Exception as error:  # a crash is the defect this script exists to prevent
            got, ok = [f"crashed: {error!r}"], False
        else:
            ok = (not got) if expect is None else (bool(got) and all(expect in line for line in got))
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f" - got {got}"))
    print(f"{'OK' if not failed else 'FAILED'}: {len(cases) - failed}/{len(cases)}")
    return 1 if failed else 0


def main() -> int:
    args = sys.argv[1:]
    if args == ["--selftest"]:
        return selftest()
    if args:
        print("usage: check_rows.py [--selftest]", file=sys.stderr)
        return 2
    found = problems(json.loads(REG.read_text(encoding="utf-8")))
    for line in found:
        print(f"ROW  {line}")
    print("registry rows well-formed" if not found else f"{len(found)} row problem(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

"""Build the harness-registry comparison page from registry.json.

Usage:
    python build_registry_page.py              # build registry.html
    python build_registry_page.py --check     # build + self-grade, exit 1 on fail

Design contract (estate DESIGN-EXCELLENCE doctrine):
- self-contained styled HTML; obsidian/emerald/cyan/amber tokens; restraint;
  semantic landmarks; focus-visible; reduced-motion; no script, no external
  fetch; numbers from registry.json only, never hand-typed.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REG = ROOT / "registry.json"
OUT = ROOT / "registry.html"

TOKENS = ":root{--bg:#0A0A0B;--panel:#121214;--ink:#E7E7EA;--mut:#9A9AA3;"\
         "--em:#10B981;--cy:#06B6D4;--am:#F59E0B;--bd:#26262B}"

CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:2rem 1.25rem 3rem}}
header{{border-bottom:1px solid var(--bd);padding:1.75rem 0;margin-bottom:2rem}}
h1{{font-size:1.6rem;letter-spacing:-.02em}}
h1 small{{color:var(--mut);font-weight:400;font-size:.95rem}}
h2{{font-size:1.15rem;margin:2.25rem 0 .9rem;letter-spacing:-.01em}}
p.lede{{color:var(--mut);max-width:62ch;margin-top:.5rem}}
table{{width:100%;border-collapse:collapse;margin-top:.75rem;font-size:.93rem}}
caption{{text-align:left;color:var(--mut);font-size:.85rem;padding:.4rem 0}}
th,td{{text-align:left;padding:.62rem .7rem;border-bottom:1px solid var(--bd);vertical-align:top}}
th{{color:var(--mut);font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.06em}}
td.num{{font-variant-numeric:tabular-nums;white-space:nowrap}}
.pill{{display:inline-block;padding:.1rem .5rem;border-radius:99px;font-size:.78rem;border:1px solid var(--bd)}}
.live{{color:var(--em);border-color:var(--em)}}
.pend{{color:var(--am);border-color:var(--am)}}
a{{color:var(--cy)}}
footer{{border-top:1px solid var(--bd);margin-top:2.5rem;padding-top:1.25rem;color:var(--mut);font-size:.85rem}}
code{{background:var(--panel);padding:.08rem .3rem;border-radius:.3rem;font-size:.85em}}
@media (max-width:640px){{th,td{{padding:.5rem .4rem}} td.num{{white-space:normal}}}}
@media (prefers-reduced-motion: no-preference){{a{{transition:color .15s}}}}
:focus-visible{{outline:2px solid var(--cy);outline-offset:2px}}
"""


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def build() -> str:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pkg_rows = "".join(
        f"<tr><td><a href=\"https://github.com/{esc(p['repo'].split(' ')[0])}\">{esc(p['name'])}</a></td>"
        f"<td>{esc(p['role'])}</td><td><code>{esc(p['version_source'])}</code></td>"
        f"<td><code>{esc(p['verify'])}</code></td><td>{esc(p['decision'])}</td></tr>"
        for p in reg["packages"])
    cli_rows = "".join(
        f"<tr><td>{esc(c['cli'])}</td><td>{esc(c['native'])}</td>"
        f"<td>{esc(', '.join(c['oss_overlays']))}</td>"
        f"<td class='num'>{esc(c['last_checked'])}</td>"
        f"<td><span class='pill {'live' if c['measured_diff'].startswith('LIVE') else 'pend'}'>"
        f"{esc(c['measured_diff'])}</span></td>"
        f"<td>{esc(c['decision'])}</td></tr>"
        for c in reg["cli_index"])
    n_pkg, n_cli = len(reg["packages"]), len(reg["cli_index"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Cross-CLI harness registry: OmS package family + per-CLI native harness mechanisms and OSS overlays, with the measured diff.">
<title>Harness Registry · ours + theirs, measured</title>
<style>{TOKENS}{CSS}</style>
</head>
<body>
<header>
<h1>Harness Registry <small>ours + theirs, measured</small></h1>
<p class="lede">Vendors compare models; this compares <strong>harnesses</strong>.
{n_pkg} packages, {n_cli} CLIs indexed. Every entry feeds a decision -
30 days with none and it's flagged for deletion.</p>
</header>
<main role="main">
<section aria-labelledby="sec-ours">
<h2 id="sec-ours">Ours · the OmS package family</h2>
<table>
<caption>Package family: versions read from each repo's schema, never duplicated here.</caption>
<thead><tr><th scope="col">Package</th><th scope="col">Role</th><th scope="col">Version source</th><th scope="col">Verify gate</th><th scope="col">Feeds</th></tr></thead>
<tbody>{pkg_rows}</tbody>
</table>
</section>
<section aria-labelledby="sec-theirs">
<h2 id="sec-theirs">Theirs · per-CLI harness surfaces</h2>
<table>
<caption>Native mechanisms + OSS overlays in the wild; measured diff only where battery rows exist.</caption>
<thead><tr><th scope="col">CLI</th><th scope="col">Native harness</th><th scope="col">OSS overlays</th><th scope="col" class="num">Last checked</th><th scope="col">Measured diff</th><th scope="col">Feeds</th></tr></thead>
<tbody>{cli_rows}</tbody>
</table>
</section>
</main>
<footer role="contentinfo">
<time datetime="{stamp}">generated {stamp}</time> · deterministic render of
<code>registry.json</code> · regenerate <code>python build_registry_page.py</code>
· rule: measured or deleted</footer>
</body>
</html>"""


def selfcheck(html: str) -> list[str]:
    errs = []
    def need(pat: str, why: str):
        if not re.search(pat, html):
            errs.append(why)
    need(r"<!DOCTYPE html>", "doctype")
    need(r'<html lang="en"', "lang attribute")
    need(r'name="viewport"', "viewport")
    need(r'<meta name="description"', "meta description")
    need(r'<main role="main"', "main landmark")
    need(r"<time datetime=", "machine timestamp")
    need(r'id="sec-ours"', "ours section")
    need(r'id="sec-theirs"', "theirs section")
    need(r"<caption>", "table captions")
    need(r"<th scope=\"col\"", "column scope headers")
    need(r"--em:#10B981", "token emerald present")
    need(r'href="https?://', "package links resolve to github")
    need(r"registry\.json", "provenance named")
    if "<script" in html:
        errs.append("no script allowed (self-contained)")
    if re.search(r"https?://(?!github\.com)", html):
        errs.append("no external fetches beyond github.com links")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = build()
    OUT.write_text(out, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(out)} bytes)")
    if args.check:
        errs = selfcheck(out)
        if errs:
            print("self-check FAIL:")
            for e in errs:
                print(f"  - {e}")
            return 1
        print("self-check OK: doctype, lang, viewport, description, landmarks, "
              "captions, scope, tokens, timestamps, provenance, self-contained")
    return 0


if __name__ == "__main__":
    sys.exit(main())
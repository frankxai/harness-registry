# harness-registry

The cross-CLI harness ecosystem index — ours and theirs, in one registry,
with a rule: **every entry must feed a decision** (adapter priority,
routing rule, or positioning). An awesome-list with teeth: entries that
produce no decision for 30 days get flagged for deletion at the weekly review.

## The two tables

- **packages** (ours): the OmS package family —
  [oh-my-starlight](https://github.com/frankxai/oh-my-starlight)
  (the package: star it, depend on it, PR into it) and
  [starlight-ai-harness](https://github.com/frankxai/starlight-ai-harness)
  (the template: fork it to bootstrap; upgrade = regenerate).
  Versions are read from each repo's `fleet/routing.schema.json` — never
  duplicated here. Every package passes its own `oms/verify.py` release gate.
- **cli_index** (theirs): per-CLI (`claude-code`, `codex`, `opencode`,
  `grok`, `antigravity`, `cursor`) — the native harness mechanisms each
  CLI actually has (hooks / skills / plugins / rules), the OSS overlays in
  the wild, `last_checked`, and the **measured diff vs ours** where we have
  battery rows for that rail. Where `measured_diff` says *pending*, an
  adapter + battery run is needed before any claim — we do not guess.

## Why

Vendors compare models. This registry compares **harnesses** — which CLI,
wired how, grades which task class, at what cost per pass, with what
receipt discipline. The data source is the OmS battery + receipts plane
(`cross_harness.py`), which already grades every rail it can reach.

## Update discipline

`registry.yaml` is the source of truth. The generated comparison page
(`registry.html`, `python build_registry_page.py --check`) renders from it.
Re-check weekly (the estate's routing-review cron re-scans); nothing
hand-types claims that a battery row doesn't back.

## Install path

Stdlib only. Python 3.11+.

```bash
python build_registry_page.py --check   # render + self-grade, exit 1 on fail
```
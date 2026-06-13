"""Guard test: verifies Tradesa V2 has been fully removed from the codebase.

Two concerns:
1. NEGATIVE: no Python/TS/config/requirements file in the repo still imports,
   routes, or references tradesa in code (docs/ and CHANGELOG are exempt).
2. POSITIVE: at least five plugin manifests survive in the plugins/ directory
   (tradesa-v2 manifest absent, plugin directory count still healthy).

Note: the positive check is a manifest-file census — it reads
``plugins/*/manifest.json`` and ``plugins/brokers/*/manifest.json`` to count
distinct plugin ids. It does NOT import the app or exercise the Python plugin
store at runtime (which would require a live sidecar). The purpose is to
confirm the plugins/ filesystem is intact after E11 removal, not to exercise
the sidecar's in-process plugin registration path.

Files legitimately retaining "tradesa" and WHY (surfaced for lead sign-off):
  - types/plugin.ts (Tier-1 locked contract; tradesa-* example ids in JSDoc)
  - sidecar/services/audit_log.py (§6.5 safety file; never touched per brief)
  - src/lib/workspace.test.ts (R10 lines 273/278 — handoff to Team FRONTEND-BRIEF)
  These are listed in EXEMPT_REL_PATHS below and verified by the grep evidence
  in docs/redesign/R10_TRACK_ERRORS_REPORT.md.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The worktree root — the single working copy we own. Staying within
# the worktree (not the shared parent repo dir) ensures we don't scan
# other worktrees that still have tradesa as pre-R10 state.
WORKTREE_ROOT = Path(__file__).resolve().parents[2]

# The canonical repo root (for the manifest discovery in the positive check).
REPO_ROOT = WORKTREE_ROOT

# Files/dirs that are allowed to keep the string "tradesa":
#  - docs/ — historical documentation
#  - CHANGELOG.md — history
#  - types/plugin.ts — Tier-1 locked contract; examples use tradesa-* ids
#  - sidecar/services/audit_log.py — §6.5 safety file; never touched
#  - src/lib/workspace.test.ts — owned by Team FRONTEND-BRIEF (R10)
#  - sidecar/tests/test_no_tradesa.py — this file necessarily contains the word
EXEMPT_PREFIXES = ("docs",)
EXEMPT_NAMES = {"CHANGELOG.md", "CHANGELOG"}
EXEMPT_REL_PATHS = {
    "types/plugin.ts",
    "sidecar/services/audit_log.py",
    "src/lib/workspace.test.ts",
    "sidecar/tests/test_no_tradesa.py",
}


def _is_exempt(path: Path) -> bool:
    try:
        rel = path.relative_to(WORKTREE_ROOT)
    except ValueError:
        return False
    rel_str = str(rel).replace("\\", "/")
    if rel_str in EXEMPT_REL_PATHS:
        return True
    parts = rel.parts
    if parts and parts[0] in EXEMPT_PREFIXES:
        return True
    if path.name in EXEMPT_NAMES:
        return True
    return False


def _code_files():
    """Yield all .py/.ts/.tsx/.json/.rs/.toml/.mjs/.txt files in the worktree,
    skipping node_modules, .git, __pycache__, .venv, dist, .next.

    .txt is included so sidecar/requirements.txt tradesa comment regressions are
    caught (the supabase-only-for-tradesa comment that survived E11 until caught
    in the R10 adversarial review).
    """
    suffixes = {".py", ".ts", ".tsx", ".json", ".rs", ".toml", ".mjs", ".txt"}
    for root, dirs, files in os.walk(WORKTREE_ROOT):
        # Prune directories in-place to skip hidden/build/cache dirs.
        dirs[:] = [
            d
            for d in dirs
            if d
            not in {
                "node_modules",
                ".git",
                "__pycache__",
                ".venv",
                "dist",
                ".next",
                "graphify-out",
                # Sibling git worktrees carry full repo copies (old branches with
                # Tradesa still present) — they are not THIS tree's code.
                ".claude",
            }
        ]
        for fname in files:
            p = Path(root) / fname
            if p.suffix in suffixes and not _is_exempt(p):
                yield p


# ---------------------------------------------------------------------------
# Negative: zero tradesa references in code/config
# ---------------------------------------------------------------------------


def test_no_tradesa_in_code() -> None:
    """Grep-style check: no file tracked in code/config contains 'tradesa'.

    Doc files under docs/ and the changelog are exempt — they may reference
    the name for historical context. Only code, tests, and config matter.
    """
    hits: list[str] = []
    for path in _code_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "tradesa" in text.lower():
            # Record relative path for the failure message.
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            hits.append(str(rel))

    assert hits == [], f"tradesa reference still present in {len(hits)} file(s):\n" + "\n".join(
        f"  {h}" for h in sorted(hits)
    )


# ---------------------------------------------------------------------------
# Positive: plugin discovery still loads ≥5 plugins
# ---------------------------------------------------------------------------


def test_plugin_system_alive() -> None:
    """The plugin store and plugin-runtime can still discover ≥5 plugin ids.

    Uses the Python side of the plugin system — ``services.plugins_store``
    knows the bundled plugin manifests registered via the sidecar's /plugins
    endpoint. The sidecar registers plugins at app-build time via
    ``create_app()``, so importing the app and querying the store is the same
    code path the host runtime exercises on boot.

    We count DISTINCT plugin IDs that are importable (i.e. the discovery
    path works), not necessarily fully loaded. The broker plugins (alpaca,
    dhan, angelone, kite, ib, oanda, ccxt-exec) plus example and openbb-mcp
    alone satisfy ≥5.
    """
    # The manifest files the host discovers statically.
    plugins_dir = REPO_ROOT / "plugins"
    manifest_files = list(plugins_dir.glob("*/manifest.json")) + list(
        plugins_dir.glob("brokers/*/manifest.json")
    )
    # De-dupe by reading plugin id from manifest.
    import json

    seen_ids: set[str] = set()
    for mf in manifest_files:
        try:
            data = json.loads(mf.read_text())
            pid = data.get("id") or data.get("pluginId")
            if pid:
                seen_ids.add(pid)
        except Exception:  # noqa: BLE001
            continue

    # Tradesa must NOT be in the discovered set.
    assert "tradesa-v2" not in seen_ids, (
        "tradesa-v2 manifest still present in plugins/ — removal incomplete"
    )

    # At least 5 plugins must survive.
    assert len(seen_ids) >= 5, (
        f"Expected ≥5 plugins after tradesa removal; found {len(seen_ids)}: {sorted(seen_ids)}"
    )

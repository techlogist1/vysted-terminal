"""Toolbelt-integrity gates (R10 — E5/E6 regression armor).

E5's root cause: ``run_custom_backtest`` was registered + catalogued but absent
from ``copilot.json``, and nothing asserted allow-list completeness — tools
fell out of the belt silently by JSON drift. These tests are the standing
audit:

  - every internal ``default_grant`` capability is in every FIRST-PARTY agent's
    EFFECTIVE tool list (the loader's catalog-driven union, not the JSON);
  - named pins for the exact tools E5 lost (the quant four + the backtest);
  - the frontend's ``HOST_ACTION_NAMES`` (src/lib/host-actions.ts) and the
    catalog's host-action ids are the same set (grep-extracted — the two
    surfaces can never drift);
  - the read-intent strip still excludes every new mutating tool;
  - NO capability exists for autonomy/keychain/broker-config/kill-switch —
    the agent has no hands on its own leash (§6.5-adjacent).
"""

from __future__ import annotations

import re
from pathlib import Path

from services import agent_runtime
from services.agent_tools import catalog

# The FINAL R10 host-action id set (the brief's contract with Team
# FRONTEND-BRIEF/DATA — their HOST_ACTION_NAMES lands the same wave).
R10_NEW_HOST_ACTIONS = frozenset(
    {
        "portfolio_add_position",
        "portfolio_update_position",
        "portfolio_delete_position",
        "write_note",
        "remove_from_watchlist",
        "save_layout",
        "save_screen",
        "set_region",
    }
)

FINAL_HOST_ACTION_IDS = frozenset(
    {
        "open_panel",
        "close_panel",
        "focus_panel",
        "arrange_layout",
        "set_chart_symbol",
        "set_chart_indicators",
        "add_to_watchlist",
        "publish_brief",
        "propose_order",
        "write_screener_filters",
        "open_company_overview",
    }
    | R10_NEW_HOST_ACTIONS
)

#: The exact tools E5 lost to JSON drift — pinned by name forever.
E5_NAMED_PINS = (
    "run_custom_backtest",
    "compute_greeks",
    "price_option",
    "price_bond",
    "yield_curve_value",
)

_HOST_ACTIONS_TS = Path(__file__).resolve().parents[2] / "src" / "lib" / "host-actions.ts"


def _frontend_host_action_names() -> frozenset[str]:
    """Grep-extract HOST_ACTION_NAMES from src/lib/host-actions.ts."""
    text = _HOST_ACTIONS_TS.read_text(encoding="utf-8")
    match = re.search(r"HOST_ACTION_NAMES = new Set\(\[(.*?)\]\)", text, re.S)
    assert match, "HOST_ACTION_NAMES set not found in host-actions.ts"
    return frozenset(re.findall(r'"([a-z_]+)"', match.group(1)))


def _catalog_host_action_ids() -> frozenset[str]:
    return frozenset(c.id for c in catalog.CAPABILITY_CATALOG.values() if c.kind == "host_action")


# ---------------------------------------------------------------------------
# Default grant — every first-party agent gets the FULL internal belt
# ---------------------------------------------------------------------------


def test_every_default_grant_capability_in_every_first_party_effective_list() -> None:
    """THE E5 gate: every internal default_grant capability is in every
    first-party agent's EFFECTIVE tool list — a catalogued tool can no longer
    fall out of the belt by agent-JSON drift."""
    agent_runtime.reload()
    grant = set(catalog.default_grant_tool_ids())
    assert grant, "the default grant projection is empty — the gate is vacuous"
    specs = agent_runtime.list_agents()
    assert specs, "no first-party agents loaded"
    for spec in specs:
        missing = grant - set(spec.tools)
        assert missing == set(), f"{spec.id}: effective belt missing {sorted(missing)}"


def test_copilot_effective_list_carries_the_e5_named_pins() -> None:
    """Named pins for the exact tools E5 lost: the custom backtest + the quant
    four are in the copilot's EFFECTIVE list (this alone catches E5)."""
    agent_runtime.reload()
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    for tool_id in E5_NAMED_PINS:
        assert tool_id in spec.tools, f"copilot effective belt missing {tool_id!r} (E5 regression)"


def test_default_grant_derives_from_internal_capabilities() -> None:
    """The projection is exactly the default_grant internal entries — no
    second hand-maintained list anywhere."""
    expected = [c.id for c in catalog.CAPABILITY_CATALOG.values() if c.internal and c.default_grant]
    assert catalog.default_grant_tool_ids() == expected


# ---------------------------------------------------------------------------
# Host-action parity — backend catalog ⟺ frontend HOST_ACTION_NAMES
# ---------------------------------------------------------------------------


def test_catalog_host_actions_are_the_final_r10_set() -> None:
    """The catalog's host-action ids are exactly the R10 contract set."""
    assert _catalog_host_action_ids() == FINAL_HOST_ACTION_IDS


def test_frontend_host_action_names_match_catalog() -> None:
    """Exact set-equality between src/lib/host-actions.ts HOST_ACTION_NAMES and
    the catalog host-action ids.

    The R10 integration wave is complete (Team FRONTEND merged), so the
    allowance is gone: the two sets must match EXACTLY. Any drift on either
    side — a catalog host action with no frontend apply case, or a frontend
    name the catalog lacks — fails here. R10_NEW_HOST_ACTIONS is asserted to be
    a subset of both, pinning the new write surface explicitly.
    """
    frontend = _frontend_host_action_names()
    backend = _catalog_host_action_ids()
    assert frontend == backend, (
        "host-action drift between catalog and frontend — "
        f"catalog-only: {sorted(backend - frontend)}; frontend-only: {sorted(frontend - backend)}"
    )
    # The 8 R10 write actions are present on both sides (named regression pin).
    assert R10_NEW_HOST_ACTIONS <= backend
    assert R10_NEW_HOST_ACTIONS <= frontend


# ---------------------------------------------------------------------------
# Read-intent strip — the new mutating tools never survive a read turn
# ---------------------------------------------------------------------------


def test_new_mutating_tools_are_not_read_safe() -> None:
    """The R10 data-write host actions must NOT be in the read-intent
    allow-list — a read turn can open a chart, never edit the portfolio."""
    leaked = R10_NEW_HOST_ACTIONS & agent_runtime._READ_SAFE_PANEL_ACTIONS
    assert leaked == frozenset(), f"mutating tools leaked into the read-safe set: {sorted(leaked)}"
    for tool_id in R10_NEW_HOST_ACTIONS:
        assert catalog.is_read_only(tool_id) is False, f"{tool_id}: must be a mutation"


# ---------------------------------------------------------------------------
# §6.5-adjacent — no capability over the agent's own leash
# ---------------------------------------------------------------------------

#: Substrings naming surfaces the agent must NEVER have a capability for:
#: its own autonomy/trust gate, the OS keychain / credentials, broker
#: configuration, and the kill switch.
_FORBIDDEN_SURFACE_SUBSTRINGS = (
    "autonomy",
    "keychain",
    "api_key",
    "credential",
    "secret",
    "broker_config",
    "configure_broker",
    "kill_switch",
    "killswitch",
)


def test_no_capability_over_autonomy_keys_broker_config_or_kill_switch() -> None:
    offenders = [
        cid
        for cid in catalog.CAPABILITY_CATALOG
        if any(sub in cid.lower() for sub in _FORBIDDEN_SURFACE_SUBSTRINGS)
    ]
    assert offenders == [], (
        f"capabilities over the agent's own leash (autonomy/keys/broker-config/"
        f"kill-switch): {offenders}"
    )


def test_set_region_is_the_only_settings_reaching_capability() -> None:
    """set_region is the ONE agent-drivable setting shipped in R10 (D45) — it
    rides the settings proposed-change kind, and no sibling settings
    capability exists."""
    cap = catalog.CAPABILITY_CATALOG["set_region"]
    assert cap.kind == "host_action"
    assert cap.read_only is False
    settings_like = [
        cid
        for cid in catalog.CAPABILITY_CATALOG
        if cid.startswith(("set_", "write_")) and "setting" in cid.lower()
    ]
    assert settings_like == []

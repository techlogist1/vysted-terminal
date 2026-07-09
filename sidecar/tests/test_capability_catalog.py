"""Single-capability-catalog parity gates (Constitution Principle II; FR-020/023, SC-006).

The catalog (:mod:`services.agent_tools.catalog`) is the one source of truth for
every terminal tool. These tests are the standing audit that the three consumers
that derive from it never drift:

  - the internal copilot/persona projection (``TOOL_SCHEMAS``);
  - the registered-handler registry (every read tool has a handler, and vice
    versa) — this is the SC-006 gate: 0 registered, agent-intended handlers
    lacking a catalog/schema entry;
  - the Custom Agent Builder allow-list (``KNOWN_TOOL_IDS``) — 0 unresolvable
    tools.

They also lock the §6.5-adjacent invariant that no catalog id is order-placing,
and the documented ``macro_series`` provider-field regression.
"""

from __future__ import annotations

from models.custom_agent import KNOWN_TOOL_IDS
from services import agent_tools
from services.agent_tools.catalog import (
    CAPABILITY_CATALOG,
    FORBIDDEN_TOOL_SUBSTRINGS,
    agent_selectable_tool_ids,
    internal_tool_ids,
    read_handler_ids,
)
from services.agent_tools.schemas import (
    HOST_ACTION_TOOLS,
    PER_INVOCATION_READ_TOOLS,
    TOOL_SCHEMAS,
)


def _register_all_production_tools() -> None:
    """Reproduce sidecar startup tool registration for an isolated test."""
    agent_tools.reset_for_tests()  # clears + re-registers import-time backtest_summary
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()


# --- SC-006: 0 registered, agent-intended handlers lack a catalog/schema entry ---


def test_every_registered_handler_has_a_catalog_entry() -> None:
    _register_all_production_tools()
    missing = [
        tid
        for tid in agent_tools.registered_tools()
        if tid not in CAPABILITY_CATALOG or not CAPABILITY_CATALOG[tid].internal
    ]
    assert missing == [], f"registered handlers with no internal catalog entry: {missing}"


def test_every_registered_handler_has_a_tool_schema() -> None:
    _register_all_production_tools()
    missing = [tid for tid in agent_tools.registered_tools() if tid not in TOOL_SCHEMAS]
    assert missing == [], f"registered handlers invisible to the model (no schema): {missing}"


def test_every_read_handler_capability_is_registered() -> None:
    """The inverse: a read_handler catalog entry must have a live handler."""
    _register_all_production_tools()
    unbacked = [tid for tid in read_handler_ids() if not agent_tools.is_registered(tid)]
    assert unbacked == [], f"read_handler catalog entries with no registered handler: {unbacked}"


# --- The catalog is THE source: every projection derives from it ---


def test_tool_schemas_keys_equal_internal_catalog() -> None:
    assert set(TOOL_SCHEMAS) == set(internal_tool_ids())


def test_per_invocation_and_host_action_tuples_derive_from_catalog() -> None:
    assert set(PER_INVOCATION_READ_TOOLS) == {
        c.id for c in CAPABILITY_CATALOG.values() if c.kind == "per_invocation"
    }
    assert set(HOST_ACTION_TOOLS) == {
        c.id for c in CAPABILITY_CATALOG.values() if c.kind == "host_action"
    }


# --- FR-023 / SC-006: custom-agent allow-list reflects the real catalog ---


def test_custom_agent_allowlist_is_the_catalog() -> None:
    assert KNOWN_TOOL_IDS == agent_selectable_tool_ids()
    assert KNOWN_TOOL_IDS == frozenset(internal_tool_ids())


def test_every_selectable_tool_resolves() -> None:
    """0 unresolvable tools — every allow-list id is a real catalog capability."""
    _register_all_production_tools()
    for tid in KNOWN_TOOL_IDS:
        cap = CAPABILITY_CATALOG.get(tid)
        assert cap is not None and cap.internal, (
            f"selectable tool {tid!r} not an internal capability"
        )
        if cap.kind == "read_handler":
            assert agent_tools.is_registered(tid), f"selectable read tool {tid!r} has no handler"
        else:
            assert cap.kind in ("per_invocation", "host_action")


def test_stale_bogus_ids_are_gone() -> None:
    """The historical stale allow-list listed ``news``/``macro`` — neither real.

    The real macro tool is ``macro_series``; there is no internal ``macro`` or
    (yet) ``news`` tool. Guard against the stale ids creeping back as silent
    no-resolves.
    """
    assert "macro" not in KNOWN_TOOL_IDS  # the real id is macro_series
    assert "macro_series" in KNOWN_TOOL_IDS


# --- open_panel carries its arguments (R8 seams) ---


def test_open_panel_schema_carries_optional_symbol() -> None:
    """The open_panel host action takes an optional ``symbol`` for symbol-aware
    panels (equity-overview, chart) — projected to TOOL_SCHEMAS from the catalog.
    ``panel`` stays the only required field (the symbol must never become
    mandatory: most panels consume none)."""
    schema = TOOL_SCHEMAS["open_panel"]["input_schema"]
    assert "panel" in schema["properties"]
    assert "symbol" in schema["properties"]
    assert schema.get("required") == ["panel"]
    # The model is TOLD what the symbol does (schemas are the model's docs).
    assert "symbol-aware" in schema["properties"]["symbol"]["description"]


# --- The documented macro_series provider-field regression ---


def test_macro_series_schema_requires_provider() -> None:
    schema = TOOL_SCHEMAS["macro_series"]["input_schema"]
    assert "provider" in schema["properties"]
    assert "provider" in schema.get("required", [])


# --- §6.5-adjacent: no order-placing id in the catalog (defense-in-depth mirror) ---


def test_no_forbidden_order_placing_ids_in_catalog() -> None:
    offenders = [
        cid
        for cid in CAPABILITY_CATALOG
        if any(sub in cid.lower() for sub in FORBIDDEN_TOOL_SUBSTRINGS)
    ]
    assert offenders == [], f"order-placing catalog id (§6.5 violation): {offenders}"


# --- read_only tags drive the gate; they must be coherent (FR-021) ---


def test_read_only_tags_are_coherent() -> None:
    for cap in CAPABILITY_CATALOG.values():
        if cap.kind in ("read_handler", "per_invocation"):
            assert cap.read_only, f"{cap.id}: a read tool must be read_only"
        if cap.kind == "host_action":
            assert not cap.read_only, f"{cap.id}: a host-action mutation must not be read_only"
    # propose_order is the one broker mutation; it is gated, never read-only.
    assert CAPABILITY_CATALOG["propose_order"].read_only is False


# --- D64 (R12): screener tool schemas must document the FULL criterion union ---
# GLM-5.2 read the numeric-only example, concluded "no sector filter exists", and
# post-filtered a limit-capped sweep client-side — silently lossy. The prose IS
# the contract the model sees; pin sector-eq + the India universes into both.


def test_screener_run_schema_documents_string_criteria() -> None:
    desc = TOOL_SCHEMAS["screener_run"]["input_schema"]["properties"]["criteria"]["description"]
    assert '"field":"sector"' in desc and '"operator":"eq"' in desc
    assert "between" in desc and '"operator":"in"' in desc
    assert "post-filtering" in desc  # the anti-lossy-sweep instruction


def test_write_screener_filters_documents_string_criteria_and_india_universes() -> None:
    desc = CAPABILITY_CATALOG["write_screener_filters"].description
    assert '"field":"sector"' in desc
    for universe in ("nse-all", "bse-all", "india-all"):
        assert universe in desc, f"stale universe list: {universe} missing"

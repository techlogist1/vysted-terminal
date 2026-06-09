"""SC-004 parity audit — one capability catalog, two consumers, zero divergence.

The internal copilot surface and the external MCP surface are both PROJECTIONS
of ``services.agent_tools.catalog`` (Constitution Principle II; FR-020/021/022).
These tests are the standing audit that the two surfaces never drift: a
capability added once is reachable by both, by the same name, with matching
read-only semantics — and the only internal/MCP divergence is the deliberate
local-only surface (host actions, per-invocation reads, the run_id-scoped
backtest digest).
"""

from __future__ import annotations

import asyncio

from services import mcp_server
from services.agent_tools.catalog import (
    CAPABILITY_CATALOG,
    internal_tool_ids,
    mcp_capabilities,
    mcp_tool_ids,
)

# Framework/runtime tools that are intentionally MCP-only (not internal-copilot
# capabilities): agent discovery/invocation, workspace + workflow surfaces.
_RUNTIME_ONLY = {
    "list_agents",
    "invoke_agent",
    "list_workspaces",
    "get_workspace",
    "run_workflow",
    "list_workflows",
    # R7 hackability — the agent's workflow-AUTHORING surface (hand-written,
    # MCP-only, like its run/list siblings; CLAUDE.md: workflow tools are not
    # catalog read_handlers).
    "save_workflow",
    "list_runs",
}


def _mcp_tools() -> list[object]:
    mcp_server._reset_for_tests()
    server = mcp_server.get_mcp_server()
    try:
        return asyncio.run(server.list_tools())
    finally:
        mcp_server._reset_for_tests()


def test_every_catalog_mcp_capability_is_exposed_on_mcp() -> None:
    names = {tool.name for tool in _mcp_tools()}
    missing = [cap.id for cap in mcp_capabilities() if cap.id not in names]
    assert missing == [], f"catalog capabilities not exposed on MCP: {missing}"


def test_mcp_data_tools_equal_the_catalog_projection() -> None:
    """No hand-maintained data tool exists outside the catalog (no divergence)."""
    names = {tool.name for tool in _mcp_tools()}
    data_tools = names - _RUNTIME_ONLY
    assert data_tools == set(mcp_tool_ids())


def test_mcp_read_only_hint_matches_the_catalog() -> None:
    """read_only drives the external readOnlyHint (one declaration, FR-021)."""
    for tool in _mcp_tools():
        cap = CAPABILITY_CATALOG.get(tool.name)
        if cap is None:
            continue  # runtime-only tool — not a catalog capability
        annotations = tool.to_mcp_tool().annotations
        assert annotations is not None, f"{tool.name}: missing annotations"
        assert annotations.readOnlyHint == cap.read_only, (
            f"{tool.name}: readOnlyHint {annotations.readOnlyHint} != catalog {cap.read_only}"
        )


def test_mcp_input_schema_matches_the_catalog() -> None:
    """The external schema is the catalog schema verbatim (single source)."""
    for tool in _mcp_tools():
        cap = CAPABILITY_CATALOG.get(tool.name)
        if cap is None:
            continue
        assert tool.to_mcp_tool().inputSchema == cap.input_schema, (
            f"{tool.name}: MCP input schema diverged from the catalog"
        )


def test_mcp_surface_is_a_subset_of_internal_modulo_local_only() -> None:
    """Every MCP capability is also internal; the only divergence is local-only."""
    internal = set(internal_tool_ids())
    assert set(mcp_tool_ids()).issubset(internal)

    internal_only = internal - set(mcp_tool_ids())
    expected_internal_only = {
        cap.id
        for cap in CAPABILITY_CATALOG.values()
        if cap.internal
        and (cap.kind in ("per_invocation", "host_action") or cap.id == "backtest_summary")
    }
    assert internal_only == expected_internal_only, (
        f"unexpected internal/MCP divergence: {internal_only ^ expected_internal_only}"
    )

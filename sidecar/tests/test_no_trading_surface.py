"""Gate 8 (D81): no order, broker or simulated-account path exists anywhere,
and the user's tracked portfolio is intact.

Trading was removed from the product permanently (operator Tier-4 sign-off,
23 Sep 2026). This file replaces the old ``test_safety_end_to_end.py`` grep
audit. It pins the removal at every layer the agent or the user can reach:
mounted routes, the capability catalog and its projections, the MCP surface,
importable modules, the files on disk, and the identifiers in source. The last
test proves the surviving half: holdings saved in the legacy ledger still import
(the ledger is read-only since R15-CODE-PLATFORM-021; holdings live in the
workspace blob).
"""

from __future__ import annotations

import asyncio
import importlib.util
import re
import typing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from models.custom_agent import KNOWN_TOOL_IDS
from services import agent_tools, mcp_server
from services.agent_tools import catalog
from services.agent_tools.schemas import TOOL_SCHEMAS

REPO_ROOT = Path(__file__).resolve().parents[2]

_SKIP_DIRS = {
    ".venv",
    "node_modules",
    "target",
    "build",
    "dist",
    ".next",
    "out",
    ".claude",
    "__pycache__",
}

_TRADING_ROUTE = re.compile(
    r"/(brokers?|orders?|margins|safety|kill-switch|audit-log|disclaimer-[a-z-]+|static-ip[a-z-]*)(/|$)"
)

ID_RE = re.compile(
    r"(^|_)(orders?|brokers?|margins?|trades?|trading|paper|kill_?switch|audit)(_|$)"
)

#: The MCP-only runtime tools (agent/workspace/workflow surfaces) — the same
#: set ``test_mcp_catalog_parity._RUNTIME_ONLY`` names.
_MCP_RUNTIME_ONLY_COUNT = 8

_TRADING_MODULES = (
    "services.brokers",
    "services.broker_base",
    "services.kill_switch",
    "services.audit_log",
    "services.disclaimer_session",
    "services.static_ip_detector",
    "services.agent_tools.broker_portfolio",
    "services.agent_tools.registry_v0_6_5",
    "models.broker",
    "models.broker_reads",
    "models.safety",
    "models.audit_log",
    "routers.brokers",
    "routers.safety",
)

_TRADING_PATHS = (
    "plugins/brokers",
    "src/modules/broker-connect",
    "src/modules/safety/OrderConfirmationDialog.tsx",
    "src/modules/safety/AuditLogViewer.tsx",
    "src/store/orders.ts",
    "src/store/brokers.ts",
    "types/broker.ts",
    "types/broker-reads.ts",
    "types/safety.ts",
    "src-tauri/src/kill_switch.rs",
    "docs/screenshots/v0.5.0/safety-audit",
)

#: (root, glob) pairs scanned for trading identifiers. Tests are excluded below.
_SCAN_GLOBS = (
    ("sidecar", "**/*.py"),
    ("sidecar/agents", "*.json"),
    ("sidecar", "requirements.txt"),
    ("src", "**/*.ts"),
    ("src", "**/*.tsx"),
    ("types", "*.ts"),
    ("plugins", "**/*.ts"),
    ("plugins", "**/*.json"),
    ("src-tauri/src", "**/*.rs"),
    ("src-tauri", "Cargo.toml"),
    ("src-tauri/capabilities", "*.json"),
)

#: Exactly one exemption. types/plugin.ts is the Tier-1 locked plugin contract;
#: it holds a kill-switch JSDoc command example and the ``"trading-bot"``
#: PluginType. Changing it is BLOCKED-FOR-OPERATOR.
_SCAN_EXEMPT = {"types/plugin.ts"}

_TRADING_TOKENS = (
    "propose_order",
    "confirm_and_place",
    "_place_confirmed",
    "routeOrderProposal",
    "BrokerAdapter",
    "BrokerOrder",
    "BrokerState",
    "BrokerId",
    "BrokerConnect",
    "BrokerFirstConnect",
    "broker_portfolio",
    "brokers_registry",
    "useBrokersStore",
    "useOrdersStore",
    "OrderConfirmation",
    "AccountSummary",
    "margins_info",
    "holdings_info",
    "positions_info",
    "KillSwitch",
    "kill_switch",
    "killSwitch",
    "kill-switch",
    "global_shortcut",
    "global-shortcut",
    "audit_orders",
    "AuditLog",
    "audit_log",
    "PositionLimits",
    "maxPercentOfAccount",
    "dailyLossCircuitBreaker",
    "first-live-order",
    "/brokers/",
    "/safety/",
    "static_ip",
    "StaticIp",
    "kiteconnect",
    "dhanhq",
    "smartapi",
    "alpaca-py",
    "ib_async",
    "oandapyV20",
)

_PORTFOLIO_TOOLS = {
    "get_portfolio": "per_invocation",
    "portfolio_add_position": "host_action",
    "portfolio_update_position": "host_action",
    "portfolio_delete_position": "host_action",
}


def _is_test_file(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return rel.startswith("sidecar/tests/") or ".test." in path.name


def _scanned_files() -> list[Path]:
    files: set[Path] = set()
    for root, pattern in _SCAN_GLOBS:
        base = REPO_ROOT / root
        for path in base.glob(pattern):
            rel_parts = path.relative_to(REPO_ROOT).parts
            if any(part in _SKIP_DIRS for part in rel_parts):
                continue
            if path.is_file() and not _is_test_file(path):
                files.add(path)
    return sorted(files)


def test_no_trading_routes_mounted() -> None:
    app = create_app()
    methods: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if path is None:
            continue
        methods.setdefault(path, set()).update(getattr(route, "methods", None) or set())
    trading = sorted(p for p in methods if _TRADING_ROUTE.search(p))
    assert trading == [], f"trading routes still mounted: {trading}"
    # R15-CODE-PLATFORM-021: the legacy ledger is read once for import, never written.
    assert methods["/portfolio/positions"] == {"GET"}
    assert "/portfolio/positions/{position_id}" not in methods


def test_no_trading_capability_in_catalog_or_registry() -> None:
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()
    surfaces = {
        "CAPABILITY_CATALOG": set(catalog.CAPABILITY_CATALOG),
        "TOOL_SCHEMAS": set(TOOL_SCHEMAS),
        "KNOWN_TOOL_IDS": set(KNOWN_TOOL_IDS),
        "registered_tools": set(agent_tools.registered_tools()),
    }
    for name, ids in surfaces.items():
        offenders = sorted(
            tid
            for tid in ids
            if ID_RE.search(tid) or any(sub in tid for sub in catalog.FORBIDDEN_TOOL_SUBSTRINGS)
        )
        assert offenders == [], f"trading ids on {name}: {offenders}"
    assert "brokers" not in typing.get_args(catalog.Domain)
    assert "brokers" not in catalog.TIMEOUT_HINTS

    grant = set(catalog.default_grant_tool_ids())
    for tool_id, kind in _PORTFOLIO_TOOLS.items():
        assert tool_id in catalog.CAPABILITY_CATALOG, f"tracked-portfolio tool {tool_id} missing"
        assert catalog.CAPABILITY_CATALOG[tool_id].kind == kind
        assert tool_id in grant, f"{tool_id} is not default-granted"


def test_no_trading_tool_on_mcp_surface() -> None:
    mcp_server._reset_for_tests()
    try:
        tools = asyncio.run(mcp_server.get_mcp_server().list_tools())
    finally:
        mcp_server._reset_for_tests()
    names = sorted(tool.name for tool in tools)
    offenders = [n for n in names if ID_RE.search(n)]
    assert offenders == [], f"trading tools on MCP: {offenders}"
    assert len(names) == len(catalog.mcp_tool_ids()) + _MCP_RUNTIME_ONLY_COUNT


def test_trading_modules_are_gone() -> None:
    importable = [m for m in _TRADING_MODULES if importlib.util.find_spec(m) is not None]
    assert importable == [], f"trading modules still importable: {importable}"


def test_trading_files_absent() -> None:
    present = [p for p in _TRADING_PATHS if (REPO_ROOT / p).exists()]
    assert present == [], f"trading files still present: {present}"


def test_no_trading_identifiers_in_source() -> None:
    hits: list[str] = []
    for path in _scanned_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in _SCAN_EXEMPT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in _TRADING_TOKENS:
            if token in text:
                hits.append(f"{rel}: {token}")
    assert hits == [], "trading identifiers in source:\n" + "\n".join(hits)


def test_proposed_change_kind_has_no_order() -> None:
    text = (REPO_ROOT / "types" / "proposed-change.ts").read_text(encoding="utf-8")
    match = re.search(r"type ProposedChangeKind\s*=([^;]*);", text)
    assert match, "ProposedChangeKind union not found in types/proposed-change.ts"
    body = match.group(1)
    if "PROPOSED_CHANGE_KINDS" in body:
        # The union is derived from the `as const` kinds list; read the list.
        listed = re.search(r"PROPOSED_CHANGE_KINDS\s*=\s*\[([^\]]*)\]", text)
        assert listed, "PROPOSED_CHANGE_KINDS list not found in types/proposed-change.ts"
        body = listed.group(1)
    kinds = set(re.findall(r'"([a-z-]+)"', body))
    assert "order" not in kinds
    assert {"panel", "chart", "watchlist", "data-write", "settings"} <= kinds


def test_tracked_portfolio_legacy_ledger_still_imports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Converted from the CRUD round-trip (R15-CODE-PLATFORM-021): a v0.8 row
    still reads back for the one-time import, and nothing can write the ledger."""
    from services import portfolio_db

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    client = TestClient(create_app())
    with portfolio_db._connect() as conn:
        conn.execute(
            "INSERT INTO positions (symbol, quantity, cost_basis) VALUES ('AAPL', 10, 150)"
        )

    listed = client.get("/portfolio/positions").json()
    assert [(p["symbol"], p["quantity"], p["cost_basis"]) for p in listed] == [("AAPL", 10, 150)]

    body = {"symbol": "AAPL", "quantity": 12, "cost_basis": 150}
    assert client.post("/portfolio/positions", json=body).status_code == 405
    position_id = listed[0]["id"]
    assert client.put(f"/portfolio/positions/{position_id}", json=body).status_code == 404
    assert client.delete(f"/portfolio/positions/{position_id}").status_code == 404
    assert client.get("/portfolio/positions").json() == listed

"""Every node-type handler the workflow engine runs.

The engine (:mod:`services.workflow_engine`) is registry-driven — concrete
node types register against a module-level table via
:func:`workflow_engine.register_node_type`. This package ships the core
built-ins (:mod:`builtin`), the ``transform.code`` expression node
(:mod:`code_node`) and the domain nodes (``<domain>_nodes.py``: macro, SEC,
quant, earnings/analyst research, screener). The core built-ins:

  - ``data.fetch_quote``         — latest quote via provider registry
  - ``data.fetch_history``       — OHLCV history
  - ``compute.indicator``        — run one indicator from the 50-key registry
  - ``ai.agent_invoke``          — invoke a first-party agent, aggregate stream
  - ``logic.branch``             — route a value down one of two paths
  - ``logic.compare``            — numeric comparator emits a boolean
  - ``action.log``               — write a workflow log entry
  - ``action.notify_desktop``    — emit a desktop-notification intent
  - ``action.webhook``           — POST the value to a keychain-held URL
  - ``transform.json_path``      — extract a value by dotted path
  - ``flow.sleep``               — bounded ``asyncio.sleep``

Plugin-contributed node specs have no handler here (no TS→Python node
bridge exists), so the engine cannot run them; see ``workflow_engine``.

:func:`register_all` is the single entry point — ``app.create_app`` calls
it, so the production boot and every TestClient build register the same
set; a test that resets the registry calls it again. It is idempotent;
re-registration overwrites without raising.
"""

from __future__ import annotations

import logging
from typing import Any

from services import workflow_engine

from . import (
    builtin,
    code_node,
    macro_nodes,
    quant_nodes,
    research_nodes,
    screener_nodes,
    sec_nodes,
)

logger = logging.getLogger(__name__)

#: The canonical port and config contract of each built-in, read off its
#: handler in :mod:`builtin`: the input ports it reads, the output keys it
#: returns and the config keys it reads (a key maps to its allowed values, or
#: ``None`` when free-form). The node-editor palette (``node-registry.ts``)
#: must only use these names; ``tests/fixtures/workflow_node_types.json``
#: pins both sides (pytest + vitest), so either drifting fails a test.
#: Template nodes (agent_invoke, log, notify) render any input key; the port
#: listed is the one their default template reads.
BUILTIN_NODE_SPECS: dict[str, dict[str, Any]] = {
    "data.fetch_quote": {
        "inputs": ["symbol"],
        "outputs": ["quote"],
        "config": {"symbol": None, "asset_class": None},
    },
    "data.fetch_history": {
        "inputs": ["symbol", "interval", "period"],
        "outputs": ["series"],
        "config": {"symbol": None, "period": None, "interval": None, "asset_class": None},
    },
    "compute.indicator": {
        "inputs": ["series"],
        "outputs": ["result"],
        "config": {"indicator_id": None},
    },
    "ai.agent_invoke": {
        "inputs": ["context", "context_snapshot"],
        "outputs": ["content", "agent_id"],
        "config": {"agent_id": None, "prompt_template": None, "provider": None, "model": None},
    },
    "logic.branch": {
        "inputs": ["value", "threshold"],
        "outputs": ["true_path", "false_path"],
        "config": {"mode": ["truthy", "gt"], "threshold": None, "condition_field": None},
    },
    "logic.compare": {
        "inputs": ["a", "b"],
        "outputs": ["result"],
        "config": {"op": sorted(builtin._COMPARE_OPS)},
    },
    "action.log": {
        "inputs": ["value"],
        "outputs": ["logged", "level", "message"],
        "config": {"level": list(builtin._LOG_LEVELS), "message_template": None},
    },
    "action.notify_desktop": {
        "inputs": ["value"],
        "outputs": ["notified", "title", "message", "intent"],
        "config": {"title": None, "message_template": None},
    },
    "action.webhook": {
        "inputs": ["value"],
        "outputs": ["status_code"],
        "config": {"secret_ref": None},
    },
    "transform.json_path": {
        "inputs": ["value"],
        "outputs": ["extracted"],
        "config": {"path": None},
    },
    "flow.sleep": {
        "inputs": ["value"],
        "outputs": ["value", "slept"],
        "config": {"seconds": None},
    },
}


def register_all() -> None:
    """Register every node type this package ships against the workflow engine.

    Safe to call repeatedly — :func:`workflow_engine.register_node_type`
    overwrites existing entries.
    """
    workflow_engine.register_node_type("data.fetch_quote", builtin.fetch_quote)
    workflow_engine.register_node_type("data.fetch_history", builtin.fetch_history)
    workflow_engine.register_node_type("compute.indicator", builtin.compute_indicator)
    workflow_engine.register_node_type("ai.agent_invoke", builtin.agent_invoke)
    workflow_engine.register_node_type("logic.branch", builtin.logic_branch)
    workflow_engine.register_node_type("logic.compare", builtin.logic_compare)
    workflow_engine.register_node_type("action.log", builtin.action_log)
    workflow_engine.register_node_type("action.notify_desktop", builtin.action_notify_desktop)
    workflow_engine.register_node_type("action.webhook", builtin.action_webhook)
    workflow_engine.register_node_type("transform.json_path", builtin.transform_json_path)
    workflow_engine.register_node_type("flow.sleep", builtin.flow_sleep)
    # R7 hackability — the agent-authorable restricted-expression code node
    # (server parity for the node editor's client-side mathjs lane).
    code_node.register()
    for domain in (macro_nodes, sec_nodes, quant_nodes, research_nodes, screener_nodes):
        domain.register()
    logger.info(
        "workflow_nodes: %d node types registered", len(workflow_engine.registered_node_types())
    )


__all__ = ["BUILTIN_NODE_SPECS", "builtin", "register_all"]

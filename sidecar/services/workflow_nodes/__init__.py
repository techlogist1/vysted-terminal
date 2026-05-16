"""Built-in node-type handlers for the v0.5.0 workflow engine.

The foundation engine (:mod:`services.workflow_engine`) is registry-driven —
concrete node types register against a module-level table via
:func:`workflow_engine.register_node_type`. This package ships the ten
built-in node types Phase-4 promises:

  - ``data.fetch_quote``         — latest quote via provider registry
  - ``data.fetch_history``       — OHLCV history
  - ``compute.indicator``        — run one indicator from the 50-key registry
  - ``ai.agent_invoke``          — invoke a first-party agent, aggregate stream
  - ``logic.branch``             — route a value down one of two paths
  - ``logic.compare``            — numeric comparator emits a boolean
  - ``action.log``               — write a workflow log entry
  - ``action.notify_desktop``    — emit a desktop-notification intent
  - ``transform.json_path``      — extract a value by dotted path
  - ``flow.sleep``               — bounded ``asyncio.sleep``

Plugin-contributed node types use the same registration surface via the
locked ``VystedPlugin.getNodes()`` capability.

:func:`register_all` is the single entry point — call it once on sidecar
startup (``main.py``) and once at the top of every test suite that exercises
a built-in handler. The function is idempotent; re-registration overwrites
without raising.
"""

from __future__ import annotations

import logging

from services import workflow_engine

from . import builtin

logger = logging.getLogger(__name__)


def register_all() -> None:
    """Register every built-in node type against the workflow engine.

    Safe to call repeatedly — :func:`workflow_engine.register_node_type`
    overwrites existing entries. Sidecar startup calls this once; tests
    that depend on the built-ins call it from a fixture so registration
    survives the :func:`workflow_engine.reset_registry_for_tests` reset.
    """
    workflow_engine.register_node_type("data.fetch_quote", builtin.fetch_quote)
    workflow_engine.register_node_type("data.fetch_history", builtin.fetch_history)
    workflow_engine.register_node_type("compute.indicator", builtin.compute_indicator)
    workflow_engine.register_node_type("ai.agent_invoke", builtin.agent_invoke)
    workflow_engine.register_node_type("logic.branch", builtin.logic_branch)
    workflow_engine.register_node_type("logic.compare", builtin.logic_compare)
    workflow_engine.register_node_type("action.log", builtin.action_log)
    workflow_engine.register_node_type("action.notify_desktop", builtin.action_notify_desktop)
    workflow_engine.register_node_type("transform.json_path", builtin.transform_json_path)
    workflow_engine.register_node_type("flow.sleep", builtin.flow_sleep)
    logger.info("workflow_nodes: registered %d built-in node types", 10)


__all__ = ["builtin", "register_all"]

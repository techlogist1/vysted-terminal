"""Pinning tests for the lows-P2-W3 (tools-envelope) register entries.

Each test names the register id it pins in its docstring so a future reader
can trace the fix back to ``vysted-r15-register.json``.
"""

from __future__ import annotations

import importlib
import sys

import pytest


def test_no_agent_tools_registry_v0_6_0_module() -> None:
    """R15-CODE-AGENT-028: the pure pass-through module is gone; its body
    lives inline in ``register_v0_6_0_tools`` and the function still runs
    every Phase 6 domain's ``register()``."""
    assert "services.agent_tools.registry_v0_6_0" not in sys.modules
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("services.agent_tools.registry_v0_6_0")

    from services import agent_tools

    agent_tools.reset_for_tests()
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()
    for tool_id in ("macro_series", "sec_filings_list", "compare_symbols", "research"):
        assert agent_tools.is_registered(tool_id)

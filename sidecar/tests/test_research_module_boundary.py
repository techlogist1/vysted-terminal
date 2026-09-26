"""R15-CODE-RESEARCH-005: no research module imports another's private names.

``iter``, ``verify`` and ``citecheck`` built on ``deep``'s underscore-private
helpers, so ``deep``'s private surface was a de-facto public API. The shared
round helpers are now public ``deep`` exports; this audit keeps it that way.
"""

from __future__ import annotations

import ast
from pathlib import Path

from services.research import deep

_RESEARCH_DIR = Path(__file__).resolve().parents[1] / "services" / "research"


def test_no_research_module_imports_a_private_name_across_modules() -> None:
    leaks = []
    for path in sorted(_RESEARCH_DIR.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "services.research"
            ):
                leaks += [
                    f"{path.name}: {node.module}.{alias.name}"
                    for alias in node.names
                    if alias.name.startswith("_")
                ]
    assert leaks == []


def test_shared_round_helpers_are_public_deep_exports() -> None:
    shared = {
        "ROUND_MODEL",
        "ROUND_PROVIDER",
        "WEB_ONLY_FLOOR_NOTE",
        "Findings",
        "emit_step",
        "record_structured",
        "record_web",
        "reflect_says_complete",
        "round_wall_limit",
        "run_researcher",
        "safe_llm",
        "safe_tool",
        "split_subquestions",
        "synthesis_llm",
        "synthesize_brief",
    }
    assert shared <= set(deep.__all__)
    assert all(hasattr(deep, name) for name in deep.__all__)

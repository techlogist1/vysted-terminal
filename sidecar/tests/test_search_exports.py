"""Every name in ``services.search.__all__`` must have a real caller (R15-CODE-RESEARCH-004).

R15-CODE-RESEARCH-004 deleted a batch of dead search scaffolding
(``locale_domains``, ``KNOWN_BACKENDS``, ``detect_searxng``, ``breaker_status``,
``untrusted_context_message``, ``SearchResponse.metadata``) that was exported
but never called outside its own defining module and its tests. This test
pins the invariant going forward: a name only earns a spot in
``services.search.__all__`` if some non-test file in ``sidecar/`` actually
uses it.
"""

from __future__ import annotations

import re
from pathlib import Path

import services.search as search_pkg

SIDECAR_ROOT = Path(__file__).resolve().parent.parent


def _non_test_python_files() -> list[Path]:
    return [
        p
        for p in SIDECAR_ROOT.rglob("*.py")
        if "tests" not in p.relative_to(SIDECAR_ROOT).parts and "__pycache__" not in p.parts
    ]


def test_every_export_has_a_non_test_caller() -> None:
    files = _non_test_python_files()
    contents = {p: p.read_text(encoding="utf-8") for p in files}
    init_file = Path(search_pkg.__file__).resolve()

    orphans: list[str] = []
    for name in search_pkg.__all__:
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        # ``__init__.py`` is just re-export wiring, never a caller. A symbol
        # that appears in only ONE remaining file is referenced solely by its
        # own defining module — that's the dead shape R15-CODE-RESEARCH-004
        # cleaned up (a name used nowhere but its definition + re-export +
        # tests). A real caller is a SECOND file.
        hit_files = {p for p, text in contents.items() if p != init_file and pattern.search(text)}
        if len(hit_files) < 2:
            orphans.append(name)

    assert orphans == [], f"dead exports in services.search.__all__: {orphans}"

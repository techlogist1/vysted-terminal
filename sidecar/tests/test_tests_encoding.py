"""R15-CROSS-PLATFORM-002: every text-mode file read/write in the test suite
must name its encoding explicitly.

``open()``/``Path.read_text()``/``Path.write_text()`` with no ``encoding``
kwarg fall back to ``locale.getpreferredencoding()`` — UTF-8 on macOS/Linux CI,
but ``cp1252`` on a plain Windows shell, so a fixture with a smart quote or a
non-ASCII company name silently mis-decodes (or fails outright) ONLY on
Windows. This is an AST scan, not a grep: it is the class pin (CLAUDE.md
"Fix it once, where all callers route through") — it fails on ANY future test
file that reintroduces the pattern, including ones written by other batches
after this fix landed, not just the files this batch happened to touch.
"""

from __future__ import annotations

import ast
from pathlib import Path

_TESTS_DIR = Path(__file__).parent

#: Method/function names whose text-mode call must carry ``encoding=``.
_WATCHED_NAMES = frozenset({"open", "read_text", "write_text"})


def _mode_literal(call: ast.Call) -> str | None:
    """The ``mode``/``2nd positional`` argument of an ``open()`` call, if literal."""
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        return call.args[1].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _violations(path: Path) -> list[tuple[int, str]]:
    """Every text-mode ``open``/``read_text``/``write_text`` call in ``path``
    missing an explicit ``encoding=`` keyword, as ``(line, call)``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in _WATCHED_NAMES:
            continue
        if any(kw.arg == "encoding" for kw in node.keywords):
            continue
        if name == "open":
            mode = _mode_literal(node)
            # A binary mode carries no text encoding to name at all.
            if isinstance(mode, str) and "b" in mode:
                continue
        found.append((node.lineno, name))
    return found


def test_every_test_file_names_its_text_encoding() -> None:
    violations: list[str] = []
    for path in sorted(_TESTS_DIR.glob("*.py")):
        for lineno, name in _violations(path):
            violations.append(f"{path.name}:{lineno} {name}()")
    assert violations == [], (
        "text-mode open()/read_text()/write_text() without encoding= "
        f"(decodes with the platform default — wrong on Windows): {violations}"
    )


def test_scanner_itself_catches_a_missing_encoding(tmp_path) -> None:
    """Class pin: a case the fix was not written against — a fresh throwaway
    file the scanner has never seen, not one of the files this batch edited."""
    offender = tmp_path / "offender.py"
    offender.write_text('from pathlib import Path\n\nPath("x").read_text()\n', encoding="utf-8")
    assert _violations(offender) == [(3, "read_text")]


def test_scanner_ignores_a_binary_open_and_an_encoded_call(tmp_path) -> None:
    """No false positives: a binary-mode ``open`` and a call that already
    names its encoding are both clean."""
    clean = tmp_path / "clean.py"
    clean.write_text(
        'open("x", "rb")\nopen("y", encoding="utf-8")\n'
        'from pathlib import Path\nPath("z").read_text(encoding="utf-8")\n',
        encoding="utf-8",
    )
    assert _violations(clean) == []

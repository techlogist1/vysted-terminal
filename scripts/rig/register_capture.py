#!/usr/bin/env python3
"""The run's capture registry: one provenance row per image, in CAPTURES.jsonl.

The pre-push hook (scripts/git-hooks/pre-push) refuses any image added under
docs/redesign/verification/r15/ whose sha256 is not in that ledger — so every
screenshot that ships says which tool took it and, for a GUI capture, what was
actually on screen. `rig.py capture` imports this; any other tool registers its own:

    python3 scripts/rig/register_capture.py shot.png --tool browse.py

Idempotent: re-registering the same bytes is a no-op. Deliberately stdlib-only
(no PyObjC) so a scratch-venv python can call it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAPTURES = REPO / "docs/redesign/verification/r15/CAPTURES.jsonl"


def register_capture(
    path: Path, tool: str, frontmost: str = "", owner: str = ""
) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if CAPTURES.exists():
        for line in CAPTURES.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("sha256") == digest:
                return row
    row = {
        "sha256": digest,
        "path": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        "tool": tool,
        "frontmost_app": frontmost,
        "window_owner": owner,
        "taken_at": datetime.now(timezone.utc).isoformat(),
    }
    CAPTURES.parent.mkdir(parents=True, exist_ok=True)
    with CAPTURES.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="register_capture.py", description=__doc__)
    p.add_argument("png")
    p.add_argument("--tool", required=True, help="what produced it, e.g. browse.py")
    p.add_argument("--frontmost-app", default="", help="frontmost app at capture time")
    p.add_argument("--window-owner", default="", help="captured window owner, if known")
    a = p.parse_args(argv)
    path = Path(a.png).resolve()
    if not path.is_file():
        p.error(f"no such capture: {path}")
    print(json.dumps(register_capture(path, a.tool, a.frontmost_app, a.window_owner)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

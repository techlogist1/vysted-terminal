#!/usr/bin/env python3
"""Register a capture in docs/redesign/verification/r15/CAPTURES.jsonl.

The pre-push hook (scripts/git-hooks/pre-push) refuses any image added under
docs/redesign/verification/r15/ whose sha256 is not in that ledger — so every
screenshot that ships carries a provenance line saying which tool took it and,
for a GUI capture, what was actually on screen.

    python3 scripts/rig/register_capture.py <image> --tool rigcap \\
        --frontmost-app vysted-terminal --window-owner vysted-terminal

Idempotent: re-registering the same bytes is a no-op.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/redesign/verification/r15/CAPTURES.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("path", help="image file to register")
    ap.add_argument(
        "--tool", required=True, help="what took it (rigcap, playwright, ...)"
    )
    ap.add_argument("--frontmost-app", default="", help="frontmost app at capture time")
    ap.add_argument("--window-owner", default="", help="owner of the captured window")
    args = ap.parse_args()

    img = pathlib.Path(args.path).resolve()
    if not img.is_file():
        print("register_capture: not a file: %s" % args.path, file=sys.stderr)
        return 2
    try:
        rel = img.relative_to(ROOT).as_posix()
    except ValueError:
        print("register_capture: %s is outside the repo" % args.path, file=sys.stderr)
        return 2

    digest = hashlib.sha256(img.read_bytes()).hexdigest()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                if json.loads(line).get("sha256") == digest:
                    print("already registered: %s" % rel)
                    return 0
            except ValueError:
                continue

    entry = {
        "sha256": digest,
        "path": rel,
        "tool": args.tool,
        "frontmost_app": args.frontmost_app,
        "window_owner": args.window_owner,
        "taken_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    print("registered: %s sha256=%s" % (rel, digest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

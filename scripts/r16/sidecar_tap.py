#!/usr/bin/env python3
"""Run the sidecar from source with a tap on every dispatched tool result.

  VYSTED_TAP_FILE=out.jsonl python scripts/r16/sidecar_tap.py --port P --data-dir D

Same argv as ``sidecar/main.py``. The SSE stream carries each tool's outcome but
never its payload, so the invented-figure check (``scripts/agent_eval/grounding.py``)
has nothing to compare an answer against; this wrapper appends one JSON line per
dispatched tool - ``{name, tool_call_id, ok, result}`` - to ``$VYSTED_TAP_FILE``.
No app code is edited: ``agent_runtime._tool_result_event`` is wrapped in-process.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SIDECAR = Path(__file__).resolve().parents[2] / "sidecar"


def main() -> None:
    os.chdir(SIDECAR)
    sys.path.insert(0, str(SIDECAR))
    tap = os.environ["VYSTED_TAP_FILE"]
    from services import agent_runtime

    original = agent_runtime._tool_result_event

    def tapped(tool_call, result_str):
        outcome = original(tool_call, result_str)
        row = {
            "name": tool_call.name,
            "tool_call_id": tool_call.tool_call_id,
            "ok": outcome.ok,
            "result": result_str,
        }
        with open(tap, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return outcome

    agent_runtime._tool_result_event = tapped
    import main as sidecar_main

    sidecar_main.main()


if __name__ == "__main__":  # the guard keeps multiprocessing spawn workers from re-running this
    main()

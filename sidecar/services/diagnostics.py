"""Diagnostics bundle: the status JSON plus a redacted tail of the persisted log.

The Tauri core appends every Rust, sidecar and MCP-subprocess line to
``<data-dir>/logs/vysted.log`` (``src-tauri/src/diag_log.rs``). Settings shows
this bundle in a preview and the user copies it by hand; nothing leaves the
machine otherwise. Before it is returned, every line and status string is
redacted: query strings, key-like tokens, public IP addresses, the home
directory, URL path identifiers (symbols, ids) and long quoted text (prompts,
briefs, notes) are replaced.
"""

from __future__ import annotations

import ipaddress
import re
from collections import deque
from pathlib import Path
from typing import Any

from config import get_data_dir

LOG_RELATIVE_PATH = Path("logs") / "vysted.log"
TAIL_LINES = 300

_QUERY = re.compile(r"\?[^\s\"'<>]+")
# Provider-style secrets (sk-..., AIza..., gsk_..., xai-...) and any long
# unbroken token run (bearer tokens, hex / base64 keys).
_KEYLIKE = re.compile(r"\b(?:sk|pk|rk|gsk|xai|key|AIza)[-_A-Za-z0-9]{12,}|\b[A-Za-z0-9+=_\-]{32,}")
_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
# A URL path: keep the first segment (the route family), drop the rest. A
# home-relative file path (``~/...``, e.g. a traceback frame) is kept.
_PATH = re.compile(r"(?<![A-Za-z.~])(/[A-Za-z_][\w\-]*)((?:/[^\s\"'?<>]+)+)")
_QUOTED = re.compile(r"(['\"])([^'\"\n]{40,})\1")


def _public_ip(match: re.Match[str]) -> str:
    try:
        is_global = ipaddress.ip_address(match.group(0)).is_global
    except ValueError:
        return match.group(0)
    return "<ip>" if is_global else match.group(0)


def redact_line(line: str) -> str:
    """Strip identifying or secret text from one log line."""
    home = str(Path.home())
    if home and home != "/":
        line = line.replace(home, "~")
    line = _QUERY.sub("?<query>", line)
    line = _PATH.sub(r"\1/<id>", line)
    line = _QUOTED.sub(r"\1<text>\1", line)
    line = _KEYLIKE.sub("<redacted>", line)
    return _IPV4.sub(_public_ip, line)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_line(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def log_tail(lines: int = TAIL_LINES) -> list[str]:
    """The last ``lines`` lines of the persisted log, redacted ([] if none yet)."""
    path = get_data_dir() / LOG_RELATIVE_PATH
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            tail = deque(handle, maxlen=lines)
    except FileNotFoundError:
        return []
    return [redact_line(line.rstrip("\r\n")) for line in tail]


def build_bundle(version: str, status: dict[str, Any]) -> dict[str, Any]:
    """The diagnostics bundle: version, redacted status JSON and log tail."""
    return {
        "version": version,
        "logFile": str(LOG_RELATIVE_PATH),
        "status": _redact_value(status),
        "logTail": log_tail(),
    }

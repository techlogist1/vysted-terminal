"""``GET /system/diagnostics`` returns the status JSON and a redacted log tail
(R15-LIFECYCLE-008): no query string, key or public IP survives."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from services import diagnostics

_KEY = "sk-or-v1-canaryKEY0123456789abcdef"
_LOG_LINES = [
    '1727200000.123 [sidecar] 2026-09-24 01:02:03 INFO uvicorn.access: 127.0.0.1:5051 - "GET '
    '/quotes/CANARYSYM?range=1y&apikey=canaryquery HTTP/1.1" 200',
    f"1727200000.456 [sidecar] WARNING llm: provider rejected key {_KEY}",
    "1727200000.789 [openbb-mcp] upstream 93.184.216.34 timed out; loopback 127.0.0.1 ok",
    '1727200001.000 [sidecar] INFO agent: prompt "compare CANARYSYM margins against its three '
    'closest peers please"',
]


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def test_redactor_strips_query_key_ip_symbol_and_prompt_text() -> None:
    out = "\n".join(diagnostics.redact_line(line) for line in _LOG_LINES)

    for canary in ("canaryquery", "CANARYSYM", _KEY, "canaryKEY", "93.184.216.34", "peers"):
        assert canary not in out
    # What a maintainer needs stays: route family, loopback, level, tags.
    assert "GET /quotes/<id>?<query> HTTP/1.1" in out
    assert "127.0.0.1" in out
    assert "[openbb-mcp]" in out


def test_diagnostics_route_returns_status_and_a_redacted_log_tail(data_dir: Path) -> None:
    from app import create_app

    log = data_dir / diagnostics.LOG_RELATIVE_PATH
    log.parent.mkdir(parents=True)
    log.write_text("\n".join(_LOG_LINES) + "\n", encoding="utf-8")

    body = TestClient(create_app()).get("/system/diagnostics").json()

    assert body["version"] == body["status"]["health"]["version"]
    assert {"health", "providerHealth", "mcp", "openbbMcp"} <= body["status"].keys()
    assert len(body["logTail"]) == len(_LOG_LINES)
    assert "canaryquery" not in str(body) and _KEY not in str(body)


def test_diagnostics_without_a_log_file_has_an_empty_tail(data_dir: Path) -> None:
    from app import create_app

    body = TestClient(create_app()).get("/system/diagnostics").json()
    assert body["logTail"] == []

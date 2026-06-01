"""runs router tests — the exact wire shapes + api_key-never-echoed.

The executor (``run_manager``) is unit-tested in ``test_run_manager``; here we
exercise the TRANSPORT: the routes the frontend consumes, the camelCase wire
shape, the status codes, and the security invariant that the BYOK ``api_key``
crosses for the run only and is never echoed in any response. ``run_manager`` is
mocked at the boundary so a route test does not depend on a detached task
running on the TestClient's short-lived event loop.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.run import RunBudget
from services import run_manager, runs_store
from services.run_manager import RunManagerError


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))


def _seed_run(run_id: str = "run-1", **budget_kw: object) -> None:
    runs_store.create_run(
        run_id=run_id,
        agent_id="copilot",
        agent_name="Copilot",
        budget=RunBudget(**budget_kw),  # type: ignore[arg-type]
        now=1000,
    )


# ---------------------------------------------------------------------------
# POST /agents/{agent_id}/runs
# ---------------------------------------------------------------------------


def test_launch_returns_201_with_run_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _fake_launch(**kwargs: object) -> str:
        captured.update(kwargs)
        return "run-xyz"

    monkeypatch.setattr(run_manager, "launch_run", _fake_launch)
    resp = client.post(
        "/agents/copilot/runs",
        json={
            "prompt": "research NVDA",
            "provider": "anthropic",
            "model": "claude-opus-4-8",
            "apiKey": "sk-secret-123",
            "budget": {"maxTokens": 50000, "maxSpendUsd": 2.5},
            "options": {"temperature": 0.2},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    # Emitted in BOTH spellings so either frontend read resolves.
    assert body["runId"] == "run-xyz"
    assert body["run_id"] == "run-xyz"
    # The launch was driven with the parsed budget + key.
    assert captured["agent_id"] == "copilot"
    assert captured["prompt"] == "research NVDA"
    budget = captured["budget"]
    assert isinstance(budget, RunBudget)
    assert budget.max_tokens == 50000
    assert budget.max_spend_usd == 2.5


def test_launch_response_never_echoes_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "sk-must-not-leak-abc"
    monkeypatch.setattr(run_manager, "launch_run", lambda **_k: "run-1")
    resp = client.post(
        "/agents/copilot/runs",
        json={"prompt": "x", "apiKey": secret},
    )
    assert resp.status_code == 201
    assert secret not in resp.text


def test_launch_unknown_agent_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(**_k: object) -> str:
        raise RunManagerError("unknown agent: 'ghost'")

    monkeypatch.setattr(run_manager, "launch_run", _raise)
    resp = client.post("/agents/ghost/runs", json={"prompt": "x"})
    assert resp.status_code == 404


def test_launch_accepts_snake_case_run_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """populate_by_name lets the body use snake_case too (defensive)."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(run_manager, "launch_run", lambda **k: captured.update(k) or "run-1")
    resp = client.post(
        "/agents/copilot/runs",
        json={"prompt": "x", "budget": {"max_tokens": 100}},
    )
    assert resp.status_code == 201
    assert captured["budget"].max_tokens == 100  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# GET /runs  +  GET /runs/{id}
# ---------------------------------------------------------------------------


def test_list_runs_dual_case_shape(client: TestClient) -> None:
    """GET /runs emits BOTH camelCase and snake_case so either poller read works."""
    _seed_run("run-1", max_tokens=5000, max_spend_usd=1.5)
    runs_store.update_run(
        "run-1",
        cost={"tokens": 1234, "spend_usd": 0.05, "steps": 3},
        status="running",
    )
    resp = client.get("/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body
    row = body["runs"][0]
    assert row["id"] == "run-1"
    assert row["status"] == "running"
    # camelCase (the documented contract).
    assert row["agentId"] == "copilot"
    assert row["agentName"] == "Copilot"
    assert row["cost"]["spendUsd"] == 0.05
    assert row["budget"]["maxTokens"] == 5000
    assert "createdAt" in row and "updatedAt" in row
    # snake_case (what the lead's run-tray poller currently reads).
    assert row["agent_id"] == "copilot"
    assert row["agent_name"] == "Copilot"
    assert row["cost"]["spend_usd"] == 0.05
    assert row["cost"]["tokens"] == 1234
    assert row["cost"]["steps"] == 3
    assert row["budget"]["max_tokens"] == 5000


def test_get_run_returns_transcript(client: TestClient) -> None:
    _seed_run("run-1")
    runs_store.update_run(
        "run-1",
        status="done",
        checkpoint=[
            {"role": "system", "content": "persona"},
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "done"},
        ],
    )
    resp = client.get("/runs/run-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["checkpointMessages"] == 3
    roles = [m["role"] for m in body["transcript"]]
    assert roles == ["user", "assistant"]  # system elided


def test_get_unknown_run_404(client: TestClient) -> None:
    assert client.get("/runs/nope").status_code == 404


# ---------------------------------------------------------------------------
# Control routes
# ---------------------------------------------------------------------------


def test_cancel_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_manager, "cancel_run", lambda rid: rid == "run-1")
    assert client.post("/runs/run-1/cancel").json() == {"cancelled": True}
    assert client.post("/runs/ghost/cancel").status_code == 404


def test_answer_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_answer(run_id: str, answer: str) -> bool:
        captured["run_id"] = run_id
        captured["answer"] = answer
        return True

    monkeypatch.setattr(run_manager, "answer_run", _fake_answer)
    resp = client.post("/runs/run-1/answer", json={"answer": "yes proceed"})
    assert resp.status_code == 200
    assert resp.json() == {"resumed": True}
    assert captured == {"run_id": "run-1", "answer": "yes proceed"}


def test_answer_not_paused_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_manager, "answer_run", lambda *_a, **_k: False)
    resp = client.post("/runs/run-1/answer", json={"answer": "x"})
    assert resp.status_code == 409


def test_answer_unknown_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> bool:
        raise RunManagerError("unknown run: 'ghost'")

    monkeypatch.setattr(run_manager, "answer_run", _raise)
    resp = client.post("/runs/ghost/answer", json={"answer": "x"})
    assert resp.status_code == 404


def test_resume_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_manager, "resume_run", lambda *_a, **_k: True)
    resp = client.post("/runs/run-1/resume")
    assert resp.status_code == 200
    assert resp.json() == {"resumed": True}


def test_resume_already_running_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> bool:
        raise RunManagerError("run 'run-1' is already running")

    monkeypatch.setattr(run_manager, "resume_run", _raise)
    resp = client.post("/runs/run-1/resume")
    assert resp.status_code == 409

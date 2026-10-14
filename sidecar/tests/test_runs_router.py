"""runs router tests — the exact wire shapes + api_key-never-echoed.

The executor (``run_manager``) is unit-tested in ``test_run_manager``; here we
exercise the TRANSPORT: the routes the frontend consumes, the snake_case wire
shape (the one spelling, R15-CODE-AGENT-031), the status codes, and the
security invariant that the BYOK ``api_key`` crosses for the run only and is
never echoed in any response. ``run_manager`` is mocked at the boundary so a
route test does not depend on a detached task
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
from services.runs_store import RunNotFound, RunStateError


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
            "api_key": "sk-secret-123",
            "budget": {"max_tokens": 50000, "max_spend_usd": 2.5},
            "options": {"temperature": 0.2},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body == {"run_id": "run-xyz"}
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
        json={"prompt": "x", "api_key": secret},
    )
    assert resp.status_code == 201
    assert secret not in resp.text


def test_launch_unknown_agent_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(**_k: object) -> str:
        raise RunManagerError("unknown agent: 'ghost'")

    monkeypatch.setattr(run_manager, "launch_run", _raise)
    resp = client.post("/agents/ghost/runs", json={"prompt": "x"})
    assert resp.status_code == 404


def test_launch_rejects_a_non_positive_ceiling(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-AGENT-034: 0 is not a ceiling (it aborted instantly); it is a 422."""
    monkeypatch.setattr(run_manager, "launch_run", lambda **_k: "run-1")
    resp = client.post("/agents/copilot/runs", json={"prompt": "x", "budget": {"max_steps": 0}})
    assert resp.status_code == 422


def test_launch_rejects_a_camel_case_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-CODE-AGENT-031: the body has one spelling; a camelCase ceiling is a 422,
    never a silently dropped limit."""
    monkeypatch.setattr(run_manager, "launch_run", lambda **_k: "run-1")
    resp = client.post("/agents/copilot/runs", json={"prompt": "x", "budget": {"maxTokens": 100}})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /runs  +  GET /runs/{id}
# ---------------------------------------------------------------------------


#: The exact ``GET /runs`` row keys, and the nested cost / budget keys.
_SUMMARY_KEYS = {
    "id",
    "agent_id",
    "agent_name",
    "mode",
    "status",
    "cost",
    "budget",
    "provider",
    "model",
    "plan",
    "activity",
    "detail",
    "question",
    "created_at",
    "updated_at",
}
_DETAIL_KEYS = _SUMMARY_KEYS | {
    "transcript",
    "checkpoint_messages",
    "answer",
    "brief",
    "host_actions",
}
_COST_KEYS = {"tokens", "spend_usd", "steps"}
_BUDGET_KEYS = {"max_tokens", "max_spend_usd", "max_wall_seconds", "max_steps"}


def test_runs_rows_carry_only_snake_case_keys(client: TestClient) -> None:
    """R15-CODE-AGENT-031: the wire is snake_case only, list and detail alike.

    The router used to emit every key twice (camelCase + snake_case); the rail
    reads ``cost.spend_usd``, so a camelCase-only "cleanup" zeroed its cost.
    The exact key sets pin the one spelling both ways.
    """
    _seed_run("run-1", max_tokens=5000, max_spend_usd=1.5)
    runs_store.update_run("run-1", cost={"tokens": 1234, "spend_usd": 0.05, "steps": 3})
    row = client.get("/runs").json()["runs"][0]
    detail = client.get("/runs/run-1").json()
    assert set(row) == _SUMMARY_KEYS
    assert set(detail) == _DETAIL_KEYS
    for body in (row, detail):
        assert set(body["cost"]) == _COST_KEYS
        assert set(body["budget"]) == _BUDGET_KEYS
        assert body["cost"]["spend_usd"] == 0.05
        assert body["budget"]["max_tokens"] == 5000


def test_list_runs_shape(client: TestClient) -> None:
    """GET /runs returns ``{runs: [...]}`` with the rail's snake_case fields."""
    _seed_run("run-1", max_tokens=5000, max_spend_usd=1.5)
    runs_store.update_run("run-1", cost={"tokens": 1234, "spend_usd": 0.05, "steps": 3})
    resp = client.get("/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body
    row = body["runs"][0]
    assert row["id"] == "run-1"
    assert row["status"] == "running"
    assert row["agent_id"] == "copilot"
    assert row["agent_name"] == "Copilot"
    assert row["cost"]["spend_usd"] == 0.05
    assert row["cost"]["tokens"] == 1234
    assert row["cost"]["steps"] == 3
    assert row["budget"]["max_tokens"] == 5000
    assert row["created_at"] == 1000
    assert isinstance(row["updated_at"], int)


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
    assert body["checkpoint_messages"] == 3
    roles = [m["role"] for m in body["transcript"]]
    assert roles == ["user", "assistant"]  # system elided


def test_get_unknown_run_404(client: TestClient) -> None:
    assert client.get("/runs/nope").status_code == 404


# ---------------------------------------------------------------------------
# Control routes
# ---------------------------------------------------------------------------


def test_cancel_route(client: TestClient) -> None:
    _seed_run("run-1")
    assert client.post("/runs/run-1/cancel").json() == {"cancelled": True}
    assert client.post("/runs/ghost/cancel").status_code == 404


def test_control_routes_on_a_done_run_are_409_and_leave_it(client: TestClient) -> None:
    """R15-CODE-AGENT-010: cancel, resume and answer never rewrite a finished run."""
    _seed_run("run-1")
    runs_store.update_run(
        "run-1",
        status="done",
        detail="completed",
        checkpoint=[{"role": "user", "content": "go"}],
        now=1100,
    )
    for path, body in (("cancel", None), ("resume", None), ("answer", {"answer": "x"})):
        resp = client.post(f"/runs/run-1/{path}", json=body)
        assert resp.status_code == 409, path
    row = runs_store.get_run("run-1")
    assert row is not None
    assert (row.status, row.detail, row.updated_at) == ("done", "completed", 1100)


def test_answer_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_answer(run_id: str, answer: str, **_k: object) -> None:
        captured["run_id"] = run_id
        captured["answer"] = answer

    monkeypatch.setattr(run_manager, "answer_run", _fake_answer)
    resp = client.post("/runs/run-1/answer", json={"answer": "yes proceed"})
    assert resp.status_code == 200
    assert resp.json() == {"resumed": True}
    assert captured == {"run_id": "run-1", "answer": "yes proceed"}


def test_answer_not_paused_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise RunStateError("run 'run-1' is running; it is not awaiting an answer")

    monkeypatch.setattr(run_manager, "answer_run", _raise)
    resp = client.post("/runs/run-1/answer", json={"answer": "x"})
    assert resp.status_code == 409


def test_answer_unknown_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise RunNotFound("unknown run: 'ghost'")

    monkeypatch.setattr(run_manager, "answer_run", _raise)
    resp = client.post("/runs/ghost/answer", json={"answer": "x"})
    assert resp.status_code == 404


def test_resume_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_manager, "resume_run", lambda *_a, **_k: True)
    resp = client.post("/runs/run-1/resume")
    assert resp.status_code == 200
    assert resp.json() == {"resumed": True}


def test_resume_and_answer_take_the_key_from_a_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-AGENT-035: the routes took no key, so a resumed BYOK run had none."""
    secret = "sk-resume-must-not-leak"
    captured: list[object] = []
    monkeypatch.setattr(run_manager, "resume_run", lambda _rid, **k: captured.append(k["api_key"]))
    monkeypatch.setattr(
        run_manager, "answer_run", lambda _rid, _a, **k: captured.append(k["api_key"])
    )
    monkeypatch.setattr(run_manager, "start_run", lambda _rid, **k: captured.append(k["api_key"]))
    headers = {"X-LLM-Api-Key": secret}
    resume = client.post("/runs/run-1/resume", headers=headers)
    answer = client.post("/runs/run-1/answer", json={"answer": "NSE"}, headers=headers)
    start = client.post("/runs/run-1/start", headers=headers)
    assert (resume.status_code, answer.status_code, start.status_code) == (200, 200, 200)
    assert captured == [secret, secret, secret]
    assert secret not in resume.text + answer.text + start.text


def test_resume_already_running_409(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise RunStateError("run 'run-1' is still running")

    monkeypatch.setattr(run_manager, "resume_run", _raise)
    resp = client.post("/runs/run-1/resume")
    assert resp.status_code == 409

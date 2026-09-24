"""R15-AGENT-023: unattended workflow schedules + the action.webhook node."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV, get_data_dir
from models.announcements import Announcement, AnnouncementsResponse
from models.workflow import ScheduleCreate, WorkflowSpec
from services import (
    corporate_disclosures,
    workflow_engine,
    workflow_nodes,
    workflow_scheduler,
    workflow_store,
)
from services.workflow_nodes import builtin

SECRET_URL = "https://hooks.example.test/T000/B000/s3cr3t-path"
T0 = 1_800_000_000.0  # fake clock, epoch seconds


@pytest.fixture(autouse=True)
def _env(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(builtin, "_WEBHOOK_URLS", {})
    workflow_engine.reset_registry_for_tests()
    workflow_nodes.register_all()
    yield
    workflow_engine.reset_registry_for_tests()


def _save(nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None) -> WorkflowSpec:
    return workflow_store.save_workflow(
        WorkflowSpec.model_validate(
            {
                "id": "wf-1",
                "name": "Results alert",
                "nodes": [{"position": {"x": 0, "y": 0}, **n} for n in nodes],
                "edges": edges or [],
            }
        )
    )


def _mock_webhook(monkeypatch: pytest.MonkeyPatch, status: int = 200) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status)

    real = httpx.AsyncClient
    monkeypatch.setattr(
        builtin.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(_handler), **kw),
    )
    return seen


async def _tick(now: float) -> int:
    fires = await workflow_scheduler.tick(now)
    await asyncio.gather(*fires)
    return len(fires)


@pytest.mark.asyncio
async def test_interval_fires_once_when_due_and_not_again_before_the_next_interval() -> None:
    _save([{"id": "s", "type": "flow.sleep", "config": {"seconds": 0}}])
    body = ScheduleCreate.model_validate(
        {"workflowId": "wf-1", "trigger": {"kind": "interval", "everyMinutes": 5}}
    )
    schedule = workflow_store.create_schedule(body, now_ms=int(T0 * 1000))

    assert await _tick(T0 + 299) == 0  # not yet due
    assert await _tick(T0 + 300) == 1  # due
    assert await _tick(T0 + 301) == 0  # just fired
    assert await _tick(T0 + 599) == 0  # before the next interval
    assert await _tick(T0 + 600) == 1

    stored = workflow_store.get_schedule(schedule.id)
    assert stored is not None
    assert stored.last_fired_at == int((T0 + 600) * 1000)
    assert stored.last_status == "ok"


@pytest.mark.asyncio
async def test_announcement_fires_once_per_new_matching_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed: list[Announcement] = [
        # filed before the schedule existed: never fires
        Announcement(
            symbol="TCS",
            exchange="NSE",
            headline="Outcome of Board Meeting - Financial Results",
            ts=datetime.fromtimestamp(T0 - 60, UTC),
        )
    ]

    async def _feed(symbol: str, exchange: str | None = None, limit: int = 50):
        return AnnouncementsResponse(symbol=symbol, count=len(feed), announcements=list(feed))

    monkeypatch.setattr(corporate_disclosures, "get_announcements_cached", _feed)
    _save([{"id": "log", "type": "action.log", "config": {"message_template": "{value}"}}])
    body = ScheduleCreate.model_validate(
        {
            "workflowId": "wf-1",
            "trigger": {"kind": "announcement", "symbol": "TCS", "phrase": "financial results"},
        }
    )
    workflow_store.create_schedule(body, now_ms=int(T0 * 1000))
    ran: list[dict[str, Any]] = []
    real_run = workflow_engine.run_workflow

    async def _spy(spec: WorkflowSpec, **kw: Any):
        ran.append(kw["inputs"])
        return await real_run(spec, **kw)

    monkeypatch.setattr(workflow_engine, "run_workflow", _spy)

    assert await _tick(T0 + 60) == 0
    feed.insert(
        0,
        Announcement(
            symbol="TCS",
            exchange="NSE",
            headline="Trading window closure",
            ts=datetime.fromtimestamp(T0 + 100, UTC),
        ),
    )
    feed.insert(
        0,
        Announcement(
            symbol="TCS",
            exchange="NSE",
            headline="Audited Financial Results for Q2",
            ts=datetime.fromtimestamp(T0 + 200, UTC),
        ),
    )
    assert await _tick(T0 + 300) == 1
    assert await _tick(T0 + 360) == 0  # repeat poll, same feed
    assert [r["announcement"]["headline"] for r in ran] == ["Audited Financial Results for Q2"]


@pytest.mark.asyncio
async def test_webhook_node_posts_the_value_to_the_registered_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _mock_webhook(monkeypatch)
    builtin.register_webhook_url("wh-1", SECRET_URL)
    spec = _save([{"id": "hook", "type": "action.webhook", "config": {"secret_ref": "wh-1"}}])

    result = await workflow_engine.run_workflow(spec, inputs={"value": {"score": 8}})

    assert result.status == "ok"
    assert result.nodes[0].outputs == {"status_code": 200}
    assert [str(r.url) for r in seen] == [SECRET_URL]
    assert seen[0].read() == b'{"workflow":"Results alert","node":"hook","value":{"score":8}}'


@pytest.mark.asyncio
async def test_webhook_non_2xx_is_a_node_error_without_the_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_webhook(monkeypatch, status=500)
    builtin.register_webhook_url("wh-1", SECRET_URL)
    spec = _save([{"id": "hook", "type": "action.webhook", "config": {"secret_ref": "wh-1"}}])

    result = await workflow_engine.run_workflow(spec, inputs={"value": 1})

    assert result.status == "error"
    assert result.nodes[0].error == "action.webhook: endpoint answered HTTP 500"


def test_webhook_url_reaches_no_row_response_or_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from app import create_app

    caplog.set_level(logging.DEBUG)
    seen = _mock_webhook(monkeypatch)
    client = TestClient(create_app())
    responses: list[httpx.Response] = []

    def call(method: str, path: str, **kw: Any) -> httpx.Response:
        response = client.request(method, path, **kw)
        responses.append(response)
        return response

    bad = call("PUT", "/workflow/webhooks/wh-1", headers={"X-Vysted-Webhook-Url": "http://x.test"})
    assert bad.status_code == 400
    ok = call("PUT", "/workflow/webhooks/wh-1", headers={"X-Vysted-Webhook-Url": SECRET_URL})
    assert ok.json() == {"refs": ["wh-1"]}
    assert call("GET", "/workflow/webhooks").json() == {"refs": ["wh-1"]}
    spec = {
        "id": "wf-1",
        "name": "hook",
        "nodes": [
            {
                "id": "hook",
                "type": "action.webhook",
                "position": {"x": 0, "y": 0},
                "config": {"secret_ref": "wh-1"},
            }
        ],
        "edges": [],
    }
    assert call("POST", "/workflow/save", json=spec).status_code == 200
    created = call(
        "POST",
        "/workflow/schedules",
        json={"workflowId": "wf-1", "trigger": {"kind": "interval", "everyMinutes": 5}},
    ).json()
    assert created["enabled"] is True
    assert call("GET", "/workflow/schedules").json()[0]["id"] == created["id"]

    asyncio.run(_tick(created["createdAt"] / 1000 + 300))
    assert [str(r.url) for r in seen] == [SECRET_URL]
    listed = call("GET", "/workflow/schedules").json()[0]
    assert listed["lastStatus"] == "ok"
    assert (
        call("PATCH", f"/workflow/schedules/{created['id']}", json={"enabled": False}).json()[
            "enabled"
        ]
        is False
    )

    db_bytes = (get_data_dir() / workflow_store.DB_FILENAME).read_bytes()
    assert b"s3cr3t" not in db_bytes
    for response in responses:
        assert "s3cr3t" not in response.text
    assert not [r for r in caplog.records if "s3cr3t" in r.getMessage()]
    assert call("DELETE", f"/workflow/schedules/{created['id']}").json() == {"deleted": True}

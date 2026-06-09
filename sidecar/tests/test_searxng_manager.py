"""Tests for the one-click SearXNG manager state machine (R7 Component 2).

Docker is NEVER required: every docker CLI invocation goes through the
manager's injected runner seam (a programmable :class:`FakeDocker` that records
each call), health checks through an injected probe, and port probing through
an injected checker — no subprocess, no network, no container in CI.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from services import searxng_manager
from services.searxng_manager import (
    CONTAINER_NAME,
    DEFAULT_HOST_PORT,
    IMAGE,
    STATE_DOCKER_PRESENT_NOT_SETUP,
    STATE_ERROR,
    STATE_NOT_INSTALLED_DOCKER,
    STATE_PULLING,
    STATE_READY,
    STATE_STARTING,
    SearxngManager,
    write_settings,
)

# ---------------------------------------------------------------------------
# Canned `docker version --format {{json .}}` payloads
# ---------------------------------------------------------------------------

_VERSION_ORBSTACK = json.dumps(
    {
        "Client": {"Version": "27.4.0"},
        "Server": {"Version": "27.4.0", "Platform": {"Name": "OrbStack"}},
    }
)
_VERSION_DESKTOP = json.dumps(
    {
        "Client": {"Version": "27.4.0"},
        "Server": {"Version": "27.4.0", "Platform": {"Name": "Docker Desktop 4.30 (149282)"}},
    }
)
#: Daemon down: the CLI still prints the Client block, exits non-zero.
_VERSION_DAEMON_DOWN = json.dumps({"Client": {"Version": "27.4.0"}})


class FakeDocker:
    """Programmable docker-CLI seam: responses keyed by subcommand, calls recorded."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._responses: dict[str, tuple[int, str, str]] = {}

    def set(self, subcommand: str, code: int, out: str = "", err: str = "") -> None:
        self._responses[subcommand] = (code, out, err)

    def subcommands(self) -> list[str]:
        return [call[0] for call in self.calls]

    async def __call__(self, *args: str, timeout: float | None = None) -> tuple[int, str, str]:
        self.calls.append(args)
        return self._responses.get(args[0], (1, "", f"no fake response for docker {args[0]}"))


async def _health_up(_url: str) -> bool:
    return True


async def _health_down(_url: str) -> bool:
    return False


def _manager(fake: FakeDocker, tmp_path, **overrides) -> SearxngManager:
    kwargs: dict = {
        "runner": fake,
        "health_probe": _health_up,
        "port_free": lambda _port: True,
        "config_dir": tmp_path / "searxng",
        "health_timeout_secs": 0.2,
        "health_interval_secs": 0.01,
    }
    kwargs.update(overrides)
    return SearxngManager(**kwargs)


# ---------------------------------------------------------------------------
# refresh() / detect() — passive state derivation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_without_docker_cli_reports_not_installed(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 127, "", "docker CLI not found")
    mgr = _manager(fake, tmp_path)

    status = await mgr.refresh()

    assert status["state"] == STATE_NOT_INSTALLED_DOCKER
    assert status["docker"] == {"cli_present": False, "daemon_running": False, "runtime": None}
    assert mgr.ready_base_url() is None


@pytest.mark.asyncio
async def test_refresh_with_daemon_down_reports_not_installed_but_cli_present(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 1, _VERSION_DAEMON_DOWN, "Cannot connect to the Docker daemon")
    mgr = _manager(fake, tmp_path)

    status = await mgr.refresh()

    assert status["state"] == STATE_NOT_INSTALLED_DOCKER
    docker = status["docker"]
    assert docker["cli_present"] is True
    assert docker["daemon_running"] is False


@pytest.mark.asyncio
async def test_refresh_with_docker_but_no_container_reports_not_setup(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_ORBSTACK)
    fake.set("inspect", 1, "", f"Error: No such object: {CONTAINER_NAME}")
    mgr = _manager(fake, tmp_path)

    status = await mgr.refresh()

    assert status["state"] == STATE_DOCKER_PRESENT_NOT_SETUP
    # OrbStack is recognized and surfaced for the guided UI copy.
    assert status["docker"]["runtime"] == "OrbStack"
    assert status["container"] is None


@pytest.mark.asyncio
async def test_refresh_with_running_healthy_container_reports_ready(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_DESKTOP)
    fake.set("inspect", 0, "running\n")
    fake.set("port", 0, "127.0.0.1:8899\n")
    mgr = _manager(fake, tmp_path)

    status = await mgr.refresh()

    assert status["state"] == STATE_READY
    assert status["port"] == 8899
    assert status["url"] == "http://127.0.0.1:8899"
    assert mgr.ready_base_url() == "http://127.0.0.1:8899"


@pytest.mark.asyncio
async def test_refresh_with_running_unhealthy_container_reports_starting(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_DESKTOP)
    fake.set("inspect", 0, "running\n")
    fake.set("port", 0, f"127.0.0.1:{DEFAULT_HOST_PORT}\n")
    mgr = _manager(fake, tmp_path, health_probe=_health_down)

    status = await mgr.refresh()

    assert status["state"] == STATE_STARTING
    assert mgr.ready_base_url() is None


@pytest.mark.asyncio
async def test_refresh_with_exited_container_reports_not_setup_with_container_status(
    tmp_path,
) -> None:
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_DESKTOP)
    fake.set("inspect", 0, "exited\n")
    mgr = _manager(fake, tmp_path)

    status = await mgr.refresh()

    assert status["state"] == STATE_DOCKER_PRESENT_NOT_SETUP
    assert status["container"] == "exited"  # the UI words the CTA "Start", not "Set up"


# ---------------------------------------------------------------------------
# setup() — the pull → configure → run → health sequence
# ---------------------------------------------------------------------------


def _fresh_setup_fake() -> FakeDocker:
    """Docker fake for a fresh setup: daemon up, no container, pull/run succeed."""
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_ORBSTACK)
    fake.set("inspect", 1, "", f"Error: No such object: {CONTAINER_NAME}")
    fake.set("pull", 0, "Status: Downloaded newer image\n")
    fake.set("run", 0, "abc123\n")
    return fake


@pytest.mark.asyncio
async def test_setup_happy_path_pulls_configures_runs_and_reaches_ready(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path)

    status = await mgr.setup()

    assert status["state"] == STATE_READY
    assert status["port"] == DEFAULT_HOST_PORT
    assert status["url"] == f"http://127.0.0.1:{DEFAULT_HOST_PORT}"
    assert ("pull", IMAGE) in fake.calls

    run_call = next(call for call in fake.calls if call[0] == "run")
    assert "--name" in run_call and CONTAINER_NAME in run_call
    assert "--restart" in run_call and "unless-stopped" in run_call
    assert f"127.0.0.1:{DEFAULT_HOST_PORT}:8080" in run_call
    assert f"{tmp_path / 'searxng'}:/etc/searxng" in run_call
    assert run_call[-1] == IMAGE


@pytest.mark.asyncio
async def test_setup_writes_settings_yml_enabling_json_format(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path)

    await mgr.setup()

    settings = (tmp_path / "searxng" / "settings.yml").read_text(encoding="utf-8")
    assert "- json" in settings
    assert "use_default_settings: true" in settings
    assert "limiter: false" in settings
    # The secret key was actually generated, not left as a template placeholder.
    assert "{secret_key}" not in settings
    assert 'secret_key: ""' not in settings


@pytest.mark.asyncio
async def test_setup_probes_past_an_occupied_preferred_port(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path, port_free=lambda port: port != DEFAULT_HOST_PORT)

    status = await mgr.setup()

    assert status["state"] == STATE_READY
    assert status["port"] == DEFAULT_HOST_PORT + 1
    run_call = next(call for call in fake.calls if call[0] == "run")
    assert f"127.0.0.1:{DEFAULT_HOST_PORT + 1}:8080" in run_call


@pytest.mark.asyncio
async def test_setup_with_no_free_port_errors_with_reason(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path, port_free=lambda _port: False)

    status = await mgr.setup()

    assert status["state"] == STATE_ERROR
    assert "no free port" in str(status["reason"])


@pytest.mark.asyncio
async def test_setup_pull_failure_reports_error_with_stderr_reason(tmp_path) -> None:
    fake = _fresh_setup_fake()
    fake.set("pull", 1, "", "Error response from daemon: pull access denied")
    mgr = _manager(fake, tmp_path)

    status = await mgr.setup()

    assert status["state"] == STATE_ERROR
    assert "pull access denied" in str(status["reason"])
    # Never tried to run a container after a failed pull.
    assert "run" not in fake.subcommands()


@pytest.mark.asyncio
async def test_setup_run_failure_reports_error(tmp_path) -> None:
    fake = _fresh_setup_fake()
    fake.set("run", 125, "", "Error: port is already allocated")
    mgr = _manager(fake, tmp_path)

    status = await mgr.setup()

    assert status["state"] == STATE_ERROR
    assert "port is already allocated" in str(status["reason"])


@pytest.mark.asyncio
async def test_setup_without_docker_lands_in_not_installed(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 127, "", "docker CLI not found")
    mgr = _manager(fake, tmp_path)

    status = await mgr.setup()

    assert status["state"] == STATE_NOT_INSTALLED_DOCKER
    assert fake.subcommands() == ["version"]  # nothing else was attempted


@pytest.mark.asyncio
async def test_setup_restarts_an_existing_stopped_container_without_repulling(tmp_path) -> None:
    fake = FakeDocker()
    fake.set("version", 0, _VERSION_ORBSTACK)
    fake.set("inspect", 0, "exited\n")
    fake.set("start", 0, f"{CONTAINER_NAME}\n")
    fake.set("port", 0, "127.0.0.1:8890\n")
    mgr = _manager(fake, tmp_path)

    status = await mgr.setup()

    assert status["state"] == STATE_READY
    assert status["port"] == 8890
    assert ("start", CONTAINER_NAME) in fake.calls
    assert "pull" not in fake.subcommands()
    assert "run" not in fake.subcommands()


@pytest.mark.asyncio
async def test_setup_health_never_passing_errors_with_log_hint(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path, health_probe=_health_down)

    status = await mgr.setup()

    assert status["state"] == STATE_ERROR
    assert "never became healthy" in str(status["reason"])
    assert f"docker logs {CONTAINER_NAME}" in str(status["reason"])


@pytest.mark.asyncio
async def test_begin_setup_returns_pulling_immediately_then_settles_ready(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path)

    immediate = mgr.begin_setup()
    assert immediate["state"] == STATE_PULLING

    # A status poll while the task is in flight returns the in-flight state
    # without re-probing docker.
    in_flight = await mgr.refresh()
    assert in_flight["state"] in (STATE_PULLING, STATE_STARTING, STATE_READY)

    assert mgr._task is not None
    final = await mgr._task
    assert final["state"] == STATE_READY

    # A second begin_setup while settled simply starts a fresh pass; while in
    # flight it must join, not double-run — covered by the lock + task guard.
    assert mgr.ready_base_url() == f"http://127.0.0.1:{DEFAULT_HOST_PORT}"


@pytest.mark.asyncio
async def test_begin_setup_is_idempotent_while_in_flight(tmp_path) -> None:
    fake = _fresh_setup_fake()
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_health(_url: str) -> bool:
        started.set()
        await release.wait()
        return True

    mgr = _manager(fake, tmp_path, health_probe=slow_health, health_timeout_secs=5.0)
    mgr.begin_setup()
    first_task = mgr._task
    await started.wait()

    again = mgr.begin_setup()
    assert mgr._task is first_task  # joined, not respawned
    assert again["state"] == STATE_STARTING

    release.set()
    final = await first_task
    assert final["state"] == STATE_READY
    # Exactly one pull and one run despite two begin_setup calls.
    assert fake.subcommands().count("pull") == 1
    assert fake.subcommands().count("run") == 1


@pytest.mark.asyncio
async def test_error_from_background_setup_survives_the_status_poll(tmp_path) -> None:
    """Regression: error(reason) must be observable through refresh(), the poll surface.

    begin_setup runs setup as a background task, so the UI only ever sees the
    polled status. refresh() used to re-derive unconditionally once the task was
    done — the very first poll after a failed pull returned
    docker_present_not_setup with reason=None and state=error was unreachable
    through the wire contract.
    """
    fake = _fresh_setup_fake()
    fake.set("pull", 1, "", "Error response from daemon: pull access denied")
    mgr = _manager(fake, tmp_path)

    mgr.begin_setup()
    assert mgr._task is not None
    await mgr._task  # background setup fails on the pull

    polled = await mgr.refresh()
    assert polled["state"] == STATE_ERROR
    assert "pull access denied" in str(polled["reason"])

    # Sticky: subsequent polls keep showing the error, not a silent re-derive.
    again = await mgr.refresh()
    assert again["state"] == STATE_ERROR
    assert "pull access denied" in str(again["reason"])
    assert mgr.ready_base_url() is None


@pytest.mark.asyncio
async def test_retry_setup_clears_a_sticky_error_and_can_reach_ready(tmp_path) -> None:
    fake = _fresh_setup_fake()
    fake.set("pull", 1, "", "Error response from daemon: pull access denied")
    mgr = _manager(fake, tmp_path)
    mgr.begin_setup()
    assert mgr._task is not None
    await mgr._task
    assert (await mgr.refresh())["state"] == STATE_ERROR

    # The user fixes the world (e.g. logs into the registry) and retries.
    fake.set("pull", 0, "Status: Downloaded newer image\n")
    immediate = mgr.begin_setup()
    assert immediate["state"] == STATE_PULLING  # the retry cleared the error
    assert mgr._task is not None
    final = await mgr._task
    assert final["state"] == STATE_READY

    # The poll surface follows: with the container now live, refresh re-derives
    # READY instead of replaying the stale error.
    fake.set("inspect", 0, "running\n")
    fake.set("port", 0, f"127.0.0.1:{DEFAULT_HOST_PORT}\n")
    polled = await mgr.refresh()
    assert polled["state"] == STATE_READY
    assert polled["reason"] is None


@pytest.mark.asyncio
async def test_teardown_clears_a_sticky_error(tmp_path) -> None:
    fake = _fresh_setup_fake()
    fake.set("pull", 1, "", "Error response from daemon: pull access denied")
    fake.set("stop", 0, f"{CONTAINER_NAME}\n")
    fake.set("rm", 0, f"{CONTAINER_NAME}\n")
    mgr = _manager(fake, tmp_path)
    mgr.begin_setup()
    assert mgr._task is not None
    await mgr._task
    assert (await mgr.refresh())["state"] == STATE_ERROR

    status = await mgr.teardown()

    assert status["state"] == STATE_DOCKER_PRESENT_NOT_SETUP
    assert status["reason"] is None


@pytest.mark.asyncio
async def test_shutdown_cancels_an_in_flight_setup(tmp_path) -> None:
    fake = _fresh_setup_fake()
    hung = asyncio.Event()

    async def hung_health(_url: str) -> bool:
        hung.set()
        await asyncio.sleep(3600)
        return True

    mgr = _manager(fake, tmp_path, health_probe=hung_health, health_timeout_secs=3600)
    mgr.begin_setup()
    await hung.wait()

    await mgr.shutdown()

    assert mgr._task is None
    assert mgr.state == STATE_ERROR
    assert "cancelled" in str(mgr.reason)


# ---------------------------------------------------------------------------
# teardown()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teardown_stops_and_removes_then_reports_not_setup(tmp_path) -> None:
    fake = _fresh_setup_fake()
    mgr = _manager(fake, tmp_path)
    await mgr.setup()
    assert mgr.state == STATE_READY

    # After `docker rm` the container no longer inspects.
    fake.set("stop", 0, f"{CONTAINER_NAME}\n")
    fake.set("rm", 0, f"{CONTAINER_NAME}\n")
    fake.set("inspect", 1, "", f"Error: No such object: {CONTAINER_NAME}")

    status = await mgr.teardown()

    assert ("stop", CONTAINER_NAME) in fake.calls
    assert ("rm", CONTAINER_NAME) in fake.calls
    assert status["state"] == STATE_DOCKER_PRESENT_NOT_SETUP
    assert status["port"] is None
    assert mgr.ready_base_url() is None


# ---------------------------------------------------------------------------
# write_settings()
# ---------------------------------------------------------------------------


def test_write_settings_is_idempotent_and_preserves_the_secret(tmp_path) -> None:
    first = write_settings(tmp_path / "searxng").read_text(encoding="utf-8")
    second = write_settings(tmp_path / "searxng").read_text(encoding="utf-8")
    assert first == second  # the per-install secret key survives re-setup


# ---------------------------------------------------------------------------
# Routing: detect_searxng() prefers the managed instance when READY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_searxng_prefers_the_managed_ready_instance(monkeypatch, tmp_path) -> None:
    from services.search.searxng import detect_searxng

    ready = _manager(FakeDocker(), tmp_path)
    ready.state = STATE_READY
    ready.port = 9123
    monkeypatch.setattr(searxng_manager, "manager", ready)

    probed: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        probed.append(f"{request.url.host}:{request.url.port}")
        if request.url.port == 9123:
            return httpx.Response(200, json={"results": []})
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        found = await detect_searxng(client=client)

    assert found == "http://127.0.0.1:9123"
    assert probed[0] == "127.0.0.1:9123"  # managed URL probed FIRST


@pytest.mark.asyncio
async def test_detect_searxng_falls_back_to_conventional_ports_when_not_ready(
    monkeypatch, tmp_path
) -> None:
    from services.search.searxng import detect_searxng

    idle = _manager(FakeDocker(), tmp_path)  # state unknown → no managed URL
    monkeypatch.setattr(searxng_manager, "manager", idle)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == 8080:
            return httpx.Response(200, json={"results": []})
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        found = await detect_searxng(client=client)

    assert found == "http://localhost:8080"

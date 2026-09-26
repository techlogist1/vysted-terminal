"""One-click managed SearXNG — the T2 "Unlimited Research" tier (R7 Component 2).

The keyless T1 tier scrapes public engines and is therefore rate-limited by
nature. T2 removes that ceiling without a key: the sidecar manages a **local
SearXNG container** (``vysted-searxng``) on the user's own docker runtime
(Docker Desktop, OrbStack, or a bare engine), bound to loopback only, with a
generated ``settings.yml`` that enables the JSON output format the existing
:mod:`services.search.searxng` backend consumes.

The manager is a small state machine — the CONTRACT for the UI's guided
"Unlimited Research" flow (exposed via :mod:`routers.search_tiers`):

  ``not_installed_docker``        no usable docker (CLI missing OR daemon down —
                                  ``docker.cli_present`` / ``docker.daemon_running``
                                  in the status payload disambiguate the CTA:
                                  "Install Docker/OrbStack" vs "Start it").
  ``docker_present_not_setup``    docker works; the managed container does not
                                  exist yet (or exists but is stopped — the
                                  ``container`` field carries the raw status so
                                  the UI can word the button "Start" not "Set up").
  ``pulling``                     ``docker pull searxng/searxng`` in flight.
  ``starting``                    container created/started; waiting for the
                                  JSON search endpoint to answer.
  ``ready``                       ``/search?q=…&format=json`` answers — the
                                  research engine routes SearXNG searches here.
  ``error``                       a setup/start step failed; ``reason`` says why.
                                  STICKY through the status poll: the polled
                                  surface is the only one the UI has (setup runs
                                  as a background task), so :meth:`refresh` must
                                  not re-derive over it — only the next
                                  ``setup()``/``teardown()`` clears it.

Every docker CLI invocation goes through ONE asyncio-subprocess seam
(:func:`_run_docker`) and every health check through one probe seam
(:func:`_probe_health`), both injectable per-instance and monkeypatchable at
module level — tests never need docker or the network. The docker CLI here is a
short-lived external command (the container itself is owned by dockerd, not by
the sidecar process), so the Tauri-sidecar spawn rule does not apply.

Routing: :func:`services.search.registry.resolve` consults
:meth:`SearxngManager.ready_base_url` (in-process, no probe), so the moment the
managed instance is READY the SearXNG backend resolves to it with zero extra config.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import shutil
import socket
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import httpx

from config import get_cache_dir

_log = logging.getLogger(__name__)

#: The official SearXNG image and the fixed name of the managed container.
IMAGE = "searxng/searxng"
CONTAINER_NAME = "vysted-searxng"

#: Preferred host port (matches the conventional local port the backend's
#: autodetect already probes). The container listens on 8080 internally.
DEFAULT_HOST_PORT = 8888
_CONTAINER_INTERNAL_PORT = 8080

#: How many consecutive ports to try when the preferred one is taken.
PORT_PROBE_SPAN = 20

# State-machine states (string-valued so status payloads serialize as-is).
STATE_NOT_INSTALLED_DOCKER = "not_installed_docker"
STATE_DOCKER_PRESENT_NOT_SETUP = "docker_present_not_setup"
STATE_PULLING = "pulling"
STATE_STARTING = "starting"
STATE_READY = "ready"
#: R15-RESEARCH-028: the container answers with valid JSON (so ``STATE_READY``'s
#: own bool-only health check passes) but the search is USELESS — every engine
#: is unresponsive (CAPTCHA-suspended, timing out) or a run of consecutive
#: probes has returned zero results. ``reason`` names why (see ``_set``).
STATE_DEGRADED = "degraded"
STATE_ERROR = "error"

#: Pre-first-refresh placeholder. Never returned by the router (its status
#: endpoint always refreshes first); exists so a fresh manager is honest about
#: not having probed anything yet.
STATE_UNKNOWN = "unknown"

# Per-operation docker CLI budgets (seconds). The pull is the big one — a cold
# image download on slow links takes minutes; everything else is local-daemon RPC.
_DOCKER_TIMEOUT_SECS = 15.0
_PULL_TIMEOUT_SECS = 900.0
_RUN_TIMEOUT_SECS = 120.0
_STOP_TIMEOUT_SECS = 60.0

#: Health-probe budgets: per-request timeout, and the post-start polling loop.
_HEALTH_REQUEST_TIMEOUT_SECS = 5.0
DEFAULT_HEALTH_TIMEOUT_SECS = 90.0
DEFAULT_HEALTH_INTERVAL_SECS = 1.5

#: R15-RESEARCH-028: consecutive zero-result engine-quality probes (no engine
#: named itself unresponsive, but nothing came back either) before a
#: structurally-healthy container is called DEGRADED rather than READY.
DEFAULT_EMPTY_PROBE_DEGRADE_THRESHOLD = 3

#: Generated SearXNG configuration. ``use_default_settings`` keeps upstream
#: defaults; we add exactly what the managed tier needs: the JSON output format
#: (OFF by default upstream — the whole reason a stock instance 403s the
#: backend), the limiter off (a localhost-only instance serving one research
#: engine must not throttle itself), and a per-install secret key.
_SETTINGS_TEMPLATE = """\
# Generated by Vysted Terminal — managed SearXNG instance (T2 search tier).
# The sidecar's research engine consumes /search?format=json, so the JSON
# output format is enabled here; the limiter is off because this instance is
# bound to 127.0.0.1 and serves only the local research engine.
use_default_settings: true
server:
  secret_key: "{secret_key}"
  limiter: false
  image_proxy: false
search:
  formats:
    - html
    - json
"""

# Type aliases for the injectable seams.
DockerRunner = Callable[..., Awaitable[tuple[int, str, str]]]
HealthProbe = Callable[[str], Awaitable[bool]]
PortChecker = Callable[[int], bool]
QualityProbe = Callable[[str], Awaitable["EngineProbe"]]

#: R15-LIFECYCLE-007: a bare "docker" exec relies on the sidecar process's own
#: PATH, which is minimal/empty when the app is launched from Finder/Dock (or
#: any non-shell launcher) rather than a terminal — the CLI is installed but
#: invisible, and every call wrongly reports ``not_installed_docker``. These
#: are the install locations Docker Desktop, OrbStack, and Homebrew actually
#: use on macOS; checked only after ``PATH`` itself has a hit.
_KNOWN_DOCKER_LOCATIONS = (
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    str(Path.home() / ".orbstack" / "bin" / "docker"),
    "/Applications/Docker.app/Contents/Resources/bin/docker",
)


def _resolve_docker_binary() -> str | None:
    """Find the docker CLI's absolute path: ``PATH`` first, then known installs."""
    found = shutil.which("docker")
    if found:
        return found
    for candidate in _KNOWN_DOCKER_LOCATIONS:
        if Path(candidate).is_file():
            return candidate
    return None


async def _run_docker(*args: str, timeout: float = _DOCKER_TIMEOUT_SECS) -> tuple[int, str, str]:
    """Run a docker CLI command via asyncio subprocess; return ``(code, stdout, stderr)``.

    All failure modes collapse into the same return shape so callers branch on
    one thing: ``127`` models "docker CLI not found" (FileNotFoundError, or no
    resolvable binary at all — see :func:`_resolve_docker_binary`), ``126``
    "CLI present but not executable", ``124`` a timeout (CLI present, daemon or
    network wedged). This is the single subprocess seam tests monkeypatch.
    """
    binary = _resolve_docker_binary()
    if binary is None:
        return 127, "", "docker CLI not found"
    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return 127, "", "docker CLI not found"
    except OSError as exc:
        return 126, "", f"docker CLI could not be executed: {exc}"
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        with suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        return 124, "", f"docker {' '.join(args[:2])} timed out after {timeout:.0f}s"
    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def _probe_health(url: str) -> bool:
    """One capability probe: does ``url`` answer a JSON-format search?

    Mirrors the backend's autodetect probe (:mod:`services.search.searxng`):
    only a 200 with a parseable ``results`` list counts — a 403 means the JSON
    format is disabled, anything else means the instance is not (yet) serving.
    """
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_REQUEST_TIMEOUT_SECS) as http:
            response = await http.get(f"{url}/search", params={"q": "test", "format": "json"})
    except httpx.HTTPError:
        return False
    if not response.is_success:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    return isinstance(payload, dict) and isinstance(payload.get("results"), list)


@dataclass(frozen=True)
class EngineProbe:
    """One engine-quality read of a live SearXNG (R15-RESEARCH-028).

    ``has_results`` is the "did this probe query come back with anything"
    signal; ``unresponsive`` is the ``(engine, reason)`` pairs SearXNG itself
    reported as unresponsive on the SAME response, when it did.
    """

    has_results: bool
    unresponsive: tuple[tuple[str, str], ...] = ()


def _parse_unresponsive_engines(raw: object) -> tuple[tuple[str, str], ...]:
    """Normalize SearXNG's ``unresponsive_engines`` field to ``(name, reason)`` pairs.

    SearXNG emits ``[[engine, reason], ...]``; tolerate a bare engine name too
    (some SearXNG versions/forks have shipped a flat string list).
    """
    if not isinstance(raw, list):
        return ()
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if isinstance(entry, (list, tuple)) and entry:
            name = str(entry[0])
            reason = str(entry[1]) if len(entry) > 1 and entry[1] else "unresponsive"
            pairs.append((name, reason))
        elif isinstance(entry, str) and entry:
            pairs.append((entry, "unresponsive"))
    return tuple(pairs)


async def _probe_engines(url: str) -> EngineProbe:
    """One capability probe read for engine-level detail (same request shape
    as :func:`_probe_health`, plus the ``unresponsive_engines`` field a live
    SearXNG reports when its upstream engines are CAPTCHA-suspended/timing
    out). A live-but-useless container answers HTTP 200 with ``results: []``
    — indistinguishable from genuinely-empty at the health-probe layer, which
    is exactly what this probe exists to tell apart.
    """
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_REQUEST_TIMEOUT_SECS) as http:
            response = await http.get(f"{url}/search", params={"q": "test", "format": "json"})
    except httpx.HTTPError:
        return EngineProbe(has_results=False)
    if not response.is_success:
        return EngineProbe(has_results=False)
    try:
        payload = response.json()
    except ValueError:
        return EngineProbe(has_results=False)
    if not isinstance(payload, dict):
        return EngineProbe(has_results=False)
    results = payload.get("results")
    has_results = isinstance(results, list) and len(results) > 0
    return EngineProbe(
        has_results=has_results,
        unresponsive=_parse_unresponsive_engines(payload.get("unresponsive_engines")),
    )


def _format_unresponsive_reason(unresponsive: tuple[tuple[str, str], ...]) -> str:
    """``[("google", "CAPTCHA"), ("duckduckgo", "CAPTCHA")]`` -> ``"google,
    duckduckgo: CAPTCHA"`` — engines sharing a reason are grouped so the UI
    names the actual cause once, not once per engine."""
    groups: dict[str, list[str]] = {}
    for name, reason in unresponsive:
        groups.setdefault(reason, []).append(name)
    return "; ".join(f"{', '.join(names)}: {reason}" for reason, names in groups.items())


def _port_is_free(port: int) -> bool:
    """Can the host bind ``127.0.0.1:<port>``? (The collision-avoidance probe.)"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _parse_docker_version(stdout: str) -> tuple[bool, str | None]:
    """Parse ``docker version --format {{json .}}`` → ``(server_present, runtime_name)``.

    The ``Server`` block only appears when the daemon answered; its
    ``Platform.Name`` identifies the runtime ("OrbStack", "Docker Desktop …",
    "Docker Engine - Community", …). OrbStack is normalized to a clean label so
    the guided UI can name it.
    """
    try:
        payload = json.loads(stdout.strip() or "{}")
    except ValueError:
        return False, None
    if not isinstance(payload, dict):
        return False, None
    server = payload.get("Server")
    if not isinstance(server, dict):
        return False, None
    platform = server.get("Platform")
    name = platform.get("Name") if isinstance(platform, dict) else None
    if isinstance(name, str) and name.strip():
        if "orbstack" in name.lower():
            return True, "OrbStack"
        return True, name.strip()
    return True, "Docker Engine"


@dataclass(frozen=True)
class DockerProbe:
    """Result of the docker detection step (drives the install-vs-start CTA)."""

    cli_present: bool
    daemon_running: bool
    runtime: str | None


def write_settings(directory: Path) -> Path:
    """Write the generated ``settings.yml`` into ``directory`` (idempotent).

    An existing file is preserved — it carries the per-install secret key, and
    the user may have customized engines; regeneration would clobber both.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "settings.yml"
    if not path.exists():
        path.write_text(
            _SETTINGS_TEMPLATE.format(secret_key=secrets.token_hex(32)),
            encoding="utf-8",
        )
    return path


class SearxngManager:
    """The docker detect/pull/run/health/teardown state machine (one per process).

    All side-effectful steps go through injectable seams (``runner`` — the
    docker CLI; ``health_probe`` — the JSON capability check; ``port_free`` —
    host-port binding), defaulting to the module-level implementations at CALL
    time so module-level monkeypatching reaches the singleton too.
    """

    def __init__(
        self,
        *,
        runner: DockerRunner | None = None,
        health_probe: HealthProbe | None = None,
        port_free: PortChecker | None = None,
        quality_probe: QualityProbe | None = None,
        config_dir: Path | None = None,
        preferred_port: int = DEFAULT_HOST_PORT,
        health_timeout_secs: float = DEFAULT_HEALTH_TIMEOUT_SECS,
        health_interval_secs: float = DEFAULT_HEALTH_INTERVAL_SECS,
        empty_probe_degrade_threshold: int = DEFAULT_EMPTY_PROBE_DEGRADE_THRESHOLD,
    ) -> None:
        self._runner = runner
        self._health_probe = health_probe
        self._port_free = port_free
        self._quality_probe = quality_probe
        self._config_dir = config_dir
        # One-shot hot-path world-derivation guard (see ready_base_url_detected).
        self._hot_path_detected = False
        self._detect_lock = asyncio.Lock()
        self._detect_task: asyncio.Task[str | None] | None = None
        self._consecutive_empty_probes = 0
        self.preferred_port = int(preferred_port)
        self.health_timeout_secs = float(health_timeout_secs)
        self.health_interval_secs = float(health_interval_secs)
        self.empty_probe_degrade_threshold = int(empty_probe_degrade_threshold)

        self.state: str = STATE_UNKNOWN
        self.detail: str | None = None
        self.reason: str | None = None
        self.port: int | None = None
        self._container: str | None = None
        self._docker_probe: DockerProbe | None = None
        self._task: asyncio.Task[dict[str, object]] | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ seams

    async def _docker(self, *args: str, timeout: float = _DOCKER_TIMEOUT_SECS):
        runner = self._runner if self._runner is not None else _run_docker
        return await runner(*args, timeout=timeout)

    async def _health_once(self, port: int | None = None) -> bool:
        target = port or self.port or self.preferred_port
        probe = self._health_probe if self._health_probe is not None else _probe_health
        return await probe(f"http://127.0.0.1:{target}")

    async def _quality_once(self, port: int | None = None) -> EngineProbe:
        target = port or self.port or self.preferred_port
        probe = self._quality_probe if self._quality_probe is not None else _probe_engines
        return await probe(f"http://127.0.0.1:{target}")

    def _check_port_free(self, port: int) -> bool:
        checker = self._port_free if self._port_free is not None else _port_is_free
        return checker(port)

    # ------------------------------------------------------------ state plumbing

    def _set(self, state: str, *, detail: str | None = None, reason: str | None = None) -> None:
        self.state = state
        self.detail = detail
        self.reason = reason if state in (STATE_ERROR, STATE_DEGRADED) else None

    def _apply_quality(self, probe: EngineProbe, port: int) -> None:
        """Resolve READY vs DEGRADED from one engine-quality probe (R15-RESEARCH-028).

        A structurally-healthy container (``_health_once`` already passed)
        still needs this second read: HTTP 200 + ``results: []`` is exactly
        what a container answers when every upstream engine is
        CAPTCHA-suspended, and the plain health probe cannot tell that apart
        from a genuinely-empty answer.

        ``unresponsive`` is checked BEFORE ``has_results`` (residual fix): the
        probe's own "test" query can come back with a stray result from an
        unrelated engine while every REAL search engine on the SAME response
        reports itself unresponsive — reading ``has_results`` first hid that
        behind a false READY.
        """
        if probe.unresponsive:
            self._consecutive_empty_probes = (
                0 if probe.has_results else (self._consecutive_empty_probes + 1)
            )
            self._set(
                STATE_DEGRADED,
                detail="SearXNG is running but its search engines are blocked",
                reason=_format_unresponsive_reason(probe.unresponsive),
            )
            return
        if probe.has_results:
            self._consecutive_empty_probes = 0
            self._set(
                STATE_READY,
                detail=f"SearXNG serving JSON search at http://127.0.0.1:{port}",
            )
            return
        self._consecutive_empty_probes += 1
        if self._consecutive_empty_probes >= self.empty_probe_degrade_threshold:
            self._set(
                STATE_DEGRADED,
                detail="SearXNG is running but its search engines are blocked",
                reason=f"no results from any engine across {self._consecutive_empty_probes} probes",
            )
            return
        # Not yet confirmed degraded — one empty probe can just be an unlucky
        # query; stay READY until the threshold.
        self._set(
            STATE_READY,
            detail=f"SearXNG serving JSON search at http://127.0.0.1:{port}",
        )

    def record_search_result(self, had_results: bool) -> None:
        """Feed a REAL query's outcome into the same consecutive-empty signal
        the periodic quality probe uses (R15-RESEARCH-028 residual, C10):
        ``web_search`` calls this after every SearXNG-served search, since an
        actual finance-query miss is a stronger tell than the periodic "test"
        probe. Three consecutive empty real answers degrades the same as
        three empty probes; a real answer WITH results heals a degraded state
        back to READY (mirrors ``_apply_quality``'s own has_results branch).
        """
        if had_results:
            self._consecutive_empty_probes = 0
            if self.state == STATE_DEGRADED:
                self._set(
                    STATE_READY,
                    detail=f"SearXNG serving JSON search at http://127.0.0.1:{self.port}",
                )
            return
        self._consecutive_empty_probes += 1
        if self._consecutive_empty_probes >= self.empty_probe_degrade_threshold:
            n = self._consecutive_empty_probes
            self._set(
                STATE_DEGRADED,
                detail="SearXNG is running but its search engines are blocked",
                reason=f"no results from any engine across {n} real queries",
            )

    def snapshot(self) -> dict[str, object]:
        """The status payload — the wire contract for the guided UI flow."""
        url: str | None = None
        if self.port and self.state in (STATE_READY, STATE_STARTING):
            url = f"http://127.0.0.1:{self.port}"
        probe = self._docker_probe
        return {
            "state": self.state,
            "detail": self.detail,
            "reason": self.reason,
            "port": self.port,
            "url": url,
            "container": self._container,
            "container_name": CONTAINER_NAME,
            "image": IMAGE,
            "docker": {
                "cli_present": probe.cli_present if probe else None,
                "daemon_running": probe.daemon_running if probe else None,
                "runtime": probe.runtime if probe else None,
            },
        }

    def ready_base_url(self) -> str | None:
        """The managed instance's base URL when READY, else ``None``.

        Pure in-memory read (no I/O) — :func:`services.search.registry.resolve`
        reads this on every search-backend resolution; the health probe that
        gates READY is what keeps a stale URL from being handed out.
        """
        if self.state == STATE_READY and self.port:
            return f"http://127.0.0.1:{self.port}"
        return None

    async def ready_base_url_detected(self) -> str | None:
        """:meth:`ready_base_url`, with ONE lazy world-derivation per process.

        A fresh sidecar process starts state-cold even when the user's managed
        container is already running (the in-memory machine only advances via
        setup/status/teardown). The retrieval hot path must never bypass a live
        instance just because the process restarted — the R8 "green in settings
        but unused" disease (gate 2: running -> used). The FIRST hot-path read
        re-derives from docker once; every later read is the pure in-memory
        check again (status polls keep it current thereafter).

        R15-LIFECYCLE-018: the guard flag flips only AFTER ``refresh()``
        completes (never before it), under a dedicated lock — two concurrent
        callers racing the cold first read both await the SAME derivation
        instead of the second one reading a still-``STATE_UNKNOWN`` manager and
        wrongly concluding "no managed instance" for that one request.
        """
        if not self._hot_path_detected:
            async with self._detect_lock:
                if not self._hot_path_detected:
                    try:
                        await self.refresh()
                    except Exception:  # noqa: BLE001 — detection must never break retrieval
                        pass
                    finally:
                        self._hot_path_detected = True
        return self.ready_base_url()

    def warm_detect(self) -> None:
        """Kick the one-shot hot-path derivation off eagerly (app lifespan boot).

        Fire-and-forget: :meth:`ready_base_url_detected`'s lock keeps a later
        hot-path read from racing it, and :meth:`shutdown` cancels it if the
        process shuts down before it lands.
        """
        if self._detect_task is None or self._detect_task.done():
            self._detect_task = asyncio.ensure_future(self.ready_base_url_detected())

    # --------------------------------------------------------------- detection

    async def detect(self) -> DockerProbe:
        """Is a usable docker (CLI + daemon) available? Recognizes OrbStack."""
        code, stdout, _stderr = await self._docker("version", "--format", "{{json .}}")
        if code in (126, 127):
            probe = DockerProbe(cli_present=False, daemon_running=False, runtime=None)
        else:
            server_present, runtime = _parse_docker_version(stdout)
            daemon = code == 0 and server_present
            probe = DockerProbe(
                cli_present=True,
                daemon_running=daemon,
                runtime=runtime if daemon else None,
            )
        self._docker_probe = probe
        return probe

    async def _container_status(self) -> str | None:
        """The managed container's docker status ("running"/"exited"/…), or ``None``."""
        code, stdout, _stderr = await self._docker(
            "inspect", "--format", "{{.State.Status}}", CONTAINER_NAME
        )
        if code != 0:
            return None
        return stdout.strip() or None

    async def _container_port(self) -> int | None:
        """The published host port of a live container (``docker port`` parse)."""
        code, stdout, _stderr = await self._docker(
            "port", CONTAINER_NAME, f"{_CONTAINER_INTERNAL_PORT}/tcp"
        )
        if code != 0:
            return None
        for line in stdout.splitlines():
            _host, _sep, port = line.strip().rpartition(":")
            if port.isdigit():
                return int(port)
        return None

    async def refresh(self) -> dict[str, object]:
        """Re-derive the state from the world (passive — never mutates docker).

        While a setup task is in flight the in-flight state (pulling/starting)
        is authoritative and returned untouched; otherwise docker + container +
        health are re-probed so the status endpoint never lies about a container
        the user removed behind our back.

        Exception: a settled ``error`` is STICKY. Setup runs as a background
        task, so the status poll is the only surface that can ever deliver
        ``error(reason)`` to the UI — re-deriving here would overwrite a failed
        pull/run with ``docker_present_not_setup`` on the very first poll and
        the reason would never be observable. The error survives until the next
        :meth:`setup`/:meth:`begin_setup` (retry) or :meth:`teardown` clears it.
        """
        if self._task is not None and not self._task.done():
            return self.snapshot()
        if self.state == STATE_ERROR:
            return self.snapshot()
        probe = await self.detect()
        if not probe.cli_present:
            self._container = None
            self._set(
                STATE_NOT_INSTALLED_DOCKER,
                detail="docker CLI not found — install Docker Desktop or OrbStack",
            )
            return self.snapshot()
        if not probe.daemon_running:
            self._container = None
            self._set(
                STATE_NOT_INSTALLED_DOCKER,
                detail="docker CLI found but the daemon is not running — start Docker/OrbStack",
            )
            return self.snapshot()

        container = await self._container_status()
        self._container = container
        if container is None:
            self._set(
                STATE_DOCKER_PRESENT_NOT_SETUP,
                detail=f"docker is ready ({probe.runtime}) — SearXNG is not set up yet",
            )
        elif container == "running":
            port = await self._container_port() or self.port or self.preferred_port
            self.port = port
            if await self._health_once(port):
                self._apply_quality(await self._quality_once(port), port)
            else:
                self._set(
                    STATE_STARTING,
                    detail="container is running; waiting for the JSON search endpoint",
                )
        else:
            self._set(
                STATE_DOCKER_PRESENT_NOT_SETUP,
                detail=f"managed container exists but is {container} — setup will restart it",
            )
        return self.snapshot()

    # ------------------------------------------------------------------- setup

    def pick_port(self) -> int:
        """First free host port from the preferred one upward (collision avoidance)."""
        for candidate in range(self.preferred_port, self.preferred_port + PORT_PROBE_SPAN):
            if self._check_port_free(candidate):
                return candidate
        raise RuntimeError(
            f"no free port between {self.preferred_port} and "
            f"{self.preferred_port + PORT_PROBE_SPAN - 1}"
        )

    def settings_dir(self) -> Path:
        """The host directory mounted at ``/etc/searxng`` (under the cache dir; regenerable)."""
        return self._config_dir if self._config_dir is not None else get_cache_dir() / "searxng"

    def begin_setup(self) -> dict[str, object]:
        """Kick off the guided setup as a background task; return the immediate status.

        Idempotent: a setup already in flight is left alone. The UI polls the
        status endpoint to follow pulling → starting → ready/error.
        """
        if self._task is not None and not self._task.done():
            return self.snapshot()
        self._set(STATE_PULLING, detail="starting guided setup — checking docker")
        self._task = asyncio.create_task(self.setup())
        return self.snapshot()

    async def setup(self) -> dict[str, object]:
        """Run the full pull → configure → run → health sequence to READY (or error)."""
        try:
            async with self._lock:
                return await self._setup_locked()
        except asyncio.CancelledError:
            self._set(STATE_ERROR, reason="setup cancelled before it completed")
            raise

    async def _setup_locked(self) -> dict[str, object]:
        probe = await self.detect()
        if not probe.cli_present or not probe.daemon_running:
            self._set(
                STATE_NOT_INSTALLED_DOCKER,
                detail=(
                    "docker CLI not found — install Docker Desktop or OrbStack"
                    if not probe.cli_present
                    else "docker CLI found but the daemon is not running — start Docker/OrbStack"
                ),
            )
            return self.snapshot()

        container = await self._container_status()
        self._container = container
        if container == "running":
            self.port = await self._container_port() or self.port or self.preferred_port
            self._set(STATE_STARTING, detail="container already running; checking health")
        elif container is not None:
            # The container exists but is stopped — start it rather than re-pulling.
            self._set(STATE_STARTING, detail=f"starting existing container {CONTAINER_NAME}")
            code, _stdout, stderr = await self._docker(
                "start", CONTAINER_NAME, timeout=_RUN_TIMEOUT_SECS
            )
            if code != 0:
                self._set(STATE_ERROR, reason=f"docker start failed: {stderr.strip()}")
                return self.snapshot()
            self.port = await self._container_port() or self.port or self.preferred_port
        else:
            self._set(STATE_PULLING, detail=f"pulling {IMAGE} (first run can take a few minutes)")
            code, _stdout, stderr = await self._docker("pull", IMAGE, timeout=_PULL_TIMEOUT_SECS)
            if code != 0:
                self._set(STATE_ERROR, reason=f"docker pull failed: {stderr.strip()}")
                return self.snapshot()

            settings_dir = self.settings_dir()
            write_settings(settings_dir)
            try:
                port = self.pick_port()
            except RuntimeError as exc:
                self._set(STATE_ERROR, reason=str(exc))
                return self.snapshot()
            self.port = port

            self._set(
                STATE_STARTING,
                detail=f"starting {CONTAINER_NAME} on 127.0.0.1:{port}",
            )
            code, _stdout, stderr = await self._docker(
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                "--restart",
                "unless-stopped",
                "-p",
                f"127.0.0.1:{port}:{_CONTAINER_INTERNAL_PORT}",
                "-v",
                f"{settings_dir}:/etc/searxng",
                "-e",
                f"SEARXNG_BASE_URL=http://127.0.0.1:{port}/",
                IMAGE,
                timeout=_RUN_TIMEOUT_SECS,
            )
            if code != 0:
                self._set(STATE_ERROR, reason=f"docker run failed: {stderr.strip()}")
                return self.snapshot()
            self._container = "running"

        if await self.wait_healthy(self.port or self.preferred_port):
            port = self.port or self.preferred_port
            self._set(
                STATE_READY,
                detail=f"SearXNG serving JSON search at http://127.0.0.1:{port}",
            )
        else:
            self._set(
                STATE_ERROR,
                reason=(
                    f"container started but never became healthy within "
                    f"{self.health_timeout_secs:.0f}s — check `docker logs {CONTAINER_NAME}`"
                ),
            )
        return self.snapshot()

    async def wait_healthy(self, port: int) -> bool:
        """Poll the JSON capability probe until OK or the health budget elapses."""
        deadline = time.monotonic() + self.health_timeout_secs
        while True:
            if await self._health_once(port):
                return True
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(self.health_interval_secs)

    async def health(self) -> bool:
        """One immediate health probe of the managed instance (no polling)."""
        return await self._health_once()

    # ---------------------------------------------------------------- teardown

    async def teardown(self) -> dict[str, object]:
        """Stop + remove the managed container, then re-derive the honest state."""
        await self.shutdown()
        async with self._lock:
            await self._docker("stop", CONTAINER_NAME, timeout=_STOP_TIMEOUT_SECS)
            await self._docker("rm", CONTAINER_NAME)
            self.port = None
            self._container = None
            # Teardown is one of the two transitions allowed to clear a sticky
            # error (the other is a setup retry); drop back to the pre-probe
            # placeholder so the closing refresh() re-derives from the world.
            self._set(STATE_UNKNOWN)
        return await self.refresh()

    async def shutdown(self) -> None:
        """Cancel any in-flight setup/detect task (app-lifespan teardown)."""
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._task = None
        detect_task = self._detect_task
        if detect_task is not None and not detect_task.done():
            detect_task.cancel()
            with suppress(asyncio.CancelledError):
                await detect_task
        self._detect_task = None


#: Process-global manager — the router and the backend autodetect share it so
#: there is exactly ONE view of the managed instance per sidecar process.
manager = SearxngManager()


def reset_for_tests() -> None:
    """Replace the process-global manager with a fresh one (test isolation only)."""
    global manager
    manager = SearxngManager()


async def shutdown() -> None:
    """Module-level shutdown hook the app lifespan calls."""
    await manager.shutdown()


__all__ = [
    "CONTAINER_NAME",
    "DEFAULT_EMPTY_PROBE_DEGRADE_THRESHOLD",
    "DEFAULT_HEALTH_INTERVAL_SECS",
    "DEFAULT_HEALTH_TIMEOUT_SECS",
    "DEFAULT_HOST_PORT",
    "IMAGE",
    "PORT_PROBE_SPAN",
    "STATE_DEGRADED",
    "STATE_DOCKER_PRESENT_NOT_SETUP",
    "STATE_ERROR",
    "STATE_NOT_INSTALLED_DOCKER",
    "STATE_PULLING",
    "STATE_READY",
    "STATE_STARTING",
    "STATE_UNKNOWN",
    "DockerProbe",
    "EngineProbe",
    "SearxngManager",
    "manager",
    "reset_for_tests",
    "shutdown",
    "write_settings",
]

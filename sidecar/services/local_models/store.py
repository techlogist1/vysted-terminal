"""Models dir state: verified resumable downloads, installed models, Ollama.

Layout (R16 contract): ``<models dir>/<file>.gguf`` once verified, in flight
``<file>.gguf.part`` + ``<file>.gguf.part.json`` (url, sha256, totalBytes, etag).
A ``.gguf`` only ever appears via ``os.replace`` after its sha256 matched, so a
catalog file of the catalog size is trusted on rescan without rehashing.
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import hashlib
import json
import logging
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

import config
from models.local_models import DownloadState, InstalledModel, OllamaStatus
from services.local_models import catalog, engine

CHUNK = 1 << 20
DISK_CHECK_EVERY = 256 * 1024 * 1024
RETRIES = 3
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

logger = logging.getLogger(__name__)

NO_INTERNET = "No internet connection"
INTERRUPTED = "Download was interrupted — resume to continue"
CORRUPTED = "The download was corrupted — try again"
LINK_GONE = "The download link stopped working — try again later"
UNEXPECTED = "The download stopped unexpectedly — try again"


def _gb(n: int) -> str:
    return f"{n / 1e9:.1f} GB"


def disk_message(needed: int, free: int) -> str:
    return f"Not enough disk space (needs {_gb(needed)}, {_gb(free)} free)"


class DiskSpaceError(Exception):
    def __init__(self, needed: int, free: int) -> None:
        super().__init__(disk_message(needed, free))
        self.needed = needed
        self.free = free


class ActiveModelError(Exception):
    pass


class _Transient(Exception):
    pass


class _Fatal(Exception):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def _hash_into(path: Path, hasher: Any) -> None:
    with open(path, "rb") as fh:
        while block := fh.read(CHUNK):
            hasher.update(block)


def _unlink(*paths: Path) -> None:
    for p in paths:
        with contextlib.suppress(FileNotFoundError):
            p.unlink()


@dataclass
class _Job:
    offset: int = 0
    hasher: Any = field(default_factory=hashlib.sha256)

    def reset(self) -> None:
        self.offset, self.hasher = 0, hashlib.sha256()


class ModelStore:
    #: Seconds to wait before transient retry 1, 2, 3.
    backoff: tuple[float, ...] = (1.0, 4.0, 10.0)

    def __init__(
        self,
        models_dir: Path,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        disk_free: Callable[[], int] | None = None,
    ) -> None:
        self.dir = models_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._transport = transport
        self._disk_free = disk_free or (lambda: shutil.disk_usage(self.dir).free)
        self._states: dict[str, DownloadState] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._scan()

    # -- paths ---------------------------------------------------------------

    def _final(self, m: dict[str, Any]) -> Path:
        return self.dir / m["file"]

    def _part(self, m: dict[str, Any]) -> Path:
        return self.dir / f"{m['file']}.part"

    def _meta(self, m: dict[str, Any]) -> Path:
        return self.dir / f"{m['file']}.part.json"

    def _read_meta(self, m: dict[str, Any]) -> dict[str, Any] | None:
        try:
            meta = json.loads(self._meta(m).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return meta if isinstance(meta, dict) else None

    def _write_meta(self, m: dict[str, Any], etag: str | None) -> None:
        meta = {"url": m["url"], "sha256": m["sha256"], "totalBytes": m["sizeBytes"]}
        if etag:
            meta["etag"] = etag
        self._meta(m).write_text(json.dumps(meta), encoding="utf-8")

    def _scan(self) -> None:
        """Relaunch view: a recorded ``.part`` is a paused download."""
        for m in catalog.entries():
            meta = self._read_meta(m)
            if meta is None or self._final(m).exists():
                continue
            part = self._part(m)
            self._states[m["id"]] = DownloadState(
                id=m["id"],
                state="paused",
                receivedBytes=part.stat().st_size if part.exists() else 0,
                totalBytes=int(meta.get("totalBytes") or m["sizeBytes"]),
                error=INTERRUPTED,
                retryable=True,
            )

    # -- downloads -----------------------------------------------------------

    def downloads(self) -> list[DownloadState]:
        return list(self._states.values())

    def start(self, model_id: str) -> DownloadState:
        m = catalog.entry(model_id)
        if m is None:
            raise KeyError(model_id)
        task = self._tasks.get(model_id)
        if task is not None and not task.done():
            return self._states[model_id]
        final, part = self._final(m), self._part(m)
        if final.exists() and final.stat().st_size == m["sizeBytes"]:
            st = DownloadState(
                id=model_id,
                state="done",
                receivedBytes=m["sizeBytes"],
                totalBytes=m["sizeBytes"],
            )
            self._states[model_id] = st
            return st
        meta = self._read_meta(m)
        prev = self._states.get(model_id)
        not_resumable = prev is not None and prev.state == "failed" and not prev.retryable
        if not_resumable or meta is None or meta.get("sha256") != m["sha256"]:
            # No record, a .part of an older catalog pin, or a failure that said
            # the bytes can't be resumed: never splice files, start over.
            _unlink(part)
            meta = None
        have = part.stat().st_size if part.exists() else 0
        needed = m["diskNeededBytes"] - have
        free = self._disk_free()
        if free < needed:
            raise DiskSpaceError(needed, free)
        self._write_meta(m, (meta or {}).get("etag"))
        st = DownloadState(
            id=model_id, state="queued", receivedBytes=have, totalBytes=m["sizeBytes"]
        )
        self._states[model_id] = st
        self._tasks[model_id] = asyncio.create_task(self._run(m, st))
        return st

    async def cancel(self, model_id: str, discard: bool = False) -> DownloadState:
        m = catalog.entry(model_id)
        if m is None:
            raise KeyError(model_id)
        task = self._tasks.pop(model_id, None)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        part = self._part(m)
        st = self._states.get(model_id) or DownloadState(
            id=model_id,
            state="cancelled",
            receivedBytes=part.stat().st_size if part.exists() else 0,
            totalBytes=m["sizeBytes"],
        )
        if st.state != "done":
            st.state, st.bytesPerSec, st.error, st.retryable = "cancelled", None, None, True
        if discard:
            _unlink(part, self._meta(m))
            st.receivedBytes = 0
            self._states.pop(model_id, None)
        return st

    async def _run(self, m: dict[str, Any], st: DownloadState) -> None:
        part, total = self._part(m), m["sizeBytes"]
        # ``job`` is the single truth for bytes on disk + their running hash;
        # every attempt mutates it, so a retry resumes exactly where the file is.
        job = _Job(offset=part.stat().st_size if part.exists() else 0)
        try:
            if job.offset:
                await asyncio.to_thread(_hash_into, part, job.hasher)
            failures = 0
            while True:
                try:
                    await self._fetch(m, st, job)
                    break
                except _Transient as exc:
                    failures += 1
                    if failures > RETRIES:
                        st.state, st.error, st.retryable = "paused", str(exc), True
                        st.bytesPerSec = None
                        return
                    await asyncio.sleep(self.backoff[min(failures, len(self.backoff)) - 1])
            st.state, st.bytesPerSec = "verifying", None
            if job.offset != total or job.hasher.hexdigest() != m["sha256"]:
                _unlink(part, self._meta(m))
                st.state, st.receivedBytes, st.error, st.retryable = "failed", 0, CORRUPTED, True
                return
            os.replace(part, self._final(m))
            _unlink(self._meta(m))
            st.state, st.receivedBytes, st.error = "done", total, None
        except _Fatal as exc:
            st.state, st.error, st.retryable, st.bytesPerSec = (
                "failed",
                str(exc),
                exc.retryable,
                None,
            )
        except asyncio.CancelledError:
            st.state, st.bytesPerSec = "cancelled", None
            raise
        except Exception as exc:  # noqa: BLE001 — never leave a download stuck in flight
            # Type + errno only: str(exc) of an httpx error can carry the URL.
            logger.error(
                "download of %s stopped unexpectedly: %s (errno=%s)",
                m["id"],
                type(exc).__name__,
                getattr(exc, "errno", None),
            )
            st.state, st.error, st.retryable, st.bytesPerSec = "failed", UNEXPECTED, True, None

    async def _fetch(self, m: dict[str, Any], st: DownloadState, job: _Job) -> None:
        """One HTTP attempt from ``job.offset``; raises _Transient / _Fatal."""
        total, part = m["sizeBytes"], self._part(m)
        etag = (self._read_meta(m) or {}).get("etag")
        # Ranges + the hash are over the stored bytes: never let a proxy encode.
        headers: dict[str, str] = {"Accept-Encoding": "identity"}
        if job.offset:
            headers["Range"] = f"bytes={job.offset}-"
            if etag:
                headers["If-Range"] = etag
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, connect=10.0),
            ) as client:
                async with client.stream("GET", m["url"], headers=headers) as resp:
                    code = resp.status_code
                    if code == 416 and job.offset >= total:
                        return
                    if code == 429 or code >= 500:
                        raise _Transient(INTERRUPTED)
                    if code not in (200, 206):
                        raise _Fatal(LINK_GONE)
                    if code == 206:
                        got = resp.headers.get("content-range", "").removeprefix("bytes ")
                        if not got.startswith(f"{job.offset}-"):
                            if not job.offset:
                                raise _Fatal(LINK_GONE)
                            job.reset()
                            st.receivedBytes = 0
                            raise _Transient(INTERRUPTED)
                    elif job.offset:
                        # Server ignored the Range (or If-Range said the file
                        # changed): start over, never append a full body.
                        job.reset()
                    new_etag = resp.headers.get("etag")
                    if new_etag and not new_etag.startswith("W/") and new_etag != etag:
                        self._write_meta(m, new_etag)
                    st.state, st.error = "downloading", None
                    base, began = job.offset, time.monotonic()
                    next_check = job.offset + DISK_CHECK_EVERY
                    # ponytail: sync file write + hash per network chunk on the loop
                    # (sub-ms each); move to a writer thread if it shows in latency.
                    with open(part, "ab" if job.offset else "wb") as fh:
                        # aiter_raw, unbuffered: every byte received is on disk
                        # before a drop surfaces, so a resume never refetches it.
                        async for chunk in resp.aiter_raw():
                            fh.write(chunk)
                            job.hasher.update(chunk)
                            job.offset += len(chunk)
                            st.receivedBytes = job.offset
                            elapsed = max(time.monotonic() - began, 1e-3)
                            st.bytesPerSec = (job.offset - base) / elapsed
                            if job.offset > total:
                                raise _Fatal(CORRUPTED, retryable=True)
                            if job.offset >= next_check:
                                next_check += DISK_CHECK_EVERY
                                free = self._disk_free()
                                if free < total - job.offset:
                                    raise _Fatal(disk_message(total - job.offset, free), True)
        except httpx.ConnectError as exc:
            raise _Transient(NO_INTERNET) from exc
        except httpx.TransportError as exc:
            raise _Transient(INTERRUPTED) from exc
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                free = self._disk_free()
                raise _Fatal(disk_message(total - job.offset, free), True) from exc
            raise
        if job.offset < total:
            raise _Transient(INTERRUPTED)

    # -- installed -----------------------------------------------------------

    def installed(self) -> list[InstalledModel]:
        active = engine.active_model_id()
        known: dict[str, dict[str, Any]] = {m["file"]: m for m in catalog.entries()}
        out: list[InstalledModel] = []
        for path in sorted(self.dir.glob("*.gguf")):
            m = known.get(path.name)
            size = path.stat().st_size
            mid = m["id"] if m else path.stem
            out.append(
                InstalledModel(
                    id=mid,
                    name=m["name"] if m else path.stem,
                    path=str(path),
                    sizeBytes=size,
                    verified=bool(m) and size == m["sizeBytes"],
                    active=mid == active,
                )
            )
        return out

    async def delete(self, model_id: str) -> None:
        if model_id == engine.active_model_id():
            raise ActiveModelError(model_id)
        m = catalog.entry(model_id)
        if m is not None:
            await self.cancel(model_id, discard=True)
            target = self._final(m)
        else:
            target = self.dir / f"{model_id}.gguf"
            if target.parent != self.dir:
                raise KeyError(model_id)
        if not target.exists():
            if m is None:
                raise KeyError(model_id)
            return
        target.unlink()


# -- Ollama --------------------------------------------------------------------


def _ollama_models_root() -> Path:
    raw = os.environ.get("OLLAMA_MODELS")
    return Path(raw) if raw else Path.home() / ".ollama" / "models"


def ollama_blob_path(name: str, root: Path | None = None) -> Path | None:
    """GGUF blob behind an Ollama model name, read from its on-disk manifest.

    ``qwen2.5:7b`` -> manifests/registry.ollama.ai/library/qwen2.5/7b;
    ``user/m:t`` -> registry.ollama.ai/user/m/t; ``hf.co/o/r:t`` -> hf.co/o/r/t.
    """
    root = root or _ollama_models_root()
    repo, _, tag = name.partition(":")
    parts = repo.split("/")
    if len(parts) == 1:
        parts = ["registry.ollama.ai", "library", *parts]
    elif "." not in parts[0]:
        parts = ["registry.ollama.ai", *parts]
    if any(p in ("", ".", "..") for p in parts) or tag in (".", ".."):
        return None
    manifest = root.joinpath("manifests", *parts, tag or "latest")
    try:
        layers = json.loads(manifest.read_text(encoding="utf-8")).get("layers", [])
    except (OSError, ValueError, AttributeError):
        return None
    for layer in layers:
        if layer.get("mediaType") == "application/vnd.ollama.image.model":
            digest = str(layer.get("digest", ""))
            blob = root / "blobs" / digest.replace(":", "-")
            if digest.startswith("sha256:") and blob.is_file():
                return blob
    return None


async def ollama_status(
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[OllamaStatus, list[InstalledModel]]:
    """Ollama's pulled models (1 s budget). Each one whose GGUF blob resolves is
    also returned as an InstalledModel (``ollama:<name>``) the engine can load;
    every name stays usable through the ``ollama`` provider either way."""
    try:
        async with httpx.AsyncClient(transport=transport, timeout=1.0) as client:
            resp = await client.get(OLLAMA_TAGS_URL)
            resp.raise_for_status()
            names = [str(m["name"]) for m in resp.json().get("models", []) if m.get("name")]
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        return OllamaStatus(running=False, models=[]), []
    active = engine.active_model_id()
    usable: list[InstalledModel] = []
    for name in names:
        blob = await asyncio.to_thread(ollama_blob_path, name)
        if blob is not None:
            usable.append(
                InstalledModel(
                    id=f"ollama:{name}",
                    name=f"{name} (Ollama)",
                    path=str(blob),
                    sizeBytes=blob.stat().st_size,
                    verified=False,
                    active=f"ollama:{name}" == active,
                )
            )
    return OllamaStatus(running=True, models=names), usable


_store: ModelStore | None = None


def models_dir() -> Path:
    return config.get_data_dir() / "models"


def get_store() -> ModelStore:
    """Process-wide store for the current data dir (a new dir -> a fresh scan)."""
    global _store
    wanted = models_dir()
    if _store is None or _store.dir != wanted:
        _store = ModelStore(wanted)
    return _store

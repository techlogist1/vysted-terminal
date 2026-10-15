"""R16 local-model manager: catalog, verified resumable downloads, provider ``local``."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import socket
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from services.llm import LOCAL_NOT_RUNNING, get_provider
from services.local_models import catalog, engine, hardware, store

DATA = bytes(range(256)) * 12_000  # ~3 MB, every byte position distinct mod 256
SHA = hashlib.sha256(DATA).hexdigest()
URL = "https://models.example/resolve/abc/fake-Q4_K_M.gguf"
FILE = "fake-Q4_K_M.gguf"


def _fake_catalog(sha: str = SHA) -> dict[str, Any]:
    return {
        "recommendedByTier": {"under-8gb": "fake", "8gb": "fake", "16gb": "fake", "32gb": "fake"},
        "models": [
            {
                "id": "fake",
                "name": "Fake 1B",
                "family": "fake",
                "params": "1B",
                "quant": "Q4_K_M",
                "file": FILE,
                "url": URL,
                "sizeBytes": len(DATA),
                "sha256": sha,
                "minRamBytes": len(DATA) + 1,
                "diskNeededBytes": len(DATA) * 11 // 10,
                "licence": {
                    "id": "mit",
                    "name": "MIT",
                    "url": "https://opensource.org/license/mit",
                },
                "purpose": "A test model.",
            }
        ],
    }


@pytest.fixture(autouse=True)
def _fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VYSTED_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(catalog, "raw_catalog", lambda: _fake_catalog())
    monkeypatch.setattr(store.ModelStore, "backoff", (0.0, 0.0, 0.0))
    engine.set_engine(None, None)
    yield
    engine.set_engine(None, None)


class Server:
    """Range-aware fake host; ``drop_at`` cuts the FIRST body short with a read error."""

    def __init__(self, drop_at: int | None = None, stall: bool = False) -> None:
        self.drop_at = drop_at
        self.stall = stall
        self.requests: list[httpx.Request] = []
        self.served = 0

    async def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        start = 0
        rng = request.headers.get("range")
        if rng:
            start = int(re.match(r"bytes=(\d+)-", rng).group(1))  # type: ignore[union-attr]
        body = DATA[start:]
        drop = self.drop_at if len(self.requests) == 1 else None
        server = self

        async def stream():  # noqa: ANN202
            sent = 0
            for i in range(0, len(body), 65536):
                chunk = body[i : i + 65536]
                if drop is not None and start + sent + len(chunk) > drop:
                    chunk = chunk[: drop - start - sent]
                    server.served += len(chunk)
                    yield chunk
                    raise httpx.ReadError("connection dropped")
                sent += len(chunk)
                server.served += len(chunk)
                yield chunk
                if server.stall:
                    await asyncio.sleep(3600)

        headers = {"etag": '"strong-etag"'}
        if rng:
            headers["content-range"] = f"bytes {start}-{len(DATA) - 1}/{len(DATA)}"
            return httpx.Response(206, headers=headers, content=stream())
        return httpx.Response(200, headers=headers, content=stream())


def _store(tmp_path: Path, server: Server, free: int = 10**12) -> store.ModelStore:
    return store.ModelStore(
        tmp_path, transport=httpx.MockTransport(server.handler), disk_free=lambda: free
    )


async def _finish(s: store.ModelStore, model_id: str = "fake") -> None:
    task = s._tasks[model_id]
    await asyncio.wait_for(task, 10)


@pytest.mark.asyncio
async def test_full_download_verifies_and_renames(tmp_path: Path) -> None:
    srv = Server()
    s = _store(tmp_path, srv)
    st = s.start("fake")
    assert s.start("fake") is st  # idempotent while running
    await _finish(s)
    assert st.state == "done" and st.receivedBytes == len(DATA)
    assert (tmp_path / FILE).read_bytes() == DATA
    assert not (tmp_path / f"{FILE}.part").exists()
    assert not (tmp_path / f"{FILE}.part.json").exists()
    assert len(srv.requests) == 1
    [m] = s.installed()
    assert m.id == "fake" and m.verified and not m.active


@pytest.mark.asyncio
async def test_resume_after_drop_at_80_percent(tmp_path: Path) -> None:
    drop = int(len(DATA) * 0.8)
    srv = Server(drop_at=drop)
    s = _store(tmp_path, srv)
    st = s.start("fake")
    await _finish(s)
    assert st.state == "done"
    assert len(srv.requests) == 2
    assert srv.requests[1].headers["range"] == f"bytes={drop}-"
    assert srv.requests[1].headers["if-range"] == '"strong-etag"'
    assert srv.served == len(DATA)  # nothing before the drop came down twice
    assert hashlib.sha256((tmp_path / FILE).read_bytes()).hexdigest() == SHA


@pytest.mark.asyncio
async def test_checksum_mismatch_deletes_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(catalog, "raw_catalog", lambda: _fake_catalog(sha="0" * 64))
    s = _store(tmp_path, Server())
    st = s.start("fake")
    await _finish(s)
    assert st.state == "failed" and st.error == store.CORRUPTED and st.retryable
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_transient_errors_exhaust_to_paused_then_relaunch_resumes(tmp_path: Path) -> None:
    calls = 0

    async def refuse(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline")

    # A 40% .part (+ its record) left by an earlier session.
    half = int(len(DATA) * 0.4)
    (tmp_path / f"{FILE}.part").write_bytes(DATA[:half])
    (tmp_path / f"{FILE}.part.json").write_text(
        json.dumps({"url": URL, "sha256": SHA, "totalBytes": len(DATA)}), encoding="utf-8"
    )

    offline = store.ModelStore(
        tmp_path, transport=httpx.MockTransport(refuse), disk_free=lambda: 10**12
    )
    st = offline.start("fake")
    await _finish(offline)
    assert calls == store.RETRIES + 1
    assert st.state == "paused" and st.retryable and st.error == store.NO_INTERNET
    assert st.receivedBytes == half

    srv = Server()
    relaunched = _store(tmp_path, srv)
    [paused] = relaunched.downloads()
    assert paused.state == "paused" and paused.receivedBytes == half
    assert paused.totalBytes == len(DATA)
    assert round(100 * paused.receivedBytes / paused.totalBytes) == 40
    relaunched.start("fake")
    await _finish(relaunched)
    assert srv.requests[0].headers["range"] == f"bytes={half}-"
    assert (tmp_path / FILE).read_bytes() == DATA


@pytest.mark.asyncio
async def test_cancel_keeps_part_and_discard_removes(tmp_path: Path) -> None:
    s = _store(tmp_path, Server(stall=True))
    s.start("fake")
    for _ in range(200):
        if s._states["fake"].receivedBytes:
            break
        await asyncio.sleep(0.01)
    st = await s.cancel("fake")
    assert st.state == "cancelled"
    part = tmp_path / f"{FILE}.part"
    assert part.stat().st_size == 65536
    meta = json.loads((tmp_path / f"{FILE}.part.json").read_text(encoding="utf-8"))
    assert meta == {"url": URL, "sha256": SHA, "totalBytes": len(DATA), "etag": '"strong-etag"'}

    [paused] = _store(tmp_path, Server()).downloads()
    assert paused.state == "paused" and paused.receivedBytes == 65536

    await s.cancel("fake", discard=True)
    assert list(tmp_path.iterdir()) == []


def test_disk_short_is_409_before_any_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    srv = Server()
    s = _store(tmp_path, srv, free=1_000_000)
    monkeypatch.setattr(store, "get_store", lambda: s)
    resp = client.post("/local-models/fake/download")
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"] == "Not enough disk space (needs 0.0 GB, 0.0 GB free)"
    assert body["neededBytes"] == len(DATA) * 11 // 10 and body["freeBytes"] == 1_000_000
    assert srv.requests == []
    assert list(tmp_path.iterdir()) == []


def test_unknown_model_is_404(client: TestClient) -> None:
    assert client.post("/local-models/nope/download").status_code == 404
    assert client.post("/local-models/nope/cancel").status_code == 404


@pytest.mark.asyncio
async def test_ollama_absent_reports_not_running_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    monkeypatch.setattr(store, "OLLAMA_TAGS_URL", f"http://127.0.0.1:{port}/api/tags")
    began = time.monotonic()
    status, models = await store.ollama_status()
    assert time.monotonic() - began < 1.5
    assert status.running is False and status.models == [] and models == []


@pytest.mark.asyncio
async def test_ollama_models_resolve_to_gguf_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest = "a" * 64
    (tmp_path / "blobs").mkdir()
    (tmp_path / "blobs" / f"sha256-{digest}").write_bytes(b"GGUF")
    manifest = tmp_path / "manifests/registry.ollama.ai/library/qwen2.5/7b"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "layers": [
                    {
                        "mediaType": "application/vnd.ollama.image.model",
                        "digest": f"sha256:{digest}",
                    }
                ]
            }
        ),  # fmt: skip
        encoding="utf-8",
    )
    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path))

    def tags(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}, {"name": "x:y"}]})

    status, models = await store.ollama_status(transport=httpx.MockTransport(tags))
    assert status.running and status.models == ["qwen2.5:7b", "x:y"]
    [m] = models
    assert m.id == "ollama:qwen2.5:7b" and m.path == str(tmp_path / "blobs" / f"sha256-{digest}")
    assert store.ollama_blob_path("../../etc:passwd", tmp_path) is None


@pytest.mark.asyncio
async def test_delete_refuses_the_active_model(tmp_path: Path) -> None:
    (tmp_path / FILE).write_bytes(DATA)
    s = _store(tmp_path, Server())
    engine.set_engine(51234, "fake")
    assert s.installed()[0].active
    with pytest.raises(store.ActiveModelError):
        await s.delete("fake")
    engine.set_engine(None, None)
    await s.delete("fake")
    assert not (tmp_path / FILE).exists()


# -- provider ``local`` --------------------------------------------------------


def test_local_not_configured_without_engine(client: TestClient) -> None:
    resp = client.post("/llm/keys/validate", json={"provider": "local", "model": "qwen3.5-4b"})
    assert resp.json() == {"ok": False, "reason": "not_configured", "detail": LOCAL_NOT_RUNNING}


def test_engine_base_url_built_only_from_port(client: TestClient) -> None:
    resp = client.put(
        "/local-models/engine",
        json={"port": 51234, "modelId": "fake", "baseUrl": "http://evil.example/v1"},
    )
    assert resp.json() == {"baseUrl": "http://127.0.0.1:51234/v1", "modelId": "fake"}
    adapter = get_provider("local", base_url="http://evil.example/v1")
    assert adapter._client(None).base_url == httpx.URL("http://127.0.0.1:51234/v1/")
    assert client.put("/local-models/engine", json={"port": 0}).status_code == 422
    assert client.put("/local-models/engine", json={"port": 70000}).status_code == 422
    cleared = client.put("/local-models/engine", json={"port": None, "modelId": "fake"})
    assert cleared.json() == {"baseUrl": None, "modelId": None}


def test_local_provider_listed_without_key(client: TestClient) -> None:
    row = next(r for r in client.get("/llm/providers").json() if r["id"] == "local")
    assert row["label"] == "On this computer" and row["requires_key"] is False


# -- the real catalog ------------------------------------------------------------


def test_real_catalog_is_pinned_and_consistent() -> None:
    raw = json.loads(catalog._CATALOG_PATH.read_text(encoding="utf-8"))
    ids = {m["id"] for m in raw["models"]}
    assert 1 <= len(ids) <= 4
    assert set(raw["recommendedByTier"]) == {"under-8gb", "8gb", "16gb", "32gb"}
    assert set(raw["recommendedByTier"].values()) <= ids
    for m in raw["models"]:
        assert re.fullmatch(
            rf"https://huggingface\.co/[\w.-]+/[\w.-]+/resolve/[0-9a-f]{{40}}/{re.escape(m['file'])}",
            m["url"],
        )
        assert re.fullmatch(r"[0-9a-f]{64}", m["sha256"])
        assert m["licence"]["id"] in {"apache-2.0", "mit"}
        # Measured peak RSS (always above the file size) + 1 GiB, rounded up to 50 MB.
        assert m["minRamBytes"] >= m["sizeBytes"] + 1024**3
        assert m["minRamBytes"] % 50_000_000 == 0
        assert m["diskNeededBytes"] == math.ceil(m["sizeBytes"] * 1.1)
        assert m["purpose"].endswith(".")


def test_fits_and_tiers(client: TestClient) -> None:
    gib = 1024**3
    assert catalog.fits(6 * gib, 8 * gib) == "good"
    assert catalog.fits(7 * gib, 8 * gib) == "tight"
    assert catalog.fits(9 * gib, 8 * gib) == "too-big"
    assert hardware.tier_for(int(7.8 * gib)) == "8gb"  # Windows "8 GB" after reservations
    assert hardware.tier_for(4 * gib) == "under-8gb"
    assert hardware.tier_for(16 * gib) == "16gb"
    assert hardware.tier_for(64 * gib) == "32gb"
    body = client.get("/local-models/catalog").json()
    assert body["recommendedId"] == "fake" and body["models"][0]["fits"] == "good"
    assert "file" not in body["models"][0]
    hw = client.get("/local-models/hardware").json()
    assert hw["totalRamBytes"] > 0 and hw["freeDiskBytes"] > 0


@pytest.mark.asyncio
async def test_disk_filling_mid_download_fails_and_keeps_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "DISK_CHECK_EVERY", 1 << 20)
    frees = iter([10**12])  # the pre-start check passes; every later check is short
    s = store.ModelStore(
        tmp_path,
        transport=httpx.MockTransport(Server().handler),
        disk_free=lambda: next(frees, 1000),
    )
    st = s.start("fake")
    await _finish(s)
    assert st.state == "failed" and st.retryable
    assert st.error and st.error.startswith("Not enough disk space (needs ")
    assert (tmp_path / f"{FILE}.part").exists() and not (tmp_path / FILE).exists()


@pytest.mark.asyncio
async def test_unexpected_error_fails_retryably_then_try_again_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    real_replace = store.os.replace

    def locked(src: Any, dst: Any) -> None:
        raise PermissionError(13, "file in use")

    monkeypatch.setattr(store.os, "replace", locked)
    s = _store(tmp_path, Server())
    st = s.start("fake")
    await _finish(s)
    assert st.state == "failed" and st.retryable and st.error == store.UNEXPECTED
    assert st.bytesPerSec is None
    assert "PermissionError" in caplog.text and URL not in caplog.text

    monkeypatch.setattr(store.os, "replace", real_replace)
    again = s.start("fake")
    await _finish(s)
    assert again.state == "done"
    assert (tmp_path / FILE).read_bytes() == DATA


@pytest.mark.asyncio
async def test_non_transport_httpx_error_is_not_stuck_in_flight(tmp_path: Path) -> None:
    async def loop(request: httpx.Request) -> httpx.Response:
        raise httpx.TooManyRedirects("redirect loop", request=request)

    s = store.ModelStore(tmp_path, transport=httpx.MockTransport(loop), disk_free=lambda: 10**12)
    st = s.start("fake")
    await _finish(s)
    assert st.state == "failed" and st.retryable and st.error == store.UNEXPECTED


@pytest.mark.asyncio
async def test_non_resumable_failure_starts_over_on_try_again(tmp_path: Path) -> None:
    half = len(DATA) // 2
    (tmp_path / f"{FILE}.part").write_bytes(b"\0" * half)  # bytes a 404 says not to trust
    (tmp_path / f"{FILE}.part.json").write_text(
        json.dumps({"url": URL, "sha256": SHA, "totalBytes": len(DATA)}), encoding="utf-8"
    )
    s = store.ModelStore(
        tmp_path,
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
        disk_free=lambda: 10**12,
    )
    st = s.start("fake")
    await _finish(s)
    assert st.state == "failed" and not st.retryable and st.error == store.LINK_GONE

    srv = Server()
    s._transport = httpx.MockTransport(srv.handler)
    again = s.start("fake")
    await _finish(s)
    assert "range" not in srv.requests[0].headers
    assert again.state == "done"
    assert (tmp_path / FILE).read_bytes() == DATA

"""Provider ``local`` budgets against the bundled engine's real context size.

llama-server answers HTTP 400 past its ``-c``, so the sidecar reads ``n_ctx``
from ``/props`` when the engine's port is set and the provider declares a window
the runtime's chars/4 estimate cannot overrun.
"""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMUsage
from services import agent_runtime
from services.llm import LOCAL_TOKENS_PER_ESTIMATE, LocalEngineProvider, get_provider
from services.local_models import engine

PROPS = {"default_generation_settings": {"n_ctx": 24576}, "total_slots": 4}


@pytest.fixture(autouse=True)
def _reset_engine() -> Iterator[None]:
    engine.set_engine(None, None)
    yield
    engine.set_engine(None, None)


def _props(status: int = 200, body: Any = PROPS) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://127.0.0.1:51234/props"
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_n_ctx_reads_the_engine_props() -> None:
    assert await engine.fetch_n_ctx(51234, transport=_props()) == 24576


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "transport",
    [
        _props(500),
        _props(body={"default_generation_settings": {}}),
        _props(body={"default_generation_settings": {"n_ctx": "big"}}),
        _props(body=[1, 2]),
        httpx.MockTransport(lambda _r: httpx.Response(200, text="not json")),
    ],
)
async def test_fetch_n_ctx_is_none_when_props_is_unusable(transport: httpx.MockTransport) -> None:
    assert await engine.fetch_n_ctx(51234, transport=transport) is None


@pytest.mark.asyncio
async def test_fetch_n_ctx_is_none_when_the_engine_does_not_answer() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert await engine.fetch_n_ctx(51234, transport=httpx.MockTransport(refuse)) is None


def test_put_engine_keeps_n_ctx_beside_the_port_and_clears_it(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = engine.fetch_n_ctx
    monkeypatch.setattr(engine, "fetch_n_ctx", functools.partial(real, transport=_props()))
    client.put("/local-models/engine", json={"port": 51234, "modelId": "granite-4.2-3b"})
    assert engine.n_ctx() == 24576

    client.put("/local-models/engine", json={"port": None})
    assert engine._n_ctx is None
    assert engine.n_ctx() == engine.DEFAULT_N_CTX


def test_unreadable_props_assumes_the_rust_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = engine.fetch_n_ctx
    monkeypatch.setattr(engine, "fetch_n_ctx", functools.partial(real, transport=_props(503)))
    client.put("/local-models/engine", json={"port": 51234, "modelId": "granite-4.2-3b"})
    assert engine.n_ctx() == engine.DEFAULT_N_CTX == 16384


def test_local_window_is_the_engine_context_over_the_calibrated_factor() -> None:
    engine.set_engine(51234, "granite-4.2-3b", 24576)
    assert get_provider("local").context_window("granite-4.2-3b") == 24576 // 2
    assert LOCAL_TOKENS_PER_ESTIMATE == 2
    engine.set_engine(51234, "granite-4.2-3b")
    assert get_provider("local").context_window("x") == engine.DEFAULT_N_CTX // 2


def test_the_window_keeps_the_worst_measured_request_under_n_ctx() -> None:
    """The estimate never exceeds window - window/8; numeric tool JSON measured
    at up to 1.9 real tokens per estimated token (R16 calibration)."""
    for n_ctx in (8192, 16384, 24576, 32768):
        window = n_ctx // LOCAL_TOKENS_PER_ESTIMATE
        worst_real = (window - window // agent_runtime._ANSWER_RESERVE_SHARE) * 1.9
        assert worst_real < n_ctx


class _CapturingLocal(LocalEngineProvider):
    def __init__(self) -> None:
        super().__init__()
        self.tool_ids: list[str] | None = None

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        self.tool_ids = list(kwargs.get("tool_ids") or [])
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def _offered(
    monkeypatch: pytest.MonkeyPatch, n_ctx: int, hosted: bool = False
) -> tuple[list[str], Any]:
    engine.set_engine(51234, "granite-4.2-3b", n_ctx)
    provider = _CapturingLocal()
    if hosted:
        monkeypatch.setattr(provider, "context_window", lambda _m: None)
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    agent_runtime.reload()
    done = None
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot", prompt="What is Apple's price?", provider="local", mode="agent"
    ):
        if isinstance(event, LLMDoneEvent):
            done = event
    assert provider.tool_ids is not None
    return provider.tool_ids, done


@pytest.mark.asyncio
async def test_the_runtime_subsets_tools_on_the_bundled_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect: provider ``local`` was treated as a hosted lane and sent the
    full tool set (10.5k real tokens into an 8k engine)."""
    hosted, _ = await _offered(monkeypatch, 16384, hosted=True)
    offered, done = await _offered(monkeypatch, 16384)
    assert 0 < len(offered) < len(hosted)
    assert set(offered) <= set(hosted)
    assert done is not None and done.context_window == 8192


@pytest.mark.asyncio
async def test_a_large_engine_context_admits_the_full_tool_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hosted, _ = await _offered(monkeypatch, 131072, hosted=True)
    offered, _ = await _offered(monkeypatch, 131072)
    assert offered == hosted

# Critic fresh variant for R15-AGENT-074 (not part of the repo test suite).
import pytest
from models.run import RunBudget
from services import run_manager, runs_store
from services.budget_guard import estimate_spend_usd
from tests.test_run_manager import (  # noqa: F401
    _isolated, _patch, _await_terminal, _LoopingProvider, _OneShotProvider,
)


@pytest.mark.asyncio
async def test_providerless_ollama_default_is_free(monkeypatch):
    # copilot defaults to ollama/qwen2.5:7b (0 $/M); old code priced '' at 5 $/M.
    _patch(monkeypatch, _OneShotProvider())
    rid = run_manager.launch_run(agent_id="copilot", prompt="x", api_key=None)
    row = await _await_terminal(rid)
    assert row.status == "done", row.detail
    assert row.cost.tokens == 70
    assert row.cost.spend_usd == 0.0


@pytest.mark.asyncio
async def test_providerless_opus_default_breaches_on_round_one(monkeypatch):
    # 100k tokens at opus 30 $/M = $3 > $1 ceiling on round 1; at the old 5 $/M
    # fallback round 1 was $0.5 and the run would have taken a second round.
    prov = _LoopingProvider(per_round=100_000)
    _patch(monkeypatch, prov)
    rid = run_manager.launch_run(agent_id="buffett", prompt="x", api_key="sk",
                                 budget=RunBudget(max_spend_usd=1.0))
    row = await _await_terminal(rid)
    assert row.status == "error" and "spend ceiling" in (row.detail or ""), row.detail
    assert prov.calls == 1
    assert row.cost.spend_usd == round(estimate_spend_usd("anthropic", "claude-opus-4-8", 100_000), 6)


@pytest.mark.asyncio
async def test_resume_of_providerless_run_prices_at_resolved_provider(monkeypatch):
    prov = _LoopingProvider(per_round=100_000)
    _patch(monkeypatch, prov)
    rid = run_manager.launch_run(agent_id="buffett", prompt="x", api_key="sk",
                                 budget=RunBudget(max_spend_usd=1.0))
    row = await _await_terminal(rid)
    assert row.status == "error"
    before = row.cost.spend_usd
    assert runs_store.get_run(rid).provider in (None, "")  # launched provider-less
    _patch(monkeypatch, _OneShotProvider())
    run_manager.resume_run(rid, api_key="sk", budget=RunBudget(max_spend_usd=100.0))
    row = await _await_terminal(rid)
    assert row.status == "done", row.detail
    delta = round(row.cost.spend_usd - before, 6)
    assert delta == round(estimate_spend_usd("anthropic", "claude-opus-4-8", 70), 6), (before, row.cost)
    assert delta != round(estimate_spend_usd("", "claude-opus-4-8", 70), 6)

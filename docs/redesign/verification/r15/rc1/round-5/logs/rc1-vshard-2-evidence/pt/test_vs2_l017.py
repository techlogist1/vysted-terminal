import logging, pytest
from models.screener import ScreenerRequest, NumericThresholdCriterion
from services import screener
from services.errors import ProviderError
from tests.test_b5_screener import _install_v7, _fake_universe

@pytest.mark.asyncio
async def test_vs2_mixed_failures_25(monkeypatch, caplog):
    symbols = [f"S{i:02d}" for i in range(25)]
    _install_v7(symbols)
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe(symbols))
    async def adapter(symbol):
        i = int(symbol[1:])
        if i % 3 == 0: raise KeyError("trailingPE")
        if i % 3 == 1: raise TypeError("unsupported operand")
        raise ProviderError("not found", kind="not_found")
    monkeypatch.setattr("services.provider_registry.get_fundamentals", adapter)
    frames = []
    req = ScreenerRequest(universe="sp500", criteria=[NumericThresholdCriterion(field="roe", operator="gt", value=0.1)], limit=100)
    with caplog.at_level(logging.DEBUG, logger="services.screener"):
        res = await screener.run_screener(req, on_progress=lambda p, d, t, _x: frames.append((p, d, t)))
    warn = [r for r in caplog.records if r.levelno >= logging.WARNING and "unexpected enrichment error" in r.getMessage()]
    enrich = [(d, t) for p, d, t in frames if p == "enrich"]
    print("WARNINGS", len(warn), sorted({r.getMessage().split(': ')[1] for r in warn}))
    print("ENRICH FRAMES", enrich)
    assert len(warn) == 17  # 9 KeyError + 8 TypeError; the 8 not_found stay DEBUG
    assert enrich[-1] == (25, 25)

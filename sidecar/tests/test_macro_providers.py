"""Per-provider unit tests for the v0.6.0 macro providers (Teammate M).

Each upstream SDK (``fredapi``, ``ecbdata``, ``sdmx1``, ``wbgapi``) is
mocked at the module factory seam (``_make_client``) so no live network
call is ever issued. The tests cover (a) the wire-shape mapping from
upstream to :class:`MacroSeriesExtended`, (b) the error-translation
path (missing key / bad upstream → :class:`ProviderError`), and (c)
provider-specific id parsing where relevant.
"""

from __future__ import annotations

from typing import Any

import httpx
import pandas as pd
import pytest

from services.errors import ProviderError
from services.macro import (
    ecb_provider,
    fred_provider,
    imf_provider,
    world_bank_provider,
)

# ---------------------------------------------------------------------------
# FRED provider
# ---------------------------------------------------------------------------


class _FakeFred:
    """Stand-in for :class:`fredapi.Fred`."""

    def get_series(self, series_id: str) -> pd.Series:
        if series_id == "BADID":
            raise RuntimeError("FRED upstream said no")
        idx = pd.to_datetime(["2026-05-12", "2026-05-13", "2026-05-14"])
        return pd.Series([4.21, 4.25, float("nan")], index=idx, name=series_id)

    def get_series_info(self, series_id: str) -> pd.Series:
        return pd.Series(
            {
                "title": "10-Year Treasury Constant Maturity Rate",
                "units": "Percent",
                "frequency_short": "D",
                "seasonal_adjustment_short": "NSA",
                "last_updated": "2026-05-14 09:00:00-05",
                "notes": "Daily, not seasonally adjusted",
            }
        )

    def search(self, query: str, limit: int = 25) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "id": "DGS10",
                    "title": "10-Year Treasury",
                    "frequency_short": "D",
                    "units": "Percent",
                    "popularity": 95,
                },
                {
                    "id": "DGS2",
                    "title": "2-Year Treasury",
                    "frequency_short": "D",
                    "units": "Percent",
                    "popularity": 80,
                },
            ]
        )


@pytest.fixture
def fake_fred(monkeypatch: pytest.MonkeyPatch) -> _FakeFred:
    """Wire :class:`_FakeFred` in as the FRED client + populate the env key."""
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    fake = _FakeFred()
    monkeypatch.setattr(fred_provider, "_make_client", lambda: fake)
    return fake


def test_fred_get_series_maps_pandas_into_extended_shape(fake_fred: _FakeFred) -> None:
    series = fred_provider.get_series("DGS10")
    assert series.provider == "fred"
    assert series.series_id == "DGS10"
    assert series.title.startswith("10-Year")
    assert series.units == "Percent"
    assert series.frequency == "daily"
    assert series.seasonal_adjustment == "not-adjusted"
    assert series.last_updated is not None
    assert len(series.observations) == 3
    # NaN -> None
    assert series.observations[2].value is None
    # Real values pass through.
    assert series.observations[0].value == pytest.approx(4.21)


def test_fred_get_series_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    # R9 V8: the keyless detail is user-facing product copy — it must speak
    # Settings-language (free key, where to get it, keyless alternatives),
    # never the raw env-var name.
    with pytest.raises(ProviderError, match="needs a free API key") as excinfo:
        fred_provider.get_series("DGS10")
    assert "FRED_API_KEY" not in str(excinfo.value)


def test_fred_get_series_wraps_upstream_errors(fake_fred: _FakeFred) -> None:
    with pytest.raises(ProviderError, match="FRED upstream error"):
        fred_provider.get_series("BADID")


def test_fred_search_normalises_popularity_score(fake_fred: _FakeFred) -> None:
    results = fred_provider.search("treasury")
    assert len(results) == 2
    assert results[0].score == pytest.approx(0.95)
    assert results[1].score == pytest.approx(0.80)
    assert all(r.provider == "fred" for r in results)


def test_fred_search_empty_query_returns_empty() -> None:
    assert fred_provider.search("") == []


def test_fred_catalog_returns_curated_set(fake_fred: _FakeFred) -> None:
    cat = fred_provider.catalog()
    assert cat.provider == "fred"
    assert len(cat.entries) >= 5
    assert any(e.series_id == "DGS10" for e in cat.entries)


# ---------------------------------------------------------------------------
# ECB provider
# ---------------------------------------------------------------------------


class _FakeEcbModule:
    """Stand-in for :mod:`ecbdata`."""

    def __init__(self, payload: pd.DataFrame | None = None) -> None:
        self._payload = payload

    def get_series(self, series_id: str) -> pd.DataFrame:
        if series_id == "FAIL":
            raise RuntimeError("ECB upstream said no")
        if self._payload is not None:
            return self._payload
        return pd.DataFrame(
            [
                {"TIME_PERIOD": "2026-05-12", "OBS_VALUE": 4.0, "TITLE": "Main Refi Rate"},
                {"TIME_PERIOD": "2026-05-13", "OBS_VALUE": 4.0, "TITLE": "Main Refi Rate"},
                {"TIME_PERIOD": "2026-05-14", "OBS_VALUE": 3.75, "TITLE": "Main Refi Rate"},
            ]
        )


@pytest.fixture
def fake_ecb(monkeypatch: pytest.MonkeyPatch) -> _FakeEcbModule:
    fake = _FakeEcbModule()
    monkeypatch.setattr(ecb_provider, "_make_client", lambda: fake)
    return fake


def test_ecb_get_series_parses_observations(fake_ecb: _FakeEcbModule) -> None:
    series = ecb_provider.get_series("FM.D.U2.EUR.4F.KR.MRR_FR.LEV")
    assert series.provider == "ecb"
    assert series.frequency == "daily"  # second token of the key is "D"
    assert len(series.observations) == 3
    assert series.observations[-1].value == pytest.approx(3.75)
    assert series.title == "Main Refi Rate"


def test_ecb_get_series_wraps_upstream_errors(fake_ecb: _FakeEcbModule) -> None:
    with pytest.raises(ProviderError, match="ECB upstream error"):
        ecb_provider.get_series("FAIL")


def test_ecb_get_series_rejects_empty_id() -> None:
    with pytest.raises(ProviderError, match="non-empty"):
        ecb_provider.get_series("")


def test_ecb_search_against_curated_catalog_substring() -> None:
    results = ecb_provider.search("MRO")
    # The MRO entry title is "Main Refinancing Operations Rate (MRO) — daily".
    assert any(r.series_id.startswith("FM.D.U2.EUR") for r in results)


def test_ecb_search_empty_query_returns_empty() -> None:
    assert ecb_provider.search("") == []


def test_ecb_catalog_returns_curated_set(fake_ecb: _FakeEcbModule) -> None:
    cat = ecb_provider.catalog()
    assert cat.provider == "ecb"
    assert len(cat.entries) >= 5


# ---------------------------------------------------------------------------
# IMF provider
# ---------------------------------------------------------------------------


# A live SDMX 3.0 answer for CPI/USA.CPI._T.IX.M?lastNObservations=3, recorded
# 2026-09-24 and trimmed to the fields the parser reads (R15-UI-053).
_IMF_CPI_USA_MESSAGE: dict[str, Any] = {
    "meta": {},
    "data": {
        "dataSets": [
            {
                "structure": 0,
                "action": "Replace",
                "series": {
                    "0:0:0:0:0": {
                        "attributes": [0, None, 0, "2010A", "true"],
                        "observations": {
                            "0": ["153.150000802548", None, 0, "2010A", None],
                            "1": ["153.1344084418875", None, 0, "2010A", None],
                            "2": ["NaN", None, 0, "2010A", None],
                        },
                    }
                },
            }
        ],
        "structures": [
            {
                "dataSets": [0],
                "dimensions": {
                    "series": [
                        {"id": "COUNTRY", "keyPosition": 0, "values": [{"id": "USA"}]},
                        {"id": "INDEX_TYPE", "keyPosition": 1, "values": [{"id": "CPI"}]},
                        {"id": "COICOP_1999", "keyPosition": 2, "values": [{"id": "_T"}]},
                        {
                            "id": "TYPE_OF_TRANSFORMATION",
                            "keyPosition": 3,
                            "values": [{"id": "IX"}],
                        },
                        {"id": "FREQUENCY", "keyPosition": 4, "values": [{"id": "M"}]},
                    ],
                    "observation": [
                        {
                            "id": "TIME_PERIOD",
                            "keyPosition": 5,
                            "values": [
                                {"value": "2026-M06"},
                                {"value": "2026-M07"},
                                {"value": "2026-M08"},
                            ],
                        }
                    ],
                },
            }
        ],
    },
}

# What the API answers for a key the dataflow does not carry: 200, no series.
_IMF_EMPTY_MESSAGE: dict[str, Any] = {
    "meta": {},
    "data": {"dataSets": [{"structure": 0, "action": "Replace"}], "structures": [{}]},
}


@pytest.fixture
def fake_imf(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    def fetch(dataflow: str, key: str) -> dict[str, Any]:
        calls.append((dataflow, key))
        if key.startswith("FAIL"):
            request = httpx.Request("GET", "https://api.imf.org/x")
            raise httpx.ConnectError("IMF upstream said no", request=request)
        if key.startswith("ZZZ"):
            return _IMF_EMPTY_MESSAGE
        return _IMF_CPI_USA_MESSAGE

    monkeypatch.setattr(imf_provider, "_fetch", fetch)
    return calls


def test_imf_get_series_parses_a_recorded_sdmx3_message(fake_imf: list[tuple[str, str]]) -> None:
    series = imf_provider.get_series("CPI/USA.CPI._T.IX.M")
    assert series.provider == "imf"
    assert series.frequency == "monthly"
    assert series.title == "Consumer Price Index, monthly, United States"
    assert [o.date.date().isoformat() for o in series.observations] == [
        "2026-06-01",
        "2026-07-01",
        "2026-08-01",
    ]
    assert series.observations[1].value == pytest.approx(153.1344084418875)
    assert series.observations[2].value is None  # NaN -> None
    assert fake_imf == [("CPI", "USA.CPI._T.IX.M")]


def test_imf_period_formats_parse() -> None:
    assert imf_provider._parse_period("2031").month == 1
    assert imf_provider._parse_period("2026-Q2").month == 4
    assert imf_provider._parse_period("2026-M11").month == 11


def test_imf_get_series_wraps_upstream_errors(fake_imf: list[tuple[str, str]]) -> None:
    with pytest.raises(ProviderError, match="IMF upstream error") as info:
        imf_provider.get_series("CPI/FAIL.X.X")
    assert info.value.kind == "network"


def test_imf_unknown_key_is_not_found(fake_imf: list[tuple[str, str]]) -> None:
    with pytest.raises(ProviderError) as info:
        imf_provider.get_series("CPI/ZZZ.CPI._T.IX.M")
    assert info.value.kind == "not_found"


def test_imf_get_series_rejects_unparseable_key() -> None:
    with pytest.raises(ProviderError, match="must be"):
        imf_provider.get_series("notakey")


def test_imf_search_returns_curated_matches() -> None:
    results = imf_provider.search("GDP")
    assert results
    assert all(r.provider == "imf" for r in results)


def test_imf_search_empty_returns_empty() -> None:
    assert imf_provider.search("") == []


def test_imf_catalog_returns_curated_set() -> None:
    cat = imf_provider.catalog()
    assert cat.provider == "imf"
    assert len(cat.entries) >= 5
    # The retired SDMX 2.1 IFS dataflow answers 204/404 upstream (R15-UI-053).
    assert not any(e.series_id.startswith("IFS") for e in cat.entries)


# ---------------------------------------------------------------------------
# World Bank provider
# ---------------------------------------------------------------------------


class _FakeWbModule:
    """Stand-in for :mod:`wbgapi`."""

    class _Data:
        def fetch(self, indicator: str, country: str):
            if indicator == "FAIL":
                raise RuntimeError("WB upstream said no")
            yield {"economy": country, "series": indicator, "time": "YR2022", "value": 70000.0}
            yield {"economy": country, "series": indicator, "time": "YR2023", "value": 76329.6}
            yield {"economy": country, "series": indicator, "time": "YR2024", "value": None}

    class _Series:
        def info(self, indicator: str):
            class _Info:
                items: list = []

            return _Info()

        def list(self, q: str = ""):  # noqa: ARG002
            return iter([])

    data = _Data()
    series = _Series()


@pytest.fixture
def fake_wb(monkeypatch: pytest.MonkeyPatch) -> _FakeWbModule:
    fake = _FakeWbModule()
    monkeypatch.setattr(world_bank_provider, "_make_client", lambda: fake)
    return fake


def test_wb_get_series_default_country_usa(fake_wb: _FakeWbModule) -> None:
    series = world_bank_provider.get_series("NY.GDP.PCAP.CD")
    assert series.provider == "world-bank"
    assert series.frequency == "annual"
    assert len(series.observations) == 3
    assert series.observations[0].date.year == 2022
    assert series.observations[1].value == pytest.approx(76329.6)
    assert "USA" in series.title


def test_wb_get_series_explicit_country(fake_wb: _FakeWbModule) -> None:
    series = world_bank_provider.get_series("NY.GDP.PCAP.CD:DEU")
    assert "DEU" in series.title


def test_wb_bare_id_takes_the_region_country(fake_wb: _FakeWbModule) -> None:
    # R15-DATA-046: IN routes macro to World Bank for India series, but a bare
    # featured id used to read as USA. An explicit country still wins.
    assert world_bank_provider.get_series("NY.GDP.MKTP.KD.ZG", region="IN").title.endswith("IND")
    series = world_bank_provider.get_series("NY.GDP.MKTP.KD.ZG:DEU", region="IN")
    assert series.title.endswith("DEU")


def test_wb_get_series_with_wb_prefix(fake_wb: _FakeWbModule) -> None:
    series = world_bank_provider.get_series("WB:NY.GDP.PCAP.CD:GBR")
    assert "GBR" in series.title


def test_wb_get_series_wraps_upstream_errors(fake_wb: _FakeWbModule) -> None:
    with pytest.raises(ProviderError, match="World Bank upstream error"):
        world_bank_provider.get_series("FAIL")


def test_wb_get_series_titles_with_the_indicator_name(
    fake_wb: _FakeWbModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-DATA-085: wbgapi's ``series.info`` is a Featureset whose ``items`` is a
    list of dicts; the ``callable(info.items)`` guard left every title a raw code."""
    import wbgapi

    info = wbgapi.Featureset([{"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"}])
    monkeypatch.setattr(fake_wb.series, "info", lambda indicator: info)
    series = world_bank_provider.get_series("NY.GDP.MKTP.CD")
    assert series.title == "GDP (current US$) — USA"


def test_wb_search_falls_back_to_curated_catalog(fake_wb: _FakeWbModule) -> None:
    results = world_bank_provider.search("GDP")
    assert results
    assert all(r.provider == "world-bank" for r in results)


def test_wb_catalog_returns_curated_set(fake_wb: _FakeWbModule) -> None:
    cat = world_bank_provider.catalog()
    assert cat.provider == "world-bank"
    assert len(cat.entries) >= 5

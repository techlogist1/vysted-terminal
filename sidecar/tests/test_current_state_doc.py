"""Pins docs/CURRENT_STATE.md section 3.3 against code drift (R15-DOCS-017,
R15-DOCS-018).

Reads the code (the bundled sp500 pack, the ScreenerUniverseId literal, the
provider registry's region-scoped declarations) rather than hardcoding
numbers, so the doc and the code can only drift apart if this test is edited
alongside one of them without the other.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import get_args

from models.screener import ScreenerUniverseId
from services.provider_registry import _PROVIDERS

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC_PATH = _REPO_ROOT / "docs" / "CURRENT_STATE.md"


def _load_sp500_pack() -> dict:
    with (
        resources.files("services.screener_universes")
        .joinpath("sp500.json")
        .open("r", encoding="utf-8")
    ) as fp:
        return json.load(fp)


def _section_3_3() -> str:
    """The text of docs/CURRENT_STATE.md section 3.3, isolated from the rest
    of the doc so a name/number that only happens to appear elsewhere does
    not satisfy an assertion about this section."""
    text = _DOC_PATH.read_text(encoding="utf-8")
    match = re.search(r"### 3\.3 .*?\n(.*?)\n### 3\.4 ", text, flags=re.DOTALL)
    assert match is not None, "docs/CURRENT_STATE.md section 3.3 not found"
    return match.group(1)


def test_screener_bullet_names_current_sp500_size_and_snapshot() -> None:
    """R15-DOCS-017: the sp500 clause must quote the live pack's count and
    snapshot_date, and must not still cite the closed R15-LEAD-013 finding."""
    section = _section_3_3()
    pack = _load_sp500_pack()
    assert f"{len(pack['symbols'])} symbols" in section
    assert pack["snapshot_date"] in section
    assert "R15-LEAD-013 open" not in section


def test_screener_bullet_names_every_universe_id_in_backticks() -> None:
    """R15-DOCS-017: every ScreenerUniverseId literal except 'custom' (nse-all,
    bse-all, india-all were previously undocumented) is named in backticks."""
    section = _section_3_3()
    universe_ids = [uid for uid in get_args(ScreenerUniverseId) if uid != "custom"]
    assert universe_ids, "ScreenerUniverseId carries no literals to check"
    for uid in universe_ids:
        assert f"`{uid}`" in section, f"{uid!r} not named in backticks in section 3.3"


def test_region_scoped_providers_are_named_and_yfinance_is_region_qualified() -> None:
    """R15-DOCS-018: every ProviderDeclaration whose region includes IN has its
    id present in section 3.3, and the yfinance bullet no longer claims to be
    the unqualified default for equities (it is region-gated for IN)."""
    section = _section_3_3()
    in_provider_ids = [p.id for p in _PROVIDERS if "IN" in p.region]
    assert in_provider_ids, "no IN-region ProviderDeclaration found to check against"
    for provider_id in in_provider_ids:
        assert f"`{provider_id}`" in section, f"{provider_id!r} not named in section 3.3"

    yfinance_match = re.search(
        r"\*\*`yfinance_provider\.py`\*\*.*?(?=\n- \*\*|\Z)", section, flags=re.DOTALL
    )
    assert yfinance_match is not None, "yfinance_provider.py bullet not found in section 3.3"
    yfinance_bullet = yfinance_match.group(0)
    assert "IN" in yfinance_bullet, "yfinance bullet does not qualify its default role by region"

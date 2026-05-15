"""OpenBB ODP provider — Phase 2 wrap of the OpenBB Platform.

OpenBB-core 1.6.9 strictly pins fastapi (<0.129) and uvicorn (<0.41), which
are incompatible with the main Vysted sidecar's pins (fastapi 0.136, uvicorn
0.46). The Tier 1 in-process bundling path crashed `pnpm sidecar:build` at
the dependency-resolution step. This module ships the **Tier 2 (separate-
process)** path per plan §A2 + BLOCKERS-C.md: OpenBB lives in its own venv
under ``sidecar/openbb_subprocess/``, packaged as its own PyInstaller
``--onefile`` binary by ``scripts/ensure-openbb-sidecar.mjs``.

The provider lazily launches that binary on first OpenBB request and proxies
HTTP calls through. The subprocess inherits the standard stdin-EOF watchdog
shutdown pattern, so when the Tauri core drops the main sidecar's stdin the
main sidecar's stdin-EOF read returns, which closes the subprocess's stdin
in turn — full process tree shutdown without manual reaping.

The public callable surface (`get_quote`, `get_history`, etc.) is unchanged
from the Phase-1 stub's signatures and from what the Tier-1 attempt shipped,
so :mod:`services.provider_registry` and the OpenBB tests do not need to
follow the implementation pivot. Test fakes monkeypatch the cached ``_runner``
just as before — the ``Runner`` interface (a single ``sync_run(route, *,
provider_choices, standard_params, extra_params)`` method) is preserved.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any

import httpx

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import (
    MacroObservation,
    MacroSeries,
    OHLCVBar,
    OHLCVSeries,
    Quote,
)
from services.errors import ProviderError

PROVIDER = "openbb"

_log = logging.getLogger(__name__)

# Map Vysted timeframe ids to the subprocess's ``interval`` strings (mirrors
# the OpenBB equity router vocabulary).
_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "1wk": "1W",
    "1mo": "1M",
}

# How long we wait for the subprocess /health endpoint to respond before
# treating the launch as failed.
_HEALTH_TIMEOUT_S = 30.0
_HEALTH_POLL_INTERVAL_S = 0.25
_HTTP_TIMEOUT_S = 30.0

# Environment override for the subprocess binary path (CI / advanced users).
_BINARY_PATH_ENV = "VYSTED_OPENBB_SIDECAR"


# ---------------------------------------------------------------------------
# Subprocess discovery + launch
# ---------------------------------------------------------------------------


def _binary_name() -> str:
    """Return the OpenBB subprocess binary filename for the current platform."""
    return (
        "vysted-openbb-sidecar.exe" if platform.system() == "Windows" else "vysted-openbb-sidecar"
    )


def _candidate_binary_paths() -> list[Path]:
    """Return ordered candidate locations for the subprocess binary.

    The PyInstaller-built sidecar runs from a temporary `_MEIPASS` directory
    in `--onefile` mode, but Tauri places the binary in `src-tauri/binaries/`
    next to the main sidecar. The dev path uses `sidecar/openbb_subprocess/dist/`.
    """
    candidates: list[Path] = []
    env_override = os.environ.get(_BINARY_PATH_ENV)
    if env_override:
        candidates.append(Path(env_override))

    name = _binary_name()
    # Production / Tauri-bundled path: sibling of the main sidecar binary.
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / name)
    # Dev path: sidecar/openbb_subprocess/dist/<name>
    sidecar_dir = Path(__file__).resolve().parent.parent
    candidates.append(sidecar_dir / "openbb_subprocess" / "dist" / name)
    # Dev fallback: same dist/ as the main sidecar build
    candidates.append(sidecar_dir / "dist" / name)
    return candidates


def _find_binary() -> Path | None:
    """Return the first existing candidate binary, or ``None`` if none found."""
    for path in _candidate_binary_paths():
        if path.is_file():
            return path
    return None


def _free_port() -> int:
    """Bind to an ephemeral port, immediately release, and return it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# ---------------------------------------------------------------------------
# Runner — preserves the sync_run(route, *, provider_choices, ...) interface
# the in-process Tier-1 implementation used, so the test fixtures do not
# need to change.
# ---------------------------------------------------------------------------


class _SubprocessRunner:
    """Routes OpenBB calls through the subprocess HTTP API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._client = httpx.Client(base_url=base_url, timeout=_HTTP_TIMEOUT_S)

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass

    def sync_run(
        self,
        route: str,
        *,
        user: str = "",  # noqa: ARG002 - kept for interface parity
        provider_choices: dict[str, Any] | None = None,
        standard_params: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> Any:
        """Translate an OpenBB route into a subprocess HTTP call.

        Returns a ``SimpleNamespace`` whose ``.results`` attribute mimics the
        OpenBB ``OBBject.results`` list — keeps the call sites identical to
        the Tier-1 in-process attempt.
        """
        provider = (provider_choices or {}).get("provider", "yfinance")
        standard = standard_params or {}
        extra = extra_params or {}
        symbol = standard.get("symbol", "")

        try:
            if route == "/equity/price/quote":
                row = self._client.get(f"/quote/{symbol}").raise_for_status().json()
                return SimpleNamespace(results=[row], extra={})
            if route == "/equity/price/historical":
                params = {"interval": extra.get("interval", "1d")}
                if "start_date" in extra:
                    params["start_date"] = extra["start_date"]
                payload = (
                    self._client.get(f"/history/{symbol}", params=params).raise_for_status().json()
                )
                return SimpleNamespace(results=payload.get("bars", []), extra={})
            if route == "/equity/profile":
                row = self._client.get(f"/profile/{symbol}").raise_for_status().json()
                results = [row] if row else []
                return SimpleNamespace(results=results, extra={})
            if route == "/equity/fundamental/metrics":
                row = self._client.get(f"/metrics/{symbol}").raise_for_status().json()
                results = [row] if row else []
                return SimpleNamespace(results=results, extra={})
            if route == "/equity/fundamental/income":
                payload = (
                    self._client.get(f"/statement/{symbol}", params={"kind": "income"})
                    .raise_for_status()
                    .json()
                )
                return SimpleNamespace(results=payload.get("rows", []), extra={})
            if route == "/equity/fundamental/balance":
                payload = (
                    self._client.get(f"/statement/{symbol}", params={"kind": "balance"})
                    .raise_for_status()
                    .json()
                )
                return SimpleNamespace(results=payload.get("rows", []), extra={})
            if route == "/equity/fundamental/cash":
                payload = (
                    self._client.get(f"/statement/{symbol}", params={"kind": "cash"})
                    .raise_for_status()
                    .json()
                )
                return SimpleNamespace(results=payload.get("rows", []), extra={})
            if route == "/equity/estimates/price_target":
                row = self._client.get(f"/ratings/{symbol}").raise_for_status().json()
                results = [row] if row else []
                return SimpleNamespace(results=results, extra={})
            if route == "/economy/fred_series":
                payload = (
                    self._client.get(f"/macro/{symbol}", params={"provider": provider})
                    .raise_for_status()
                    .json()
                )
                return SimpleNamespace(
                    results=payload.get("observations", []),
                    extra={"results_metadata": {symbol: {"title": payload.get("title", "")}}},
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenBB subprocess call {route!r} failed: {exc}") from exc

        raise ProviderError(f"OpenBB subprocess does not support route {route!r}")


# ---------------------------------------------------------------------------
# Lifecycle — module-level cached process + runner.
# ---------------------------------------------------------------------------

_runner: Any = None
_subprocess: subprocess.Popen[bytes] | None = None
_runner_lock = Lock()
_OPENBB_AVAILABLE: bool | None = None  # None = not yet probed


def _probe_binary_present() -> bool:
    """Return whether the subprocess binary can be located on disk."""
    return _find_binary() is not None


def is_available() -> bool:
    """Return whether the OpenBB subprocess binary is locatable.

    Cached after first call so the registry's hot path is a dict lookup, not
    a filesystem walk. Tests reset by monkeypatching ``_OPENBB_AVAILABLE``.
    """
    global _OPENBB_AVAILABLE
    if _OPENBB_AVAILABLE is None:
        _OPENBB_AVAILABLE = _probe_binary_present()
    return bool(_OPENBB_AVAILABLE)


def _wait_for_health(base_url: str, deadline: float) -> bool:
    """Poll ``/health`` until OK or the deadline passes."""
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=2.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(_HEALTH_POLL_INTERVAL_S)
    return False


def _launch_subprocess() -> tuple[subprocess.Popen[bytes], str]:
    """Spawn the OpenBB subprocess and return (process handle, base URL)."""
    binary = _find_binary()
    if binary is None:
        raise ProviderError("OpenBB subprocess binary not found — run `pnpm openbb-sidecar:build`.")
    port = _free_port()
    proc = subprocess.Popen(  # noqa: S603 - binary path is module-controlled
        [str(binary), "--port", str(port)],
        stdin=subprocess.PIPE,  # gives the subprocess an EOF watchdog
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + _HEALTH_TIMEOUT_S
    if not _wait_for_health(base_url, deadline):
        try:
            proc.terminate()
        except Exception:  # noqa: BLE001
            pass
        raise ProviderError(
            f"OpenBB subprocess at {base_url} did not become healthy within {_HEALTH_TIMEOUT_S}s."
        )
    _log.info("OpenBB subprocess ready at %s (pid=%s)", base_url, proc.pid)
    return proc, base_url


def _get_runner() -> Any:
    """Return a cached :class:`_SubprocessRunner`, lazy-launching on first use."""
    global _runner, _subprocess
    if not is_available():
        raise ProviderError(
            "OpenBB subprocess is not bundled in this build — falling back to yfinance."
        )
    with _runner_lock:
        if _runner is None:
            _subprocess, base_url = _launch_subprocess()
            _runner = _SubprocessRunner(base_url)
        return _runner


def shutdown() -> None:
    """Tear down the subprocess (called on sidecar shutdown).

    Closing the runner's HTTP client and dropping the subprocess's stdin
    triggers its stdin-EOF watchdog, which is the canonical exit path. Falls
    back to ``terminate()`` if the polite path does not work in 2 s.
    """
    global _runner, _subprocess
    with _runner_lock:
        if _runner is not None:
            _runner.close()
            _runner = None
        if _subprocess is not None:
            try:
                if _subprocess.stdin is not None:
                    _subprocess.stdin.close()
                _subprocess.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                _subprocess.terminate()
                try:
                    _subprocess.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    _subprocess.kill()
            except Exception:  # noqa: BLE001
                pass
            _subprocess = None


# ---------------------------------------------------------------------------
# Helpers — shared across the public accessors.
# ---------------------------------------------------------------------------


def _normalize_symbol(symbol: str) -> str:
    """Mirror yfinance's dot-ticker fix at the OpenBB seam."""
    return symbol.replace(".", "-").upper()


def _run(
    route: str,
    *,
    provider: str,
    standard_params: dict[str, Any] | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Any:
    """Execute an OpenBB route and unwrap the ``OBBject``-shaped result."""
    runner = _get_runner()
    try:
        return runner.sync_run(
            route,
            user="",
            provider_choices={"provider": provider},
            standard_params=standard_params or {},
            extra_params=extra_params or {},
        )
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"OpenBB call {route!r} failed: {exc}") from exc


def _model_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return dict(item.model_dump())
    if isinstance(item, dict):
        return dict(item)
    return {}


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if hasattr(value, "isoformat"):
        return datetime.fromisoformat(value.isoformat()).replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(tz=UTC)


# Default upstream provider per data class. The user-visible provider field on
# returned models is always ``"openbb"`` regardless — the upstream choice is
# an implementation detail.
_DEFAULT_PROVIDERS = {
    "quote": "yfinance",
    "history": "yfinance",
    "fundamentals": "yfinance",
    "income": "yfinance",
    "balance": "yfinance",
    "cashflow": "yfinance",
    "ratings": "yfinance",
    "macro": "fred",
}


# ---------------------------------------------------------------------------
# Public accessors — match yfinance_provider's surface for drop-in dispatch.
# ---------------------------------------------------------------------------


def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    result = _run(
        "/equity/price/quote",
        provider=_DEFAULT_PROVIDERS["quote"],
        standard_params={"symbol": normalized},
    )
    rows = getattr(result, "results", None) or []
    if not rows:
        raise ProviderError(f"OpenBB quote returned no rows for {symbol!r}")
    row = _model_to_dict(rows[0])

    price = _coerce_float(row.get("last_price") or row.get("close"))
    prev = _coerce_float(row.get("prev_close") or row.get("previous_close"))
    change = _coerce_float(row.get("change"))
    change_percent = _coerce_float(row.get("change_percent"))
    if price is None:
        raise ProviderError(f"OpenBB quote missing price for {symbol!r}")
    if change is None and prev is not None:
        change = price - prev
    if change_percent is None and prev:
        change_percent = ((price - prev) / prev) * 100.0

    return Quote(
        symbol=normalized,
        price=price,
        change=change or 0.0,
        change_percent=change_percent or 0.0,
        volume=_coerce_float(row.get("volume") or row.get("exchange_volume")),
        currency=str(row.get("currency") or "USD"),
        timestamp=_ensure_datetime(row.get("last_timestamp") or row.get("date")),
        provider=PROVIDER,
    )


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    interval = _TIMEFRAME_MAP.get(timeframe, "1d")
    extra: dict[str, Any] = {"interval": interval}
    if range_ and len(range_) >= 8 and range_[4] == "-":
        extra["start_date"] = range_

    result = _run(
        "/equity/price/historical",
        provider=_DEFAULT_PROVIDERS["history"],
        standard_params={"symbol": normalized},
        extra_params=extra,
    )
    rows = getattr(result, "results", None) or []
    bars: list[OHLCVBar] = []
    for raw in rows:
        row = _model_to_dict(raw)
        try:
            bars.append(
                OHLCVBar(
                    timestamp=_ensure_datetime(row.get("date") or row.get("timestamp")),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return OHLCVSeries(symbol=normalized, timeframe=timeframe, bars=bars, provider=PROVIDER)


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    profile_rows: list[Any] = []
    try:
        profile = _run(
            "/equity/profile",
            provider=_DEFAULT_PROVIDERS["fundamentals"],
            standard_params={"symbol": normalized},
        )
        profile_rows = getattr(profile, "results", None) or []
    except ProviderError:
        profile_rows = []
    profile_row = _model_to_dict(profile_rows[0]) if profile_rows else {}

    metric_rows: list[Any] = []
    try:
        metric = _run(
            "/equity/fundamental/metrics",
            provider=_DEFAULT_PROVIDERS["fundamentals"],
            standard_params={"symbol": normalized},
        )
        metric_rows = getattr(metric, "results", None) or []
    except ProviderError:
        metric_rows = []
    metric_row = _model_to_dict(metric_rows[0]) if metric_rows else {}

    if not profile_row and not metric_row:
        raise ProviderError(f"OpenBB fundamentals returned no rows for {symbol!r}")

    raw_yield = _coerce_float(metric_row.get("dividend_yield"))
    return Fundamentals(
        symbol=normalized,
        name=profile_row.get("name") or profile_row.get("long_name"),
        sector=profile_row.get("sector"),
        industry=profile_row.get("industry_category") or profile_row.get("industry"),
        market_cap=_coerce_float(profile_row.get("market_cap") or metric_row.get("market_cap")),
        pe_ratio=_coerce_float(metric_row.get("pe_ratio") or metric_row.get("trailing_pe")),
        forward_pe=_coerce_float(metric_row.get("forward_pe")),
        peg_ratio=_coerce_float(metric_row.get("peg_ratio")),
        price_to_book=_coerce_float(metric_row.get("price_to_book")),
        # OpenBB providers return dividend_yield as a fraction already
        # (`0.0036` for AAPL), unlike yfinance 1.3.0 which returns a
        # percentage number. No /100 here.
        dividend_yield=raw_yield,
        eps=_coerce_float(metric_row.get("eps") or metric_row.get("trailing_eps")),
        beta=_coerce_float(profile_row.get("beta") or metric_row.get("beta")),
        fifty_two_week_high=_coerce_float(
            profile_row.get("year_high") or metric_row.get("fifty_two_week_high")
        ),
        fifty_two_week_low=_coerce_float(
            profile_row.get("year_low") or metric_row.get("fifty_two_week_low")
        ),
        provider=PROVIDER,
    )


def _statement_lines(rows: list[dict[str, Any]]) -> tuple[list[str], list[StatementLine]]:
    """Pivot a list-of-rows OpenBB statement payload into (periods, lines)."""
    periods: list[str] = []
    seen_periods: set[str] = set()
    for row in rows:
        period = str(row.get("period_ending") or row.get("date") or row.get("fiscal_year") or "")
        if period and period not in seen_periods:
            periods.append(period)
            seen_periods.add(period)

    lines_by_label: dict[str, dict[str, float | None]] = {}
    for row in rows:
        period = str(row.get("period_ending") or row.get("date") or row.get("fiscal_year") or "")
        if not period:
            continue
        for key, value in row.items():
            if key in {"symbol", "period_ending", "date", "fiscal_year", "period", "cik"}:
                continue
            coerced = _coerce_float(value)
            if coerced is None and value is not None and not isinstance(value, (int, float)):
                continue
            slot = lines_by_label.setdefault(key, {})
            slot[period] = coerced

    lines = [StatementLine(label=label, values=values) for label, values in lines_by_label.items()]
    return periods, lines


def _financial_statement(symbol: str, route: str) -> tuple[list[str], list[StatementLine]]:
    """Fetch a financial-statement route and pivot it to (periods, lines)."""
    normalized = _normalize_symbol(symbol)
    result = _run(
        route,
        provider=_DEFAULT_PROVIDERS["income"],
        standard_params={"symbol": normalized},
    )
    rows = [_model_to_dict(r) for r in (getattr(result, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB {route} returned no rows for {symbol!r}")
    return _statement_lines(rows)


def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income-statement excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/income")
    return IncomeStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance-sheet excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/balance")
    return BalanceSheet(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow-statement excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/cash")
    return CashFlowStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    try:
        estimates = _run(
            "/equity/estimates/price_target",
            provider=_DEFAULT_PROVIDERS["ratings"],
            standard_params={"symbol": normalized},
        )
    except ProviderError as exc:
        raise ProviderError(f"OpenBB analyst rating failed for {symbol!r}: {exc}") from exc
    rows = [_model_to_dict(r) for r in (getattr(estimates, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB analyst rating returned no rows for {symbol!r}")
    row = rows[0]
    return AnalystRating(
        symbol=normalized,
        consensus=str(row.get("consensus") or row.get("rating") or "") or None,
        target_mean=_coerce_float(row.get("target_mean") or row.get("price_target_mean")),
        target_high=_coerce_float(row.get("target_high") or row.get("price_target_high")),
        target_low=_coerce_float(row.get("target_low") or row.get("price_target_low")),
        strong_buy=int(_coerce_float(row.get("strong_buy")) or 0),
        buy=int(_coerce_float(row.get("buy")) or 0),
        hold=int(_coerce_float(row.get("hold")) or 0),
        sell=int(_coerce_float(row.get("sell")) or 0),
        strong_sell=int(_coerce_float(row.get("strong_sell")) or 0),
        provider=PROVIDER,
    )


def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style) via OpenBB."""
    upstream = provider or _DEFAULT_PROVIDERS["macro"]
    result = _run(
        "/economy/fred_series",
        provider=upstream,
        standard_params={"symbol": series_id},
    )
    rows = [_model_to_dict(r) for r in (getattr(result, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB macro series returned no rows for {series_id!r}")

    title = ""
    metadata = getattr(result, "extra", None) or {}
    if isinstance(metadata, dict):
        info = metadata.get("results_metadata") or {}
        if isinstance(info, dict):
            entry = info.get(series_id) or next(iter(info.values()), {})
            if isinstance(entry, dict):
                title = str(entry.get("title") or "")

    observations: list[MacroObservation] = []
    for row in rows:
        date = row.get("date")
        value = _coerce_float(row.get("value") or row.get(series_id))
        if date is None:
            continue
        observations.append(MacroObservation(date=_ensure_datetime(date), value=value))

    return MacroSeries(
        series_id=series_id,
        title=title or series_id,
        units=None,
        observations=observations,
        provider=PROVIDER,
    )

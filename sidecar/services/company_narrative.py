"""Company-overview AI narrative WITH a numeric-verification pass.

The promise of this service: **every number that reaches the UI has been checked
against the real source data.** A finance terminal cannot ship hallucinated
figures — a confidently-wrong "$4.2T market cap" is worse than no narrative at
all. So the flow is:

1. Fetch the SAME real :class:`~models.fundamentals.Fundamentals` +
   :class:`~models.market.Quote` the equity-overview panel renders.
2. Ask the configured BYOK model for a tight 2–4 sentence narrative + 2–4 key
   insights, with the real numbers handed to it in the prompt and a hard
   instruction to use ONLY those figures (no external/recalled/invented data).
3. **Numeric-verification pass** (the load-bearing part): extract every numeric
   claim from the model's output, normalise it (handling ``$``, ``%``, K/M/B/T
   suffixes, ``x`` ratio markers, commas), and match it against the source
   values within a sensible tolerance. Any claim that matches NOTHING is treated
   as a likely hallucination — it is REDACTED from the prose and recorded in
   ``unverified_claims`` so a fabricated figure never renders as fact.

The model never reads the keychain — the BYOK key arrives on the request (a
header for this read-only GET path) and is held in memory for the call only. No
key / no model output → a graceful ``200`` with ``summary=None`` + a ``reason``,
never a ``500``.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import UTC, datetime

from models.fundamentals import CompanyNarrative, Fundamentals, UnverifiedClaim
from models.market import Quote
from services import provider_registry
from services.llm.oneshot import complete

logger = logging.getLogger(__name__)

# A single LLM call gates the whole panel section — keep it snappy so a slow
# "thinking" model never wedges the overview. The oneshot helper returns the
# partial text on timeout, which the verifier still vets.
_LLM_TIMEOUT_SECS = 30.0

# Verification tolerances. Large currency sizes (market cap, revenue) are
# rounded heavily by both the source display and the model, so a RELATIVE
# tolerance fits; small ratios (P/E, beta) need a tight ABSOLUTE tolerance so
# "31" vs "37" never both "match" 31.5.
_REL_TOLERANCE = 0.02  # 2% — covers rounding of B/T-scale figures
_ABS_TOLERANCE = 0.06  # absolute slack for ratios / small values / percents

# Magnitude suffixes the model (and humans) use for large numbers.
_SUFFIX_SCALE: dict[str, float] = {
    "k": 1e3,
    "m": 1e6,
    "b": 1e9,
    "t": 1e12,
}

# Matches a numeric token, optionally money-prefixed, with optional thousands
# separators, optional decimal, optional magnitude suffix (K/M/B/T), optional
# percent sign, and optional trailing "x" ratio marker. Examples it catches:
#   "$2.95T"  "31.5"  "21.3%"  "1,234,567"  "0.21"  "37x"  "-4.2%"  "$4.20"
_NUMBER_RE = re.compile(
    r"""
    (?P<dollar>\$)?                       # optional leading $
    (?P<sign>[-+])?                       # optional sign
    (?P<num>\d{1,3}(?:,\d{3})+|\d+)       # 1,234,567  OR  bare digits
    (?P<frac>\.\d+)?                      # optional decimal part
    (?:
        (?P<suffix>[KkMmBbTt])(?![A-Za-z])  # magnitude suffix, only if NOT mid-word
      | (?P<pct>%)                          # percent sign
      | (?P<ratio>[xX])(?![A-Za-z])         # ratio marker (37x), not mid-word
    )?
    """,
    re.VERBOSE,
)


def _close(a: float, b: float) -> bool:
    """True when ``a`` matches ``b`` within the relative OR absolute tolerance.

    The relative band handles heavily-rounded large figures (a model writing
    "$2.95T" against a 2,948,300,000,000 source); the absolute band handles
    small ratios and percentages where a relative band would be too loose
    (P/E 31.5 vs 31 is fine; 31.5 vs 37 is not).
    """
    if a == b:
        return True
    diff = abs(a - b)
    if diff <= _ABS_TOLERANCE:
        return True
    scale = max(abs(a), abs(b))
    return scale > 0 and diff / scale <= _REL_TOLERANCE


def _source_values(fundamentals: Fundamentals | None, quote: Quote | None) -> list[float]:
    """Collect every checkable numeric value from the source data.

    For each underlying figure we add MULTIPLE legitimate representations so the
    verifier accepts whichever form the model chose:

    * the raw value (e.g. ``2948300000000.0``)
    * its magnitude-scaled form (``2.9483`` for the "$2.95T" the model writes —
      the regex strips the suffix, so the bare mantissa must be in the set)
    * for fractions (margins, yields, growth, ownership) BOTH the fraction
      (``0.213``) and the percent (``21.3``), because the model may phrase a
      0.213 source as "21.3%".

    Returning a flat list (not a dict) is deliberate: the model is not required
    to attribute a number to the right label — it only has to state a number the
    data actually contains. That is the right bar for "did it invent this?".
    """
    values: list[float] = []

    def add(v: float | None) -> None:
        if v is None or not math.isfinite(v):
            return
        values.append(float(v))
        # Scaled mantissa forms — "2.95T" parses to 2.95, so 2.95e12 must also be
        # reachable as 2.95 / 2.948 / etc.
        av = abs(v)
        for scale in (1e3, 1e6, 1e9, 1e12):
            if av >= scale:
                values.append(float(v) / scale)

    def add_fraction(v: float | None) -> None:
        """A fraction field: accept both 0.21 and the 21(.x) percent form."""
        if v is None or not math.isfinite(v):
            return
        values.append(float(v))
        values.append(float(v) * 100.0)

    if quote is not None:
        add(quote.price)
        add(quote.change)
        add_fraction(quote.change_percent / 100.0)  # change_percent is already a percent
        values.append(quote.change_percent)
        add(quote.volume)

    if fundamentals is not None:
        # Plain numeric / ratio fields.
        for v in (
            fundamentals.market_cap,
            fundamentals.pe_ratio,
            fundamentals.forward_pe,
            fundamentals.peg_ratio,
            fundamentals.price_to_book,
            fundamentals.price_to_sales,
            fundamentals.ev_to_ebitda,
            fundamentals.book_value,
            fundamentals.dividend_per_share,
            fundamentals.eps,
            fundamentals.beta,
            fundamentals.fifty_two_week_high,
            fundamentals.fifty_two_week_low,
            fundamentals.debt_to_equity,
            fundamentals.current_ratio,
            fundamentals.quick_ratio,
            fundamentals.revenue_ttm,
            fundamentals.net_income_ttm,
            fundamentals.free_cash_flow,
            fundamentals.shares_outstanding,
        ):
            add(v)
        # Fraction fields — the model may state either form.
        for f in (
            fundamentals.dividend_yield,
            fundamentals.fifty_two_week_change,
            fundamentals.roe,
            fundamentals.roa,
            fundamentals.gross_margin,
            fundamentals.operating_margin,
            fundamentals.profit_margin,
            fundamentals.revenue_growth,
            fundamentals.earnings_growth,
            fundamentals.held_percent_insiders,
            fundamentals.held_percent_institutions,
        ):
            add_fraction(f)

    return values


def _normalise_token(match: re.Match[str]) -> float | None:
    """Turn one regex match into the canonical float to compare against source.

    A magnitude suffix scales the mantissa (``2.95`` + ``T`` → ``2.95e12``); a
    percent sign is left as the displayed percent number (``21.3%`` → ``21.3``)
    because the source set carries both the fraction and the percent form. The
    ratio ``x`` marker is informational only (``37x`` → ``37``).
    """
    raw = (match.group("num") or "").replace(",", "")
    if not raw:
        return None
    frac = match.group("frac") or ""
    try:
        value = float(raw + frac)
    except ValueError:
        return None
    if match.group("sign") == "-":
        value = -value
    suffix = match.group("suffix")
    if suffix:
        value *= _SUFFIX_SCALE[suffix.lower()]
    return value


def _verify_text(text: str, source: list[float]) -> tuple[str, list[UnverifiedClaim]]:
    """Redact every numeric claim in ``text`` that matches no source value.

    Walks the text left-to-right, and for each numeric token either keeps it (it
    matched a source figure within tolerance) or replaces the whole token with a
    neutral ``[unverified]`` marker and records the original. Years (a bare
    4-digit 19xx/20xx with no suffix/percent/decimal) are left alone — they are
    dates, not financial claims, and the source set never carries them.
    """
    unverified: list[UnverifiedClaim] = []
    out: list[str] = []
    cursor = 0
    for match in _NUMBER_RE.finditer(text):
        token = match.group(0)
        out.append(text[cursor : match.start()])
        cursor = match.end()

        value = _normalise_token(match)
        is_yearlike = (
            value is not None
            and not match.group("suffix")
            and not match.group("pct")
            and not match.group("frac")
            and not match.group("dollar")
            and 1900 <= value <= 2099
        )
        if value is None or is_yearlike or any(_close(value, s) for s in source):
            out.append(token)
            continue

        # Unverified — redact and record.
        out.append("[unverified]")
        unverified.append(
            UnverifiedClaim(
                text=token.strip(),
                reason="no source fundamental or quote value matched within tolerance",
            )
        )
    out.append(text[cursor:])
    return "".join(out), unverified


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _fmt(value: float | None, *, pct: bool = False, money: bool = False) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    if pct:
        return f"{value * 100:.2f}%"
    if money:
        av = abs(value)
        for suffix, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
            if av >= scale:
                return f"{value / scale:.2f}{suffix}"
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _build_facts(fundamentals: Fundamentals | None, quote: Quote | None) -> list[str]:
    """The numeric ground-truth block handed to the model — ONLY these figures
    may appear in the narrative."""
    facts: list[str] = []
    if quote is not None:
        facts.append(f"Last price: {_fmt(quote.price)} {quote.currency}")
        facts.append(f"Daily change: {_fmt(quote.change_percent)}%")
    if fundamentals is not None:
        f = fundamentals
        pairs: list[tuple[str, str]] = [
            ("Market cap", _fmt(f.market_cap, money=True)),
            ("P/E", _fmt(f.pe_ratio)),
            ("Forward P/E", _fmt(f.forward_pe)),
            ("PEG", _fmt(f.peg_ratio)),
            ("Price/Book", _fmt(f.price_to_book)),
            ("Price/Sales", _fmt(f.price_to_sales)),
            ("EV/EBITDA", _fmt(f.ev_to_ebitda)),
            ("EPS", _fmt(f.eps)),
            ("Beta", _fmt(f.beta)),
            ("Dividend yield", _fmt(f.dividend_yield, pct=True)),
            ("ROE", _fmt(f.roe, pct=True)),
            ("ROA", _fmt(f.roa, pct=True)),
            ("Gross margin", _fmt(f.gross_margin, pct=True)),
            ("Operating margin", _fmt(f.operating_margin, pct=True)),
            ("Net margin", _fmt(f.profit_margin, pct=True)),
            ("Debt/Equity", _fmt(f.debt_to_equity)),
            ("Current ratio", _fmt(f.current_ratio)),
            ("Revenue (TTM)", _fmt(f.revenue_ttm, money=True)),
            ("Net income (TTM)", _fmt(f.net_income_ttm, money=True)),
            ("Free cash flow", _fmt(f.free_cash_flow, money=True)),
            # D55: yfinance growth is MRQ-YoY, not annual — label the basis so
            # the LLM never narrates it as full-year growth.
            ("Revenue growth (quarterly YoY)", _fmt(f.revenue_growth, pct=True)),
            ("Earnings growth (quarterly YoY)", _fmt(f.earnings_growth, pct=True)),
            ("1Y price change", _fmt(f.fifty_two_week_change, pct=True)),
        ]
        facts.extend(f"{label}: {val}" for label, val in pairs if val != "n/a")
    return facts


def _build_messages(
    symbol: str,
    fundamentals: Fundamentals | None,
    quote: Quote | None,
) -> list[dict[str, str]]:
    name = fundamentals.name if fundamentals and fundamentals.name else symbol
    sector = fundamentals.sector if fundamentals else None
    industry = fundamentals.industry if fundamentals else None
    profile = ", ".join(p for p in (sector, industry) if p)
    facts = _build_facts(fundamentals, quote)
    facts_block = "\n".join(f"- {line}" for line in facts) if facts else "- (none available)"

    system = (
        "You are an equity analyst writing a terse company overview for a "
        "professional finance terminal. You will be given a fixed list of "
        "verified numeric facts. RULES, strictly enforced by a downstream "
        "verifier: (1) Use ONLY numbers that appear in the facts list — never "
        "recall, estimate, or invent any figure, date, or statistic from "
        "outside it. (2) If a useful number is not in the list, write the point "
        "qualitatively without a number. (3) No price targets, no forecasts, no "
        "made-up percentages. (4) Plain, neutral, no hype. Any number you write "
        "that is not in the facts list will be redacted, so do not guess."
    )
    user = (
        f"Company: {name} ({symbol})"
        + (f" — {profile}" if profile else "")
        + "\n\nVerified facts (the ONLY numbers you may cite):\n"
        + facts_block
        + "\n\nWrite the overview as exactly this structure:\n"
        "SUMMARY: a tight 2-4 sentence narrative of what the company is and what "
        "the numbers say about it.\n"
        "INSIGHTS:\n"
        "- one short insight\n"
        "- one short insight\n"
        "(2 to 4 insight bullets, each a single line starting with '- ')."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


def _parse_output(text: str) -> tuple[str, list[str]]:
    """Split the model's ``SUMMARY:`` / ``INSIGHTS:`` block into prose + bullets.

    Tolerant: if the model omits the markers we treat the first paragraph as the
    summary and any ``- ``/``* `` lines as insights. Returns ``("", [])`` for an
    empty completion.
    """
    if not text.strip():
        return "", []

    summary_lines: list[str] = []
    insights: list[str] = []
    section = "summary"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("SUMMARY:"):
            section = "summary"
            rest = line[len("SUMMARY:") :].strip()
            if rest:
                summary_lines.append(rest)
            continue
        if upper.startswith("INSIGHTS:") or upper.startswith("KEY INSIGHTS:"):
            section = "insights"
            continue
        bullet = re.match(r"^[-*•]\s+(.*)$", line)
        if bullet:
            insights.append(bullet.group(1).strip())
            section = "insights"
            continue
        if section == "summary":
            summary_lines.append(line)
        else:
            # A non-bullet line after INSIGHTS: — fold it into the previous bullet
            # if any, else treat as more summary.
            if insights:
                insights[-1] = f"{insights[-1]} {line}".strip()
            else:
                summary_lines.append(line)

    summary = " ".join(summary_lines).strip()
    # Cap insights at 4 (the contract) and drop empties.
    insights = [i for i in insights if i][:4]
    return summary, insights


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def generate_narrative(
    symbol: str,
    *,
    provider: str | None,
    model: str | None,
    api_key: str | None,
    region: str | None = None,
) -> CompanyNarrative:
    """Build a numerically-verified company narrative for ``symbol``.

    Always returns a :class:`CompanyNarrative` (never raises for the caller's
    happy path): a missing key, missing model, missing fundamentals, or empty
    model output all resolve to ``summary=None`` + a ``reason``. The route maps
    this straight to a ``200`` so the UI renders a quiet unavailable state.
    """
    normalized = symbol.strip().upper()

    # 1. Fetch the SAME real data the panel shows. Each is independent; the quote
    #    is sync, fundamentals async. A failure of either degrades — we can still
    #    narrate from whatever resolved (and verify against it).
    fundamentals: Fundamentals | None = None
    quote: Quote | None = None
    try:
        fundamentals = await provider_registry.get_fundamentals(normalized)
    except Exception as exc:  # noqa: BLE001 — degrade, never 500
        logger.info("narrative: fundamentals unavailable for %s: %s", normalized, exc)
    try:
        quote = provider_registry.get_quote(normalized, region=region)
    except Exception as exc:  # noqa: BLE001 — degrade, never 500
        logger.info("narrative: quote unavailable for %s: %s", normalized, exc)

    source_provider = (fundamentals.provider if fundamentals else None) or (
        quote.provider if quote else None
    )

    if fundamentals is None and quote is None:
        return CompanyNarrative(
            symbol=normalized,
            reason="No fundamentals or quote available for this symbol to ground a narrative.",
        )

    # 2. No model/key → graceful null (NOT an error). Ollama needs no key; every
    #    other provider does.
    if not provider or not model:
        return CompanyNarrative(
            symbol=normalized,
            source_provider=source_provider,
            reason="No AI provider configured. Add a key in Settings → AI Providers.",
        )
    if not api_key and provider != "ollama":
        return CompanyNarrative(
            symbol=normalized,
            source_provider=source_provider,
            reason=f"No API key for {provider}. Add one in Settings → AI Providers.",
        )

    # 3. Ask the model, constrained to the verified facts.
    messages = _build_messages(normalized, fundamentals, quote)
    raw = await complete(
        provider=provider,
        model=model,
        api_key=api_key,
        messages=messages,
        timeout=_LLM_TIMEOUT_SECS,
    )
    summary_raw, insights_raw = _parse_output(raw)
    if not summary_raw and not insights_raw:
        return CompanyNarrative(
            symbol=normalized,
            source_provider=source_provider,
            model=model,
            reason="The model returned no narrative. Try again or pick another model.",
        )

    # 4. Numeric-verification pass — the load-bearing step. Redact any figure that
    #    matches no source value; collect the redactions.
    source = _source_values(fundamentals, quote)
    summary_clean, summary_unverified = _verify_text(summary_raw, source)
    insights_clean: list[str] = []
    all_unverified: list[UnverifiedClaim] = list(summary_unverified)
    for insight in insights_raw:
        cleaned, unverified = _verify_text(insight, source)
        insights_clean.append(cleaned)
        all_unverified.extend(unverified)

    # A summary that became empty / placeholder-only after redaction is dropped.
    summary_final: str | None = summary_clean.strip() or None
    verified = len(all_unverified) == 0 and summary_final is not None

    return CompanyNarrative(
        symbol=normalized,
        summary=summary_final,
        insights=insights_clean,
        verified=verified,
        unverified_claims=all_unverified,
        source_provider=source_provider,
        model=model,
        generated_at=datetime.now(UTC).isoformat(),
        reason=None
        if summary_final is not None
        else "The narrative was fully redacted by the numeric verifier.",
    )


__all__ = ["generate_narrative"]

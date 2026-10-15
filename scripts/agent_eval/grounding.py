"""Invented-figure check for the agent-eval grader (R16).

``ungrounded(answer, given_text, tool_results)`` lists every numeric figure in a
final answer that no ok tool result of the turn carries. A figure is grounded when
it matches some number in a tool result within rounding (relative 1% or the
displayed precision) after unit scaling (K/M/B/T, thousand..trillion, lakh/crore,
%, bps). Ignored on purpose: years, dates, times, list markers, step numbers,
named indices, URLs, durations ("6 months"), plain integers below 100 (counts),
and anything the user's own text contains (or a sum/difference/product/ratio of
two of its numbers). Stdlib only.
"""

from __future__ import annotations

import bisect
import itertools
import re

# ponytail: plain integers under 100 are counts/ranks and are not checked, so a
# fabricated bare "P/E 28" slips; raise the floor's strictness if that matters.
_PLAIN_INT_FLOOR = 100
_REL = 0.01

_NUM = r"(?:\d{1,2}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?"
_UNIT = (
    r"(?i:\s?lakh\s*-?\s*crores?|\s?lakh\s+cr|\s?lac\s+crores?)"
    r"|(?i:\s?(?:trillion|billion|million|thousand|crores?|lakhs?|lacs?|cr|tn|trn|bn|mn|mm"
    r"|percent|per\s+cent|bps|bp|basis\s+points?)\b)"
    r"|%|\s?[KMBTkmbt]|x"
)
_TOKEN = re.compile(
    rf"(?<![\w.,/])(?P<cur>(?i:US\$|USD|INR|Rs\.?)|[₹$€£¥])?\s?(?P<num>{_NUM})"
    rf"(?P<unit>{_UNIT})?(?!\w|-[A-Za-z]|\.\d)"
)

_SCALE = {
    "k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "mm": 1e6, "million": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9, "t": 1e12, "tn": 1e12, "trn": 1e12,
    "trillion": 1e12, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
}  # fmt: skip

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
_IGNORE = [
    re.compile(p, re.I | re.M)
    for p in (
        r"https?://\S+",
        r"\b\d{10}-\d{2}-\d{6}\b",
        r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?",
        r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}(?:,?\s+\d{{4}})?",
        rf"\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?",
        rf"\b{_MONTH},?\s+\d{{4}}\b",
        r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:[ap]m)?",
        r"^\s*(?:[-*>]\s+)?\d{1,3}[.)]\s",
        r"\bsteps?\s+\d+",
        r"\(\d{1,2}\)",
        r"S&P\s*\d+|Nifty\s*(?:50|100|200|500|next\s*50)|Dow\s*30|Nasdaq[- ]?100|"
        r"Sensex\s*30|BSE\s*(?:100|200|500)|Russell\s*(?:1000|2000)|FTSE\s*100|"
        r"DAX\s*40|CAC\s*40|Nikkei\s*225",
    )
]
_DURATION = re.compile(
    r"\s?(?:days?|weeks?|months?|years?|yrs?|quarters?|hours?|hrs?|minutes?|mins?|secs?|seconds?)\b",
    re.I,
)


def _scrub(text: str) -> str:
    for pattern in _IGNORE:
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def candidates(num: str, unit: str) -> list[tuple[float, float]]:
    """(value, absolute tolerance) readings of one figure. The tolerance is half the
    last displayed digit; a scaled figure is read both scaled and as written."""
    n = float(num.replace(",", ""))
    mantissa = re.split("[eE]", num)[0]
    tol = 0.5 * 10 ** -(len(mantissa.split(".")[1]) if "." in mantissa else 0)
    key = re.sub(r"[\s-]+", " ", unit.strip().lower())
    if key in ("%", "percent", "per cent"):
        return [(n, tol), (n / 100, tol / 100)]
    if key in ("bps", "bp") or key.startswith("basis"):
        return [(n / 1e4, tol / 1e4), (n / 100, tol / 100), (n, tol)]
    if "lakh" in key.split() and "cr" in key.replace("crore", "cr") or key.startswith("lac c"):
        scale = 1e12
    else:
        scale = _SCALE.get(key, 1.0)
    return [(n * scale, tol * scale), (n, tol)] if scale != 1.0 else [(n, tol)]


def figures(text: str, *, ignore: bool) -> list[tuple[str, list[tuple[float, float]]]]:
    """(displayed form, readings) per numeric token. With ``ignore`` the
    non-figure classes (dates, years, markers, counts...) are dropped."""
    if ignore:
        text = _scrub(text)
    out = []
    for m in _TOKEN.finditer(text):
        num, unit, cur = m.group("num"), m.group("unit") or "", m.group("cur") or ""
        if ignore:
            if not unit and _DURATION.match(text, m.end()):
                continue
            plain = not (unit or cur or "," in num or "." in num or "e" in num.lower())
            if plain and (int(num) < _PLAIN_INT_FLOOR or 1900 <= int(num) <= 2100):
                continue
        out.append((m.group(0).strip(), candidates(num, unit)))
    return out


class Pool:
    """Sorted absolute values with a within-rounding membership test."""

    def __init__(self, values: list[float]) -> None:
        self.values = sorted(abs(v) for v in values)

    @classmethod
    def of_text(cls, texts: list[str]) -> Pool:
        return cls([v for t in texts for _, cs in figures(t, ignore=False) for v, _ in cs])

    def has(self, readings: list[tuple[float, float]]) -> bool:
        for value, tol in readings:
            v = abs(value)
            width = max(tol, _REL * v) * 1.02 + 1e-12
            lo = bisect.bisect_left(self.values, v - width)
            hi = bisect.bisect_right(self.values, v + width)
            if any(abs(v - p) <= max(tol, _REL * max(v, p)) for p in self.values[lo:hi]):
                return True
        return False


def _given_pool(given_text: str) -> Pool:
    base = [v for _, cs in figures(given_text, ignore=False) for v, _ in cs][:12]
    derived = list(base)
    for a, b in itertools.combinations(base, 2):
        derived += [a + b, abs(a - b), a * b]
        if a and b:
            derived += [a / b, b / a]
    return Pool(derived)


def ungrounded(answer: str, given_text: str, tool_results: list[str]) -> list[str]:
    """Figures in ``answer`` matched by neither the user's text nor any tool result."""
    given, tools = _given_pool(given_text), Pool.of_text(tool_results)
    seen: list[str] = []
    for shown, readings in figures(answer, ignore=True):
        if shown not in seen and not tools.has(readings) and not given.has(readings):
            seen.append(shown)
    return seen

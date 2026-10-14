"""Figure grounding for the streaming citation guard (R15-LEAD-030).

A figure the model streams is judged by whether anything the model was given
carries it — a tool result, the user's messages, the runtime context — not by
the shape of the prose around it. Five shape rules each leaked a new shape;
the class is closed by provenance. Pure functions and one value holder: the
guard in :mod:`services.agent_runtime` owns the per-turn state.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from itertools import combinations
from typing import Any

from services import symbol_resolver

#: Decimal exponent of each scale word ("₹4,411 cr" = 4411 × 10^7).
_SCALES = {
    "k": 3,
    "thousand": 3,
    "lakh": 5,
    "lakhs": 5,
    "m": 6,
    "mn": 6,
    "million": 6,
    "cr": 7,
    "crore": 7,
    "crores": 7,
    "b": 9,
    "bn": 9,
    "billion": 9,
    "t": 12,
    "tn": 12,
    "trillion": 12,
    "lakh crore": 12,
    "lakh cr": 12,
}
_CURRENCY = r"[$₹€£]|(?:Rs\.?|USD|INR|EUR|GBP|US\$)"
#: A number token: optional currency before it, thousands separators (Western
#: or Indian grouping), a decimal part, e-notation, a percent sign, a scale
#: word and a currency code after it. Not one glued to a letter or a symbol's
#: digits (``500325.BO``, ``Q3``, ``FY24``, ``20-F`` leaves ``20`` bare).
_NUMBER = re.compile(
    rf"(?<![\w.])(?P<cur>(?:{_CURRENCY})\s*)?"
    r"(?P<num>\d+(?:,\d+)*(?:\.\d+)?)(?P<exp>[eE][-+]?\d+)?"
    r"(?P<pct>\s?%)?"
    r"(?:\s?(?P<scale>lakh\s+cr(?:ore)?|crores?|cr|lakhs?|thousand|million|mn"
    r"|billion|bn|trillion|tn|[kmbt])(?![A-Za-z]))?"
    r"(?P<cur2>\s?(?:USD|INR|EUR|GBP|dollars?|rupees?)\b)?"
    r"(?![\dA-Za-z]|\.[A-Za-z])",
    re.IGNORECASE,
)
_YEAR = (1900, 2099)
#: A date or a time of day: its parts are no numbers at all, so a "25" in
#: today's date never grounds "$25.00", and "10:30" is never a figure.
_DATETIME = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[-+]\d{2}:?\d{2})?)?"
    r"|\b\d{1,2}:\d{2}(?::\d{2})?\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
)


@dataclass(frozen=True)
class Figure:
    """One number as written: its mantissa with the written precision, and the
    decimal exponent of its scale word (0 when none)."""

    text: str
    mantissa: Decimal
    dp: int
    scale: int = 0
    pct: bool = False

    @property
    def value(self) -> Decimal:
        return self.mantissa.scaleb(self.scale)


def _tokens(text: str) -> list[tuple[Figure, bool]]:
    """Every number of ``text`` with whether the grammar counts it a figure."""
    out: list[tuple[Figure, bool]] = []
    dates = [m.span() for m in _DATETIME.finditer(text)]
    for m in _NUMBER.finditer(text):
        if any(start <= m.start("num") < end for start, end in dates):
            continue
        raw = m.group("num").replace(",", "")
        try:
            mantissa = Decimal(raw + (m.group("exp") or ""))
        except InvalidOperation:
            continue
        dp = len(raw.split(".")[1]) if "." in raw else 0
        scale_word = re.sub(r"\s+", " ", (m.group("scale") or "").lower())
        scale = _SCALES.get(scale_word, 0)
        pct = bool(m.group("pct"))
        marked = bool(
            m.group("cur") or m.group("cur2") or pct or scale or "." in raw or "," in m.group("num")
        )
        digits = len(raw.split(".")[0])
        year = digits == 4 and not marked and _YEAR[0] <= int(raw) <= _YEAR[1]
        is_figure = marked or (digits >= 3 and not year)
        out.append((Figure(m.group().strip(), mantissa, dp, scale, pct), is_figure))
    return out


def figures(text: str) -> list[Figure]:
    """The figures of ``text`` (R15-LEAD-030): a number with a currency sign or
    code, a percent, a decimal point, a thousands separator, a scale word, or
    three or more digits. Not a bare year 1900–2099, a bare integer under 100
    (list numbers, times, dates, small counts) or digits inside a word."""
    return [fig for fig, is_figure in _tokens(text) if is_figure]


def numbers(text: str) -> set[Decimal]:
    """Every number of ``text`` as a grounding value: the mantissa as written
    and, with a scale word, the scaled value ("₹12.1 lakh cr" gives both 12.1
    and 1.21e12)."""
    out: set[Decimal] = set()
    for fig, _ in _tokens(text):
        out.add(fig.mantissa)
        if fig.scale:
            out.add(fig.value)
    return out


def payload_numbers(result_str: str) -> set[Decimal]:
    """The numbers a tool result carries: every numeric leaf of its JSON (bools
    excluded) plus the numbers inside its string leaves; a non-JSON result is
    read as text."""
    try:
        payload = json.loads(result_str)
    except (TypeError, ValueError):
        return numbers(result_str)
    out: set[Decimal] = set()
    stack: list[Any] = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, bool):
            continue
        if isinstance(node, int):
            out.add(Decimal(node))
        elif isinstance(node, float):
            if math.isfinite(node):
                out.add(Decimal(str(node)))
        elif isinstance(node, str):
            out |= numbers(node)
        elif isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return out


#: ponytail: pairwise derivations of the user/context values only. The tool
#: values ground by direct match: pairs of hundreds of payload numbers would
#: ground almost any fabricated figure.
_DERIVATION_CAP = 60


def derived(values: set[Decimal]) -> set[Decimal]:
    """The sum, difference, product, quotients and percent changes of every
    pair of ``values``: what a user's own figures let the model compute
    ("That is ₹15,000 in total" after 10 at ₹1,500)."""
    out: set[Decimal] = set()
    for a, b in combinations(sorted(values)[:_DERIVATION_CAP], 2):
        out |= {a + b, abs(a - b), a * b}
        for x, y in ((a, b), (b, a)):
            if y:
                out |= {x / y, (x - y) / y * 100}
    return out


@dataclass
class Grounding:
    """The values one turn may state (R15-LEAD-030): ``context`` from the
    user's messages and the runtime context, ``tool`` from every tool result,
    ok or errored. Assistant turns and the agent's system prompt never ground."""

    context: set[Decimal] = field(default_factory=set)
    tool: set[Decimal] = field(default_factory=set)
    _derived: set[Decimal] | None = field(default=None, repr=False)

    def seed(self, text: str) -> None:
        self.context |= numbers(text)
        self._derived = None

    def add_result(self, result_str: str) -> None:
        self.tool |= payload_numbers(result_str)

    def add_text(self, text: str) -> None:
        self.tool |= numbers(text)

    def grounded(self, fig: Figure) -> bool:
        """Whether some grounded value matches ``fig`` at its own precision,
        on the mantissa or on the scaled value (812.4 grounds "₹812.40";
        2.3e12 grounds "2.3 trillion" and "₹2.3 lakh crore"; 0.012 and 1.2
        both ground "1.2%"), or a derivation of two context values does."""
        if self._derived is None:
            self._derived = derived(self.context)
        tol = Decimal(1).scaleb(-fig.dp) / 2
        for g in self.context | self.tool | self._derived:
            g = abs(g)
            if abs(fig.mantissa - g) <= tol:
                return True
            if fig.scale and abs(fig.mantissa - g.scaleb(-fig.scale)) <= tol:
                return True
            if fig.pct and abs(fig.mantissa - g * 100) <= tol:
                return True
        return False

    def ungrounded(self, text: str) -> list[Figure]:
        return [fig for fig in figures(text) if not self.grounded(fig)]


def subjects(tool_input: Any) -> set[str]:
    """The symbols a tool call is about, as bare upper-case bases (``SBIN.NS``,
    ``sbin`` and ``SBIN`` are one subject)."""
    if not isinstance(tool_input, dict):
        return set()
    raw = tool_input.get("symbols") if "symbols" in tool_input else tool_input.get("symbol")
    items = raw if isinstance(raw, list) else [raw]
    return {
        item.strip().upper().split(".")[0]
        for item in items
        if isinstance(item, str) and item.strip() and item.strip().split(".")[0]
    }


def _distinctive(word: str) -> bool:
    return len(word) >= 4 and word.isalpha() and word not in symbol_resolver._generic_tokens()


class Initialism(str):
    """An upper-case initialism alias ("SBI", "L&T"), matched case-sensitively
    (:func:`mention_end`): in lower case, a short form is often an English
    word ("and", "all")."""


_INITIALISM_SKIP = frozenset({"of", "the", "and"})
#: Words an initialism is written both with and without ("SBI" and "SB" for
#: State Bank of India, "RIL" and "RI" for Reliance Industries Limited).
_INITIALISM_OPTIONAL = frozenset(
    {"limited", "ltd", "india", "industries", "corporation", "company"}
)


def _initialisms(words: list[str], suffix: list[str]) -> set[str]:
    """The initialisms of a name of two or more ``words`` (its corporate
    ``suffix`` stripped), ``&`` kept, three characters or more: the words
    with each leading run of the suffix's optional words ("TCS", "RIL",
    "HDFC" of Housing Development Finance Corporation Limited), and the
    words without their optional ones."""
    if len([w for w in words if w != "&"]) < 2:
        return set()
    tail = [w for w in suffix if w in _INITIALISM_OPTIONAL]
    forms = [words + tail[:k] for k in range(len(tail) + 1)]
    forms.append([w for w in words if w not in _INITIALISM_OPTIONAL])
    out: set[str] = set()
    for form in forms:
        letters = "".join(
            w[0].upper() for w in form if w not in _INITIALISM_SKIP and (w == "&" or w[0].isalnum())
        )
        if len(letters) >= 3:
            out.add(Initialism(letters))
    return out


def payload_names(result_str: str) -> list[str]:
    """Every ``name``, ``longName`` or ``shortName`` string of a tool result's
    JSON, at any depth: the names the result itself gives its subject."""
    try:
        stack: list[Any] = [json.loads(result_str)]
    except (TypeError, ValueError):
        return []
    out: list[str] = []
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            out += [
                v
                for k, v in node.items()
                if k in ("name", "longName", "shortName") and isinstance(v, str)
            ]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return out


def aliases(base: str, names: Iterable[str] = ()) -> set[str]:
    """What prose may call the subject ``base`` by (R15-LEAD-030): the symbol
    base, and for each of its names (the resolver masters, the curated
    marquee family keys, and ``names``: the call's payload names and the
    queries ``resolve_symbol`` bound to it this turn), the name lower-cased
    with the corporate suffix stripped ("state bank of india"), its first two
    words when it has three or more ("state bank"), every distinctive word
    (four or more letters, not common across the masters: "airtel", never
    "tata") and its upper-case initialisms ("SBI", "L&T").
    ponytail: the private master readers avoid a clash with pending
    symbol_resolver edits (a public accessor can replace them); two-letter
    initialisms ("SB", "BA") are dropped as too common, so an errored subject
    written that way falls to the FAIL-SAFE rule instead; a common-word alias
    ("state") over-replaces only an ungrounded figure, which fails safe."""
    out = {base}
    masters = [
        symbol_resolver._nse_master().get(base, ("",))[0],
        symbol_resolver._bse_master().get(base, ("",))[0],
        symbol_resolver._us_master().get(base, ""),
    ]
    marquee = [
        key
        for key, entry in symbol_resolver._marquee_aliases().items()
        if isinstance(entry, dict) and entry.get("primary") == base
    ]
    for name in filter(None, [*masters, *marquee, *names]):
        lowered = re.sub(r"\s*&\s*", " & ", name.lower())
        words = symbol_resolver._strip_corporate_suffix(lowered).split()
        if not words:
            continue
        suffix = re.findall(r"[a-z]+", " ".join(lowered.split()[len(words) :]))
        out.add(" ".join(words))
        if len(words) >= 3 and words[1] != "&":
            out.add(" ".join(words[:2]))
        out |= {w for w in words if _distinctive(w)}
        out |= _initialisms(words, suffix)
    return out


def mention_end(text: str, subject: str) -> int:
    """Where the last mention of ``subject`` in ``text`` ends, or -1: a whole
    word or phrase, with or without an exchange suffix, in any case but an
    :class:`Initialism`'s own; ``&`` with or without spaces ("L & T")."""
    words = re.sub(r"\s*&\s*", " & ", subject).split()
    phrase = "".join(
        (r"\s*" if "&" in (w, words[i - 1]) else r"\s+") * bool(i) + re.escape(w)
        for i, w in enumerate(words)
    )
    flags = 0 if isinstance(subject, Initialism) else re.IGNORECASE
    end = -1
    for m in re.finditer(
        rf"(?<![A-Za-z0-9]){phrase}(?:\.[A-Za-z]{{1,4}})?(?![A-Za-z0-9])", text, flags
    ):
        end = m.end()
    return end


def mentions(text: str, subject: str) -> bool:
    """Whether ``text`` names ``subject`` (see :func:`mention_end`)."""
    return mention_end(text, subject) >= 0


__all__ = [
    "Figure",
    "Grounding",
    "Initialism",
    "aliases",
    "derived",
    "figures",
    "mention_end",
    "mentions",
    "numbers",
    "payload_names",
    "payload_numbers",
    "subjects",
]

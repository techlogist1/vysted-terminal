"""Figure grounding (R15-LEAD-030): the figure grammar and the precision matcher."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services import figure_grounding as fg


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("₹812.40", [("812.40", 2, 0, False)]),
        ("2,30,000", [("230000", 0, 0, False)]),
        ("₹2.3 lakh crore", [("2.3", 1, 12, False)]),
        ("₹4,411 cr", [("4411", 0, 7, False)]),
        ("1.2%", [("1.2", 1, 0, True)]),
        ("$1320 m", [("1320", 0, 6, False)]),
        ("$4.90T", [("4.90", 2, 12, False)]),
        ("1.646e8", [("1.646E+8", 3, 0, False)]),
        ("HTTP 429", [("429", 0, 0, False)]),
        ("the S&P 500", [("500", 0, 0, False)]),
        ("12k", [("12", 0, 3, False)]),
        # not figures: years, dates, times, small counts, digits inside a word
        ("in 2024", []),
        ("as of 2026-09-25 10:30", []),
        ("500325.BO", []),
        ("Q3 FY24 20-F", []),
        ("P/E of 30", []),
        ("2:1 split", []),
        ("Quantity: 10", []),
        ("1mo 1d 5 months", []),
    ],
)
def test_the_figure_grammar(text: str, expected: list[tuple[str, int, int, bool]]) -> None:
    got = [(str(f.mantissa), f.dp, f.scale, f.pct) for f in fg.figures(text)]
    assert got == expected


@pytest.mark.parametrize(
    ("result", "text", "grounded"),
    [
        ('{"latest_price": 812.4}', "₹812.40", True),  # the figure's own precision
        ('{"latest_price": 812.4}', "₹812", True),
        ('{"latest_price": 812.4}', "₹812.45", False),
        ('{"latest_price": 812.4}', "813", False),
        ('{"marketCap": 2300000000000}', "₹2.3 lakh crore", True),  # through a scale word
        ('{"marketCap": 2300000000000}', "2.3 trillion", True),
        ('{"marketCap": 2300000000000}', "2,300 bn", True),
        ('{"marketCap": 2300000000000}', "$2,300,000,000,000", True),
        ('{"chg": 0.012}', "1.2%", True),  # a ratio as a percent
        ('{"chg": 0.012}', "1.3%", False),
        ('{"value": 44110000000}', "₹4,411 cr", True),
        ('{"value": 44110000000}', "4,411.4 cr", False),
        ('{"ok": false, "error": "HTTP 429"}', "429", True),  # an errored result grounds too
        ('{"s": "₹12.1 lakh cr"}', "₹12.1 trillion", True),  # a string leaf, scaled
        ('{"as_of": "2026-09-25"}', "$25.00", False),  # a date's parts are no numbers
    ],
)
def test_the_precision_matcher(result: str, text: str, grounded: bool) -> None:
    g = fg.Grounding()
    g.add_result(result)
    assert [g.grounded(f) for f in fg.figures(text)] == [grounded]


def test_the_users_values_ground_their_derivations() -> None:
    g = fg.Grounding()
    g.seed("I bought 10 shares at ₹1,500; it is ₹1,650 now")
    assert g.ungrounded("That is ₹15,000 in total, a 10% gain, or ₹150 a share.") == []
    assert [f.text for f in g.ungrounded("So ₹16,000 in total.")] == ["₹16,000"]
    assert fg.derived({Decimal(2), Decimal(8)}) == {
        Decimal(10),
        Decimal(6),
        Decimal(16),
        Decimal("0.25"),
        Decimal(4),
        Decimal(-75),
        Decimal(300),
    }


def test_subjects_and_mentions() -> None:
    assert fg.subjects({"symbol": "SBIN.NS"}) == {"SBIN"}
    assert fg.subjects({"symbols": ["tcs.ns", "INFY"]}) == {"TCS", "INFY"}
    assert fg.subjects({"query": "x"}) == set() and fg.subjects("SBIN") == set()
    assert fg.mentions("| SBIN.NS | ₹812.40 |", "SBIN")
    assert fg.mentions("sbin closed", "SBIN")
    assert not fg.mentions("SBINX closed", "SBIN")
    for text in ("L&T rose", "L & T rose", "Larsen&Toubro rose", "larsen & toubro rose"):
        assert fg.mentions(text, "larsen & toubro") or fg.mentions(text, "l&t")
    assert fg.mentions("L & T rose", fg.Initialism("L&T"))
    assert not fg.mentions("l & t rose", fg.Initialism("L&T"))


_ZETA_RESULT = (
    '{"ok": true, "quote": {"symbol": "ZQH", "longName": "Zeta Quanta Holdings Limited"}}'
)


@pytest.mark.parametrize(
    ("base", "names", "present", "absent"),
    [
        ("INFY", [], {"INFY", "infosys"}, set()),
        ("SBIN", [], {"state bank of india", "state bank", "SBI"}, set()),
        (
            "TCS",
            [],
            {"tata consultancy services", "tata consultancy", "TCS", "consultancy"},
            {"tata"},
        ),
        ("SIFY", [], {"sify"}, set()),
        ("LT", [], {"L&T", "larsen & toubro", "l & t", "larsen", "toubro"}, {"larsen &"}),
        ("BHARTIARTL", [], {"bharti airtel", "bharti", "airtel"}, set()),
        ("HDFCBANK", [], {"hdfc bank"}, set()),
        ("RELIANCE", [], {"RIL", "reliance"}, set()),
        ("ZQHX", fg.payload_names(_ZETA_RESULT), {"zeta quanta holdings", "quanta", "ZQH"}, set()),
        ("IBM", ["Big Blue"], {"IBM", "big blue", "machines"}, set()),
    ],
)
def test_a_subject_is_named_by_its_aliases(
    base: str, names: list[str], present: set[str], absent: set[str]
) -> None:
    """R15-LEAD-030 batch-22: a call's subject is its symbol and, for each of
    its names (the resolver masters, the marquee family keys, its payload's
    name/longName/shortName and a resolve_symbol query), the name with the
    corporate suffix stripped, its short forms, every distinctive word and
    its initialisms. Batch-21 took a distinctive word past the first only
    when the user wrote it ("consultancy"); every one is taken now."""
    got = fg.aliases(base, names)
    assert present <= got and not absent & got


def test_an_initialism_matches_in_its_own_case_only() -> None:
    """R15-LEAD-030 batch-22: an initialism is matched upper-case only and is
    three characters or more, so "it", "us" and "and" name no subject."""
    got = fg.aliases("ZZZQ", ["Alpha Network Data Limited", "Info Tech", "United Services"])
    assert "AND" in got and fg.mentions("AND rose 2%", next(a for a in got if a == "AND"))
    assert not any(fg.mentions("it and us rose 2%", alias) for alias in got)

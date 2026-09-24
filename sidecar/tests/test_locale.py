"""Pass B (B1) — locale primitives: currency, suffix, calendar, freshness."""

from __future__ import annotations

from datetime import UTC, date, datetime

from services import locale


def test_region_currency() -> None:
    assert locale.region_currency("US") == "USD"
    assert locale.region_currency("IN") == "INR"
    assert locale.region_currency("GLOBAL") == "USD"
    assert locale.region_currency("???") == "USD"


def test_region_for_suffix() -> None:
    assert locale.region_for_suffix("RELIANCE.NS") == "IN"
    assert locale.region_for_suffix("TATASTEEL.BO") == "IN"
    assert locale.region_for_suffix("reliance.ns") == "IN"
    assert locale.region_for_suffix("AAPL") is None


def test_strip_exchange_suffix() -> None:
    assert locale.strip_exchange_suffix("GOLDBEES.NS") == "GOLDBEES"
    assert locale.strip_exchange_suffix("TATASTEEL.BO") == "TATASTEEL"
    assert locale.strip_exchange_suffix("AAPL") == "AAPL"
    assert locale.strip_exchange_suffix(" aapl ") == "AAPL"


def test_market_timezone_and_session() -> None:
    assert "Kolkata" in str(locale.market_timezone("IN"))
    assert "New_York" in str(locale.market_timezone("US"))
    open_in, close_in = locale.market_session("IN")
    assert (open_in.hour, open_in.minute) == (9, 15)
    assert (close_in.hour, close_in.minute) == (15, 30)


def test_most_recent_session_skips_weekend() -> None:
    # Sunday 2026-05-31 → most recent US session is Friday 2026-05-29.
    sunday = datetime(2026, 5, 31, 18, 0, tzinfo=UTC)
    assert locale.most_recent_session("US", sunday) == date(2026, 5, 29)
    assert locale.most_recent_session("IN", sunday) == date(2026, 5, 29)


def test_trading_sessions_between() -> None:
    # Fri 2026-05-29 → Mon 2026-06-01 is one session (Mon), weekend skipped.
    assert locale.trading_sessions_between(date(2026, 5, 29), date(2026, 6, 1), "US") == 1
    assert locale.trading_sessions_between(date(2026, 6, 1), date(2026, 6, 1), "US") == 0


def test_is_rejectably_stale_tolerates_t_plus_1_eod() -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)  # Monday
    # Friday EOD read on Monday — within the T+1 tolerance, not rejected.
    assert not locale.is_rejectably_stale("IN", date(2026, 5, 29), now)
    # A month-old value — clearly a broken feed, rejected.
    assert locale.is_rejectably_stale("IN", date(2026, 4, 20), now)
    # Missing timestamp is not rejectable here (gate handles missing fields).
    assert not locale.is_rejectably_stale("IN", None, now)


def test_freshness_labels() -> None:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    f = locale.freshness_for("IN", date(2026, 5, 29), intraday=False, now=now)
    assert f.state == "eod" and f.as_of == date(2026, 5, 29)
    stale = locale.freshness_for("IN", date(2026, 4, 20), intraday=False, now=now)
    assert stale.state == "stale" and stale.is_stale


def test_holiday_calendars_cover_the_current_year() -> None:
    # R15-DATA-073: a bundled calendar that stops before December silently turns
    # every later holiday into an expected session. Regenerate the NSE list with
    # services.resolver_masters.regenerate_holidays when this fails.
    december = date(datetime.now(tz=UTC).year, 12, 1)
    for region, days in (("IN", locale._NSE_HOLIDAYS), ("US", locale._US_HOLIDAYS)):
        assert date.fromisoformat(max(days)) >= december, region


def test_2026_nse_master_days_are_not_sessions() -> None:
    # Days the NSE holiday master lists that the hand list had missed, and a day
    # it had wrongly closed (2026-03-04 traded; Holi was 03-03).
    for day in ("2026-01-15", "2026-03-26", "2026-05-28", "2026-06-26", "2026-09-14"):
        assert not locale._is_trading_day(date.fromisoformat(day), "IN"), day
    assert locale._is_trading_day(date(2026, 3, 4), "IN")
    # A session after the Ganesh Chaturthi close counts one session, not two.
    assert locale.trading_sessions_between(date(2026, 9, 11), date(2026, 9, 15), "IN") == 1


def test_regenerate_holidays_parses_the_master_shape() -> None:
    from services.resolver_masters.regenerate_holidays import holiday_lines

    master = {
        "CM": [
            {"tradingDate": "25-Dec-2026", "description": "Christmas"},
            {"tradingDate": "15-Jan-2026", "description": "Municipal Corporation Election"},
        ],
        "FO": [{"tradingDate": "01-Jan-2026", "description": "not the CM segment"}],
    }
    assert holiday_lines(master) == [
        '"2026-01-15",  # Municipal Corporation Election',
        '"2026-12-25",  # Christmas',
    ]

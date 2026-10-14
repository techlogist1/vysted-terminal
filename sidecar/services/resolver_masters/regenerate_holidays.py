"""Print the NSE trading-holiday list for ``services/locale.py`` (R15-DATA-073).

Reads NSE's holiday master (``/api/holiday-master?type=trading``, capital-market
segment ``CM``; BSE's equity segment closes on the same days) through the
nse_direct session and prints one ``"YYYY-MM-DD",  # description`` line per
holiday, ready to paste into ``_NSE_HOLIDAYS``. NSE publishes the next year's
list in December; ``test_locale`` fails once the bundled list has no holiday
left in December of the current year.

Usage::

    python -m services.resolver_masters.regenerate_holidays
"""

from __future__ import annotations

from datetime import datetime

_PATH = "/api/holiday-master"
_REFERER = "https://www.nseindia.com/resources/exchange-communication-holidays"


def holiday_lines(master: dict) -> list[str]:
    """``"YYYY-MM-DD",  # description`` lines for the CM segment, date order."""
    rows = sorted(
        (datetime.strptime(r["tradingDate"], "%d-%b-%Y").date(), r.get("description", ""))
        for r in master.get("CM") or []
    )
    return [f'"{day.isoformat()}",  # {desc.strip()}' for day, desc in rows]


def main() -> None:
    from services import nse_provider

    master = nse_provider._get_json(_PATH, {"type": "trading"}, _REFERER)
    print("\n".join(holiday_lines(master)))


if __name__ == "__main__":
    main()

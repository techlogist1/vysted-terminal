import sys
from datetime import date
sys.path.insert(0, ".")
from services.exchange_financials import FiledPeriod, FiledPeriods

def mk(start, end):
    return FiledPeriod(start=start, end=end, revenue=1.0, net_profit=1.0, eps=1.0)

# Case 1: Jan-Mar unfiled, no 6-month period covering it -> quarterly-gap
c1 = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2024, 10, 1), date(2024, 12, 31)),
    mk(date(2024, 7, 1), date(2024, 9, 30)),
    mk(date(2024, 4, 1), date(2024, 6, 30)),
))
print("case1 (3 quarters, Jan-Mar missing, no half-year):", c1.cadence())
assert c1.cadence() == "quarterly-gap"

# Case 3: complete Jul-25..Jun-26, 4 contiguous quarters -> quarterly
c3 = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2026, 4, 1), date(2026, 6, 30)),
    mk(date(2026, 1, 1), date(2026, 3, 31)),
    mk(date(2025, 10, 1), date(2025, 12, 31)),
    mk(date(2025, 7, 1), date(2025, 9, 30)),
))
print("case3 (4 contiguous quarters):", c3.cadence())
assert c3.cadence() == "quarterly"

# Case 4: pure half-yearly, newest ending March
c4 = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2025, 10, 1), date(2026, 3, 31)),
    mk(date(2025, 4, 1), date(2025, 9, 30)),
))
print("case4 (pure half-yearly, newest ends March):", c4.cadence())
assert c4.cadence() == "half-yearly"

# Case 5: pure half-yearly, newest ending September
c5 = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2025, 4, 1), date(2025, 9, 30)),
    mk(date(2024, 10, 1), date(2025, 3, 31)),
))
print("case5 (pure half-yearly, newest ends September):", c5.cadence())
assert c5.cadence() == "half-yearly"

# Case 6: calendar-FY halves (Jan-Jun, Jul-Dec)
c6 = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2025, 7, 1), date(2025, 12, 31)),
    mk(date(2025, 1, 1), date(2025, 6, 30)),
))
print("case6 (calendar-FY halves):", c6.cadence())
assert c6.cadence() == "half-yearly"

# The R15-LEAD-051 shape: a fresh listing with only its first 2 quarters ever
# filed -> still quarterly-gap (quarterly, gapped), never half-yearly.
c_fresh = FiledPeriods(venue="NSE", basis="standalone", periods=(
    mk(date(2026, 1, 1), date(2026, 3, 31)),
    mk(date(2025, 10, 1), date(2025, 12, 31)),
))
print("case_fresh (only 2 quarters ever filed):", c_fresh.cadence())
assert c_fresh.cadence() == "quarterly-gap"

print("PASS: all 6 cadence() shapes match the certified table")

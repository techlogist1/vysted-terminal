import sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
from datetime import date
from services.exchange_financials import FiledPeriod, FiledPeriods

def q(start, end):
    return FiledPeriod(start=start, end=end, revenue=100.0, net_profit=10.0, eps=1.0)

def h(start, end):
    return FiledPeriod(start=start, end=end, revenue=200.0, net_profit=20.0, eps=2.0)

print("=== R15-LEAD-051: IPO with only 2 quarters ever filed (literal repro) ===")
periods = FiledPeriods(
    venue="BSE", basis="standalone",
    periods=(q(date(2026,4,1), date(2026,6,30)), q(date(2026,1,1), date(2026,3,31))),
)
c = periods.cadence()
print(f"  cadence() = {c!r}  (must NOT be 'half-yearly')")
assert c != "half-yearly", f"regression: IPO with only 2 quarters labelled {c!r}"

print()
print("=== fresh case: single quarter ever filed (Jul-Sep 26) ===")
periods2 = FiledPeriods(
    venue="BSE", basis="standalone",
    periods=(q(date(2026,7,1), date(2026,9,30)),),
)
c2 = periods2.cadence()
print(f"  cadence() = {c2!r}  (must NOT be 'half-yearly')")
assert c2 != "half-yearly"

print()
print("=== held-back case: former-SME migrant (Oct-Mar half + Apr-Jun + Jul-Sep) -> quarterly ===")
periods3 = FiledPeriods(
    venue="BSE", basis="standalone",
    periods=(
        q(date(2026,7,1), date(2026,9,30)),
        q(date(2026,4,1), date(2026,6,30)),
        h(date(2025,10,1), date(2026,3,31)),
    ),
)
c3 = periods3.cadence()
print(f"  cadence() = {c3!r}")
assert c3 == "quarterly", f"expected quarterly (trailing chain complete), got {c3!r}"

print()
print("=== control: pure half-yearly filer (no quarter ever filed) -> half-yearly unchanged ===")
periods4 = FiledPeriods(
    venue="BSE", basis="standalone",
    periods=(h(date(2026,4,1), date(2026,9,30)), h(date(2025,10,1), date(2026,3,31))),
)
c4 = periods4.cadence()
print(f"  cadence() = {c4!r}")
assert c4 == "half-yearly", f"pure half-yearly filer must still read half-yearly, got {c4!r}"

print()
print("PASS: a filer with only 1-2 quarters ever filed is never labelled half-yearly; pure half-yearly filers are unchanged")

import sys, os, threading
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from services.quant import options as qopt
from models.quant import OptionPricingRequest

def make_req(val_date, expiry):
    return OptionPricingRequest(
        exercise="european", payoff="call", spot=100.0, strike=100.0,
        risk_free_rate=0.05, dividend_yield=0.0, volatility=0.2,
        valuation_date=val_date, expiry_date=expiry, method="black-scholes",
    )

reqA = make_req(date(2026, 5, 16), date(2027, 5, 16))
reqB = make_req(date(2030, 1, 2), date(2031, 1, 2))

# reference (single-threaded, no race possible)
ref_price = qopt.price(reqA).price
print(f"reference single-threaded price for reqA: {ref_price:.6f}")

mismatches = 0
N = 1500
def worker_a():
    global mismatches
    r = qopt.price(reqA)
    if abs(r.price - ref_price) > 1e-6:
        mismatches += 1

def worker_b():
    qopt.price(reqB)

with ThreadPoolExecutor(max_workers=2) as ex:
    for _ in range(N):
        fa = ex.submit(worker_a)
        fb = ex.submit(worker_b)
        fa.result()
        fb.result()

print(f"concurrent runs: {N}, mismatches vs reference: {mismatches}")

# bonds vs options concurrent race
from services.quant import bonds as qbonds
from models.quant import BondPricingRequest

def make_bond_req(settle):
    return BondPricingRequest(
        face_value=1000.0, coupon_rate=0.05, coupons_per_year=2,
        issue_date=date(2020,1,1), maturity_date=date(2030,1,1),
        settlement_date=settle, yield_to_maturity=0.04,
    )
bondA = make_bond_req(date(2026,5,16))
ref_bond_price = qbonds.price_bond(bondA).clean_price

mismatches2 = 0
def worker_bond():
    global mismatches2
    r = qbonds.price_bond(bondA)
    if abs(r.clean_price - ref_bond_price) > 1e-6:
        mismatches2 += 1

def worker_opt():
    qopt.price(reqB)

with ThreadPoolExecutor(max_workers=2) as ex:
    for _ in range(N):
        f1 = ex.submit(worker_bond)
        f2 = ex.submit(worker_opt)
        f1.result()
        f2.result()

print(f"bond-vs-option concurrent runs: {N}, bond mismatches vs reference: {mismatches2}")

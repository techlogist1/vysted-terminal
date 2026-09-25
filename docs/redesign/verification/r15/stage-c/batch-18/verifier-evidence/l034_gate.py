"""batch-18 verifier LEAD-034: real yfinance fundamentals for fresh NSE Emerge symbols through the correctness gate. cwd=<tree>/sidecar."""
import sys
sys.path.insert(0, ".")
from services import yfinance_provider as y, correctness_gate as g
for s in sys.argv[1:]:
    f = y.get_fundamentals(s)
    try:
        g.validate_fundamentals(f, s, "IN"); v = "GATE PASS"
    except Exception as e:
        v = f"GATE FAIL {type(e).__name__}: {str(e)[:160]}"
    print(s, "->", f.symbol, "|", f.name, "| mcap", f.market_cap, "| pe", f.pe_ratio, "|", f.currency, "|", v)
print("symbols_match SHERA/SHERA-SM.NS", g.symbols_match("SHERA", "SHERA-SM.NS"), "| SHERA/RICHA-SM.NS", g.symbols_match("SHERA", "RICHA-SM.NS"), "| SMR/SMR.NS", g.symbols_match("SMR", "SMR.NS"))

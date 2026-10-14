import sys
sys.path.insert(0, ".")
from services.screener_universe_india import load_india_universe

for uid in ("nse-all", "bse-all", "india-all"):
    u = load_india_universe(uid)
    print(f"{uid}: {len(u.symbols)} symbols")

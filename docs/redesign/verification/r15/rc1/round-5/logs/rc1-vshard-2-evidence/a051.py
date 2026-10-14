import json, sys
sys.path.insert(0, sys.argv[1] + "/sidecar")
from services.agent_runtime import _render_terminal_preamble
snap = json.load(open(sys.argv[2]))
def ts(s):
    return {"focusedPanel": s["snapshotFocusedPanel"], "focusedSymbol": s["snapshotFocusedSymbol"], "charts": s["charts"], "watchlist": {"symbols": []}}
cases = {k: ts(v) for k, v in snap.items()}
cases["fresh_three_charts_third_focused"] = {"focusedPanel": "chart-3", "focusedSymbol": "TCS.NS", "charts": [
  {"panelId": "chart", "symbol": "SPY", "timeframe": "1D", "indicators": []},
  {"panelId": "chart-2", "symbol": "NVDA", "timeframe": "1H", "indicators": ["vwap"]},
  {"panelId": "chart-3", "symbol": "TCS.NS", "timeframe": "1W", "indicators": ["rsi"]}], "watchlist": {"symbols": []}}
for k, t in cases.items():
    out = _render_terminal_preamble(t)
    print("=====", k); print(out)
    fl = [l for l in out.splitlines() if l.startswith("Focused chart:")]
    if fl:
        sym = fl[0].split(":")[1].split("(")[0].strip()
        print("AGREE" if sym == t["focusedSymbol"] else "CONTRADICT", sym, t["focusedSymbol"])

#!/usr/bin/env python3
"""L2-rot launcher: runs the UNMODIFIED sidecar main() after moving NSE's endpoint
PATHS in-process (host still resolves; the old path now 404s -- what a changed exchange
endpoint looks like to a released binary). Source files are never edited.
env ROT_MOVED=1 enables the move; otherwise behaves exactly like main.py."""
import os, sys
SIDECAR = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar"
sys.path.insert(0, SIDECAR)
os.chdir(SIDECAR)
if os.environ.get("ROT_MOVED") == "1":
    from services import nse_provider, nse_bhavcopy, nse_symbol_change
    nse_provider._HISTORICAL_PATH = "/api/historicalOR-v0-retired/cm/equity"
    nse_provider._QUOTE_PATH = "/api/quote-equity-v0-retired"
    nse_bhavcopy._UDIFF_URL = ("https://nsearchives.nseindia.com/content/cm-v0-retired/"
                               "BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip")
    nse_bhavcopy._SEC_FULL_URL = ("https://archives.nseindia.com/products/content-v0-retired/"
                                  "sec_bhavdata_full_{dmy}.csv")
    nse_symbol_change._URL = "https://nsearchives.nseindia.com/content/equities/symbolchange-v0-retired.csv"
    print("ROT_MOVED applied", nse_provider._HISTORICAL_PATH, nse_bhavcopy._UDIFF_URL, flush=True)
import main  # noqa: E402
main.main(sys.argv[1:])

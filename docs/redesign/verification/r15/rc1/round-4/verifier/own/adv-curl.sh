#!/bin/sh
# rc1-verifier adversarial-sample own repros against own sidecar :52312 (candidate source)
B=http://127.0.0.1:52312
echo "HEAD $(git -C "$1" rev-parse HEAD)  date $(date -u +%FT%TZ)"
c() { echo; echo "### $*"; curl -s -m 60 -w '\n[HTTP %{http_code} %{time_total}s]\n' "$@" | head -c 2500; echo; }
c -H 'X-Vysted-Region: US' "$B/disclosures/shareholding?symbol=AMAL"
c -H 'X-Vysted-Region: US' "$B/disclosures/announcements?symbol=AMAL&limit=25"
c -H 'X-Vysted-Region: US' "$B/resolve?q=AMAL"
c "$B/history/HDFC.NS?range=1y"
c "$B/indicators/HDFC.NS?indicators=rsi"
c "$B/fundamentals/ELCIDIN"
c "$B/fundamentals/NDTV"
c "$B/fundamentals/TCS.NS"
for s in BHP.AX 0700.HK 7203.T VOD.L 2222.SR SAP.F GGAL.BA; do c "$B/quotes/$s"; done
c "$B/quotes/ICON?asset_class=equity"
c "$B/quotes/AMAL?asset_class=equity"
c "$B/quotes/ELCIDIN?asset_class=equity"
c "$B/quotes/INFY.BO"
c "$B/quotes/INFY.NS"
for s in RDY TM SONY; do c "$B/earnings/$s/estimates"; done
c "$B/macro/DGS10?provider=fred"
c "$B/quotes/ZZZZNOTREAL"
c "$B/macro/GDP"

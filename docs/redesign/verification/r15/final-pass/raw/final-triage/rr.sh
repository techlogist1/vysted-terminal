P=http://127.0.0.1:52880
H='Origin: http://localhost:5173'
g(){ echo "### $1 [$2]"; curl -s -m 60 -H "$H" -H "X-Vysted-Region: $2" "$P$1" | head -c ${3:-2500}; echo; }
g /fundamentals/AMAL IN 4000
g /fundamentals/AMAL.BO IN 1500
g /fundamentals/SUNRAJDI IN 6000
g /earnings/SIFY/estimates US
g "/resolve?q=GSTL" IN 3000
g "/disclosures/results?symbol=GSTL" IN 1500
g /fundamentals/YASHOPTICS IN 600
g "/resolve/autocomplete?q=Zeal%20Aqua" IN 800
g "/resolve/autocomplete?q=ZEAL.BO" IN 800
g /earnings/RELIANCE.BO/history IN 1500
g /earnings/RELIANCE.NS/history IN 1500
g "/news?limit=60" IN 200000

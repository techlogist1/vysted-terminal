P=http://127.0.0.1:52887
g(){ echo "### $1 [$2]"; curl -s -m 100 -H "X-Vysted-Region: $2" "$P$1"; echo; }
g "/resolve?q=GSTL" IN
g "/disclosures/results?symbol=GSTL" IN
g "/disclosures/corporate-actions?symbol=GSTL" IN
g "/disclosures/shareholding?symbol=GSTL" IN
g "/resolve/autocomplete?q=Zeal%20Aqua" IN
g "/resolve/autocomplete?q=Sanathnagar%20Enterprises" IN
g "/resolve/autocomplete?q=ZEAL.BO" IN
g "/resolve/autocomplete?q=SEL.BO" IN
g "/resolve/autocomplete?q=RELIANCE" IN
g "/resolve?q=FOCUS" IN
g "/resolve?q=ZEAL" IN
g "/fundamentals/SUNRAJDI" IN
g "/fundamentals/YASHOPTICS" IN
g "/fundamentals/YASHOPTICS/income" IN
g "/fundamentals/YASHOPTICS/balance" IN
g "/fundamentals/SUMAX" IN
g "/fundamentals/QUALIANCE" IN
g "/fundamentals/AMAL" IN
g "/fundamentals/AMAL.BO" IN
g "/earnings/SIFY/estimates" US
g "/earnings/WIT/estimates" US
g "/earnings/INFY/estimates" US
g "/news?limit=60" IN
echo DONE

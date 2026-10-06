P=http://127.0.0.1:52887
g(){ echo "### $1 [$2]"; curl -s -m 100 -H "X-Vysted-Region: $2" "$P$1"; echo; }
g "/resolve?q=WSI" IN
g "/resolve?q=21STCENMGM" IN
g "/resolve?q=KALYANI" IN
g "/disclosures/results?symbol=KALYANI" IN
g "/resolve/autocomplete?q=Kalyani%20Cast" IN
g "/resolve/autocomplete?q=KALYANI.BO" IN
g "/resolve/autocomplete?q=Focus%20Business" IN
g "/resolve/autocomplete?q=FOCUS.BO" IN
g "/resolve/autocomplete?q=WSI" IN
g "/fundamentals/GANESHIN" IN
g "/fundamentals/VOLERCAR" IN
g "/fundamentals/ICON" IN
g "/earnings/RDY/estimates" US
g "/earnings/IBN/estimates" US
g "/earnings/HDB/estimates" US
g "/earnings/MMYT/estimates" US
echo DONE

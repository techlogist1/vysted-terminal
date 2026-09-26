for q in "0000320193-23-000077?identifier=AAPL" "0001045810-16-000358?identifier=NVDA" "0001045810-16-000343?identifier=NVDA&form_type=8-K" "0000320193-99-999999?identifier=AAPL"; do
 echo "\$ curl localhost:52600/sec/filings/$q"
 curl -s -m 110 "localhost:52600/sec/filings/$q" -w "\nHTTP %{http_code}\n" | python3 -c "
import sys,json; t=sys.stdin.read(); b,_,c=t.rpartition('\nHTTP ')
try:
  d=json.loads(b); f=d.get('filing') if isinstance(d,dict) else None
  print({k:f.get(k) for k in ['accession','form_type','filed_date','company_name','edgar_url']} if f else str(d)[:300]); print('n_sections', len(d.get('sections') or []), 'total_chars', d.get('total_chars'))
except Exception as e: print(b[:300])
print('HTTP', c.strip())"
done

P=http://127.0.0.1:52607
for q in "0000320193-25-000079?identifier=AAPL" "0000320193-24-000123?identifier=AAPL" "0000320193-21-000105?identifier=AAPL" "0000320193-17-000070?identifier=AAPL" "0000320193-21-000105/sections?identifier=AAPL&form_type=10-K" "0000320193-18-000145/sections?identifier=AAPL" "0001193125-13-160748?identifier=MSFT" "$MSFT50?identifier=MSFT" "$MSFT50?identifier=MSFT&form_type=10-Q"; do
  curl -s -m 110 "$P/sec/filings/$q" -o /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard7/sec-tmp.json -w "$q -> %{http_code} %{time_total}s " ; python3 -c "
import json
try:
  d=json.load(open('/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard7/sec-tmp.json'))
  if 'filing' in d: print('form',d['filing'].get('form_type'),'filed',d['filing'].get('filed_date'),'sections',len(d.get('sections') or []),'chars',d.get('total_chars'))
  elif 'sections' in d: print('sections',len(d['sections']))
  else: print(str(d)[:200])
except Exception as e: print('ERR',e)"
done
echo DONE

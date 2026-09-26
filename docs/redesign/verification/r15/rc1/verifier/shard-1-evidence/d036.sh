for s in JONJUA DAL; do for pass in cold warm warm2; do
  curl -s -m 280 -o /tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard1r2/d036-$s-$pass.json -w "$s $pass %{http_code} %{time_total}s\n" -H 'X-Vysted-Region: IN' "http://127.0.0.1:52601/history/$s?timeframe=1d&range=1y"
done; done

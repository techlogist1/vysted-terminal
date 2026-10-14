# free-investor-1 — "cheapest P/E" screen: does a one-off or loss-maker top the list as a bargain?

Probe: POST /screener/run on my binary stack (:52810), custom universe of 10 large/mid IN names incl. IDEA, sorted P/E ascending.
Raw: raw/investor/free1.json, raw/investor/free1-idea.json.

## Observed
- IDEA.NS tops the list at P/E 3.62 with forward P/E -8.54, P/B -3.83, ROE -104.6%, D/E -5.38 shown beside it — the negatives that tell an
  investor the 3.62 is not a bargain are on the same row. Cross-checked off-app (screener.in): TTM EPS about 3.45 is real and comes from a
  one-off other-income line, so 3.62 is the true trailing multiple, not a data error.
- TATAMOTORS.NS skipped with reason rate_limited and counted in skipped_count (disclosed, not silently dropped).
- /fundamentals/IDEA 429 returns a humanized rate_limited body with an action; /fundamentals/IDEA/income returns an empty period set
  with provider yfinance and no error (Yahoo throttled; empty rather than fabricated).

VERDICT free-investor-1: pass

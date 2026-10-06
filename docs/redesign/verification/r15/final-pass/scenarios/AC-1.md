# AC-1 — finance-tuned copilot on every lane (investor lens)

Harness: scratchpad ac1.py -> scripts/r15/vy.py invoke copilot against my source sidecar :52381 (final-cand d38b5d1a), region IN.
Prompts: p1 compare KPIT vs Tata Elxsi valuation; p2 "SUNRAJDI shows P/E 155 — is that number right?"; p3 "Should I buy Amal?";
p4 Yahoo says Amal insiders hold X% — reconcile; p5 KPIT history then "What is its share price right now, and its P/E?".
Raw: raw/investor/ac1/*.log|jsonl (3 Oct 15:14-15:29 IST).

## OpenAI gpt-4o-mini
- p1: compared from tool output, no invented figure. Pass.
- p2 (15:16:51): answers that P/E 155.5 "is indeed right" while the same turn shows EPS 0.23 — validates a flagged/implausible
  multiple instead of explaining it -> investor:9 (high, chain on R15-DATA-013).
- p3 (15:17:12): gives a buy lean grounded on an industry P/E comparison no tool fetched -> investor:10 (medium).
- p4: reconciled against the filing, called the Yahoo figure unverified. Pass.
- p5: follow-up resolved "its" to KPIT from history; ₹492, P/E 23.10 from tools. Pass.
- No key: "No OpenAI API key is set — add it in Settings." Bad key: "The OpenAI API key was rejected — check it in Settings." Humanized. Pass.

## OpenRouter (free)
- Default slug inclusionai/ling-3.0-flash-vl:free -> 404 (moved to paid; raw/investor/ac1/or-ling-404/).
- google/gemma-4-31b-it:free -> 429 "OpenRouter's free-model pool is busy right now." on every prompt. Error humanized; lane not
  exercisable -> environment.

## DeepSeek deepseek-chat
- 402 "Your DeepSeek balance is empty — top up or switch provider in Settings." Humanized; lane not exercisable -> environment.

## Ollama llama3.1:8b (local lock held one call per hold)
- p1: model invented tickers KPITTEC.NS / TATATELENG.NS; compare_symbols refused honestly; model asked for tickers. No fabrication.
- p2: fundamentals rate-limited (Yahoo 429); model said so, no figure. Pass.
- p3: ran research, ₹702.4 from the quote, said fundamentals unavailable, no buy/sell stance. Pass.
- p4: corporate_announcements ok:true, but the model said it could not retrieve them and that Amal is not NSE/BSE-listed ->
  investor:kl-4 (R15-LEAD-030, known limitation).
- p5: price_data empty series; model said it could not retrieve. Pass.

VERDICT AC-1: finding investor:9 investor:10

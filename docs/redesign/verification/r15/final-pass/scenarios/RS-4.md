# RS-4 — FAST research on an uncached Indian name (investor lens)

Lane: copilot, gpt-4o-mini via `scripts/r15/vy.py`, research_depth normal. Raw: `raw/investor/rs4-openai.log|.jsonl`, plus the two earlier first-brief runs `kpit-ollama.log` and `rs1-ollama-normal.log`.

Port note: the catalogue names :52815 (seed copy), but `vy.py` refuses non-GET calls outside 52100-52399 (vy.py:310). So the LLM drives ran on my own extra source sidecar :52381 (final-cand, clean stranger-profile copy `final-adv-investor-vy`, started 15:10 IST; nothing cached there for these names).

| run (time IST) | name | legs |
|---|---|---|
| 15:11 ollama | KPITTECH | price timed out after 6s, dropped; fundamentals rate-limited (Yahoo 429); "pulled 2/4" |
| 15:15 ollama | SUNRAJDI | fundamentals timed out after 6s, dropped; "pulled 3/4" |
| 15:21 openai | MANIKA (Manika Plastech, NSE) | filings, price AND fundamentals each timed out after 6s; "pulled 1/4"; 14.7 s total |

- This matches DECISIONS 4.1: on a name's first brief, FAST drops the fundamentals card (and price on a cold path). The degrade is honest: the brief's derived metrics are all null, nothing is fabricated, and the answer says the data "could not be retrieved at this moment due to a timeout".
- Option (a) in 4.1 assumes "the model then fetches fundamentals itself". In the MANIKA run gpt-4o-mini did not: it stopped at the staged brief and an overview open, and offered to fetch more. So the stranger's first brief for a new small-cap carries only identity fields (ticker, ISIN, BSE code, face value).
- Attached to DECISIONS 4.1 in ATTACHED.json (key investor:att-rs4-decisions41). Nothing new filed.

VERDICT RS-4: known_limitation investor:att-rs4-decisions41

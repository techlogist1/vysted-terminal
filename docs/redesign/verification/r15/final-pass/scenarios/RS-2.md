# RS-2 — deep research on an obscure IN small-cap with a common-word name (investor lens)

Target: Focus Lighting and Fixtures (NSE: FOCUS). Run: vy invoke copilot, :52381 (source sidecar at final-cand d38b5d1a),
provider openai / gpt-4o-mini, research depth deep, 2026-10-03 15:22-15:25 IST.
Raw: raw/investor/rs2-openai-deep.log, raw/investor/rs2-openai-deep.jsonl. Spend about $0.004.

## Observed
- Off-target headlines kept as sources: livemint "Flydubai pilot Smit Machchhar's old podcast resurfaces ... 'Focus on flying, not selfies'"
  and ET "European shares edge higher after bonds-driven selloff, focus on inflation data".
- Rounds 2-8 of the IterResearch loop researched the podcast's effect on FOCUS, repeating the same sub-questions.
- Brief "Sentiment Analysis" states as fact: "A resurfacing podcast featuring Smit Machchhar has caused a negative sentiment score of -0.6369,
  which may affect FOCUS's brand perception and sales [8]" and "FOCUS aims to counter negative sentiments related to the podcast by promoting
  safety and skill in aviation [8]". The company makes lighting fixtures; none of this is about it.
- Brief also prints "P/E Ratio: 71.18" as a plain fact beside EPS 0.86, with no caveat, while the gate's flag gives an implied P/E of about 62.9.
  Same class as investor:3 / investor:9 (flagged P/E shown unqualified); recorded here, not filed separately.
- Deep wall respected (179.5 s of 180 s).

## Root cause (code read)
sidecar/services/research/relevance.py:
- `_entity_signals` (:650-690): a >=4-char symbol or brand token appearing in the title is a DISTINCTIVE signal (score 1.0 outright).
  brand_tokens("Focus Lighting and Fixtures") includes "focus".
- `_strong_entity_score` (:746): the COMMON_WORD_TICKERS gate (FOCUS is listed, :313+) and the anchored-ticker requirement apply only when
  `not is_india_target(target)`. An IN target with a common-word symbol therefore matches any headline containing the English word.
- `gate_news` (:855-887) uses this same row_relevant for both news and deep researcher pulls.

## Register check (R3)
R15-RESEARCH-001 (fixed): a deep brief states another company's news as the target's facts — same symptom, now on an IN target -> NEW regression.
R15-LEAD-056 (open): company alias that is a common word — overlapping cause; noted in the finding.

VERDICT RS-2: finding investor:12

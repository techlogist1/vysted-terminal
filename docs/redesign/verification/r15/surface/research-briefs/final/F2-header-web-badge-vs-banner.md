# F2 — Brief header says "web + structured data" while the banner below says "Structured data only — no web sources found"

Head d38b5d1a. Live DEEP run `01-normal-coforge-llama.{jsonl,stdout.txt}` (ollama llama3.1:8b, :52344): web searches ran
(sidecar log: mojeek 403 for every Coforge query) and the brief published `web_available: False` with 7 sources =
5 NSE/BSE filing PDFs (https, source_type filing) + vysted://price + vysted://fundamentals.

Panel (scratch jsdom harness, `replay-01-coforge-and-states.json`) renders, in one header:
`DEEPweb + structured dataEOD as of 2026-10-03Coforge — latest quarterly resultsStructured-data-only briefStructured data only — no web sources found for COFORGE.`

Code at d38b5d1a:
- `src/modules/research/BriefPanel.tsx:178-183` — header ProvenanceBadge: `(brief.sources ?? []).some((s) => /^https?:\/\//i.test(s.url)) ? "web + structured data" : "structured data"` (any https row, filings included).
- `src/lib/host-actions.ts:192-201,297` — `isWebSearchSource` excludes `filing`/`news` rows (R15-RESEARCH-041 fix); BriefPanel.tsx:774/881 banner keys on it.
Two definitions of "web" in one panel. This exact residual ("exchange PDF rows flipping it to 'web + structured'") is
named in R15-RESEARCH-041's refuter evidence; the 041 fix (banner) holds, the header was not brought along.

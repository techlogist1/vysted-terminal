# Final-pass owner drive — research-briefs @ d38b5d1a

Driver: claude-opus-5-5 (effort high), label final-drive-research-briefs. Reads went to shared :52800 (read-only); writes and agent turns went to my own source sidecar :52344, which used the final-cand tree. That move is logged as a DECISION in logs/final-drive-research-briefs.md, because vy.py refused non-GET calls to :52841. The panel was rendered with a jsdom replay of the live jsonl through streamAgentInvocation → applyHostAction(publish_brief) → `<BriefPanel/>`. Raw evidence is in `docs/redesign/verification/r15/surface/research-briefs/final/` (E/ below).

## Scored table

| # | Control / state | Score | Evidence |
|---|---|---|---|
| 1 | Brief empty state | ok | E/replay-01-coforge-and-states.json: "Ask JARVIS to research a company…" |
| 2 | Brief in-flight state | ok | same file: "Researching — DEEP…" |
| 3 | Populated DEEP brief (Coforge, llama) | ok | E/01-normal-coforge-llama.*: synthesis 51.7 s, degraded_reason null, publish ack 200 |
| 4 | Populated ULTRA brief (Data Patterns, gpt-4o-mini) | ok | E/03b-*: brief 1 at 288 s, markers [1],[2],[4],[11],[12] all map |
| 5 | Populated FAST brief, cold name | broken | E/05-normal-tataelxsi-llama-clean.*, E/replay-05-tataelxsi.json: price + fundamentals timed out at 6 s; the panel shows 0 sources, no cards, no mention of the dropped legs (new finding :4; price half attached to LEAD-128). 3 of 3 runs (02, 04, 05) |
| 6 | Depth slider normal/deep/ultra floor | partial | the floor works (research.py:314-323), but ULTRA lifts every call of a turn: 4 heavy runs, ~$1.25 (finding :3) |
| 7 | Citation markers → sources (RESEARCH-001/003) | ok | E/replay-03b-ultra-first-brief.json |
| 8 | Grouped markers [1, 12] (RESEARCH-043) | partial (attach) | still dead text live; blocked_tier4 |
| 9 | Cross-check verify (RESEARCH-002/004) | ok | 03b "0 verified, 5 unverified", figures intact; E/06 exact strings → unverified |
| 10 | LEAD-060 `_UNVERIFIED_ -` verdict parse | broken (attach, open) | E/06-direct-code-repros.txt → still "agree" |
| 11 | Source tiering (RESEARCH-007) | ok | E/06: Medium/WordPress tier 3, Reuters tier 2 |
| 12 | Auto-publish unique `__autobrief` ids + ack (AGENT-046) | ok | acks.json 200 for every run |
| 13 | kept_previous divergence notice under auto (UI-054/AGENT-031) | ok | E/04-normal-mastek-llama-auto-keptprev.*: step_kind notice. Under ask no notice appears, by design |
| 14 | No-web banner (RESEARCH-041) | ok | replay-01/03b banner "Structured data only — no web sources found" |
| 15 | Header provenance badge vs banner | partial | the header says "web + structured data" above the banner (finding :2, low) |
| 16 | vysted:// rows as chips, no anchor (UI-080) | ok | replay-01: no vysted anchors |
| 17 | No-web note truthfulness | broken | "No web-search backend configured" when the engines are only cooling down (finding :1, E/08 repro) |
| 18 | Rate-limited note (05) | ok | "Web search was rate-limited — retry in a moment", web_reason rate_limited |
| 19 | Search status / SearXNG per-engine reasons (RESEARCH-028) | ok | E/04-search-status.json, E/05-searxng-status.json |
| 20 | Stop mid-run cancels (AGENT-002) | ok | 03b client stopped at 604 s; OpenAI calls stopped within 2 s |
| 21 | Bad key humanized (AGENT-027 401 row) | ok | E/07-badkey-humanize.*; the entry stays open, only the 401 row was checked |
| 22 | source_floor marker (RESEARCH-042) | partial | computed on the sidecar side but never rendered; the header shows "0 sources" |
| 23 | Favicon onError fallback | NEEDS-GUI | NEEDS_GUI.md |
| 24 | Export .md/PDF/PNG (UI-083) | NEEDS-GUI | NEEDS_GUI.md |
| 25 | openbb-mcp child death mid-research (LIFECYCLE-005) | not induced | the MCP is shared; code-verified in earlier rounds |

Counts: ok 16, partial 4, broken 3, needs_gui 2, not induced 1.

## Census → final deltas

- FAST cold-name brief: in the census, the KPIT FAST brief was populated with metric cards. Now 3 of 3 runs are empty because the fundamentals leg takes 9–16 s against the 6 s box. Kind: new_defect (:4). It is not scored as a regression, because the census name was warm.
- No-web wording: in the census the backend was healthy. Under breaker cooldown the note now falsely says "not configured" (:1).
- Rows newly ok since the census and the rc rounds: UI-080 (chips), RESEARCH-041 (banner), UI-054 notice under auto, AGENT-046 ack.
- Residual of RESEARCH-041: the header badge contradiction (:2).
- ULTRA fan-out cost (:3) was not exercised in the census.

## Known limitation (R4)

Sonata on llama: the chat stated "market cap ₹1.14 crore" while market_cap was None. Filed against R15-LEAD-030 in KNOWN_LIMITATION_INSTANCES.json.

## Spend

The 03b gpt-4o-mini ULTRA run cost about $0.70 before the client stop; it is recorded as a manual row in spend-ledger.jsonl. The other runs used local llama.

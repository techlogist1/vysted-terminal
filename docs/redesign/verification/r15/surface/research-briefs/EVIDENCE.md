# surf-S2A / research-briefs — owner-drive evidence (agent A)

Model: claude-opus-5-5 (agent A — see `_TWIN_AGENTS.md`: a second agent B drove the same group
concurrently; B's files here are `10-*`, `11-*`, A's are `r*-`, `replay-*`, `http-log.jsonl`).

Rig: own sidecar from source on `127.0.0.1:52218`, data dir
`scratchpad/vysted-iso/seat-research-briefs/data` (sqlite `.backup` of `vysted-iso/data`, keyless
keystore seed, `audit_log.db` not copied), MCP env pointing at the shared read-only
`:52153`/`:52154` binaries. Pids: `scratchpad/vysted-iso/pids-surf-S2A.json`.

Drive method: every LLM turn through `scripts/r15/vy.py invoke` via `harness/turn.py`, which plays
the frontend exactly as `src/modules/chat/streaming.ts:148-180` does (prompt, `context_snapshot`
with a `__terminal__` block, `options.history`, `options.research_depth`, autonomy) and POSTs
`/agents/actions/ack` for host actions the way `src/lib/host-actions.ts:1452-1487` does. The
PANEL half is proven by `harness/replay.probe.test.tsx`: each live SSE transcript is replayed
through the real `streamAgentInvocation` normaliser -> brief lifecycle store -> `applyHostAction
("publish_brief")` -> `render(<BriefPanel/>)`, and the rendered text is dumped to
`replay-*.json` (scratch vitest config, nothing written under `src/`).

Machine note: agent B was driving llama3.1:8b on the same ollama at the same time (plus three
Delegate runs), so local-lane wall times below are contended upper bounds.

## Runs

| file | lane | depth | autonomy/ack | result |
|---|---|---|---|---|
| `r0-429-gemma-free` / `r0-429-qwen-free` | OpenRouter `:free` | normal | auto | 429 error frame "OpenRouter is rate-limiting your account" — the provider said `limit_source: upstream_provider_shared_pool` (not the user's account); detail blob carries the OpenRouter `user_id` |
| `r0-5xx-nemotron-free` | OpenRouter `:free` | normal | auto | `provider_5xx` "OpenRouter returned a server error" — honest |
| `10-normal-kpit` (B) | ollama llama3.1:8b | normal | auto/applied | FAST bundle, 6 web sources, **empty markdown** (model writes prose), `backend: keyless-fallback`; replay `replay-10-normal-kpit.json` renders metric grid + "Limited keyless search — set up Unlimited local research" nudge |
| `r2-deep-cgpower` | ollama llama3.1:8b | deep | auto/applied* | 592 s; synthesis step latency 60014 ms (= `_LLM_CALL_TIMEOUT_SECS` 60) -> **structured floor** body "Web coverage for this name is thin" while 13 web + 5 filing URLs were captured; 0 `[n]` markers; raw floats in prose |
| `11-deep-bdl-llama` (B) | ollama llama3.1:8b | deep | auto | same signature: synthesis 60007 ms -> floor "Web coverage for this name is thin" |
| `r4-deep-bluestar-4omini` | OpenAI gpt-4o-mini (paid, $0.0038 on the ledger; justified: local lane provably times out DEEP synthesis 2/2) | deep | auto/applied | real IterResearch brief, 5 rounds, 13 sources — but **15 of 15 `[n]` markers point at the wrong document** (see finding 1) |
| `r3-ultra-kaynes` | ollama llama3.1:8b | ultra | auto/**kept_previous** | see below |

*`r2` ack: the harness's ack parser missed the 20 KB publish line (harness bug, fixed after —
`--max-event 50000000`), so r2's end-of-stream "The brief panel did not confirm the publish"
notice is a harness artifact, NOT a product defect; the real frontend acks `__autobrief`.

## Finding 1 — DEEP brief citations point at the wrong documents (live)

`r4-deep-bluestar-4omini.jsonl` publish_brief markdown: "Closing Price: ₹1,525.0 … [6]",
"Market Capitalization ₹313.53 billion … [7]", "P/E Ratio 61.67 … [7]", margins, "Rising oil
prices … [7]", "divestment of the MedTech business … [7]" — 15 markers, all `[6]`/`[7]`.
The published `sources` list (the rail the panel numbers 1..13, `replay-r4-…json`
`sourcesRendered: 13`, body renders chips `6`/`7`):

- `[6]` = `nsearchives…/BLUESTARCO_07082026214714_FinancialsQ1FY27Communicationtoshareholders.pdf`
- `[7]` = `nsearchives…/BLUESTARCO_06082026143619_BSLBMchangeindirectors06082026.pdf` — fetched:
  "Sub.: Change in Directorate … approved appointment of Mr Nikhilesh Panchal … as an
  Additional Director" (a director-appointment letter; no price, P/E, margin or oil content).
- the figures actually came from `[11] vysted://price/BLUESTARCO` and `[12]
  vysted://fundamentals/BLUESTARCO`.

Mechanism: round 1 distilled "8 source(s)" (step 7), round 2+ "13 source(s)" (step 13).
`_Findings.all_sources()` (`sidecar/services/research/deep.py:356-373`) puts ranked web/filing
sources FIRST and structured provenance LAST, and `_numbered_sources`
(`sidecar/services/research/iter.py:127-129`) renumbers from that list every round. With 5
filings in round 1, price/fundamentals were `[6]`/`[7]`; the working report carried those
markers forward; round 2 inserted 5 more filings ahead of them (now `[11]`/`[12]`) but the
report text keeps `[6]`/`[7]` and the final synthesis (`iter.py:223-260`) copies them. The
citation check only strips OUT-OF-RANGE markers ("stripped 0 out-of-range marker(s)"), so an
in-range-but-stale marker ships. Figures verified correct against screener.in (price 1,525,
mcap ₹31,356 cr) — the numbers are right, the provenance is wrong.

## Finding 2 — local-lane DEEP always ships the structured floor, blamed on "thin web coverage"

`r2-deep-cgpower` step trace: `round overran its 90s slice — winding down`, `synthesize | wrote
brief from evolving report | 60014 ms`, `audit skipped (-60s wall remaining < 15s)`. B's
`11-deep-bdl-llama`: synthesize 60007 ms, same body. `oneshot.complete(timeout=60)`
(`deep_research.py:69,322-325`) returns the partial/empty text, `iter.py:261-270` falls through
to `build_structured_floor` (`deep.py:523-556`), whose fixed copy says "_Web coverage for this
name is thin; this brief is built from exchange data and filings gathered this run._" — while
the same brief carries 13 http web URLs + 5 filings. The panel header renders "DEEP · 21 sources
· web + structured data" (`replay-r2-deep-cgpower.json`), `execution.degraded_reason: null`, no
note — nothing tells the user the synthesis step died. The body does not address the question
(order book / margins / peers) at all, and prints raw floats ("change % -1.527472527472525",
"market cap 1411777036288.0", no currency/unit).

## Finding 3 — SearXNG "ready" but serving nothing: Settings and the brief contradict

- `GET /search/searxng/status` (my sidecar, `http-log.jsonl`): `state: ready`, "SearXNG serving
  JSON search at http://127.0.0.1:8888".
- The same container, one read-only query: `results: 0`, `unresponsive_engines: [["brave","too
  many requests"],["duckduckgo","CAPTCHA"],["startpage","Suspended: CAPTCHA"]]`.
- The briefs whose web leg ran published `backend: keyless-fallback` (`10-normal-kpit`, `r2-deep-cgpower` — r2's 13 http URLs all came off the keyless floor); r3/r4 report `backend: native` with ZERO http web sources (only exchange filings + `vysted://`), i.e. web retrieval returned nothing usable at all.
- Health probe `sidecar/services/searxng_manager.py:161-179` counts any `results` LIST (empty
  included) as healthy and ignores `unresponsive_engines`; `web_search.py:148-166` then silently
  cross-checks every empty answer on the keyless floor.
- UI: Settings renders "Running at http://127.0.0.1:8888 — research searches route through it
  automatically." (`src/components/SettingsPanel.tsx:908-913`) while every brief renders
  "Limited keyless search — set up Unlimited local research for full capability."
  (`src/modules/research/BriefPanel.tsx:356-365`) — a remedy that is already done. The real
  cause (the container's upstream engines are CAPTCHA-blocked) is never surfaced anywhere.

## Finding 4 — structured-provenance sources render as external links

`replay-*` rails include `vysted://price/<SYM>`, `vysted://fundamentals/<SYM>`,
`vysted://news/<SYM>`; `SourceRow` (`BriefPanel.tsx:223-262`) renders every source as `<a
href={source.url} target="_blank">` with an ExternalLink icon and a Google-S2 favicon for the
bare provider id (`nse_direct`, `yfinance`). What a click on a `vysted://` href does inside the
Tauri webview: NEEDS-GUI.

## Other observations (not raw findings)

- FAST/NORMAL bundles publish with empty markdown by design (the model writes prose) — the
  panel shows metrics + sources only until the model re-publishes.
- Model narration on the local lane misreads fractions as percents ("revenue growth rate of
  0.14%", "change of -13.899999999999977%", `r2-deep-cgpower.stdout.txt`) — a weak-model
  failure; the PANEL's own metric cards format correctly (+14.00%, -1.53%).
- "Lloyd" (a Havells brand) resolved to three unrelated `LLOYDS*` listings (`r4` assistant
  text) — resolver ambiguity; out of this group.

## ULTRA (`r3-ultra-kaynes`, llama3.1:8b, research_depth=ultra, ack kept_previous)

- Depth floor works: the model called `research {depth: "deep", query: "Kaynes Technology —
  latest quarterly results"}` (it also narrowed the user's question), the slider's `ultra` won:
  `execution.requested_depth: ultra, loop: heavy` (`sidecar/services/agent_tools/research.py:160-166`).
- All three angle syntheses 60001-60012 ms (the same 60 s cap as Finding 2); merge 53 s.
- Published body: literal `[n] 1` pseudo-markers, a model-invented "Merged Sources" (7 rows) and
  "References" (7 rows) list, while the real `sources` are 3 `vysted://` rows and 0 web.
- `## Cross-check` rows: `UNVERIFIED — 232253702144`, `— 13953`, `— 5%`, `— 4%`, `— 16%` for body
  figures 67.13953 / 40.5% / -0.4% / 55.16% (`_split_subquestions`, `deep.py:179-202`, strips a
  leading `<digits>.` as a list ordinal). Step: "cross-check: verified 5 numeric claim(s), 0
  disagreement(s)".
- End-of-stream notice for the kept_previous ack: "The panel kept the brief already on screen —
  this publish did not replace it; do not claim the new one rendered." — not matched by
  `message-notices.ts:57` `DIVERGENCE_RE`, so the chat files it as a trace row.
- `applyHostAction` labels it "Published the DEEP research brief" while the header renders
  "HEAVY · deepest" (cosmetic).

Agent B's `13-ultra-hal-4omini` (gpt-4o-mini) reproduces the cross-check mangling ("P/E 34.42" ->
"UNVERIFIED — 42", "51.70%" -> "70%", "14.4%" -> "4% year-over-year") and the stale-citation bug
("Closing Price ₹4,800.0 [1]" -> [1] is a BSE Change-in-Directorate PDF; "Market Capitalization
[2]" -> HAL_…_changeindirector_signed.pdf). B's `12-deep-bdl-4omini` is the control: its source
list stayed at 8 every round and its [6]/[7] markers land on vysted://price/fundamentals.

## tier_b without an OpenRouter key (`r5-tierb-nokey-dixon`)

`X-Vysted-Research-Tier: tier_b`, no `X-Vysted-Openrouter-Key`: research returned the
needs-a-key message (`deep_research.py:632-639`), the model relayed it ("add an OpenRouter API
key in Settings → Research or switch back to Unlimited (Local)"). Panel: `research:begin` ->
in_flight -> done-without-publish -> `failRun` -> empty invite (`replay-r5-tierb-nokey.json`);
the panel itself says nothing about why. Honest overall (the chat carries it).

## Spend

One paid call (`r4`, gpt-4o-mini, ledger est $0.00378 — the research loop's own ~15 internal
LLM calls are not metered by the ledger, see COD-research-extraction-synthesis-2); every other
call local or `:free` (3 free calls all failed upstream).

## Sidecar

`:52218` left RUNNING at the end of agent A's drive because agent B still had live connections
to it (see `_TWIN_AGENTS.md`); stop = kill sleep pid 95303 (`pids-surf-S2A.json`).

## Agent B late additions (08:05-08:12, own sidecar pid 15507 on :52218, MCP pair :53217/:53218)

- **Stale auto-publish ack (SURF-RESEARCH-BRIEFS-12).** `30-staleack-run1-noack-fresh.*` (fresh process, no ack): the
  "did not confirm the publish" notice fires. `33-staleack-prior-ack-rerun.txt`: a panel ack for id `__autobrief` posted at
  08:06:03. `36-staleack-run2-final.*`: a different research turn, NO ack from any client, auto-publish `__autobrief` at
  08:12:02 (inside the 600 s TTL): zero notices, model says "Built a brief on Mazagon Dock Shipbuilders." `31/32-*` are
  invalid (sidecar killed mid-run, not by B).
- **openbb-mcp child down (SURF-RESEARCH-BRIEFS-13).** `35-openbb-mcp-down-stream-dies.txt`, `34-staleack-run2-rerun.*`:
  with the child gone, `/fundamentals/*` 500s, the agent SSE is cut with no terminal frame and `/openbb-mcp/status`
  still reports available. Restarting the child restores 200s.
- **Zero-web banner unreachable (SURF-RESEARCH-BRIEFS-11).** Every zero-web brief in this group (12, 13, 36) carries
  vysted:// / exchange rows, so `webAvailable` is true (`src/lib/host-actions.ts:228`).

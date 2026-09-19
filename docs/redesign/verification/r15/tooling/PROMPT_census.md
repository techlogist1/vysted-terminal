# Census task specs (Data packs, Intent, World, Ideation, Lifecycle)

Paths are relative to the repo root. `CENSUS` = `docs/redesign/verification/r15/census`,
`BATTERY` = `docs/redesign/verification/r15/battery`.

## PACK — outside-truth reference pack for one battery name

Your name is the entry whose `slot` equals your `<slot>` in `BATTERY/manifest.json` (read it:
symbol, name, exchange, bse_code, hostile traits). Build the OUTSIDE-TRUTH pack the in-app
values will be diffed against. Load web tools via ToolSearch (`select:WebSearch,WebFetch`).
Be polite to exchanges (≤1 req/sec/host).

Sources in order of authority: exchange filings and exchange quote pages (bseindia.com,
nseindia.com / nsearchives — shareholding pattern, results, corporate actions,
announcements), the company's investor pages / annual report, then screener.in-grade
aggregators (screener.in, Tijori, Trendlyne, Moneycontrol; for US names SEC EDGAR, company IR,
a major quote page). Where two good sources disagree, record BOTH with as-of dates — that is
a finding for the differ, not something to smooth over. Never fabricate: a value you could
not find is a recorded gap.

Fields (each: `value`, explicit `unit` e.g. "INR crore", `as_of`, `source_url`): identity
{legal_name, former_names + rename date, isin, bse_code, nse_symbol, board (mainboard/SME),
sector, industry, listing_date}; price {last_close, date}; market_cap; pe_ttm (or
"loss-making"); pb; roe; roce; debt_to_equity; revenue_ttm; net_profit_ttm;
revenue_growth_yoy (state basis); eps_ttm; book_value_per_share; face_value; dividend
{last_declared_per_share + record/ex date, paid_trailing_12m_per_share, yield}; week52 {high,
low}; shareholding for the LATEST filed quarter {quarter, promoter_pct, fii_pct, dii_pct,
public_pct, pledged_pct_of_promoter}; corporate_actions_2026; latest_results {quarter,
filing_date}; last_3_announcements {date, headline, url}; consolidated_vs_standalone note.
Plus `traps` (what would fool an automated pipeline: lakh/crore scale, same-named foreign
entity, stale aggregator pages, pre-split/bonus prices, SME lot sizes) and `world_gaps`
(fields that genuinely do not exist vs fields you merely could not reach).

Output file: `BATTERY/packs/<slot>_<SYMBOL>.json` (one JSON object, plus
`"collected_at": "2026-09-19"`). Legacy partial files from a dead attempt may exist as
`BATTERY/packs/<SYMBOL>.json` or a tiny stub at your target path — if it is YOUR entity
(careful: AMAL and SMR each appear twice, one Indian and one US), absorb it and continue.

## INTENT — verify a chunk of promises against the code

Open `CENSUS/intent/promises-<source>.json` and take the promises at array indexes
`[<start>, <end>)`. For EVERY one, determine from the ACTUAL CODE and tests (open the files;
use `graphify-out/GRAPH_REPORT.md` or grep to locate) whether it is `delivered` (cite
file:line proving it), `partial` (say exactly what is missing), `missing`, or `dropped`
(deliberately — cite the decision reference: a D-number in `docs/redesign/DECISIONS.md`, a
BLUEPRINT/spec amendment, or the out-of-scope list in COMMON.md). A promise whose delivery you
cannot confirm from code is `partial` or `missing`, never assumed delivered. Read-only GETs
against `http://127.0.0.1:52152` (`/openapi.json`, `/agents`, `/health`) may confirm a route
exists.

Output files: (1) `CENSUS/intent/ledger-<source>-<start>.json` — the promises with added
`{status, evidence, gap, decision_ref}`. (2) `CENSUS/raw/intent-<source>-<start>.json` — a RAW
FINDING (prefix `INT-<source>-<start>`) for every partial/missing promise that STILL MATTERS
for a public 0.9.0 release of this product vision (skip promises a recorded decision made
obsolete — those are `dropped`). Return counts by status.

## WORLD-RESEARCH — harness state of the art

Research the state of the art in AGENT-HARNESS design as of September 2026 for your `<topic>`:

- `harness-context`: context engineering (compaction, just-in-time retrieval, tool-result
  clearing, structured note-taking / memory files, sub-agent isolation), memory (episodic /
  semantic, user-scoped stores, claims ledgers), recovery (retries, checkpoints, resumable
  runs, budget guards, loop detection, fallback models).
- `harness-tools`: tool design (few deep tools, namespacing, response-format control,
  token-efficient results, error messages that steer, idempotency), evals (scenario
  harnesses, programmatic + LLM-judge scoring, regression suites, trajectory checks, pass^k),
  provider-quirk handling (tool-call formats, reasoning params, streaming differences,
  capability gating).

Load web tools via ToolSearch (`select:WebSearch,WebFetch`). Prefer primary sources (Anthropic
/ OpenAI / Google engineering posts and docs, well-known papers, respected practitioner
write-ups); ≥12 distinct sources; URL + quote for every claim. Output file:
`CENSUS/world/<topic>.md` ending with a crisp CHECKLIST of 15-25 concrete practices, each with
a one-line rationale and its source.

## WORLD-COMPARE — compare the in-app agent against the research

Input research file: `CENSUS/world/<topic>.md` (for `agent-native-ux` it already exists). Read
the REAL code: `sidecar/services/agent_runtime.py` (invoke loop, tool rounds, ack / read-back,
divergence notices, auto-publish), `sidecar/services/agent_tools/` (catalog.py, schemas.py,
handlers, action ledger), `sidecar/services/llm/*` (adapters, retries, native search),
`sidecar/services/run_manager.py` + `runs_store.py` + `budget_guard.py`,
`sidecar/agents/*.json` (prompts, tool allow-lists), `src/modules/chat`, the composer,
`host-actions.ts`, `proposed-changes.ts`, the context snapshot / terminal preamble / claims
ledger. For EACH practice or pattern in the research mark: present (file:line), partial,
absent, or not-applicable (say why for a local BYOK finance agent).

Output files: (1) `CENSUS/world/<topic>-COMPARE.md` — the comparison table. (2)
`CENSUS/raw/world-<topic>.json` — a RAW FINDING (prefix `WLD-<topic>`) for each REAL gap
(absent / partial AND it would change user outcomes), each with an owning subsystem and the
file:line where it would live. Do not pad.

## OPP-LEDGER — assemble the opportunity ledger

Read every `CENSUS/world/*.md` that exists (perplexity-screener, openbb-kite-mcp,
fey-tijori-trendlyne, investor-asks-forums, agent-native-ux). Write
`CENSUS/OPPORTUNITY_LEDGER.md`: deduplicated opportunities ranked by (evidence strength × fit
with the moat: data trust, research quality, finance-tuned agent, local-first BYOK ×
proximity to existing code). Each entry: id `OPP-<n>`, the unmet need, evidence (URLs / quotes
carried from the research files), who does it badly today, what Vysted already has that is
one step away (open the code and name the module with file:line), rough size. Separate
section: TABLE-STAKES GAPS (things competitors / agent tools all do that Vysted lacks), and a
COMPETITOR WATCH note (e.g. OpenBB's closure, Fincept Terminal) with what it changes. Also
write `CENSUS/raw/world-table-stakes.json` — RAW FINDINGS (prefix `WLD-T`) for table-stakes
gaps ONLY (opportunities are not defects; they feed Stage 4 invention, not the register).
Verify each claimed gap against the code before filing it.

## IDEATE — Stage 4 ideation seat (read-only thinking; nothing is built yet)

You are `<seat>`. Rethink this product with full creative liberty from YOUR seat. First learn
what exists: `docs/CURRENT_STATE.md`, `sidecar/services/agent_tools/catalog.py` (every agent
capability), `sidecar/agents/*.json`, the panel list under `src/modules/`, and whatever of
`CENSUS/world/*.md` and `CENSUS/OPPORTUNITY_LEDGER.md` exists (what the world lacks, with
evidence). Then answer: what would make this feel like JARVIS rather than a chatbot with
panels — initiative, watching, memory, receipts?

Evidence from the world, offered as a FLOOR and not a build list (if you return only these
you have failed — the operator asked for things he could not have thought of): Perplexity
Finance "answers, it does not watch" and has misread small-cap filings by 1000x; nobody ties
a user's written thesis to new filings and flags the contradiction; nobody shows management
guidance against delivery across quarters; pledge / related-party / bulk-block-deal /
results-day signals live in disconnected point tools with no agent stitching them to the
user's own holdings; no finance tool gives coding-agent-style receipts — the exact filing
page behind every number.

Hard constraints on every idea: lives inside the existing design system and plugin contract;
NEVER touches the order-safety surface or places orders; NEVER requires a hosted backend
(local-first, BYOK, runs on a laptop that sleeps); buildable to release grade by a small team
of agents in days, not months, on top of code that already exists.

Produce 6-9 ideas, at least 3 of which are NOT on the floor list above. For each: name; the
user moment (a concrete scene with a real Indian small-cap); mechanics (what runs when,
which existing module it rides on — open the code and cite file:line; what is new);
why it is Jarvis (initiative / watching / memory / receipts); the 60-second demo; lifecycle
cost (what breaks in six months, what it costs to keep alive); biggest risk; rough size
(S/M/L). End with your single strongest idea and why a rival could not copy it in a month.

Output files: `docs/redesign/verification/r15/invent/ideas/<seat-id>.md` and a machine-readable
`docs/redesign/verification/r15/invent/ideas/<seat-id>.json`
(`[{idea_id: "<seat-id>-<n>", name, one_liner, rides_on, new_parts, jarvis_axis, size, risk}]`).

## LIFECYCLE — answer one lifecycle question with an INDUCED test, not an opinion

Your question is `<question>` (below). You may start your OWN sidecar from source on port
`<port>` with your own data dir under your scratch/tmp dir (see COMMON.md for the exact
command), and must stop it when done. Induce failures only at the app's edge (its own config,
ports, a stubbed or blocked endpoint via env/config, a bad slug or key in a request) — never
system settings, Docker or the network. The operator's real data dir is read-only to you:
work on a copy (SQLite: `sqlite3 "file:<src>?mode=ro" ".backup '<dst>'"`, never `cp` a live WAL
db). For a CLEAN profile seed `<dir>/dev-keystore.json` with
`{"secrets": {}, "migrated": true}` (0600) — see `r15/stage0/ISOLATION_MAP.md` §2.4.

- `L1-stranger`: what does a stranger with no keys and no Docker see in the first five
  minutes? Clean profile: boot, `/health`, onboarding state, what the keyless lane can do
  (check `ollama list` first; at most ONE tiny keyless chat probe and only if a small model is
  already installed — never pull a model), what search tier is reported and whether the UI
  code surfaces it honestly (read the onboarding + settings + composer code paths), what
  every first-run panel shows with no data. List every dead end and every unexplained failure.
- `L2-rot`: six months from now a pinned model slug is retired or NSE changes an endpoint — is
  the breakage visible and explained, or silent? Induce: invoke with a retired slug through
  `scripts/r15/vy.py` (free lane, e.g. `z-ai/glm-4.5-air:free` is retired) and a nonsense slug;
  point a provider at a dead endpoint where config/env allows; feed junk upstream payloads to
  the parsers (call the provider functions directly in python with a stubbed response). Record
  exactly what the user would see for each (error frame text, logs, silent empty).
- `L3-diagnostics`: when a user says "the numbers look wrong", can they hand over a redacted
  diagnostics bundle without anyone adding instrumentation first? Find what exists (logs,
  provenance/field_meta, execution records, export paths, any diagnostics route/command), try
  to assemble one for a real symbol on `:52152`, and check it for secrets. If nothing exists,
  specify the smallest honest bundle from what the code already records.
- `L4-upgrade`: does 0.8.0 user data survive the upgrade? Copy the operator's data dir
  (safely), boot your own sidecar from CURRENT source on it, and verify every store opens,
  migrates and reads back (workspace blob restore guards, `modelOverridesV`, sqlite schemas,
  portfolio, notes, custom agents, plugins, runs). Also read how schema changes are handled
  (migrations? `CREATE TABLE IF NOT EXISTS` only?) and find any path that silently discards
  user data (see ISOLATION_MAP §3.3 D2–D4: a failed restore followed by autosave).
- `L5-bounds`: do logs and caches stay bounded on the hundredth day? Inventory every on-disk
  and in-memory store that grows (sqlite caches + WAL, exports/, logs, research artifacts,
  in-process dict caches, the autosave blob's researchSpaces / claims / notes), whether each
  has a TTL / cap / vacuum, and measure the operator's real dir (sizes only) as evidence.
- `L6-longsession`: does a session left open for hours stay stable? The operator's own
  instance has been up for days: sample its sidecar RSS/threads/fds read-only with `ps`/`lsof`
  a few times a minute apart, and code-read for leaks: intervals/listeners/subscriptions never
  torn down in `src/` (setInterval, addEventListener, zustand subscribe, EventSource),
  unbounded python dicts/lists, tasks never awaited or cancelled, sqlite connections never
  closed, the Yahoo breaker counters (954 opens / 28,382 throttles since 13 Sep — is the app
  hammering upstream while idle? find the poller and its backoff).

Output files: `docs/redesign/verification/r15/lifecycle/<id>.md` (what you induced, exact
commands, what happened, verdict) and `CENSUS/raw/lifecycle-<id>.json` (RAW FINDINGS, prefix
`LIF-<id>`).

# R8 Track A — research-truth report

Branch: `worktree-agent-r8-research`. All work verified against the live-run
regression payloads (`docs/redesign/verification/r8/regression-brief-{cmtl,saksoft}.json`
in the main repo).

## Per-deliverable summary

### D1 — ResearchTarget contract (`62ac2b8`)

- `sidecar/services/research/target.py` (new): frozen `ResearchTarget(symbol,
name, exchange, asset_class, confidence, region)` + `resolve_target` —
  resolve_symbol called ONCE on the CLEAN user query; confidence floor 0.5
  (`target.py:44`), ticker-shape gate `^[A-Z0-9][A-Z0-9.\-&]{0,19}$`
  (`target.py:50`). A `raw` field (compare-excluded) carries the full resolver
  reply so `structured["resolved"]` keeps the wire shape the frontend reads
  (`deriveAssetClass`) and candidates survive.
- Threading: `run_deep_research` / `run_iter_research` / `run_heavy_research`
  take `(target, bound)`; heavy resolves once at the top
  (`iter.py` `run_heavy_research`, "bind the ONE target" block), snapshots
  price/fundamentals ONCE and hands every explorer the SAME bound target +
  shared snapshot with `bound=True` — explorer task text (`{query} — focus:
{angle}`) never touches `resolve_symbol` or any structured tool. The merged
  heavy brief carries the ORIGINAL query + `target.symbol` (never the focus
  sentence) plus `resolved` + snapshot legs in `structured` so ULTRA briefs
  back the metric cards (the CMTL payload had none).
- `gather_fast` (fast.py) rides `resolve_target`; target `None` → WEB-ONLY
  bundle: `ok: True`, `symbol: ""`, `structured: {}`, zero structured calls,
  honest note `"No listed instrument matched this query — web evidence only."`
  (the note flows to the brief via the existing `_auto_publish_event` top-level
  note mapping — no agent_runtime change needed).
- `_run_researcher` (deep.py:471) uses `target.symbol` for ALL structured
  calls; web-only mode fires zero structured calls.

### D2 — PDF extraction (`0739bec`)

- `sidecar/services/search/extract.py`: `.pdf` URLs (and `application/pdf`
  replies on extension-less URLs, e.g. BSE `AttachHis` attachments) ride a new
  byte lane — `PDF_MAX_BYTES` 15MB cap (streamed on httpx so the cap aborts
  the download), `nseindia.com`/`bseindia.com` suffixes go straight to the
  curl_cffi impersonation lane, anti-bot wall statuses get one impersonated
  retry. `extract_pdf_text` reduces long documents to the most finance-relevant
  pages (revenue/profit/PAT/dividend/quarter/results/crore keyword + digit
  density, ≥ a fifth of the top page's score so boilerplate can't tie in),
  document order preserved, paragraph-boundary cut. `visit_for_research` widens
  the budget to `PDF_RESEARCH_MAX_CHARS` (4000) for `.pdf` URLs.
- `sidecar/requirements.txt`: `pypdf==6.13.1` (already present in the shared
  venv at that version). Verified pure-Python, literal `__version__`, zero
  deps, no package data → **no `scripts/ensure-sidecar.mjs` changes needed**.
- Other non-HTML types stay honestly rejected (`unsupported content type`).
- Tests build a real text-bearing PDF in-test via the pypdf writer.

### D3 — Disclosures in the loop (`2313c9f`)

- `sidecar/services/research/disclosures.py` (new). India-listed target +
  results/earnings/announcement/dividend/transcript-shaped sub-question →
  the researcher pulls the REGISTERED `corporate_announcements` tool alongside
  web; earnings-DATE questions also consult the NSE results calendar via
  `fetch_results_calendar` (direct service wrapper, monkeypatchable — the
  calendar has **no registered agent tool** and `catalog.py` is owned by
  another track; flagging rather than touching it).
- Announcement `attachment_url` rows become first-class citation rows
  (`verified_symbol` provenance → passes the relevance gate; `source_type:
filing`; nsearchives/bseindia suffix-match `finance.PRIMARY_DOMAINS` so they
  take the exchange tier — pinned by test) and are the researcher's PREFERRED
  visit target (the PDF lane reads them).
- Planner prompts in both loops carry `disclosures.plan_hint(target)` so
  results questions get shaped to use the feeds.

### D4 — Relevance + quality ladder (`54f4e9c`)

- `sidecar/services/research/relevance.py` (new): `entity_match(row, target=,
query=)` — symbol word-bounded (≥3 chars; `\bROUTE\b` does NOT match
  "Router") + distinctive name tokens (corporate suffixes dropped) across
  title/snippet/host; junk hosts (scribd/youtube/instagram/pinterest/facebook/
  quora) → 0; crypto data hosts (coinmarketcap/coingecko/…) → 0 for equity
  targets; SEO title patterns ("what is …", "support and resistance", "price
  prediction") → 0; `verified_symbol` exchange rows → 1.0. Floors:
  `MATCH_FLOOR` 0.34 bound / `RELAXED_FLOOR` 0.2 query-token (no target);
  no tokens at all → blacklists only.
- Integrated at `deep._record_web` (target+query threaded from both loops):
  dropped rows never become sources and never flip web coverage —
  `coverage_floor_met` therefore counts kept sources only.
- Researcher web queries: `"{target.name}" {symbol} {sub_question}` (quoted
  name) + the existing finance `site:` bias; web-only runs use
  `{query} {sub_question}`.

### D5 — Citation integrity (`d395673`)

- `sidecar/services/research/citecheck.py` (new): structural pass strips every
  `[n]` outside `1..len(sources)` (zero sources → ALL markers stripped) with
  punctuation tidy-up; bounded spot-audit (ONE `llm_call`, ≤8 numeric/dated
  claims with their cited sources' title/excerpt) removes citations from
  UNSUPPORTED claims and deterministically softens the sentence
  ("… (not confirmed in this run)"). Conservative parse: garbled/dead reply
  changes nothing. Audit gated on ≥15s remaining wall (`MIN_AUDIT_WALL_SECS`);
  skip is a dev step (`status: skipped`), never a user note.
- Runs at the end of iter synthesis (clean + abort) and over the MERGED heavy
  brief (explorers pass `citecheck=False` — the panel synthesist rewrites
  their prose; one audit covers the published body).

### D6 — Graceful guards + human notes (`1986ae7`)

- `deep.py`: `MIN_ROUND_WALL_SECS` (25s), `remaining_wall`, `BUDGET_STOP_NOTE`.
- (a) Top-of-round: remaining wall < 25s → break to the CLEAN synthesis path
  (`note=None`); dev step "stopped before a new round: Ns wall budget
  remaining". (b) Round `TimeoutError` → dev step "round overran its Ns slice
  — winding down"; with findings + ≥25s remaining, ONE wind-down round at
  `researchers=1, allow_visit=False`, then clean synthesis. The string
  "per-round wall-clock guard: round exceeded Ns" no longer exists.
- (c) `brief.note` is HUMAN ONLY: every budget breach → `BUDGET_STOP_NOTE`
  ("Stopped early to stay within the run's time budget — coverage may be
  lighter than usual."); raw ceiling reasons live on the step trace. The
  "heavy:N angles" note is gone (`structured.panel` carries angle data);
  `verify.cross_check`'s "cross-check flagged N numeric disagreement(s)" note
  is already human and unchanged.

### D7 — Structured parity (`2bf6005` + parts of `62ac2b8`)

- `agent_tools/fundamentals.py`: exactly two attempts with a 0.5s backoff
  before the honest `ok: False` (both `ProviderError` and unexpected).
- Researcher extraction prompt states leg status honestly: a failed structured
  pull reads "temporarily unavailable this run (…) — NOT evidence the data
  does not exist" (deep.py `_run_researcher`).
- Snapshot legs become citable `vysted://` sources
  (`deep.record_snapshot_sources` — coverage flags untouched) and ride every
  synthesis prompt as `deep.snapshot_context` ("these figures are REAL and
  citable … never claim they are unavailable") in iter, heavy, and the deep
  fallback.

### D8 — FAST/banner-body truth, frontend (`977a373`)

- `src/lib/brief-ingest.ts`: `sanitizeCitationMarkers` (markers beyond the
  deduped rail stripped; zero-source briefs lose ALL markers), `bodyCitesWeb`,
  `formatBriefTokens` (zero → omit), `formatBriefSpend` (zero → omit;
  < $0.005 → "<$0.01"; "$0.0000" cannot render). `composeBriefMarkdown`
  sanitizes the exported body against the deduped appendix count.
- `src/modules/research/brief-blocks.tsx`: `BriefBody` sanitizes before
  parsing (marker range == rail range); `MarkdownBody` gains opt-in
  `responsiveProse` — brief prose renders `text-body` (13px) and steps to
  `text-prose` (16px) only at `@min-[420px]` container width. Chat's usage is
  untouched (prop defaults off).
- `src/modules/research/BriefPanel.tsx`: panel root declares `@container`;
  meta header gets its collapse ladder (flex-wrap + `whitespace-nowrap` chips,
  honest symbol truncate) — no overlapping chips; token/spend segments omit
  when null; the no-web banner keys off `webAvailable` + `webReason` +
  `bodyCitesWeb`: a body that cites web domains with zero captured sources
  says "Sources were not captured for this brief", never "no web sources
  found". `note` renders only when present (unchanged conditional).

### D9 — Regression suite (this commit)

`sidecar/tests/test_research_r8_regressions.py`: (i) heavy spy-tool — every
structured-tool symbol arg is `SAKSOFT`, ticker-shaped, never contains
"focus:"; published symbol/query clean; (ii) `resolve_symbol` exactly once per
heavy run + the snapshot pulled once panel-level; (iii) a results PDF yields
its seeded numbers; (iv) crypto/SEO/junk rows never reach sources;
(v) markers ≤ len(sources) after synthesis; (vi) notes humanized across every
breach reason — pinned to never contain "wall-clock", "guard", "heavy:",
"exceeded", "abort".

## Test counts

| Suite                                                                  | Tests                                                                       |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| test_research_target.py (new)                                          | 8                                                                           |
| test_research_relevance.py (new)                                       | 12                                                                          |
| test_research_disclosures.py (new)                                     | 11                                                                          |
| test_research_citecheck.py (new)                                       | 11                                                                          |
| test_research_r8_regressions.py (new)                                  | 10                                                                          |
| test_fundamentals_tool.py (new)                                        | 5                                                                           |
| test_search_extract.py (18 → 28)                                       | 28                                                                          |
| test_research_iter/deep/fast/depth (updated fixtures + note semantics) | 48                                                                          |
| src/lib/brief-ingest.test.ts (25 → 37)                                 | 37                                                                          |
| Full sidecar suite                                                     | green (see verification snapshot)                                           |
| Full vitest + lint + typecheck + format:check                          | green (one pre-existing lint warning in EquityOverviewPanel.tsx, untouched) |

## Integration notes for the lead (contract changes)

- **Loop signatures** (`services/research`): `run_iter_research` /
  `run_heavy_research` / `run_deep_research` gained keyword-only
  `target: ResearchTarget | None = None, bound: bool = False`; iter also
  `snapshot: dict | None = None, citecheck: bool = True`. Defaults preserve
  the old call shapes — `deep_research._run_loop` is UNCHANGED (resolution
  happens inside the loops, once; the heavy panel binds before fan-out).
- **`_run_researcher`** now takes `(sub_question, *, target, query, region, …)`
  (was `symbol=`) and returns `(finding, web_res, structured_pairs: list)`
  (was a single pair). Internal to the research package.
- **`_record_web(findings, result, *, target=None, query="")`** — relevance-
  gated; rows below the floor are dropped.
- **Brief wire shape**: unchanged keys. `brief.symbol` is now `""` (never the
  query text) when no instrument binds; heavy `structured` carries
  `resolved` + `price` + `fundamentals` + `panel` (previously panel-only);
  `note` values are now only: `null`, the budget-stop sentence, the
  cross-check disagreement flag, or the FAST no-instrument note.
- **FAST bundle**: resolution failure no longer returns `ok: False` — it
  returns a web-only `ok: True` bundle with `symbol: ""`, `structured: {}` and
  a top-level `note`. Anything treating `gather_fast` `ok:False` as
  "unresolvable query" should key off `resolved.ok` instead (the agent prompt
  path reads the dict generically; `_auto_publish_event` verified compatible).
- **agent_runtime.py untouched** (no publish-path change was needed — the
  FAST note rides the existing top-level `note` mapping).
- **fundamentals tool**: worst-case latency +0.5s on double-failure (one
  retry). MCP projection unaffected (same handler).

## NEEDS-MANUAL-CHECK

1. **Live ULTRA run on an Indian name** (Saksoft/ROUTE): confirm the brief
   header shows the ticker chip (not a sentence), metric cards render on the
   heavy brief, and exchange PDFs appear in sources with the filing badge.
2. **nsearchives/BSE PDF fetch over curl_cffi on the dev rig** — unit tests
   inject bytes; the impersonation lane itself is environment-dependent
   (NSE/BSE anti-bot behaviour varies by IP).
3. **`@min-[420px]` container variant rendering** in the built app at narrow
   panel widths (typecheck/vitest cannot see compiled CSS) — verify prose
   downshifts at <420px panel width and chat sizing is unchanged.
4. **Results-calendar coverage** rides a direct service wrapper because the
   calendar has no catalog capability; if the catalog track adds a
   `results_calendar` capability, swap `disclosures.fetch_results_calendar`
   to the tool path.
5. **PyInstaller smoke-test** after the next sidecar build (pypdf needs no
   flags per analysis, but the smoke test is the binary-truth gate).
6. The spot-audit spends ONE extra LLM call per deep/ultra run (skipped under
   15s wall) — watch the cost telemetry on live runs.

## Commits

- `54f4e9c` feat(research): entity-relevance gate for gathered web evidence
- `62ac2b8` feat(research): ResearchTarget contract — resolve once, bind one clean symbol
- `0739bec` feat(search): PDF extraction for research visits
- `2313c9f` feat(research): exchange disclosures join the research loop
- `d395673` feat(research): citation integrity — structural marker pass + bounded spot-audit
- `1986ae7` fix(research): graceful wall guards + human-only brief notes
- `2bf6005` fix(agent): fundamentals tool retries once before reporting unavailable
- `977a373` fix(brief): frontend truth — dangling markers, honest banner, cost format, meta collapse
- (this commit) test(research): R8 regression suite + track report

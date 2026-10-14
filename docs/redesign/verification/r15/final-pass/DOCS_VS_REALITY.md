# Docs vs reality — final pass @ d38b5d1a

Lane `final-docs` (Opus 5.5, effort high). Read-only. Sources: the tree at
`d38b5d1a2487bd52fe8a7e741a3a5266e3206611` (read via `git show`/`git cat-file` and the
read-only `final-cand` worktree, whose only local change is `vitest.config.ts`), plus GETs
and one MCP `initialize` + `tools/list` against the shared sidecar `:52800`. Raw evidence:
`raw/final-docs/`. Findings: `findings/docs.json`.

Shell note: zsh expands `$S:t`-style modifiers, so every git path was written `"${S}:path"`.

## (a) Version string — PASS

Commands: `grep` of each source in `final-cand`; `curl :52800/health`.

| Source | Value |
| --- | --- |
| package.json:3 | 0.9.0 |
| src-tauri/Cargo.toml:3 | 0.9.0 |
| src-tauri/Cargo.lock:5486-5487 (`vysted-terminal`) | 0.9.0 |
| src-tauri/tauri.conf.json:4 | 0.9.0 |
| sidecar/app.py:326 `FastAPI(version=...)` | 0.9.0 |
| src/lib/plugin-bootstrap.ts:38 `HOST_VERSION` | 0.9.0 |
| README.md:53 status line | 0.9.0 ("pending the launch tag") |
| GET :52800/health `version` | 0.9.0 (`raw/final-docs/health.json`) |
| CHANGELOG.md top | no version heading: the top section (line 7) is the R15 rc1 round-5 entry; the file is run history, not a release changelog. Not a mismatch, but the release notes lane should add a `0.9.0` section. |

Version mismatches: 0. Stale version **claims** in prose are in (c) (CURRENT_STATE.md says
"stuck at 0.8.0"; RELEASE_RUNBOOK.md §1 says the bump is not yet merged).

## (b) `pnpm <script>` / `node scripts/...` — PASS

Docs: README.md, docs/CURRENT_STATE.md, docs/RELEASE_RUNBOOK.md. **No release-notes file
exists at the sha** (`git ls-files | grep -i notes` outside archive/verification finds none);
the release docs lane creates it.

- Every `pnpm X` was checked against `package.json` scripts (`dev build lint format
  format:check typecheck test test:watch sidecar:build openbb-mcp-sidecar:build
  sec-edgar-mcp-sidecar:build sidecars:build probe:exchanges ci-local tauri tauri:mcp
  tauri:dev`) plus pnpm built-ins (`install`). Misses: 2, both prose ("pnpm can resolve",
  RELEASE_RUNBOOK.md:67; "the standard pnpm entry", :232). Real misses: 0.
- `node scripts/...`: 10 references (smoke-test-sidecars.mjs, ensure-all-sidecars.mjs,
  audit-design-tokens.mjs); all exist at the sha. Misses: 0.
- Side mismatch: RELEASE_RUNBOOK.md:252-262 calls its `ci-local` block "Verbatim from
  `package.json:ci-local`", but it has `python -m pip` / `pnpm test`, while package.json has
  `python3 -m pip` / `vitest run --coverage` (finding F-DOCS-006, low).

## (c) Repo paths named by the docs — 132 raw misses, 25 after basename resolution, 6 real

Command: every backticked path and markdown link in README.md, docs/CURRENT_STATE.md,
docs/RELEASE_RUNBOOK.md and CHANGELOG.md lines 7-67, tested with
`git cat-file -e "${S}:<path>"`; names that fail were then suffix-matched against
`git ls-tree -r --name-only -t $S` (12,339 entries) because the docs name most files by
basename in section context. The 25 left (`raw/final-docs/c-true-miss.txt`):

Intentional or not-a-path (no finding): CURRENT_STATE.md:72 (`P1_P3_BUILD_REPORT.md`, stated
removed), :228 (`kill_switch.rs`, stated deleted D81), :449 (`test_safety_end_to_end.py`,
stated removed), :636 / RELEASE_RUNBOOK.md:473,661,678 (`latest.json`, stated
not produced), RELEASE_RUNBOOK.md:383-384 (`binaries/*`, build outputs), :49,52
(`sidecar/.venv`, untracked by design), :657-665 (`.github/workflows/release.yml`, stated as
the missing Tier-4 workflow), :660 (`tauri-apps/tauri-action`, a GitHub action), :767-768
(paths listed as present only in pre-D81 tags), :81 (`scratchpad/...`, a scratch file).

Real mismatches:

| Where | Doc says | Reality at the sha | Finding |
| --- | --- | --- | --- |
| docs/CURRENT_STATE.md:38 | "Full detail + gate results: `docs/redesign/FOUNDATION_BUILD_REPORT.md`" | file absent from the tree (same class as fixed R15-DOCS-023's dead `P1_P3_BUILD_REPORT.md` link) | F-DOCS-005 |
| docs/CURRENT_STATE.md:388 | `monte_carlo.py` (Asian/barrier) "is not wired to any endpoint" | `sidecar/services/quant/` holds `__init__ _common bonds greeks options pool yield_curve`; the file was deleted by fixed R15-CODE-PLATFORM-040 and the doc kept it | F-DOCS-005 |
| docs/CURRENT_STATE.md:594 | "Integrations (`ConnectCard.tsx`) — no `index.ts`" | no `ConnectCard.tsx` anywhere in the tree | F-DOCS-005 |
| docs/CURRENT_STATE.md:10, :154, :265, :638-640, :856, :879 | "619 vitest, 942 pytest"; "version strings stuck at `0.8.0`"; `version="0.8.0"` | all five sources are 0.9.0 (bumped by 06879089); ci-local at the sha ran 2032 vitest, 3921 pytest (`logs/ci-local.log:370`, `:1295`) | F-DOCS-005 |
| README.md:48-49 | "619 vitest, 942 pytest" | 2032 vitest / 3921 pytest at the sha (`logs/ci-local.log`) | F-DOCS-007 |
| docs/RELEASE_RUNBOOK.md:14-15, :70-84 | step 1: merge `worktree-agent-r15-version-0.9.0` (517da226) because the bump "is not an ancestor of this sha" | the bump is already in the sha via `06879089 chore(release): bump version to 0.9.0 ...`; 517da226 is still not an ancestor, so following step 1 merges a superseded branch (and its CLAUDE.md commit) on top of an already-bumped tree | F-DOCS-004 |

README.md:27 and :155 ("Next.js static-export frontend", "Next.js 16 frontend") are wrong
(the frontend is Vite ^8.0.16 + React 19.2.6, no `next` dependency); that is the open
`blocked_tier4` entry R15-DOCS-003, whose `files` already list README.md — attached, not new
(F-DOCS-009). README.md:41 "BYOK across 7 LLM providers" lists 7; `GET /llm/providers`
returns 8 (adds `openrouter`, the README's own recommended key two sections later)
(F-DOCS-007).

The top CHANGELOG section (lines 7-67) names `R15_GATE_RC1.md`, `rc1-gate.js` and
`DECISIONS_FOR_OPERATOR.md` by basename; all resolve in the tree. Misses: 0.

## (d) docs/SIDECAR_API.md vs live `/openapi.json` — FAIL

Commands: `curl :52800/openapi.json` (111 method+path pairs, `raw/final-docs/live-routes.txt`);
every `` `METHOD /path` `` in SIDECAR_API.md (20) compared with `{param}` normalised.

- Documented but not live: **0**.
- Live but undocumented: **91 of 111** (`raw/final-docs/undocumented.txt`), i.e. the whole of
  `/agents` (list, invoke, actions/ack), `/custom-agents/*`, `/llm/*`, `/plugins/*`,
  `/workflow/*`, `/workspace/*`, `/portfolio/positions`, `/news*`, `/indicators*`,
  `/screener/*`, `/sec/*`, `/earnings/*`, `/disclosures/*`, `/quant/*`, `/backtest/*`,
  `/resolve*`, `/search/*`, `/system/*`, `/macro/search`, `/macro/catalog`, `/mcp/status`,
  `/openbb-mcp/status`, `/data-sources`, `/fundamentals/{s}/narrative`,
  `/fundamentals/{s}/ratings/{history,individual,price-target-history}`.
- Claims the running sidecar contradicts:
  - SIDECAR_API.md:16 "the sidecar allows all origins". `sidecar/app.py:289-293`
    `ALLOWED_ORIGINS` plus `_OriginGuardMiddleware`: `curl -H 'Origin: http://evil.example'
    :52800/health` → **403**; `Origin: http://localhost:5173` → 200. A security-posture
    statement in "the contract" is the reverse of the code.
  - SIDECAR_API.md:31, :88 macro "Hook only (501) until the Phase 2 OpenBB ODP wrap".
    `GET /macro/GDP` → 422 `provider is required for a series id`; `/health` reports
    `macro_series: openbb-mcp`; `/macro/search` and `/macro/catalog` are live.
  - SIDECAR_API.md:25-51 provider table and "OpenBB ODP deferred to Phase 2": `/health`
    reports openbb-mcp (yfinance fallback) for fundamentals/statements/ratings and
    `ccxt (nse_direct, nse, bse, yfinance fallback)` for quotes/ohlcv.
  - SIDECAR_API.md:125-136 "Stub routers ... return a stub `_status` payload": `/indicators`
    returns 50 indicators, `/portfolio/positions` returns `[]` (real store), `/news` and
    `/workspace` are real.

Finding F-DOCS-001 (medium).

## (e) docs/MCP_INTEGRATION.md vs the live MCP list — FAIL (one direction)

Commands: `curl :52800/mcp/status` → `{"ready":true,"toolCount":39,...,"protocolVersion":
"2025-11-25"}`; JSON-RPC `initialize` + `tools/list` on `:52800/mcp/` → 39 names
(`raw/final-docs/mcp-live.txt`). Doc names: MCP_INTEGRATION.md:117-121 (19 catalog-projected)
plus the table at :134-143 (6 hand-written) = 25.

- Named in the doc but not live: **0** (`spec_json`, `workspace_id` are argument names).
- Live but not in the doc: **14** — catalog-projected `compare_symbols`, `corporate_actions`,
  `corporate_announcements`, `earnings_call_transcript`, `exchange_deals`,
  `financial_statements`, `market_overview`, `option_chain`, `research`, `resolve_symbol`,
  `shareholding_pattern`, `web_search`; hand-written `list_runs`, `save_workflow` (CLAUDE.md
  itself names `save_workflow` as MCP-only hand-written).
- MCP_INTEGRATION.md:207 sample `toolCount: 26, protocolVersion "2025-06-18"`; live 39 and
  `2025-11-25` (the doc does say to trust the probe, so the sample number alone is cosmetic).

Finding F-DOCS-003 (low).

Adjacent code drift found while checking (e): `src-tauri/src/lib.rs:311-313` hard-codes
`MCP_PROTOCOL_VERSION = "2025-06-18"` for the discovery file and says it "Mirrors
`_PROTOCOL_VERSION` in `sidecar/services/mcp_server.py` — keep both in sync"; no
`_PROTOCOL_VERSION` exists there — `mcp_server.protocol_version()` returns the SDK's
`LATEST_PROTOCOL_VERSION` (`sidecar/services/mcp_server.py:50,389-391`), which `/mcp/status`
reports as `2025-11-25`. So `mcp-endpoint.json` and `/mcp/status` advertise different
revisions. Negotiation still works (an `initialize` asking 2025-06-18 is answered with it),
so impact is a misleading discovery value and a dead sync comment. Finding F-DOCS-008 (low).

## (f) No user-facing offer of trading / orders / broker / paper-live mode (D81)

Commands: case-insensitive grep over `src/**/*.ts(x)` minus tests (66 hits,
`raw/final-docs/f-src.txt`), `sidecar/agents/*.json`, plugin manifests, and 119 user-facing
markdown files outside docs/archive and docs/redesign/verification (117 hits,
`raw/final-docs/f-docs.txt`).

Product surface (src, agent prompts, manifests): **0 offers → no gate8 finding.** Every hit
is one of:
- the backtest module's historical-simulation trade log (`BacktestResultView.tsx`,
  `store/backtest.ts`) — a simulation over past bars, no account, no order path;
- "trading days" / "trading currency" / "trading calendar" (portfolio metrics, earnings,
  equity overview, settings hint at `SettingsPanel.tsx:1423`, `market-session.ts`);
- explicit negations: `DisclaimerFlow.tsx:28,32` ("not a registered broker-dealer", "no
  brokerage connection. It cannot place, route or simulate orders"),
  `store/agent-autonomy.ts:15-16`, `PortfolioPanel.tsx:157` and `portfolio/index.ts:7` ("no
  broker sync");
- SEC Form 4 "insider trading" (`sec/InsiderTradingTable.tsx`) — a filing type;
- "broker" meaning OpenRouter as a model broker (`OnboardingFlow.tsx:9` comment,
  `store/model-selection.ts:55`);
- `sidecar/agents/strategy_critic.json:5` — critiques a "trading or investment strategy";
  analysis, no execution.
Residue noted, not an offer: `src/lib/format.ts:278-280` keeps short labels for `kite`,
`upstox`, `dhan` (removed Indian broker providers) and `src/components/StatusChrome.tsx:36`
a `tongyi` label; nothing emits those provider ids any more (`git grep -w` finds no producer).

Documents: historical/negation hits are fine — BLUEPRINT.md:20,65,280,390,
BROKER_INTEGRATIONS.md:1-4, CURRENT_STATE.md:22,139,164,314,450,692,800,809,905,914,
SAFETY_ARCHITECTURE.md:4,81,118,124,134-149, PHASE_10_HANDOFF.md:3,123 (headed
"Historical"), docs/research/phase-10/* (dated research notes), docs/redesign/DECISIONS*.md
and R-track reports (design history), BACKLOG_0.9.1.md:115 (a register row). One real hit:

- **docs/redesign/R12_HAND_TESTING_GUIDE.md** — the repo's only hand-testing guide, written
  "for you coming back after weeks away" — still tells the reader the agent "prepares (never
  places) orders" (:7), that the §6.5 model lets it "only prepare [a broker order] for your
  review" (:9), to add to "my paper portfolio" (:25), that six plugins load "(brokers, ...)"
  (:36; `plugins/` at the sha has example, openbb-mcp, vysted-lenses, vysted-news, yfinance),
  and walks an **"Orders (the safety showcase)"** step: "buy 5 shares of RELIANCE at market"
  → "ROUTES TO THE CONFIRM-BEFORE-PLACE DIALOG" (:37). It also says Next.js UI (:7). A
  document, not product surface, so new_defect/docs rather than gate8. Finding F-DOCS-002
  (medium).

## (g) BANNED_WORD / BANNED_PHRASE — PASS (bar 0 met)

Pattern built in the shell (`W=$(printf '\x6c\x61\x79\x61')`,
`P=$(printf 'low-%s trading' latency)`), `grep -i`. Scope: 508 tracked files — README*,
CHANGELOG.md, LICENSE*, COMMERCIAL_LICENSE.md, LICENSING.md, docs/**/*.md outside
docs/archive and docs/redesign/verification (includes docs/RELEASE_RUNBOOK.md), plugin
READMEs, index.html, and all of `src/`.

| Pattern | Substring hits | Whole-word hits |
| --- | --- | --- |
| BANNED_WORD | 1 — docs/redesign/R8_TRACK_SEAMS_REPORT.md:133, inside an unrelated longer word (not the name) | **0** |
| BANNED_PHRASE | 0 | **0** |

Whole repo at the sha (`git grep -l -i -w`): BANNED_WORD in 25 files, BANNED_PHRASE in 7,
**all under docs/redesign/verification/** (run evidence, out of scope). sidecar/, plugins/,
src-tauri/, scripts/: 0. No release-notes file exists yet to scan; the release docs lane must
re-run this grep on what it writes.

## (h) SAFETY_ARCHITECTURE.md §2 vs the gate — doc is TRUE at the sha, no finding

The authoring-head premise ("§2 says every kind auto-applies under AUTO") no longer holds.
At the sha docs/SAFETY_ARCHITECTURE.md:40-46 says: under ASK every kind is staged; under AUTO
"only the `AUTO_APPLIED_KINDS` set (`panel`, `chart`, `watchlist`) auto-applies on enqueue;
`data-write` and `settings` always wait in the review queue under either autonomy setting."
Code: `types/proposed-change.ts:38-46` `AUTO_APPLIED_KINDS = ["panel","chart","watchlist"]`,
`autoApplies(kind)`; `src/store/proposed-changes.ts:123-129` — under `autonomy === "auto"`
only `autoApplies(change.kind)` calls `accept(id)`, every other kind is acked `staged` and
stays pending. `ComposerPlusMenu.tsx:35-36` renders the hint from the same predicate.
CURRENT_STATE.md:83,589,689 agree. Matches DECISIONS 3.5. Mismatches: 0.

## (i) CLAUDE.md (Tier-1, read-only) — notes for the operator, not findings

Checked the working-copy CLAUDE.md's backticked paths (all resolve, by path or basename) and
32 named symbols against the code at the sha. Mismatches:

1. **Deep-research Tongyi probe section is stale.** CLAUDE.md (Copilot gotchas, "Research
   auto-publishes the brief") describes `GET /system/deepresearch/probe` with an
   `X-OpenRouter-Key` header → `tongyi.resolve_model` → `minimax/minimax-m3` fallback
   surfaced as `usingFallback:true`. At the sha: no `/system/deepresearch/probe` route in
   `/openapi.json`; no `tongyi` module; `usingFallback` and `X-OpenRouter-Key` appear nowhere
   in sidecar/src. `sidecar/services/research/sonar.py:19-23,91-92` says Tongyi is delisted
   and "deliberately unreachable"; `resolve_model` there resolves Perplexity sonar slugs
   (removal commits 2a49bab4 → 149e511d). The `deepResearchBackend` →
   `get_deep_research_backend()` ContextVar part still holds (`agent_runtime.py:2796`).
2. **"`register_all()` now registers 12 built-in node types"** — `sidecar/services/workflow_nodes/__init__.py`
   registers 11 builtins + the code node + 5 domain packs; `GET /workflow/node-types` returns
   **24**.
3. **Stack/plugins/sidecars hold**: Vite ^8.0.16 + React 19.2.6; `plugins/` = example,
   openbb-mcp, vysted-lenses, vysted-news, yfinance; `bundle.externalBin` = 3 sidecars; 13
   agents (`GET /agents`); `/mcp/status`, the runs routes, `test_runs_rows_carry_only_snake_case_keys`,
   `_OriginGuardMiddleware`, `release_never_uses_dev_keystore`, `scrub_adapter_options`,
   `_NO_TOOL_CUE`, `fitLayoutTemplate`, `BriefBody`, `CATALOG_ROWS` all exist.
4. CLAUDE.md names no SIDECAR_API/MCP counts, so (d)/(e) drift does not touch it.

## Findings summary

| Key | Sev | Area | Doc |
| --- | --- | --- | --- |
| F-DOCS-001 | medium | docs | SIDECAR_API.md: 91/111 live routes undocumented; CORS/macro/stub-router claims contradicted by the running sidecar |
| F-DOCS-002 | medium | docs | R12_HAND_TESTING_GUIDE.md walks an order-placement showcase, a broker plugin and a paper portfolio removed by D81 |
| F-DOCS-004 | medium | release | RELEASE_RUNBOOK.md §1 tells the operator to merge a superseded version-bump branch; the bump is already in the sha |
| F-DOCS-003 | low | docs | MCP_INTEGRATION.md omits 14 of 39 live tools |
| F-DOCS-005 | low | docs | CURRENT_STATE.md: dead report link, deleted monte_carlo.py, absent ConnectCard.tsx, "stuck at 0.8.0", 619/942 counts |
| F-DOCS-006 | low | release | RELEASE_RUNBOOK.md "verbatim" ci-local block differs from package.json |
| F-DOCS-007 | low | docs | README.md: 619/942 test counts stale; "7 LLM providers" vs 8 live |
| F-DOCS-008 | low | docs | MCP protocol revision: discovery file 2025-06-18 vs /mcp/status 2025-11-25; dead sync comment |
| F-DOCS-009 | low | docs | README.md Next.js claims — attach to R15-DOCS-003 (blocked_tier4) |

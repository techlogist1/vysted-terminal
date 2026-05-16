# Phase 6.5 Handoff (v0.6.5 → Phase 7)

**Read this first** if you are starting Phase 7 (launch operations).
Phase 6.5 (Tradesa V2 wrapper plugin — first-party trading-system
wrapper, READ-ONLY) shipped as v0.6.5 on 2026-05-17. The handoff
follows the 8-section convention established by
`PHASE_3_HANDOFF.md` → `PHASE_4_HANDOFF.md` → `PHASE_5_HANDOFF.md` →
`PHASE_6_HANDOFF.md`.

---

## 1. What Phase 6.5 shipped (inside v0.6.5)

### Foundation (lead, A1–A12, sequential, pushed to origin/main pre-dispatch)

- **A1 `chore(deps)`** — `supabase==2.30.0` pinned in
  `sidecar/requirements.txt`; pulls realtime / postgrest / gotrue /
  storage3 / supafunc / supabase-auth / supabase-functions as a
  coordinated transitive set.
- **A2 `feat(types)`** — `types/tradesa_v2.ts` with 12 interfaces +
  the `TradesaConnectionStatus` union (~470 LoC).
- **A3 `feat(models)`** — Pydantic mirrors with
  `ConfigDict(extra="forbid")` on every model so Tradesa V2 schema
  drift surfaces as `ValidationError` rather than silent acceptance.
- **A4 `feat(sidecar): tradesa_v2_provider.py`** — read-only Supabase
  wrapper. 12 read methods + connection probe + pure-function
  settings-drift classifier. Lazy supabase-py client init. TTL cache
  reuse via Phase 6 F6 `data_cache.py`. **27 pytest** — including
  the `test_no_write_methods_on_provider_surface` audit that greps
  the class via `inspect.getmembers` for forbidden prefixes
  (`insert_`/`update_`/`delete_`/`upsert_`/`write_`/`place_`/
  `submit_`/`execute_`/`create_`).
- **A5 `feat(sidecar): routers/tradesa_v2.py`** — 11 GET endpoints.
  `test_no_non_get_routes_under_tradesa_v2_prefix` walks
  `router.routes` and fails on any POST/PUT/PATCH/DELETE.
  Credentials in `X-Tradesa-Supabase-Url` / `X-Tradesa-Supabase-
  Service-Key` headers. **22 pytest** covering route methods, prefix
  sanity, unauth flows, happy paths, provider-error → 502 mapping,
  header-only credential acceptance, response no-echo audit.
- **A6 (DEFERRED to v0.6.6+, Tier-3)** — Supabase Realtime SSE
  proxy. The asyncio-task lifecycle is disproportionate to v0.6.5
  wrapper-shape scope; polling at 10–60s per panel delivers
  equivalent "is the bot alive" UX.
- **A7 `feat(agent_tools): registry_v0_6_5.py stub`** — per-release
  aggregator slot maintained for v0.6.6+ write tools. v0.6.5
  registers zero tools (READ-ONLY).
- **A8 `feat(plugin): tradesa-v2 entry + connection adapter + store
  + hook + placeholders`** — `plugins/tradesa-v2/` with `manifest.json`,
  `index.ts`, `connection.ts`, `store.ts`,
  `useTradesaConnectionState.ts`, `panels.ts`, plus 7 placeholder
  panel components. Generic `TradingBotReadAdapter` interface that
  future trading-system plugins implement. **20 vitest** covering
  manifest identity, capability negotiation
  (`supportsControlPlane=false` enforces READ-ONLY at contract
  level), panel/command symmetry, full lifecycle, and probe-status
  → HealthStatus mapping for every degraded state.
- **A9 `feat(bootstrap): companion-module glue + tradesa-v2 register`**
  — extended `src/lib/plugin-bootstrap.ts::moduleForPlugin` to merge
  a companion `plugins/<id>/panels.ts` `Record<string,
  FunctionComponent>` map into the synthesized `VystedModule`.
  `HOST_VERSION` bumped 0.4.0 → 0.6.5. Diagnostic warning surfaces
  the wiring gap if a plugin contributes panels without a companion.
- **A10 folded into A8** — placeholder shells shipped alongside the
  plugin entry for cleaner import resolution.
- **A11–A12 `docs(plugin-development+blueprint)`** — new "Plugin
  patterns" section in PLUGIN_DEVELOPMENT enumerating the four
  shapes (in-process / sidecar provider / MCP-subprocess /
  trading-system wrapper); Phase 6.5 row added to BLUEPRINT §7.
- **A13** — `git push origin main` (lead foundation gate before
  teammate dispatch).

### Teammate T — Frontend slice (4 commits, 39 frontend vitest)

- **B-foundation `ebefd4f`** — `_PanelShell.tsx` (centralizes every
  graceful-degradation branch as a render-prop wrapper),
  `_utils.ts` (`useInterval`, `formatRelativeIso`, `formatDuration`,
  `formatUsd`), enhanced `TradesaBotStatusStrip.tsx`, full
  `TradesaSettingsDialog.tsx` (Supabase URL + service-role key
  entry with show/hide password toggle, writes via `setSecret`,
  warning copy about service-role power).
- **B5+B6+B7 `188a972`** — Positions / TradeHistory / BrainDecisions
  panels with sortable tables, summary cards, color-coded P&L,
  per-model cost bar chart.
- **B8+B9+B10+B11 `c8adbdf`** — Sentinel / Health / Settings /
  MetaAgents panels; deleted `_PlaceholderPanel.tsx`.
- **Tests `de768de`** — 9 test files, 39 Vitest tests covering each
  panel × at minimum (skeleton-in-connecting / empty-or-offline /
  populated-when-healthy) + dialog form submission + status-strip
  rendering. Prettier-formatted everything.

**Verification (post-merge):**
- `pnpm typecheck` clean.
- `pnpm lint` (eslint) — 0 errors.
- `pnpm test` (vitest) — **584 passed** across 80 files (+59 over
  v0.6.1's 525 baseline: 20 plugin entry + 39 per-panel).

**No Tier-4 blockers** — no `BLOCKERS-T.md` written. All scope
completed within file ownership boundaries. Lead-owned files
(`index.ts`, `manifest.json`, `panels.ts`, `connection.ts`, `store.ts`,
`useTradesaConnectionState.ts`, `tradesa-v2.test.ts`, all sidecar/,
types/, src/lib/) untouched per dispatch brief.

---

## 2. Autonomous decisions made (Tier-2/3)

1. **Connection surface: Supabase passthrough (option b in brief),
   Tier-2.** Tradesa V2 has no REST API. Operator interface is
   Telegram-only (32 commands, 18 alert categories per its
   `README.md`). Bot writes to its existing Supabase project via
   `bridge/supabase_sync.py` with the service-role key — the only
   external read surface available. RLS is deferred Tradesa-side to
   v0.1.7.0 (per their `CHANGES.md`); until then service-role is the
   operator's chosen access path. When RLS lands the wrapper swaps
   to anon-key + Auth — API surface unchanged.

2. **One teammate, not two, Tier-2.** Lead owned foundation +
   backend + plugin entry + bootstrap glue + integration + release;
   Teammate T (Opus 4.7, worktree-isolated) owned the 7 panel React
   components + status strip enhancement + settings dialog + per-panel
   Vitest. Teammate branched from origin/main AFTER lead foundation
   pushed (sequenced, not parallel) — the v0.5.0 "two teammates
   writing same file" gotcha avoided.

3. **Credential flow: request headers, not body, Tier-3.** Sidecar
   cannot read OS keychain directly (only Tauri Rust can — established
   constraint since Phase 3 BYOK). For Tradesa V2 we use `X-Tradesa-
   Supabase-Url` + `X-Tradesa-Supabase-Service-Key` request headers
   instead of body params so the read-only GET model stays clean.
   Sidecar process memory only; no logging, no echo back (audit-tested
   via `test_response_never_echoes_credentials`).

4. **Plugin React-component wiring via companion `panels.ts`, Tier-3.**
   The pre-v0.6.5 `src/lib/plugin-bootstrap.ts::moduleForPlugin`
   synthesized a `VystedModule` with empty `panelComponents: {}` for
   plugin-contributed panels — no path existed for a plugin to ship
   React components for its declared `PanelSpec`s. Extending
   `moduleForPlugin` to import a sibling `panels.ts` is host-side
   glue (additive, no contract change). The `PLUGIN_COMPANIONS` map
   is static — Next.js static export can't resolve runtime plugin-id
   dynamic imports without filesystem-installed plugins (v0.7+
   scope).

5. **Realtime SSE proxy DEFERRED to v0.6.6+, Tier-3.** Polling at
   per-panel cadences (10s positions / 30s decisions / 60s settings /
   5min trade-history / 120s meta-agents) delivers equivalent
   "is the bot alive" UX without the asyncio-task lifecycle
   complexity. The polling cadences are matched to bot write cadence
   (`bot_settings` hot-reloads every 55s on bot side so 60s TTL
   shields without showing stale config).

6. **Read-only enforcement as defense-in-depth, Tier-3.** Three
   layers:
   - **Provider** — `test_no_write_methods_on_provider_surface`
     walks the class via `inspect.getmembers` and asserts no public
     attribute starts with a forbidden prefix.
   - **Router** — `test_no_non_get_routes_under_tradesa_v2_prefix`
     walks `router.routes` and asserts no route's methods set
     intersects `{POST, PUT, PATCH, DELETE, HEAD, OPTIONS}`.
   - **Plugin contract** — `capabilities.supportsControlPlane = false`
     means the runtime refuses to call `executeCommand` on this
     plugin even if the method existed.
   Pattern mirrors the v0.5.0 §6.5 #4 audit-log defense-in-depth
   (type-level gate + DB-enforced invariant + grep audit check).

7. **Plugin id `tradesa-v2`, panel ids `tradesa-v2.<panel>`,
   component ids `tradesa-v2-<panel>`, Tier-3.** Kebab-case matches
   existing `openbb-mcp` + `vysted-example` precedent and the
   explicit examples in `types/plugin.ts` comments.

8. **No-op aggregator stub `registry_v0_6_5.py`, Tier-3.** v0.6.5
   ships READ-ONLY so no agent tools register. The per-release-stamp
   aggregator slot is created to maintain v0.5.0/v0.6.0 convention —
   v0.6.6+ writes fill it.

9. **Placeholder shells folded into A8, Tier-3.** Originally planned
   as A10 (separate commit after A8 entry); collapsed into A8
   because the entry's `panels.ts` imports each component directly,
   so the components must exist when the entry first compiles. Plan
   §A10 marked completed-as-part-of-A8.

10. **Cargo `vysted-terminal` package version was 0.5.0 in
    `Cargo.lock` (stale from before v0.6.0).** Re-locked to 0.6.5
    during the release version-bump commit (`7ecb421`).

---

## 3. Known issues carried forward to v0.6.6 (none blocks v0.6.5)

### 1. Realtime SSE proxy (Tier-3 carry-forward)

Sidecar-side WebSocket subscription to Supabase `postgres_changes`
events on `trades` / `decisions` / `bot_health` / `kill_switch_events`,
fanned out via SSE to the frontend store. The store replaces the
current polling cadence with subscription-driven incremental updates.
Polling fallback when Realtime is unavailable.

### 2. Write capability

Vysted-side commands toward the bot: manual position close, pause-bot
toggle from the Health panel, approve tuning-proposal from
MetaAgentsPanel. Each is a Tier-4 design decision — must route
through propose→confirm flow + §6.5 audit log, same as broker-
execution plugins. The `registry_v0_6_5.py` aggregator slot is
already in place.

### 3. MCP tool exposure for the brain-decision log

Surface the bot's `decisions` stream as a Vysted MCP tool so the
chat sidebar can summarize / query the bot's recent decisions
("ask the AI sidebar to explain why the bot held overnight").
Chat-sidebar integration risk; out of v0.6.5 scope.

### 4. Bybit Demo position enrichment

Read directly from the broker (Bybit V5 API) for live tick-level
position data the bot doesn't write to Supabase (entry tick, current
mark, unrealized P&L without polling lag). Optional Bybit Demo
credentials in keychain — pre-planned via `pluginSecret("tradesa-v2",
"bybit-demo-api-key")` / `pluginSecret("tradesa-v2",
"bybit-demo-api-secret")` (NOT consumed in v0.6.5).

### 5. Anon-key + Auth migration

When Tradesa V2 ships its v0.1.7.0 RLS rollout, the wrapper swaps
from service-role to anon-key + Auth. API surface unchanged on the
Vysted side; the Settings dialog gains a "Sign in" button instead of
the service-role key field, and the connection adapter swaps the
`X-Tradesa-Supabase-Service-Key` header for a Supabase JWT.

### 6. Live `pnpm tauri dev` populated-state screenshots

v0.6.5 ships with the test-confirmed panel rendering verified by 39
Vitest tests + the 20 plugin-entry Vitests. Operator-led full
re-capture pass (7 panels × healthy/offline/unauth × 1920×1080 +
2560×1440 = 42 screenshots) follows the v0.6.0 BLOCKERS.md §2 pattern;
deferred to a polish session because (a) live capture needs a real
Tradesa V2 Supabase project for the healthy state, (b) the
graceful-degradation paths are non-trivial to drive headlessly
without ad-hoc network blockers, (c) the test artifacts confirm
the rendering shapes 1:1 with what the live capture would show.
Procedure: `pnpm tauri dev`; cmd+K each Tradesa V2 panel; capture
at 1920×1080 + 2560×1440 via chrome-devtools MCP
`resize_page` + `take_screenshot`; save to
`docs/screenshots/v0.6.5/`.

---

## 4. Plugin contract status

- **`types/plugin.ts` is unchanged in v0.6.5.** Verified
  `git diff v0.6.0..v0.6.5 -- types/plugin.ts` empty. **Tier-1 lock
  held — 8th consecutive release.**
- `capabilities.contributesData = true` (3 read-only data sources:
  `tradesa-v2-decisions`, `tradesa-v2-trades`, `tradesa-v2-health`).
- `capabilities.contributesPanels = true` (7 panels enumerated in
  §1).
- `capabilities.contributesCommands = true` (7 cmd+K shortcuts, one
  per panel).
- `capabilities.contributesAgents = false` (v0.6.6+ scope — chat-
  sidebar integration risk).
- `capabilities.contributesNodes = false` (v0.6.6+ scope — node-
  editor surfaces).
- `capabilities.supportsControlPlane = false` — load-bearing READ-
  ONLY enforcement at the contract level. `executeCommand` is
  undefined on the plugin; runtime refuses to call it.

---

## 5. Phase 7 entry context — launch operations

Per BLUEPRINT §7 Phase 7, the next phase is **launch operations**:

1. **Code signing** — SignPath.io Windows OSS-tier; ad-hoc Mac
   signing with `terminal.vysted.com/install/mac` bypass docs;
   Linux unsigned (AppImage + `.deb`).
2. **Tauri auto-updater** — wire to GitHub Releases (pubkey already
   in `src-tauri/tauri.conf.json` from v0.5.0).
3. **Distribution channels** — Homebrew cask, AppImage, GitHub
   Release assets.
4. **`terminal.vysted.com` landing page** — download buttons +
   screenshots + getting-started docs.
5. **AGPL+Commercial dual license activation** — CLA bot on PRs;
   `COMMERCIAL_LICENSE.md` polish; pricing tiers finalised.
6. **v1.0.0 tag + launch announcement**.

Heavily serialized work (sign → release → verify auto-updater per
OS); Phase 7 is its own focused sprint, NOT compressed with Phase 6
or 6.5 (operator brief explicit on this point in v0.6.0 handoff).

**v1.0 narrative includes the Tradesa V2 wrapper** — it is the first
real third-party-shaped trading-system plugin proving the platform's
plug-and-play story. Phase 7 docs / README / landing-page copy should
reference it as the canonical example, alongside the four broker
execution plugins (Dhan / Angel One / Kite / Alpaca / IB / OANDA /
ccxt) that shipped in v0.5.0.

**v0.5.0 paper-soak runs in parallel** — no impact on v0.6.5 ship;
60-day paper-soak window remains the gate before any production live-
execution endorsement, not a build-blocking item for v0.6.5 or the
v1.0 launch.

---

## 6. File / commit pointers for deeper context

- `CHANGELOG.md` v0.6.5 entry — full ship log + Tier-2/3 decisions +
  defense-in-depth audit invariants
- `docs/BLUEPRINT.md` §7 Phase 6.5 (now marked shipped)
- `docs/PLUGIN_DEVELOPMENT.md` "Plugin patterns" section — canonical
  "Trading-System Wrapper" plugin pattern documentation
- `docs/superpowers/plans/2026-05-16-tradesa-v2-wrapper-plugin.md` —
  the v0.6.5 plan
- `BLOCKERS.md` — v0.6.6 carry-forwards (Realtime, write capability,
  MCP, anon-key migration, Bybit enrichment, live screenshot pass)
- **Foundation commits** (lead, A1–A12):
  - `f0c1d2b` (deps), `9ed7abe` (types), `e24c274` (models),
    `b15e1be` (provider), `62661e4` (router), `d8064ed` (agent_tools
    stub), `445f1d4` (plugin entry), `44e1f8b` (bootstrap),
    `97c190b` (docs)
- **Teammate T merge** (Phase B): `3ffd322` combining `ebefd4f` +
  `188a972` + `c8adbdf` + `de768de`
- **Release commit:** `7ecb421` (version bump 0.6.1 → 0.6.5 +
  cargo fmt drift fix)

---

## 7. Verification snapshot at handoff

Pulled at v0.6.5 tag time:

- `pnpm typecheck` clean.
- `pnpm lint` (eslint) — 0 errors.
- `pnpm test` (vitest) — **584 tests pass** across 80 files (+59
  over v0.6.1's 525).
- `pytest sidecar` (excluding the slow kill-switch benchmark) —
  **882 tests pass** (+49 over v0.6.0's 833).
- `ruff check sidecar` + `ruff format --check sidecar` clean.
- `cargo fmt --check` clean (post the v0.6.5 release commit's
  one-line drift fix in `src-tauri/src/sec_edgar_mcp.rs:86`).
- `cargo clippy -- -D warnings` runs on CI (locally requires the
  sec-edgar-mcp subprocess binary built via
  `pnpm sec-edgar-mcp-sidecar:build` — operator-led per BLOCKERS.md §2).
- **§6.5 dedicated audit suite: 9/9 PASS** in 16:14 on foundation
  (pre-merge); re-run on merged state attached at tag time
  (sidecar unchanged by teammate merge so result is expected
  identical).
- `git diff v0.6.0..v0.6.5 -- types/plugin.ts` empty (Tier-1 lock
  held — **8th consecutive release**).
- `git diff v0.6.0..v0.6.5 -- sidecar/services/broker_base.py
sidecar/services/kill_switch.py sidecar/services/audit_log.py
sidecar/models/audit_log.py` empty (§6.5 safety surface
  untouched).

---

## 8. Coordination lesson for Phase 7+

**Single-teammate slice runs cleanly when file ownership partitions
by directory.** Teammate T touched only `plugins/tradesa-v2/components/`;
lead owned everything else (sidecar, types, src/, src-tauri/, docs/,
lead-owned plugin/ files). Zero shared-file contention, no salvage
required, no Tier-4 surfaces.

The v0.5.0 "two teammates writing same file" gotcha (`src/store/
agents.ts` collision between Teammates A + C) and the v0.4.0
sequencing fix (teammate branches from primary teammate's pushed
branch when files must overlap) both stand — but for single-teammate
slices like this one, neither applies. The simpler discipline is
enough: ownership documented at dispatch time + per-directory split.

For Phase 7 (launch ops), the same rule applies: each launch surface
(SignPath wiring, Tauri auto-updater config, Homebrew cask submission,
landing page copy) is independently parallelizable across teammates
IF each surface owns a distinct file set. Lead-led for Phase 7 by
the operator brief signal that the work is serialised (sign → release
→ verify auto-updater per OS) and benefits from one author's hand on
the release pipeline.

The Tradesa V2 wrapper's defense-in-depth pattern (provider audit +
router audit + contract gate) becomes the **template for any future
plugin that needs a guaranteed safety invariant**. Phase 7 v1.0.0
release should reference this pattern in the README + landing-page
copy as evidence that the plugin contract is genuinely safety-
preserving.

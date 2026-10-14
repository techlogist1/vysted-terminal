# R7 Track S — Research-Tier Settings UI — Final Report

Branch `worktree-agent-r7-tiers`. All gates green: `pnpm typecheck`, `pnpm lint`
(0 errors; the one warning is the pre-existing `EquityOverviewPanel.tsx:700`
exhaustive-deps), prettier on every owned file, and the FULL suite:
**133 test files / 1192 tests passed** (`pnpm test`).

## Shipped (file:line)

### 1. Store — `src/store/search-settings.ts`

- `ResearchTier` type + `RESEARCH_TIERS` + `DEFAULT_RESEARCH_TIER` (t1_local) +
  `isResearchTier` guard — :30–:41
- `HostedSearchEngine` type + `HOSTED_SEARCH_ENGINES` + `DEFAULT_HOSTED_SEARCH_ENGINE`
  (firecrawl) + `isHostedSearchEngine` guard — :48–:59
- Bundle fields `researchTier` / `hostedEngine` — :75/:80; seeded defaults — :88–:89
- `setResearchTier` / `setHostedEngine` (self-persist via `autosaveLayout`) — :134–:142
- `setAll` garbage-guard (garbled/absent → defaults, same pattern as `tier`) — :144–:157
- `toBundle` includes both fields — the workspace blob round-trip needed **no
  `workspace.ts` change** (it serializes `toBundle()` whole and restores via
  `setAll`); only the exact-shape assertion in `src/lib/workspace.test.ts:116`
  gained the two fields.

### 2. Headers — `src/lib/search-headers.ts` (ADDITIVE; legacy trio untouched)

- `getOpenrouterApiKey` — reads the SAME `llm-provider:openrouter` keychain slot
  the AI-Providers section writes (`KEYCHAIN_NAMESPACES.llmProvider`); miss/empty/
  keychain-failure → `null`, never a throw — :63–:71
- `buildSearchHeaders` — :80–:94: always emits `X-Vysted-Research-Tier`; emits
  `X-Vysted-Search-Engine` + `X-Vysted-Openrouter-Key` ONLY on t3 (key omitted
  when absent, never empty; the keychain slot is not even read on t1/t2). Names
  match `sidecar/app.py _RegionMiddleware` byte-for-byte. Both transports
  (`sidecar-client`, `chat/streaming`) already call this — no caller changes.

### 3. Settings UI — `src/components/SettingsPanel.tsx` (Research section)

- `ResearchTierGroup` (three 32px radio rows, `role=radiogroup/radio`, name +
  one-line honest description, selected row expands its detail surface) — :1405;
  options copy — :1375; mounted first in `ResearchSection` — :1512; section hint
  updated.
- T1 `T1StatusLine` — :1042 — polls `GET /search/status` every 20s
  (`T1_STATUS_POLL_MS` :1039) while mounted+visible (skips when `document.hidden`),
  renders `t1EngineStatusLine` (:1024, exported, test-locked):
  "DuckDuckGo — cooling down 24s · Brave — ok · Mojeek — ok"; honest
  "unavailable (sidecar not connected)" fallback; all-engines-open warning rider.
- T2 `SearxngGuidedFlow` — :1137 — verbatim off `GET /search/searxng/status`:
  `not_installed_docker` → explanation + plain-text docs.docker.com hint (NOT a
  link); `docker_present_not_setup` → [Set up] → `POST /search/searxng/setup`;
  `pulling`/`starting` → progress + sidecar `detail`, 3s poll
  (`SEARXNG_TRANSITION_POLL_MS` :1129) only during transitions; `ready` → green
  check + "running at {url} — research searches use it automatically" + [Remove]
  → `POST /search/searxng/teardown`; `error` → reason + [Retry] (re-POSTs setup);
  unknown future state → shown honestly verbatim.
- T3 `HostedEngineControls` — :1314 — Firecrawl (default, free-credits cost line)
  | Exa (~$0.005/search, flagged driftable) segmented control (:1294); OpenRouter
  key PRESENCE via the same `useProviderKeysStore` keychain probe the AI
  Providers rows use (`refreshOne("openrouter")`), with a pointer to AI Providers
  when absent. The key value never enters frontend state.

### 4. Tests

- `src/store/search-settings.test.ts` — defaults, setter persistence, setAll
  round-trip + garbage guard (garbled tier/engine → defaults; absent fields →
  seed), bundle snapshot shape.
- `src/lib/search-headers.test.ts` (new) — full emit/omit matrix: t1 tier-only
  (+ never reads the OpenRouter slot), t2 tier-only, t3 engine+key-when-present,
  key omitted when absent/empty/keychain-failure, legacy trio untouched
  alongside, `getOpenrouterApiKey` account-string contract.
- `src/components/SettingsPanel.test.tsx` — three tier rows w/ radio semantics +
  store wiring; T1 live line from mocked `/search/status` + unreachable fallback
  - formatter contract; T2 EVERY state (not_installed_docker/plain-text-no-link,
    docker_present_not_setup, pulling, starting, ready, error) plus both POST
    actions asserted by URL+method; T3 engine switch + both key-presence branches.

## What to eyeball live

1. Settings → Research → "Search tier": three rows, t1 pre-selected, selection
   highlight + dot, hairline-divided detail area under the selected row.
2. With the sidecar up, T1's status line should tick (engine cooldowns count
   down on the ~20s poll after a few searches).
3. Select T3: segmented control flips cost lines; with an OpenRouter key saved
   in AI Providers the green "key configured" line appears (presence only).
4. Persistence: pick t3+exa, relaunch — the selection survives via the
   workspace blob; the bundle field names are `researchTier`/`hostedEngine`.

## NEEDS-MANUAL-CHECK

- **T2 end-to-end needs the live Docker daemon — the lead runs it.** The state
  machine UI is fully covered with mocked fetch, but pull→start→ready→teardown
  against real Docker (incl. the multi-minute first pull staying in `pulling`
  on the 3s poll) was NOT run here.
- T3 against a real OpenRouter key: confirm the sidecar receives
  `X-Vysted-Openrouter-Key`/`X-Vysted-Search-Engine` only on t3 requests (the
  middleware never logs the key, so verify via tier routing behaviour).
- Pre-existing repo-wide `pnpm format:check` failures in four docs from earlier
  tracks (INTEGRATION_NOTES_R7, LEAD_INTEGRATION_TODO, R7_TRACK_RESEARCH_BRIEF,
  R7_TRACK_RESEARCH_REPORT) — present at this worktree's branch HEAD before this
  track; not touched (not owned). Every Track-S file is prettier-clean.

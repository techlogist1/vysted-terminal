# R8 Track B — settings-truth report

Branch: `worktree-agent-r8-settings`. Mission: ONE settings truth for web
search — the legacy "Web search" surface is gone, the R7 Research tiers are
authoritative end-to-end, and a READY managed SearXNG is never bypassed.

## Deliverables

### 1. Sidecar: one resolution path

`sidecar/services/agent_tools/web_search.py`

- `_resolve_backend()` (web_search.py:99) is the single selection path:
  - **(a)** explicit R7 tier header wins — `_resolve_r7_tier()`
    (web_search.py:55) unchanged: t1 → keyless rotation, t2 → configured URL
    else `detect_searxng()` (which itself probes the manager first), t3 →
    hosted (BYOK OpenRouter). An unservable explicit tier still fails honestly
    (C.1), never re-routes.
  - **(b)** legacy headers map into the same lanes (web_search.py:122-141):
    `byok-exa` → `registry.resolve("exa", exa_key=…)`; `local-searxng` →
    t2 detection with the provided URL (autodetect when blank). An unservable
    legacy lane falls through to (c) — the legacy contract always floored.
  - **(c)** DEFAULT (web_search.py:143-159): `searxng_manager.manager.
ready_base_url()` — an instant in-process read, no network probe — READY →
    the managed instance's own URL; else `keyless` → `ddg` floor.
- `_web_search()` (web_search.py:162) now just resolves + dispatches; the
  typed `rate_limited` vs `unreachable` reason pass-through in `_dispatch`
  is untouched, so the "rate-limited, retrying" vs "no backend" fast-path
  distinction keeps working (pinned by test).
- Message copy now points at **Settings → Research** (the legacy section is
  gone).

**Routing matrix evidence** — `sidecar/tests/test_web_search.py`
`test_routing_matrix` (test_web_search.py:158), registry + manager mocked,
14 parametrized cells + 7 targeted tests:

| r7 header  | legacy header | creds          | manager    | chosen backend                                 |
| ---------- | ------------- | -------------- | ---------- | ---------------------------------------------- |
| t1_local   | —             | —              | READY      | keyless (explicit t1 never re-routes)          |
| t1_local   | —             | —              | not        | keyless                                        |
| t2_searxng | —             | URL header     | READY      | searxng @ provided URL (no autodetect call)    |
| t2_searxng | —             | none           | detect hit | searxng @ detected URL                         |
| t2_searxng | —             | none           | nothing    | **honest t2 error** (names the unlock)         |
| t3_hosted  | —             | OpenRouter key | either     | hosted                                         |
| t3_hosted  | —             | no key         | READY      | **honest t3 error** (manager never masks it)   |
| —          | byok-exa      | Exa key        | READY      | exa (lane wins over manager)                   |
| —          | byok-exa      | no key         | READY      | searxng @ managed URL                          |
| —          | byok-exa      | no key         | not        | keyless                                        |
| —          | local-searxng | URL header     | either     | searxng @ provided URL                         |
| —          | local-searxng | none           | detect hit | searxng @ detected URL                         |
| —          | local-searxng | none           | nothing    | keyless                                        |
| —          | native        | —              | READY      | **searxng @ managed URL** ← the fixed bug cell |
| —          | native        | —              | not        | keyless                                        |
| — (none)   | — (none)      | —              | READY      | **searxng @ managed URL**                      |
| — (none)   | — (none)      | —              | not        | keyless                                        |

Extra assertions: the default lane resolves with the manager's REPORTED base
URL (never a guessed port) and never calls the network autodetect
(`test_default_lane_reads_manager_in_process_no_network_probe`).

### 2. Frontend: one surface

`src/components/SettingsPanel.tsx`

- **DELETED**: the legacy `WebSearchSection` (~290 lines: Native/BYOK/SearXNG
  select, the native-status copy machinery `nativeSearchStatus` +
  `PROVIDER_LEVEL_NATIVE_SEARCH` + `OPENROUTER_WEB_SEARCH_EST_USD`, the
  standalone Exa key card, and the manual `docker run …searxng` snippet).
  "Web search" removed from the jump nav (`SECTION_NAV`).
- The Research tier group is the only search settings surface:
  - **t1** detail: live per-engine status line (unchanged).
  - **t2** detail (`SearxngTierDetail`, SettingsPanel.tsx ~1296): the guided
    one-click flow + **"Advanced: custom instance URL"** (the old SearXNG URL
    field; optional, empty = managed/autodetect; wired to `searxngUrl`).
  - **t3** detail (`ByokSearchControls`, SettingsPanel.tsx ~1019): sub-mode
    segmented control **"Via OpenRouter" | "Exa direct"** →
    `HostedEngineControls` (engine + OpenRouter key presence, as before) or
    `ExaDirectControls` (SettingsPanel.tsx ~1080: the legacy
    `vysted-search-exa:exa_api_key` keychain card — presence/save/remove,
    value never echoed; honest warning when the sub-mode is on with no key).
  - t3 row renamed "BYOK search (hosted or Exa direct)".

### 3. Store + headers + migration

- `src/store/search-settings.ts`: `researchTier` is the only authoritative
  tier; new `exaDirect: boolean` t3 sub-mode flag; the legacy `tier` field
  stays in the bundle **for blob round-trip only** (no setter is exposed for
  it; `page.tsx`'s read-only subscription keeps compiling). `setTier` deleted.
  `migrateSearchSettings()` (search-settings.ts:130) folds a pre-R8 blob
  (valid legacy `tier`, no valid `researchTier`) into the R7 vocabulary;
  `setAll` applies it on every restore/import path, so `workspace.ts
deserializeWorkspace` migrates without extra plumbing (workspace.ts:333).
- **Migration matrix** (store test + workspace restore test):
  - `native` → `t1_local`, exaDirect false
  - `local-searxng` → `t2_searxng`, custom URL preserved
  - `byok-exa` → `t3_hosted` + `exaDirect: true`
  - blob with BOTH fields → `researchTier` wins verbatim, never rerouted
  - garbled values → seed defaults (never an unknown id in a header)
- `src/lib/search-headers.ts` — the new wire contract:
  - t1: `X-Vysted-Research-Tier: t1_local` only.
  - t2: `…Research-Tier: t2_searxng` + `X-Vysted-Searxng-Url` **only when a
    custom URL is set** (and only on t2 — a leftover URL is never sent
    off-t2).
  - t3 hosted: `…Research-Tier: t3_hosted` + `X-Vysted-Search-Engine` +
    `X-Vysted-Openrouter-Key` (when stored).
  - t3 **Exa direct**: `X-Vysted-Search-Tier: byok-exa` +
    `X-Vysted-Exa-Key`; the **R7 header is deliberately omitted** (an explicit
    R7 header always wins on the sidecar, so sending it would shadow the
    Exa-direct lane — this is the designed exception to "always send the R7
    trio", per the mapped-lane contract).
  - Keychain slots are read only for the lane that needs them (asserted:
    t1 reads nothing; Exa direct never touches the OpenRouter slot).
- Vitest: `src/store/search-settings.test.ts` (migration matrix),
  `src/lib/search-headers.test.ts` (emit/omit matrix incl. Exa direct),
  `src/lib/workspace.test.ts` (serialize shape + restore-time migration +
  R7-blob no-reroute).

### 4. Proportion law (R8_PROPORTION_LAW.md)

`src/components/SettingsPanel.tsx`:

- §3.5 — "Set default" + the "default" chip: `whitespace-nowrap` in their
  fixed `w-20` slot; `Button` (Add/Update key etc.) already carries nowrap in
  its base cva.
- Jump-nav chips: `whitespace-nowrap` per chip — the nav `flex-wrap`s whole
  chips, a label never breaks mid-word or clips in the h-6 chip.
- §3.4 collapse order — provider rows, `SettingRow`, and keybinding rows are
  `flex-wrap` with an `ml-auto` control cluster: when a row starves (≈360px
  panel), the cluster wraps below the label as ONE right-aligned unit; the
  fixed-slot columns (w-20/w-28/w-12) keep label/status/control aligned row to
  row, nothing overlaps.
- kbd combo chip + the t3 segmented-control labels: nowrap inside their
  fixed-height containers; the hosted-engine buttons are "Firecrawl"/"Exa"
  (the "(default)" suffix moved into the cost line — designed short form).

### 5. Gates (run from this worktree, branch tip)

- `pytest sidecar/tests -q` — **1901 passed, 1 skipped**
  (`test_web_search.py` grew 8 → 29 tests).
- `ruff format --check sidecar` — 354 files clean; `ruff check sidecar` — pass.
- `pnpm install --frozen-lockfile` — clean; `pnpm test` — **137 files /
  1301 tests passed**; `pnpm lint` — 0 errors (1 pre-existing warning in
  `EquityOverviewPanel.tsx`, untouched); `pnpm typecheck` — clean;
  `pnpm format:check` — clean.

## Integration notes for the lead (header-contract changes)

1. **The legacy trio is no longer always sent.** New clients send
   `X-Vysted-Search-Tier`/`X-Vysted-Exa-Key` ONLY in the t3 Exa-direct
   sub-mode, and `X-Vysted-Searxng-Url` only on t2-with-custom-URL. The
   sidecar keeps full back-compat for OLD clients (legacy lanes mapped in
   `_resolve_backend` step b).
2. **Native-search injection** (`agent_runtime.py:829`, untouched — outside
   this track's file allowance) still keys on the LEGACY tier ContextVar,
   which now usually rests at its `native` default (header absent). Practical
   effect: unchanged for everyone except a user who had EXPLICITLY set the
   legacy "Local SearXNG" tier — pre-R8 that selection suppressed native
   injection on native-capable chat models; post-migration (t2) the chat
   model's own search injects again while research tools ride SearXNG.
   If t2/t3 should also suppress native injection for plain chat, that is a
   one-line gate change in `agent_runtime` — flagging rather than touching.
3. **Exa direct omits the R7 header by design** (see §3 above). Any sidecar
   middleware/telemetry that assumes the R7 header is always present should
   treat "absent + legacy byok-exa" as the Exa-direct lane.
4. The web_search tool's "unavailable" copy now says **Settings → Research**.

## NEEDS-MANUAL-CHECK

- **Live 360px screenshot** of the Settings panel (populated providers list,
  t2 and t3 details expanded) — the collapse behaviour is structural
  (flex-wrap + nowrap) and unit-tested for presence, but the proportion-law
  verdict is visual; the rig screenshot path (`/tmp/rigcap.py`) is on the
  lead's machine state.
- **Live end-to-end**: with the managed SearXNG green in Settings and a
  native-incapable model (e.g. DeepSeek), a chat-triggered `web_search` should
  now report `backend: searxng` instead of the keyless floor — verify in the
  brief's source tray on the live rig.
- A user keychain that already holds an Exa key: after migration from legacy
  `byok-exa`, Settings should show t3 + "Exa direct" with the key card green —
  worth one manual relaunch check with a real pre-R8 workspace blob.

## Commits

1. `5beeb56` fix(search): one backend-resolution path — a READY managed
   SearXNG is never bypassed
2. `0b8ca42` feat(settings): researchTier is the one authoritative search
   preference — store, headers, blob migration
3. `027ad1c` feat(settings): one search surface — legacy Web search section
   folds into the Research tiers
4. `18a8bae` fix(settings): proportion-law pass — no two-line buttons,
   governed rows at 360px
5. (this report)

# R7 Track S — Research-Tier Settings UI (worktree: worktree-agent-r7-tiers)

Build the frontend half of the R7 search-tier system, inside THIS worktree only:
`~/Documents/dev/vysted-terminal/.claude/worktrees/r7-tiers`. Branch
`worktree-agent-r7-tiers`. NEVER write to the main repo path. This worktree branches
from a HEAD that already contains the merged sidecar tiers + the redesigned
sectioned SettingsPanel.

## Ground rules

- You OWN: `src/store/search-settings.ts`, `src/lib/search-headers.ts`,
  `src/components/SettingsPanel.tsx`, `src/lib/workspace.ts` ONLY IF the settings
  bundle needs new fields serialized (follow the existing searchSettings bundle
  pattern exactly), their tests. Nothing else.
- Gates per commit: `pnpm typecheck && pnpm lint && pnpm vitest run src/store/search-settings.test.ts src/components/SettingsPanel.test.tsx` + prettier. Full `pnpm test` at the end.
- Conventional commits; push to `origin worktree-agent-r7-tiers`.
- Design law: docs/redesign/VYSTED_DESIGN.md. The SettingsPanel was JUST redesigned
  (sectioned hierarchy, 32px rows, ToggleSwitch) — match its new idioms exactly.

## The sidecar contract (already merged and tested — read these files, don't guess)

- `sidecar/config.py` — research tier ContextVar: tiers `t1_local | t2_searxng | t3_hosted`,
  set by middleware from header `X-Vysted-Research-Tier`; hosted engine from
  `X-Vysted-Search-Engine` (firecrawl|exa); BYOK OpenRouter key from
  `X-Vysted-Openrouter-Key` (never logged/persisted sidecar-side).
- `GET /search/status` — per-engine T1 state: name, breaker state, cooldown seconds,
  e.g. "DuckDuckGo cooling down (24s)"; `available` only false when all engines open.
- SearXNG guided flow (T2): `GET /search/searxng/status` returns the state machine
  verbatim: `not_installed_docker | docker_present_not_setup | pulling | starting |
ready | error(reason)`; `POST /search/searxng/setup` begins/retries setup;
  `POST /search/searxng/teardown` removes. Drive the UI off these states EXACTLY.
- The EXISTING legacy header trio (X-Vysted-Search-Tier/Exa-Key/Searxng-Url) stays
  untouched — the R7 research-tier headers are ADDITIVE.

## Deliverables

1. **Store**: extend `useSearchSettingsStore` with `researchTier`
   ('t1_local'|'t2_searxng'|'t3_hosted', default t1_local) and `hostedEngine`
   ('firecrawl'|'exa', default firecrawl); persist via the existing settings bundle
   round-trip (serialize/deserialize with garbage-guard like the current fields).
2. **Headers**: `buildSearchHeaders` additionally emits `X-Vysted-Research-Tier`,
   `X-Vysted-Search-Engine` (only when t3), and `X-Vysted-Openrouter-Key` (only when
   t3; read at call time from the OS keychain under the llm-provider namespace for
   `openrouter` — find the exact KEYCHAIN_NAMESPACES helper the provider settings use;
   omit when absent, never empty).
3. **Settings UI** (in the Research section of the redesigned SettingsPanel): a
   three-option tier picker (32px rows, radio semantics, name + one-line honest
   description each):
   - T1 "Local scraping (keyless)": when selected, show a live per-engine status line
     polled from `/search/status` every ~20s while the panel is visible ("DuckDuckGo —
     cooling down 24s · Brave — ok · Mojeek — ok"), tertiary text, honest.
   - T2 "Unlimited Research (local SearXNG)": guided one-click flow driven verbatim
     off the status states: not_installed_docker → explain + link hint (docs.docker.com
     install; render as plain text url, no external nav); docker_present_not_setup →
     [Set up] button → POST setup → show pulling/starting progress states (poll ~3s
     during transitions) → ready (green OK + the instance serves automatically) →
     error → show reason + [Retry]. Include [Remove] (teardown) when ready.
   - T3 "Hosted search (BYOK via OpenRouter)": engine segmented control
     Firecrawl (default; free credits note) | Exa ($0.005/req note); show whether an
     OpenRouter key is configured (presence only — reuse however the AI Providers
     section detects key presence) with a pointer to AI Providers if absent; honest
     per-search cost line.
4. **Tests**: store round-trip incl. garbage guard; headers emit/omit matrix (t1 emits
   tier only; t3 emits engine + key-when-present); SettingsPanel renders the three
   tiers and the T2 state machine renders each state (mock fetch).

## Done =

Gates green, full pnpm test green, committed + pushed, report
`docs/redesign/R7_TRACK_TIERS_REPORT.md` (shipped file:line, what to eyeball live,
NEEDS-MANUAL-CHECK — note T2 end-to-end needs the live Docker daemon, the lead runs it).

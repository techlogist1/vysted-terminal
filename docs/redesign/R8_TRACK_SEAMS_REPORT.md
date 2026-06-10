# R8 Track E — Agent Seams Report

Branch: `worktree-agent-r8-seams`. Mission: kill the three operator-evidenced
seams — (1) a persona declaring "I don't have the ability to open panels",
(2) `open_panel` opening equity-overview WITHOUT the requested symbol,
(3) narration claims diverging from actual panel state — under lead decision
D21 (locked): **persona = voice + analytical style ONLY; every first-party
agent gets Copilot's host actions via a loader-level union**.

## Deliverable 1 — Loader-level parity (commit `308a783`)

The first-party roster loader is `sidecar/services/agent_runtime.py`
(`_discover_specs`). Changes:

- `agent_runtime.py:128` — `_host_action_tool_ids()`: projects
  `kind == "host_action"` from `catalog.CAPABILITY_CATALOG` (Constitution
  Principle II — a projection, never a hand-list).
- `agent_runtime.py:173` — `_grant_first_party_hands(spec)`: unions each
  validated spec's tools with the host-action projection plus
  `_FIRST_PARTY_EXTRA_TOOLS = ("research",)`, order-preserving (voice tools
  lead), duplicate-free, idempotent.
- `agent_runtime.py:256` — applied in `_discover_specs` only, so **custom
  agents are NOT unioned** (their authors pick tools; the builder allow-list
  still validates).

§6.5 untouched: the union widens the allow-list only. `propose_order` still
returns `awaiting_user_review` in every autonomy mode
(`_build_local_tools`, pinned by
`test_propose_order_always_awaits_review_even_in_auto`), the frontend gate
still excludes orders from auto-apply, and the read-only mode gate strips
mutators exactly as before (`test_ask_mode_strips_all_mutators` green).

Parity tests (`sidecar/tests/test_agent_runtime.py`):

- `:175 test_first_party_effective_tools_superset_of_catalog_host_actions` —
  every first-party agent's EFFECTIVE tools ⊇ catalog host-action ids (derived
  in the test from the catalog too) and contain `research`; no duplicates.
- `:194 test_grant_first_party_hands_is_idempotent_and_order_preserving` —
  graham's JSON voice tools lead; re-application is a no-op.
- `:205 test_every_agent_json_tool_id_resolves_to_a_catalog_capability` —
  every tool id in every agent JSON resolves to a real internal capability.
- `:257 test_custom_agents_are_not_unioned_with_host_actions`.

**Real seam found by the resolution audit:** `dalio`, `druckenmiller`,
`soros`, `marks`, and `portfolio_advisor` carried the stale `macro` tool id,
which resolves to NO catalog capability (the real ids are
`macro_series`/`macro_search` — the same stale-id class
`test_stale_bogus_ids_are_gone` documents). Those five personas silently
lacked their macro lens. Fixed in the same commit (tool-id correction only;
no voice text touched). Roster counts stay 13 everywhere
(`test_agent_runtime` / `test_agents_router` / `test_mcp_server` coherent).

## Deliverable 2 — Persona prompts know their hands (commit `629ffeb`)

- `agent_runtime.py:149` — `TERMINAL_CAPABILITIES_PREAMBLE`: the shared
  "## Terminal capabilities" note, appended once (idempotent guard) to every
  first-party spec's system prompt inside `_grant_first_party_hands`
  (`agent_runtime.py:199-200`). It names the host actions (including
  `open_panel`'s optional symbol), forbids claiming the agent cannot drive
  the terminal, and states the truthful-narration rule: `applied` → past
  tense; `awaiting_user_review` → "proposed", never "done"; failure → say
  plainly what did not happen; orders always stage behind the confirm dialog.
- JSON voice text untouched on disk — loader-level only.

Tests: `test_agent_runtime.py:223` (every first-party effective prompt
carries it exactly once, voice leading) and `:240` (no JSON file carries it;
graham's on-disk tools/voice intact).

## Deliverable 3 — open_panel carries its arguments (commit `a975dbd`)

- Catalog (`sidecar/services/agent_tools/catalog.py:894` `open_panel` — the
  ONLY catalog change): optional `symbol` property + description telling the
  model to ALWAYS pass it for symbol-aware panels (equity-overview, chart).
  Auto-projects to `TOOL_SCHEMAS`; `test_capability_catalog.py` fully green,
  with a new pin at `:121 test_open_panel_schema_carries_optional_symbol`
  (`panel` stays the only required field).
- Frontend executor (`src/lib/host-actions.ts`):
  - `:462 symbolAwarePanelTarget()` — resolves the panel token through the
    same alias-tolerant `resolvePanelToken` map arrange uses ("overview"
    routes like "equity-overview").
  - `:700 applyHostAction("open_panel")` — a symbol on an equity-overview
    open routes through `openCompanyOverview` → `useEquityCommandStore.
loadSymbol`; on a chart open through `loadSymbolIntoChart` → the
    chart-command channel. Both open the panel first so the command has a
    consumer; both stores RETAIN the last command (mount-race safe). A stray
    symbol on a non-symbol-aware panel is ignored.
  - `:511 describeHostAction("open_panel")` — renders
    "Open Equity Overview — SAKSOFT.NS", and only promises the symbol when
    the apply will actually load it.
- Tests: `src/lib/host-actions.test.ts` — describe rendering, equity routing,
  alias resolution, chart routing, stray-symbol no-op (5 new tests).

## Deliverable 4 — Equity command consumption (commit `b5d0c2e`)

Verified, not broken — pinned with tests:

- `src/modules/equity-overview/EquityOverviewPanel.tsx:685-700` consumes
  `useEquityCommandStore` keyed on the command object whose `seq` bumps on
  every issue → same-symbol re-trigger works.
- Mount-time race: `src/store/equity-command.ts` RETAINS the last command
  (state, never consume-and-clear), so a panel opened by the same host action
  that issued the command still reads it at mount via the selector's initial
  read. No store/effect fix required.

Tests:

- `src/store/equity-command.test.ts` — late-subscriber retention contract
  (loadSymbol with no subscriber → a later read sees the retained command;
  no spurious replay event; `highlightMetric` carries and drops).
- `src/modules/equity-overview/EquityOverviewPanel.test.tsx` — a command
  issued BEFORE mount loads the symbol after the deferred consumption tick;
  re-issuing the SAME symbol re-triggers the load (seq-keyed).

## Deliverable 5 — Grounded narration (commit `3fc1caf`)

`applyHostAction` audit (`src/lib/host-actions.ts`): no branch returns a
success label without doing (or verifying) the work; every failure returns
`null`, which the proposed-changes gate re-pends and surfaces — narration can
never claim an action that did not land.

- `open_panel`/`close_panel`/`focus_panel` resolve via `resolvePanelToken`:
  `open_panel("screener")` now opens the REGISTERED `screener-panel` id
  (previously a silent no-op that still claimed "Opened Screener" — the
  documented id-drift class). Unknown token → `null`.
- `open_panel`/`focus_panel` verify against the live dockview layout
  (`:444 findOpenPanel`, by registered id OR component): a disabled-module
  no-op open returns `null` instead of "Opened X".
- `close_panel` of a not-open panel narrates the truthful idempotent end
  state ("X was already closed"); an open one is closed and says "Closed X".
- `focus_panel` of a not-yet-open singleton narrates "Opened and focused X".

Sidecar side (pinned `sidecar/tests/test_agent_runtime.py:1100` and `:1113`):
a tool call to an unknown/disallowed tool returns the structured relayable
`{ok: false, error: "tool '…' is not available in this build"}` result, and a
raising handler surfaces a structured error keyed to the tool name — the
model can narrate both honestly; neither crashes the stream
(`_dispatch_tool`, `agent_runtime.py`).

Also in this track: `b26298c` (prettier wrap of `portfolio_advisor.json`
after the tool-id fix).

## Verification (from this worktree)

- `sidecar/.venv/bin/python -m pytest sidecar/tests -q` — **full suite
  green** (1889 passed, 1 skipped; baseline 1880/1). Note: the benchmark test
  regenerates `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json`
  as a side effect; the artifact churn was restored, not committed.
- `ruff format --check sidecar` + `ruff check sidecar` — clean.
- `pnpm install --frozen-lockfile` — clean.
- `pnpm test` — **137 files / 1301 tests green**.
- `pnpm lint` — 0 errors (1 pre-existing warning:
  `EquityOverviewPanel.tsx:700 react-hooks/exhaustive-deps` on the
  command-consumption effect — present at baseline, file's effect logic
  deliberately untouched per the track constraints).
- `pnpm typecheck`, `pnpm format:check` — clean.

## Commits

| sha       | deliverable                                                     |
| --------- | --------------------------------------------------------------- |
| `308a783` | D1 — loader-level host-action parity + stale `macro` id fix     |
| `629ffeb` | D2 — loader-level terminal-capabilities preamble                |
| `b26298c` | style — prettier wrap of portfolio_advisor.json                 |
| `a975dbd` | D3 — open_panel optional symbol (catalog + executor + describe) |
| `b5d0c2e` | D4 — equity command-channel contract tests                      |
| `3fc1caf` | D5 — grounded narration on host-action failures + sidecar pins  |

## NEEDS-MANUAL-CHECK (lead's rig)

1. **Live persona drive**: ask Benjamin Graham (or any persona) to "open the
   equity overview on SAKSOFT.NS" on the live rig — it should stage/apply
   `open_panel`/`open_company_overview` with the symbol landing in the panel,
   and the persona should narrate proposed-vs-applied correctly per autonomy
   mode. (Unit/integration layers are pinned; the model-behavior layer needs
   the live loop.)
2. **Proposal-bar failure copy**: `src/store/proposed-changes.ts:112` shows
   the generic "Could not apply this change — its arguments were incomplete."
   for EVERY null apply. With D5 a null can now also mean "unknown panel id"
   or "panel failed to open". The file is outside this track's touch list —
   if the lead wants per-failure copy ("could not open panel X"), the seam is
   ready: `applyHostAction` could return a discriminated result and
   `accept()` could carry its message into `detail`. One-file change.
3. **Persona token cost**: every persona now carries 11 host-action schemas +
   research in its tool list every turn. Schema overhead is the same the
   copilot already pays; flagging only in case the lead wants a leaner set on
   the weak local-model path (ollama/qwen-7b).

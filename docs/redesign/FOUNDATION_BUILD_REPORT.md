# Agent-Native Redesign — Foundation Build Report

**Branch:** `001-agent-native-redesign` · **Window:** foundation + gap-closes ·
**Baseline:** `cfcf5be` (spec amendment) · **Head at report:** `d5d5250`

> **Read this first — honest scope.** This window delivered the **verifiable
> foundation** of the agent-native redesign and closed every documented copilot/
> catalog/runtime gap from `CURRENT_STATE.md`. It did **not** build the three
> large user-facing phases (P1 agent-centric UX, P2 minimal-dark shell +
> marketplace UI, P3 data hub + durable agents). Those are predominantly
> WKWebView UI work that this harness cannot visually validate (the
> `isTrusted`/headless limit), and building them to the constitution's
> full-scope/no-half-ships bar needs either far more build budget or the
> operator's eyeball. They are scoped, not stubbed — see §7. Nothing in this
> report claims the redesign is finished.

---

## 1. What this window shipped (7 commits, all machine-verified)

| #   | Commit    | Item                                                                                                                                                                                                                                                                                 | Satisfies                                                      | Gate result                        |
| --- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- | ---------------------------------- |
| 0   | `a6bdd2f` | Step-0 spec clarification: first-party features ship **pre-installed as built-in plugins**; brokers none pre-installed; yfinance is a pre-installed data plugin                                                                                                                      | reconciles FR-050/US10 with FR-032                             | docs only                          |
| F1  | `0e248f9` | **Single capability catalog** (`catalog.py`) as the one source of truth; closed the ~11 registered-but-schema-less handlers (QuantLib quartet, extended earnings/analyst/SEC, macro_search) + the schema-less `backtest_summary`; fixed `macro_series` missing required `provider`   | FR-023, **SC-006** (0 handlers lacking a schema)               | §6.5 9/9; 107 + 14 pytest; ruff    |
| F2  | `0e248f9` | **Gemini multi-round** fix: thread the tool name onto the `role=tool` message so Gemini's name-keyed `function_response` pairs correctly                                                                                                                                             | FR-024, **SC-005**                                             | pytest (3 new)                     |
| F3  | `0e248f9` | **Custom-agent allow-list** now derives from the catalog (was a stale 5-id set with bogus `news`/`macro`); corrected `researcher.json`'s bogus ids                                                                                                                                   | FR-023, **SC-006** (0 unresolvable)                            | pytest                             |
| F6  | `9ab0272` | **Boot-path hardening**: `pick_free_port`→`Option`, `resolve_data_dir` temp fallback, `start_main_sidecar` never panics (the boot path used to `.expect()`-panic with no window); MCP supervisors handle a `None` port                                                               | spec Edge Cases ("never block boot or panic")                  | cargo fmt + clippy `-D` + test 6/6 |
| F7  | `9ab0272` | Grant **`shell:allow-open`** — the frontend `open()` (Kite OAuth URL, SEC browser) was denied at runtime                                                                                                                                                                             | CURRENT_STATE §1 capability bug                                | cargo                              |
| F8  | `6718418` | **Real plugin-runtime guarantees**: manifest↔instance id/version checks + `requiredHostVersion` semver check reject incompatible plugins **at load** (surfaced, never silently loaded); keychain-backed `resolveSecrets` wired (was the no-op default)                               | FR-054, **SC-015**                                             | eslint/prettier/tsc; vitest +10    |
| F5  | `b9d8908` | **Catalog→MCP single-source projection**: the external MCP surface is now projected from the catalog (same names, same schemas, `readOnlyHint` from `read_only`, same handlers); added a `news` tool reachable by both surfaces; new standing parity audit                           | FR-020/021/022, **SC-004** (US7)                               | §6.5 9/9; 128 pytest               |
| F4  | `d5d5250` | **Ollama-onboarding gate**: a keyless provider must be **reachable** before the first agent call (probe via `/llm/keys/validate`); an absent local model surfaces a clear "start it or pick a cloud provider" message instead of failing silently; folds the WIP local-first default | US1 AS4, FR-032 ("offer both; no silent absent-model default") | eslint/tsc; vitest 630/630 (+1)    |

**Net catalog effect:** 14 → 27 internal capabilities; ~11 unreachable handlers →
**0**; MCP tools 11 → 26, all projected from the catalog. `KNOWN_TOOL_IDS`,
`TOOL_SCHEMAS`, and the MCP surface are now three _derivations_ of one catalog,
not three hand-maintained lists (Constitution Principle II — real, dogfooded).

## 2. Verification snapshot

- **§6.5 audit: 9/9** (`test_safety_end_to_end.py`) — run as a hard gate after
  every change near safety/the registry. The §6.5 LOCKED set and `types/plugin.ts`
  are **byte-for-byte untouched** (verified — only read-only ids entered the
  grep-audited registry).
- **Frontend:** eslint + prettier + `tsc --noEmit` clean; **vitest 630/630**
  (86 files; +11 new: 6 plugin-compat, 4 hostSatisfies, 1 Ollama-gate).
- **Rust:** `cargo fmt --check` + `clippy -D warnings` + `cargo test` 6/6.
- **Python:** `ruff check` + `ruff format --check` clean; **full sidecar pytest
  961 passed / 0 failed** (incl. the SC-004 parity audit + SC-006 catalog audit).
  The full run surfaced 7 failures in `test_agents_store.py` — the same
  bug-encoding (`"macro"` instead of `macro_series`) the F3 sweep fixed in
  `test_custom_agents_router.py` but missed here; fixed in `eda3589` and re-run
  green.
- **Adversarial verification:** a 7-agent workflow cross-checked every new
  catalog schema against its real handler + Pydantic model; it found 2 genuine
  over-constraints (`sec_filings_list`/`sec_insider_transactions` required
  `symbol` though the handler accepts cik-OR-symbol) — both fixed before commit.

## 3. Autonomous decisions & assumptions (Tier-2/3)

1. **`catalog.py` as the single source** (new module) rather than patching three
   lists — Constitution Principle II. `schemas.py`/`KNOWN_TOOL_IDS`/the MCP server
   derive from it. (Tier-3: spec-ambiguous, derives from DNA.)
2. **MCP tool names converge to the internal copilot names** (FR-022): the
   external `get_quote/get_history/get_fundamentals/get_news/get_macro_series`
   are replaced by their catalog equivalents (`price_data`, `fundamentals`,
   `macro_series`, `news`, …). This **renames external MCP tools** — acceptable
   because the project is pre-1.0/unreleased and FR-022 mandates name parity.
   (Tier-2.)
3. **MCP projection rule** = every `read_handler` capability except the
   run_id-scoped `backtest_summary`; per-invocation reads + host actions stay
   local-only. One rule, audited by the parity test. (Tier-3.)
4. **Added a `news` agent tool** (handler + catalog entry + copilot allow-list)
   so news is reachable by both the copilot and MCP (FR-022 domain coverage).
   (Tier-3.)
5. **Ollama readiness gate via `/llm/keys/validate`** (ollama's `validate_key`
   already probes daemon reachability) — the minimal correct fix for the "silent
   failure against an absent local model" defect; the richer offer-both
   onboarding UI belongs to P1. (Tier-2.)
6. **Boot resilience mirrors the MCP children** (port-0 sentinel + graceful
   degrade) rather than introducing a new error UI — consistent with the existing
   pattern; the connecting/error _chrome_ is a P2 deliverable. (Tier-2.)
7. **Version bump deferred.** Left `0.8.0` everywhere: bumping the user-facing
   version implies a release the redesign hasn't reached. `HOST_VERSION` stays
   `0.8.0`, which the new `requiredHostVersion` check now actually enforces. Bump
   when the redesign reaches a release-worthy state. (Flagged, not done.)

## 4. WIP-file disposition (operator's 4 uncommitted files)

All four were **coherent and folded**, none discarded:

- `sidecar/agents/copilot.json`, `sidecar/services/agent_runtime.py`
  (`qwen2.5:7b` default) → folded into **F1** (`0e248f9`).
- `src/modules/chat/ChatSidebar.tsx` (`qwen2.5:7b`), `src/store/llm-providers.ts`
  (`defaultProviderId: "ollama"`) → folded into **F4** (`d5d5250`), now safe
  behind the reachability gate. **Working tree is clean.**

## 5. Tier-1 / §6.5 lock verification

`types/plugin.ts` and the §6.5 LOCKED files (`broker_base.py`, the audit-log DDL,
the kill-switch contracts, the broker/safety mirrors, `test_safety_end_to_end.py`)
are unchanged. The §6.5 grep audit (`registered_tools()` for
`place_/submit_/execute_order` + the `auto_approve` source grep) passes — the
catalog/news additions introduced only read-only ids. No new path to
`confirm_and_place`; `propose_order` still only proposes.

## 6. What needs the operator's eyeball (cannot verify in this harness)

- A **live BYOK agent answer** on each provider (the multi-round Gemini fix is
  unit-proven against a scripted provider; live needs real keys).
- A **live Kite OAuth** round-trip (read-only) now that `shell:allow-open` is
  granted.
- The **Ollama gate** with Ollama actually running vs. stopped.
- The **boot-resilience** path under a real spawn failure (structurally verified;
  not exercised against a forced failure).

## 7. Not built this window — P1/P2/P3 (scoped for continuation)

These are the user-facing redesign and remain **pending** (greenfield — e.g. no
four-mode concept exists in the code today):

- **P1 (US1–US4):** agent as co-equal primary surface; the four-mode spine
  (Ask/Edit-panel/Build/Delegate, FR-003/004); the diff/accept trust gate on
  every mutation with orders routed through §6.5 (FR-010/011); one-shared-context
  hand+agent editing (FR-007). _Recommended first slices (verifiable):_ the
  four-mode agent **store + types**, then the **proposed-mutation (diff) store**
  with the order path wired to the existing §6.5 `confirm_and_place` boundary —
  both pure-TS, vitest-testable — before the UI components.
- **P2 (US5–US7, US10):** the minimal-dark Cursor-grade shell + teaching command
  palette + status chrome (FR-030–033, re-skin `tokens.css` **and**
  `chart-theme.ts` together); the plugin **marketplace** as the primary extension
  model + filesystem loader + signing (FR-050–053) standing on F8's now-real
  runtime checks; first-party features repackaged as pre-installed plugins; Kite
  repackaged as the reference broker plugin; retire `bootstrap_default_adapters`
  as the broker entry path (FR-051); MCP stdio entrypoint + port-discovery file
  (FR-025). _Use the `frontend-design` skill for the shell._
- **P3 (US8/US9 + FR-042):** provider-shaped data registry by model-key +
  preference order with provenance (FR-035); the single BYOK/credentials hub
  rendered from declarations (FR-034/037); durable Delegate agents bounded by a
  **BudgetGuard** + agents rail (FR-026–028); broker granular reads — distinct
  real positions/holdings/P&L/margins (FR-042/SC-012); Cursor-grade settings +
  remappable keybindings (FR-038/039).

The foundation makes these tractable: the catalog gives the agent a complete,
correct toolset; F5 gives the framework story; F8 gives the marketplace its trust
layer; F4/F6/F7 remove the boot/onboarding/capability footguns.

## 8. Genuine blockers / notes for the operator

- **`pnpm ci-local` raw is environment-blocked here:** it calls bare `python`,
  which is not on this Mac's PATH (only `.venv/bin/python` / `python3`). Its
  component checks were run with the correct interpreters and are green; the
  end-to-end `ci-local` (with the PyInstaller sidecar rebuild) + the
  `smoke-test-sidecars.mjs` were **not** run end-to-end this window and should be
  run in CI / a python-aliased shell before any tag.
- **Full sidecar pytest: 961 passed / 0 failed** (`46s`). Full vitest 630/630.
  cargo test 6/6. §6.5 9/9. The remaining un-run gate is the PyInstaller sidecar
  **rebuild + `smoke-test-sidecars.mjs`** (needs a python-on-PATH shell / CI).
- **Pre-existing `pnpm format:check` debt (not this work):** dozens of `.specify/`
  scaffold files + several `docs/` files (incl. the pre-redesign `CURRENT_STATE.md`
  and `CLAUDE.md`) were committed without prettier and fail `format:check`. To keep
  this window's diff reviewable, the doc edits here are **surgical** (not whole-file
  reflows); the scaffold debt is left for a one-time `prettier --write` by the
  operator. The code surfaces this window touched (TS/Python/Rust) are all
  formatter-clean.
- Branch is **not** merged/pushed to `main` — left on `001-agent-native-redesign`
  for review, as instructed.

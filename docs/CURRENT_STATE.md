# Vysted Terminal - Current State (0.9.0)

True at `1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056` (release code head, tags `r15-rc2` / `r15-launch`); register and docs read at `4b460027` (docs-only commits on top of the launch tag). This file describes what exists now; build history is in `CHANGELOG.md`.

## 1. What the product is

A source-available, AI-native finance desktop terminal: bring-your-own-keys, local-first, agent-first, with a plugin architecture. Trading (broker connectivity, orders, simulated accounts) was removed permanently by D81 and is not a feature. Core licence: PolyForm Strict 1.0.0 plus a commercial licence; the plugin contract (`types/plugin.ts`, `types/plugin-runtime.ts`) and the example plugin are Apache-2.0 (`LICENSING.md`). Every commit before the relicensing commit remains AGPL-3.0.

## 2. Versions and stack

- Version **0.9.0** in `package.json`, `src-tauri/Cargo.toml` and `src-tauri/tauri.conf.json` (checked at the launch sha). The sidecar `app.py` (`FastAPI(..., version="0.9.0")`) and `HOST_VERSION` in `src/lib/plugin-bootstrap.ts` both carry the same version — confirmed directly from the launch-sha tree, not inferred; the smoke test asserts `/health` equals `package.json`. Last release tag before this one: `v0.8.0`.
- Interface: Vite 8, React 19, TypeScript strict, Tailwind 4 with shadcn/ui, Zustand, Framer Motion, lightweight-charts, `@xyflow/react`, dockview (panel layout engine, `src/components/PanelHost.tsx`).
- Desktop core: Tauri 2.x (Rust): windowing, OS keychain, sidecar and MCP-subprocess lifecycle. App identifier `com.vysted.terminal`, product name "Vysted Terminal".
- Sidecar: Python 3.13 FastAPI on `127.0.0.1`, port assigned by the core at launch, shipped as a PyInstaller `--onefile` binary. Three sidecars are declared in `bundle.externalBin`: main (`vysted-sidecar`), `vysted-openbb-mcp-sidecar`, `vysted-sec-edgar-mcp-sidecar`. Measured sizes at the release bundle build: main 87,426,304 bytes (target at most 120 MB), openbb-mcp 54,434,448, sec-edgar-mcp 82,788,512. Production dmg: `Vysted Terminal_0.9.0_aarch64.dmg`, 228,480,607 bytes, sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53`.
- Bundled plugins (`plugins/`): openbb-mcp, yfinance, vysted-news, vysted-lenses, example. Compiled-in registry: `src/lib/marketplace.ts` `CATALOG_ROWS`.
- 13 first-party agents under `sidecar/agents/*.json` (copilot, researcher, portfolio_advisor, strategy_critic and the investor personas). The capability catalog `sidecar/services/agent_tools/catalog.py` is the single source for agent tools, the custom-agent allow-list and the external MCP surface.

## 3. Boot and lifecycle (R15-LEAD-123, merged before this tag)

- The core spawns the main data sidecar and waits **45 s x 6 = 270 s** for it to bind (`MAIN_SIDECAR_WAIT_ATTEMPTS = 6`, `src-tauri/src/lib.rs`). The renderer readiness deadline is **300 s** (`READY_DEADLINE_MS = 300_000`, `src/lib/sidecar-client.ts`), set to exceed the core budget plus the health check.
- The two MCP sidecars keep the shared budget of **45 s x 2** (`MCP_PORT_WAIT_SECS = 45`, `MCP_PORT_WAIT_ATTEMPTS = 2`). A contended cold extraction can outlast it: sec-edgar-mcp is killed while still extracting and `/sec` routes return 501 for the session (R15-LEAD-124, open medium).
- A bind later than 270 s still latches the session failed; the core never flips Failed to Ready on a late bind, because the workspace restore would autosave the empty default over the saved layout. The real fix is a `--onedir` build (deferred, `BLOCKERS.md`).
- Because a `--onefile` binary extracts on every launch, the first launch can take up to a few minutes. Measured on the verifier's machine, the release build bound at about 92-114 s and reached connected, holding steady with live data past +340 s (`stage-d/bundle-rc2b/launch/LAUNCH.md`).
- The window paints and accepts input before any MCP child binds (boot runs on its own thread); confirmed headlessly. The packaged-app click-through for this is fixed and no longer awaits manual check (R15-LIFECYCLE-001 is now `fixed`, not `needs_gui`).
- The app writes a rotating log at `<app data>/logs/vysted.log` and Settings offers "Copy diagnostics" (redacted); `GET /system/diagnostics` serves version, status and a redacted log tail. The macOS packaged click-through for "Copy diagnostics" passed on 4 Oct (preview, "Copied", clipboard read back with no key shapes), so R15-LIFECYCLE-008 is `fixed`. Tickers inside log text are not yet stripped (R15-LEAD-149, open medium). Rotation itself was shown on the debug bundle built at the launch sha on 4 Oct (`docs/redesign/verification/r15/gui-close/R15-LIFECYCLE-008/DRIVE.md`).

## 4. Safety model (section 6.5, Tier-1 locked)

Every agent host action (`HOST_ACTION_NAMES`, `src/lib/host-actions.ts`) is staged by the proposed-changes gate (`src/store/proposed-changes.ts`). AUTO autonomy auto-applies only panel, chart and watchlist kinds (`AUTO_APPLIED_KINDS`, `types/proposed-change.ts`); portfolio and other data writes always wait for review. The read-intent strip (`agent_runtime`) and the no-trading invariant (`sidecar/tests/test_no_trading_surface.py`) stay. The sidecar allows only allow-listed browser Origins and returns 403 to any other, including on `/mcp` (R15-CODE-AGENT-001; sidecar side and the macOS packaged app and `pnpm tauri:dev` are all verified live; the Windows packaged click-through is the one piece still awaiting manual check, open high, `needs_gui`). Secrets: the renderer reads the OS keychain and passes keys in request headers; the sidecar cannot read the keychain and never logs a key. Debug builds use a git-ignored dev keystore, release builds the OS keychain.

## 5. Known limitation - agent chat with a keyless local model

Reproduced verbatim from the operator briefing (`docs/redesign/OPERATOR_BRIEFING.md`; DECISIONS_FOR_OPERATOR 4.9-4.12):

> ### Known limitations at rc1 — agent chat with a keyless local model
>
> Accepted by you Sat 26 Sep 04:15 IST (Tier-4 sign-off): `LEAD-030`, `LEAD-037`, `LEAD-038` ship `blocked_tier4` as one documented limitation class. `LEAD-035` now carries the SAME status
> (`blocked_tier4` as of `4c6dfe8c`, batch-24 merged `6778f892`) but for a different reason: it is an ESCALATION under your three-failure stop rule, not a fresh-verifier concurrence — batch-24's
> verifier REFUSED certification a fourth time and named a further narrowing-only fix it would certify (§4.10 below has the detail and your two options). No further filter round this release
> for the other three: a fresh "the local model states a figure with no successful tool call behind it" files against this limitation, not as a new fix. Carried verbatim into
> `RELEASE_NOTES.md`, `CURRENT_STATE.md` and this file, per your sign-off (LEAD-035's wording pending your (a)/(b) choice).
>
> - **`R15-LEAD-030`** (high, `blocked_tier4`, fresh verifier concurred in batch 23,
>   `r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`):
>   > With a keyless local model, the agent can still state an invented price or metric as if a
>   > tool had returned it when the figure is about a company no successful tool call in that turn
>   > covered — one named in the same paragraph as a company whose call succeeded (under a name the
>   > guard cannot map, or never looked up at all), or any company in a turn where no call failed or
>   > no tool was called — and a figure-less fabricated result dump or a code fence left open from
>   > an earlier round can also render, and every shape pinned in eight fix rounds is replaced by an
>   > honest "returned no data" note.
> - **`R15-LEAD-035`** (medium, `blocked_tier4` as of `4c6dfe8c` — an ESCALATION under your
>   three-failure rule, NOT a fresh-verifier concurrence like the other three; batch-24's verifier
>   REFUSED certification a fourth time; this is your call at rc1, §4.10):
>
>   > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an
>   > unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose a
>   > portfolio change (always held for your review, never applied; under AUTO a watchlist or chart
>   > change does apply) and can occasionally state a price it never fetched, while a data request
>   > that qualifies a no-tool instruction after a comma or in reported speech ("Don't use any
>   > tools, except price_data …", "No tools, other than the price lookup …", "He says don't use
>   > tools, but …") still loses every tool and the agent then usually states an invented price as
>   > if fetched.
>
>   Your two options at rc1 (§4.10): (a) accept this residual as a documented known limitation
>   with the wording above, or (b) authorise one bounded round for the verifier's named guard (a
>   qualifier negative lookahead plus `(?<!says )`, which clears 3 of the 4 remaining over-matches
>   offline with 0 lost strips) on the rc2 line. **The lead recommends (b).**
>
> - **`R15-LEAD-037`** (medium, `blocked_tier4`, concurred on corrected wording):
>   > With a keyless local model, a figure the agent states for a company whose data call succeeded
>   > is not checked against that result at all, so it can give an older bar's value from the same
>   > payload as the current price (2 of 18 live runs, 5-6% off) or a figure that appears nowhere in
>   > the payload (1 of 18: ₹20,820 for a ₹2,082 stock).
> - **`R15-LEAD-038`** (medium, `blocked_tier4`, concurred):
>   > With a keyless local model, when you tell the agent not to use tools and ask for a portfolio
>   > change in the same message, it makes no call and nothing is written or queued, but its reply
>   > can say the change was made or staged for your review and can describe holdings that do not
>   > exist.
>
> Fail-safe (why this ships): `data-write` proposed changes always stage for review — AUTO only auto-applies `panel`/`chart`/`watchlist` kinds (`AUTO_APPLIED_KINDS`, `types/proposed-change.ts:38-46`); a narrated
> write stages nothing (no `tool_use` event); there is no `audit_orders` table any more (D81), so no order row can exist. Figure grounding by provenance
> (`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, `agent_runtime.py:2321`, rules 1/2a/2b/2c/3) replaces an ungrounded figure tied to an errored or never-called
> subject with an honest "returned no data" note. The rule-2c fail-safe (`agent_runtime.py:2378-2383`) fires only in a turn with an errored tool call — **a figure for a subject whose call
> succeeded is not checked at all** (LEAD-037). The shipping no-tool matcher is the closed
> `_NO_TOOL_CUE` list in `sidecar/services/planner.py` (`planner.py:136`, batch 21); batch 24 narrows it further, pending its own concurrence. Post-launch design (`DECISIONS_FOR_OPERATOR.md`
> §4.9–4.12, not built): claim grounding by field/provenance plus a structured no-data turn.

Status note (from `docs/redesign/DECISIONS_FOR_OPERATOR.md` section 4.10, outside the quoted block): the operator's ruling of 07:50 IST 26 Sep records R15-LEAD-035 as ACCEPTED, joining LEAD-030, LEAD-037 and LEAD-038 as one documented known-limitation class of the keyless local-model lane, `blocked_tier4`, with no further rounds this release. The quoted block above is the operator briefing's section as promoted at rc1 and is reproduced unchanged; where it says LEAD-035's wording is pending, 4.10 is the later record.

## 6. Register state

Entries at `4b460027` (803). Final adversarial pass: a fresh-context Opus 5.5 pass (battery/drive lanes plus a cross-adversarial keyless + real-user round) admitted 58 new entries after rc1 (`R15-FINAL-001..038`, `R15-LEAD-125..144`); every admitted critical and high was fixed and certified by a fresh verifier before this tag (R15-LEAD-127 at `stage-c/lead127`; FINAL-001..008 at `fix-r1`/`rc2-round2`; LEAD-136/137/141 at `rc2-round3`/`rc2-failsafe`); new mediums and lows are filed for 0.9.1. A carry-forward judge then re-checked every passing final-pass observation against the launch-head code (`final-pass/CARRY_FORWARD_launch.md`): 26 carried, 30 already re-proved, 4 freshly rerun — all 4 held (`final-pass/rerun-launch/RERUN.md`). The pass's GUI half was **not tested** at the launch head (`DECISIONS_FOR_OPERATOR.md` 5.15). A GUI pass on the same sha after the tag (4 Oct) found 0 passed, 0 failed, 1 partial, nothing filed (`docs/redesign/verification/r15/gui-close/VERDICTS.md`). The fresh dmg install and launch passed; the keychain prompt was answered Always Allow. The release app read back a real 0.8.0 profile intact, but its on-screen half was not driven. R15-UI-022 and six parked scenarios did not run: the rig read a stale frontmost app and stopped (fixed in `scripts/rig/rig.py` since), and the operator was present. A second GUI run on 4 Oct with the fixed rig found 1 passed, 1 failed, 2 partial (`docs/redesign/verification/r15/gui-close-2/VERDICTS.md`). LIFECYCLE-008 passed. On screen, the upgrade hides three invalid legacy rows without notice: R15-LEAD-145, medium; the ledger keeps all 84. UI-022 and UI-7 held where driven. Five parked scenarios were not run because the away window ended. Six new mediums and lows were filed (R15-LEAD-145..150); none critical or high.

| Status               | critical | high | medium | low | total |
| -------------------- | -------- | ---- | ------ | --- | ----- |
| fixed                | 17       | 120  | 277    | 215 | 629   |
| open                 | 0        | 0    | 43     | 72  | 115   |
| needs_gui            | 0        | 2    | 1      | 1   | 4     |
| blocked_tier4        | 1        | 11   | 19     | 4   | 35    |
| removed_with_feature | 0        | 1    | 9      | 4   | 14    |
| not_a_defect         | 0        | 0    | 6      | 0   | 6     |
| **total**            | 18       | 134  | 355    | 296 | 803   |

- No critical or high is open. R15-LEAD-116 (high): register status **fixed**, fixed in 0.9.0 (`3acd24dc` and `3af0502c`, certified at `d3509715`). R15-LEAD-127 (critical, the research/copilot-side sibling of R15-DATA-002): **fixed and certified** before this tag (`stage-c/lead127/VERIFY.md`).
- Open (43 medium, 72 low), filed for 0.9.1: the full table is in `RELEASE_NOTES.md` and `BACKLOG_0.9.1.md`.
- Awaiting manual check (3): R15-CODE-AGENT-001 (Windows half only — macOS and dev are confirmed), R15-UI-022, R15-DOCS-024. R15-LIFECYCLE-008 passed its macOS click-through on 4 Oct and is `fixed`. R15-LIFECYCLE-001 is now `fixed`, dropped from this list.
- `blocked_tier4` (35): waiting on operator decisions; grouped in `BACKLOG_0.9.1.md`. The one critical among them is R15-DATA-002 (a bare ticker in both the US and Indian masters binds to the session region; the user-pick fix is merged, the agent-add leg is not; DECISIONS 4.15). This is distinct from R15-LEAD-127 above, which is the research/copilot data-fetch path and is already fixed.

## 7. Distribution and verification

- **Unsigned.** Bundles are not Developer-ID signed or notarized; Gatekeeper refuses the dmg on other Macs (R15-RELEASE-001, DECISIONS 2.8). Windows has no code-signing certificate. **Operator to confirm:** whether this release's dmg gets signed and notarized before publishing.
- **No release pipeline and no auto-update.** Pushing a `v*` tag produces no Release (R15-RELEASE-002); the updater is registered but never invoked and no update artifact is produced (R15-RELEASE-003).
- **CI has not run on the product branch** (R15-RELEASE-004, R15-CROSS-PLATFORM-001): the three workflows trigger on push to `main` and on pull requests. `pnpm ci-local` is the real gate; at the release code head it was exit 0 (vitest 2048, cargo 32, pytest 4013 with 1 skip), with the sidecar smoke test exit 0 (13 agents, toolCount 39) and Gate 8 8 passed.
- **Windows and Linux are unverified** for this release; the Windows list is `WINDOWS_MANUAL_CHECK.md`.
- Release docs: runbook `docs/RELEASE_RUNBOOK.md`; third-party licences `THIRD_PARTY_NOTICES.md` (AGPL-3.0 components ship inside two of the three sidecar binaries and `frozendict` LGPL-3.0 inside two, DECISIONS 5.1-5.2).

## 8. Reference docs

`docs/BLUEPRINT.md` (section 2 locked decisions, 6.5 safety), `docs/SAFETY_ARCHITECTURE.md`, `docs/MCP_INTEGRATION.md`, `docs/SIDECAR_API.md`, `docs/PLUGIN_DEVELOPMENT.md`, `docs/DESIGN_SYSTEM.md`, `docs/redesign/DECISIONS_FOR_OPERATOR.md`, `docs/redesign/OPERATOR_BRIEFING.md`, `docs/redesign/BACKLOG_0.9.1.md`.

A panel-by-panel and endpoint-by-endpoint inventory (the kind the pre-redesign baseline carried in its old sections 3.2-3.11) is not restated here: the previous version of this file described a Next.js App Router static-export frontend, a `tradesa-v2` broker-wrapper plugin and other facts that no longer match the shipped Vite/React stack and the current bundled-plugin set (openbb-mcp/yfinance/vysted-news/vysted-lenses/example per `CLAUDE.md`). That staleness is itself a tracked, open register entry — **R15-FINAL-036** (low, open, filed for 0.9.1): "CURRENT_STATE.md cites a missing build report, the deleted `monte_carlo.py` and an absent `ConnectCard.tsx`, and reports 0.8.0 and 619 vitest / 942 pytest." A from-scratch subsystem inventory at the current stack is 0.9.1 scope; until then, the per-subsystem reference docs listed above are the accurate current-state source for their areas.

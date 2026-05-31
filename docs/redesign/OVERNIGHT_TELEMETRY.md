# Overnight build — telemetry log

Branch `001-agent-native-redesign`. Build start **2026-05-31 23:30 IST** → closeout
**2026-06-01 ~01:00 IST** (~1h30m). Lead: Opus 4.8 (1M). Rig: tauri-plugin-mcp driving the
real Tauri app (`dev-tools` feature). Narrative: `OVERNIGHT_BUILD_REPORT.md`.

## Agents / workflows dispatched

| #    | Phase     | Agent / workflow                          | Tokens | Tool-uses | Wall  | Outcome                          |
| ---- | --------- | ----------------------------------------- | ------ | --------- | ----- | -------------------------------- |
| wf1  | map       | `redesign-surface-map` (10 Explore subagents) | ~860k  | 276       | 343s  | 8/10 structured; full code map   |
| tm1  | item 5    | teammate — cold-boot panel auto-retry     | ~93k   | 46        | 285s  | hook + 4 panels, 78 tests green  |
| wf2  | review    | `overnight-diff-review` (5 review + verify subagents) | ~910k | 151 | 145s | 3 confirmed; 2 fixed, §6.5 clean |
| lead | all       | Opus — rig driving, shell/overlap/Jarvis/model, integration, verification, report | — | — | — | — |

Subagents: ~22 (10 map + 1 teammate + 11 review) + lead.

## Per-item outcome

- Item 1 (shell craft): **done + rig-verified** (overlap gone by rect math; kill-switch demoted; banner de-leaked).
- Item 2 (Jarvis): **done + rig-verified e2e** (propose→gate→accept→panel closed on the live agent).
- Item 3 (model): **done** — default already qwen2.5:7b (verified in UI); test fixed. Finding: 7b tool-use inconsistent → cloud for reliable control.
- Item 4 (overlap): **done + rig-verified** (no overlap at 90px; host-side min-sizes, types/plugin.ts untouched).
- Item 5 (cold-boot): **implemented + unit-verified** (live self-heal pending a timed cold start).
- Item 1b (dock/palette/settings): **partial** — persona Lens picker done; palette/settings/placement deferred (documented).

## Gates (closeout)

- Frontend: `format:check` PASS · `eslint` PASS · `tsc` PASS · `vitest` **744/744** (102 files).
- Sidecar (venv): catalog / mcp-parity / runtime / agents-store / tool-loop / mcp-server /
  router / schemas / ollama PASS; **`test_safety_end_to_end` 55 passed — §6.5 still 9/9**.
- Not run (operator pre-tag): full `pnpm ci-local`, `smoke-test-sidecars.mjs`.

## Code

10 commits · **32 files, ~+2500 / −195** (incl. post-review hardening). Branch pushed to
origin at every checkpoint (backup). NOT merged, NOT version-bumped (all five version sources
read `0.8.0`).

## Guardrails

Tier-1 LOCKED set (`types/plugin.ts`, `tauri.conf.json`, safety/broker/audit/kill-switch
models, `broker_base.py`, `kill_switch.rs`, `test_safety_end_to_end.py`, CI) **byte-for-byte
untouched**. No STOP-AND-SURFACE hit; the PanelSpec-min-size temptation was avoided by routing
the fix host-side. Rig stays dev-only.

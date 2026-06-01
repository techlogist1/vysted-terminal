# JARVIS Sprint — telemetry

_Live log of the overnight JARVIS intelligence sprint on branch `002-jarvis-intelligence`
(off `001-agent-native-redesign`). Maintained by the lead throughout. Append-only per
phase; never rewrite history. Started 2026-06-02._

## Conventions

- **Agents** = subagents spawned (workflow + ad-hoc). **Wall** = approximate elapsed.
- **Tokens** = approximate output-token spend where known (workflow budget pool).
- Files/lines tallied at each track's integration commit (`git diff --stat`).

## Phase ledger

| Phase           | What                                                                  | Agents         | Wall     | Files/lines          | Notes                                                                                                                                                                  |
| --------------- | --------------------------------------------------------------------- | -------------- | -------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0 — Spike       | Map as-built Pass-B + 4 external-integration feasibility + HW fit     | 8 (1 workflow) | ~4.5 min | docs only (+2 files) | read-only; ~615k subagent tokens; verdicts in FINDINGS §2                                                                                                              |
| A — Aliveness   | Live research step-log surface (SSE research_step + ResearchActivity) | 0 (lead)       | —        | 15 files             | commit `ba517ca`; sidecar e2e + vitest + typecheck green; **RIG-VERIFIED** (live "RESEARCHING" trace, 12s timer, 5 steps, scanline; populated dark cockpit, Connected) |
| E — Smart brain | OpenRouter broker + in-house planner (intent + decompose)             | 0 (lead)       | —        | 11 files             | commit `5131758`; +rig-bridge `ad92316`; 259-test sweep + 22 planner tests + typecheck green                                                                           |
| D — Fit-scorer  | hardware_fit.py + /system/hardware + Settings card                    | 0 (lead)       | —        | 8 files              | commit `0e4d6c0`; 17 tests; live curl on this M1 = correct verdicts (qwen GREEN, Tongyi-30B RED)                                                                       |
| C — Research    | SearXNG autodetect fix + Tongyi-remote backend                        | 0 (lead)       | —        | 7 files              | commit `5cb6207`; **LIVE-VERIFIED** vs a real searxng/searxng container (autodetect 1.96s, absent 0.01s); 50+ tests                                                    |
| B — Competence  | inferred-intent mode collapse + custom arrange + act-first prompt     | 0 (lead)       | —        | 14 files             | commit `98a1ba8`; sidecar inference-gate + planCustom tests; 854 vitest + full sidecar agent/catalog sweep green; AUTO-vs-Build contradiction killed                   |

## Floor verification (the non-negotiable spine)

- **Tier-1 LOCKED diff vs base `fcd6fcf`: EMPTY** — byte-for-byte untouched (plugin/safety/broker/audit/kill-switch contracts, broker_base.py, kill_switch.rs, test_safety_end_to_end.py, tauri.conf.json, CI).
- **§6.5 audit: 9/9 PASS** (`test_safety_end_to_end.py`, 32s) — incl. test*audit_2 (no bypass to `_place_confirmed`) + test_audit_6 (AI-order grep gate: no `place*/submit\_/execute_order`, no `auto_approve` anywhere). Orders never auto-apply; brokers read-only.
- No new pip dependency added in any track (all on existing httpx/fastapi/openai-SDK/stdlib) — no PyInstaller `--copy-metadata`/`--collect-data` exposure.
- **`pnpm ci-local`: PASS** — full CI mirror green: ensure-sidecars (clean rebuild, all 5 tracks) → lint → format → tsc → cargo fmt → clippy `-D warnings` → ruff → **vitest 854** → cargo test → **pytest 1288**. (Two earlier attempts failed only on a bare-`python` PATH gap in the background shell; resolved by venv-on-PATH — not a code failure.)
- **`smoke-test-sidecars.mjs`: PASS** — all 3 `--onefile` binaries boot (main `/health` + screener endpoint OK; both MCP children bound + survived).
- **Final rig pass (rebuilt binary): DONE** — mode bar = `Agent`+`Delegate` (pixel+DOM); `/system/hardware` + `/llm/providers` (openrouter) live; Track A `ResearchActivity` rig-verified earlier. App + rig left running (sidecar `:52479`).

## Running totals

- Subagents spawned: 8 (Phase-0 workflow `ws1wyq5b2`, 615452 tokens, 199 tool uses); the
  five build tracks were lead-driven (sequential, to avoid the worktree-contamination
  risk CLAUDE.md warns about) — workflows used for read-only fan-out, not parallel edits.
- Commits on branch: 9 (`2f1c154` Phase-0 docs → `98a1ba8` Track B), + final docs/report.
- Tracks declared done: 5 / 5 (A, E, D, C, B) — all test-verified; A rig-verified, C live-verified.
- Build order executed: A → E → D → C → B (by dependency).

_(Updated as the sprint proceeds.)_

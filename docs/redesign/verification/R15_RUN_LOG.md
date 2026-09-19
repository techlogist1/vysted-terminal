# R15 LAUNCH — run log (telemetry)

Owned by the telemetry worker; appended at every wave boundary. Times are IST, from the real clock.

## Waves

| # | Started | Workflow / task | Agents | Routed → actual model | Purpose | Result |
|---|---|---|---|---|---|---|
| W0 | 06:11 | lead own-hands Stage 0 | 0 | lead = claude-fable-5-1 | brief saved, tree adjudicated, 4 commits (043850c, 7a1cd8f, 0112a0c, 96511d6) | done |
| W1 | 06:20 | wf_6871fdb3-621 r15-stage0-truth | 11 | sonnet×5 → claude-sonnet-5, opus×5 → claude-opus-5, haiku×1 | Stage 0 scouts + pushguard + rig | 8/11 done; 3 died on network resets (partition file landed; pushguard committed; rig salvaged in W5) |
| W2 | 06:23 | wf_734dffa1-5d4 r15-census-intent-world | 16 | sonnet×4, opus×12 → claude-opus-5[1m] | Intent + World sweeps | 7/16: 4 extracts (1,032 promises) + 5 world research files; verifies/ledgers died → relaunched in W5 |
| W3 | 06:30 | wf_4073e516-82c battery curate + packs | 25 | opus | curator + 24 packs | curator + 1 pack done; 23 died → W5 |
| W4 | 07:05 | wf_6c0515c7-f78 code census | 31×2 | opus | critique → refute | 3 critiques landed; machine lost power 10:17; stopped 14:50 → W5 |
| W5 | 14:50 | 18 × r15-fanout (see run-state L5) | ~100 | Fable 5.1 + Opus 5 mix | all five census sweeps + lifecycle + audits + ideation | in flight |
| bg | 06:20 | `pnpm ci-local` baseline (detached) | — | — | full chain baseline numbers | in flight |

## Strategy changes

- 10:17–14:36 IST: not a usage wall — the MacBook battery died (Low Power Sleep → hibernate). ~50 agents lost mid-flight; files-as-you-go + per-item outputs kept the loss to in-flight work. Operator re-logged in 14:41.

## Limit walls

- 10:17–14:36 IST: not a usage wall — the MacBook battery died (Low Power Sleep → hibernate). ~50 agents lost mid-flight; files-as-you-go + per-item outputs kept the loss to in-flight work. Operator re-logged in 14:41.

## API spend

(budget pending `r15/stage0/BUDGET.md`)

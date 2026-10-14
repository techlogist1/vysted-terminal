# lows-int fix-C (cluster C, 04:11 IST)

Base: worktree-agent-lows-int-9368c62 at 2dbcde70. Branch: worktree-agent-lows-fix-C-9368c62.
Writer: Opus 5.5. Only test files changed. No assertion removed, skipped or weakened; no product code changed.

## Discriminator

`git log --oneline 4c6dfe8c..9368c626 -- <file>` is EMPTY for all three test files, for
`src/store/quant.ts`, `src/store/agents.ts` and `src/modules/agent-builder/`. For
`src/lib/sidecar-client.ts` the only 004 commit is `4d7bc887 fix(watchlist): carry the picked
listing's region ... (R15-DATA-002)` (adds a region header to `quotes`, no deadline change).
No 004 rc1 fix pins any of these tests, so none is immovable.

Partition origins (`git log --oneline 4c6dfe8c..<partition> -- <file>`):

- OptionPricerPanel.test.tsx: P3 `4803edee fix(quant,backtest): derive date defaults at mount ... (R15-UI-063, R15-UI-062)` (carries the R15-CODE-PLATFORM-041 test); P2 `f8d6594f fix(stores): one sidecar transport for the agents, quant and workflow stores (R15-CODE-FRONTEND-027)`.
- YieldCurvePanel.test.tsx: P3 `7ce27e29 fix(quant): duplicate-pillar yield curve bootstrap returns 400, not 500 (R15-UI-077)`; P2 `f8d6594f` (as above).
- agent-builder.test.tsx: no commit in any partition or on 004 (pre-base test). The code it exercises, `src/store/agents.ts`, changed only in P2 (`f8d6594f`, `72daa055`, `26c0cb03`, `e9da8e93`, R15-CODE-FRONTEND-027).

## Per test

### src/modules/quant/OptionPricerPanel.test.tsx — R15-CODE-PLATFORM-041 steps below the shared floor blocks submit
- Verdict: test_drift.
- Cause: P3 wrote the "no POST" check as `expect(vi.mocked(fetch)).not.toHaveBeenCalled()`; P2 moved the quant store onto `sidecarRequest` and the file's mocks to `vi.mock("@/lib/sidecar-client", ... sidecarRequest: vi.fn())`. Global `fetch` is no longer a spy: `TypeError: [Function fetch] is not a spy`.
- Action: the same assertion against the store's transport, `expect(sidecarRequest).not.toHaveBeenCalled()` (identical to the sibling "blocks the POST on a bad input" test P2 converted). Validation message and disabled-button assertions unchanged.

### src/modules/quant/YieldCurvePanel.test.tsx — R15-UI-077 duplicate pillar blocks the POST
- Verdict: test_drift. Same cause and same one-line repointing as above.

### src/modules/agent-builder/agent-builder.test.tsx — POSTs the payload and refreshes the list on save
- Verdict: test_drift (fixture, not assertion).
- Cause: reproduced on the P2 candidate alone (78220d0c: 1 failed / 11 passed), so P2 shipped it red; P1/P3 are not involved (neither touches the panel or the store). The test seeded the mount list GET with `fetchMock.mockImplementationOnce([])`, i.e. by call order. P2's `refreshCustom` now awaits `sidecarRequestInit` (async `buildSearchHeaders`) before `fetch`, so the panel's own `GET /custom-agents/tool-ids` lands first, eats the one-shot `[]`, and no tool button renders (`Unable to find ... button "price_data"`).
- Action: the same `[]` answer routed by URL (`/custom-agents`), every other URL delegating to the file's default mock. All assertions (POST body id and tools, list refresh to one agent) untouched. Reordering product awaits to satisfy call order would be special-casing product code for a test, so it was not done.

## Ruling on integrator commit b016ac26 (sidecarRequestInit no default deadline)

Upheld, no change. 004 certified no deadline behaviour in range: at 9368c626 `src/lib/sidecar-client.ts` has no timeout at all (R15-LIFECYCLE-027 `f1182138` is P3-only, not an ancestor of 9368c626). The two intents being reconciled are partition intents: P3 (every `sidecarRequest` bounded by a 30 s default) and P2 (`sidecarRequestInit` deadline only when `timeoutMs` is passed; `sidecar-client.test.ts` pins `init.signal` undefined). Callers after b016ac26:
- every `sidecarRequest` / `sidecarGet` caller: 30 s default, or the caller's `timeoutMs` (P3 intent kept);
- `store/workflow.ts` REST helper: explicit `SIDECAR_REQUEST_TIMEOUT_MS` (P2 intent);
- `store/agents.ts refreshCustom`: `sidecarRequestInit("GET", { timeoutMs: SIDECAR_REQUEST_TIMEOUT_MS })`, bounded;
- `store/workflow.ts runWorkflow` SSE stream: no deadline, by design ("the stream lives as long as the run"). A 30 s default here, as the pre-fix merge had, would abort every workflow run longer than 30 s.

## Verification

- Focused: `vitest run src/modules/quant src/modules/agent-builder src/lib/sidecar-client.test.ts src/store/agents.test.ts src/store/workflow.test.ts src/store/quant.test.ts src/modules/node-editor/schedule-control.test.tsx` -> `Test Files 12 passed (12)`, `Tests 101 passed (101)`.
- Full vitest: `Test Files 169 passed (169)`, `Tests 2031 passed (2031)`.
- prettier --check (3 files) clean; eslint (3 files) exit 0; `pnpm typecheck` exit 0.

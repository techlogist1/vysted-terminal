# R15-CODE-FRONTEND-027 (second attempt, CN)

- Entry: R15-CODE-FRONTEND-027 (P2, prior set W8)
- Outcome: fixed_untested
- Branch: worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8 (base 4c6dfe8c)
- Written: 07:04 IST

## Commits

- 72daa055: a cherry-pick (-x) of W8's 26c0cb03. refreshCustom: a non-2xx now sets customStatus 'error' with the server detail. It is kept verbatim.
- f8d6594f: fix(stores): one sidecar transport for the agents, quant and workflow stores.

## What changed

- `src/lib/sidecar-client.ts`:
  - Adds `sidecarRequestInit(method, opts)`, the single builder for region, search headers, per-call headers, JSON body and deadline. `sidecarRequest` now builds on it.
  - Adds a `timeoutMs` option. A deadline that passes throws `SidecarError(504, SIDECAR_TIMED_OUT)`, both in `sidecarFetch` and while the body is still arriving.
  - Adds `SIDECAR_REQUEST_TIMEOUT_MS` (30 s) and a `PATCH` verb (`SidecarMethod`).
- `src/store/quant.ts`: `postJson` now goes through `sidecarRequest`. That gives the one error policy, the region/search headers and the named unreachable error. It has no deadline because the sidecar caps compute with MAX_MC_PATHS=10M and MAX_BINOMIAL_STEPS.
- `src/store/workflow.ts`:
  - The schedules, webhooks and saved-list calls now go through `sidecarRequest` under the 30 s deadline, with PATCH going through the verb.
  - `runWorkflow` (SSE) uses `sidecarRequestInit` + `sidecarFetch`, so a run carries the region and search headers. A non-2xx now shows the `extractSidecarDetail` sentence instead of the raw body. `_safeText` and `JSON_HEADERS` are removed.
- `src/store/agents.ts`: `refreshCustom` uses `sidecarFetch` + `sidecarRequestInit` under the deadline, so it gets the region/search headers, the unreachable sentence and reachability reporting.

## Tests written (source only, NOT run: off-lane rule)

- `src/lib/sidecar-client.test.ts`:
  - A call past its `timeoutMs` gives SidecarError(504) with the timed-out sentence.
  - `sidecarRequestInit` sets the region, per-call headers, drops undefined headers, sets a JSON body and PATCH.
  - custom-agents refresh sends the region under a deadline.
  - A refused custom-agents load gives SIDECAR_UNREACHABLE, not 'Load failed'.
- `src/store/workflow.test.ts`: the run carries region, Accept and Content-Type, and a 422 JSON detail is the error message.
- `src/modules/node-editor/schedule-control.test.tsx`:
  - Mocks `sidecarRequest`.
  - The create case now asserts the POST args + timeoutMs.
  - New case: the PATCH toggle, whose failure shows its sentence.
- `src/store/agents.test.ts` (cherry-picked, unchanged): refreshCustom 404 gives customStatus 'error'. This is the entry's acceptance test.

Tests changed because they pinned the old transport:

- `src/store/quant.test.ts` and the 4 quant panel tests (Option, Bond, Greeks, YieldCurve):
  - They now mock `sidecarRequest`. They used to stub fetch + `getSidecarBaseUrl`, and the store no longer calls fetch directly.
  - quant.test's error case expected the old "POST <path> failed (400)" prefix. It now expects the server sentence; the status is on `SidecarError.status`.
- `src/store/workflow.test.ts`: the sidecar-client mock now spreads the actual module (the store imports more of it); it still stubs only `getSidecarBaseUrl`.
- `src/modules/node-editor/NodeEditorPanel.test.tsx`: the mock also answers `sidecarRequest` with [] for the embedded ScheduleControl list. The verb's port lookup is internal to sidecar-client, so the stubbed `getSidecarBaseUrl` does not reach it.

## Untested pending integration

Everything above: vitest, tsc and eslint were not run (off-lane). Prettier was run on every touched file.

## Merge

Simulated: 4c6dfe8 + merge W8 (origin/worktree-agent-lows-P2-W8-shell-page) + merge this branch. Both merged cleanly.

To keep that clean:

- W8's lines in agents.ts stay verbatim: its import line and the non-2xx block.
- The new sidecar-client names ride a second import line placed after the type imports. It can be folded into the first import after both land.
- refreshCustom therefore keeps its explicit base URL + non-2xx block instead of a bare `sidecarGet`. The transport it uses is identical to `sidecarGet`'s (same init builder, same fetch wrapper, same `extractSidecarDetail` normalisation).

## Risks / notes

- No `sidecarPost` was added. `sidecarRequest("POST", ...)` already is the shared POST path, so a wrapper would be a second name for the same thing.
- `safety.ts` no longer has a sidecar fetch: that surface went with the trading removal. Nothing to switch.
- `AbortSignal.any` is used only when a caller passes both a signal and `timeoutMs`. No current call site does. It needs Safari 17.4+ on the macOS webview.
- The deadline is opt-in. `sidecarGet` sites keep no deadline because SEC and research GETs can be legitimately slow.
- Out of scope, left as is:
  - NodeEditorPanel.tsx's own save/load fetches and AgentBuilderPanel's write/delete (already `sidecarFetch` + `extractSidecarDetail`). Neither is in the entry's file list.
  - The workflow run still sends `apiKey` in the body. That is pre-existing and not this entry.

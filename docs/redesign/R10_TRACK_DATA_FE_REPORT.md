# R10 Track FRONTEND-DATA — ship report

Branch: `worktree-agent-r10-fedata`. Commits: `c6f4159` (feat) + `ed64c9d` (fix) + this
round-2 fix commit.

## What shipped

### §1 Streaming screener run

`runScreener` in `src/store/screener.ts` now POSTs to `/screener/run/stream` and
consumes the SSE response. The parser strips the `data:` prefix per the sidecar wire
format (`routers/backtest.py:195`: `f"data: {json}\n\n".encode()`), handles `\n\n`
event boundaries, and flushes the trailing decoder buffer after the final read chunk.
Bare NDJSON is also tolerated for resilience. Progress frames populate
`progress: {phase, done, total, detail} | null`; the result frame finalises
`lastResult` with `partial`, `coverage`, and `freshness`. `cancelRun()` aborts via
`AbortController` — server-side engine disconnects per Team SCREENER's SSE contract.
Unary fallback on `404` (older sidecar). Network error before any response attempts
the unary fallback honestly; if that also fails, an honest error message is set (not a
fabricated status code).

AbortController race fixed: every async state write is guarded by
`_runAbortController === controller` so a superseded run cannot clobber the live run's
state or null the live controller.

### §2 Saved screens

`saveScreen / deleteScreen / loadScreen / setSavedScreens / savedScreens` are in
`useScreenerStore`. Serialization helpers are **exported**:

```ts
import { serializeSavedScreens, deserializeSavedScreens } from "@/store/screener";
```

// R10-INTEGRATION: wire savedScreens into the workspace blob in two places:

**1. `src/lib/workspace.ts` — `serializeWorkspace`:**

```ts
import { serializeSavedScreens } from "@/store/screener";

// Inside SerializedWorkspace / serializeWorkspace:
savedScreens: serializeSavedScreens(useScreenerStore.getState().savedScreens),
```

**2. `src/lib/workspace.ts` — `deserializeWorkspace`:**

```ts
import { deserializeSavedScreens } from "@/store/screener";

// Inside deserializeWorkspace, guard for older blobs:
if (typeof blob.savedScreens === "string") {
  useScreenerStore.getState().setSavedScreens(deserializeSavedScreens(blob.savedScreens));
}
```

`setSavedScreens` is a proper store action — it calls `set({ savedScreens })` so all
subscribers are notified and restored screens render. Do NOT write directly to
`getState().savedScreens` (direct mutation bypasses Zustand's subscriber notification).

**3. `src/app/page.tsx` — autosave subscription:**

Because savedScreens changes do not move the dockview layout, add a store subscription
in `page.tsx` that calls `autosaveLayout()` when `savedScreens` changes (per the
CLAUDE.md workspace blob rule: "if the change doesn't move the dockview layout, add a
store subscription in page.tsx calling autosaveLayout()").

The store is created bare with `create<ScreenerState>(...)` — **no `subscribeWithSelector`
middleware**. Use the established two-argument `subscribe((state, previous) => …)` pattern
that all 12 existing page.tsx subscriptions follow:

```ts
const unsubscribeScreens = useScreenerStore.subscribe((state, previous) => {
  if (state.savedScreens !== previous.savedScreens) {
    void autosaveLayout();
  }
});
// Add unsubscribeScreens() to the cleanup return.
```

Without these three wires, `savedScreens` are session-only and do not persist across
relaunches. The store API is complete; the lead wires workspace.ts at merge.

### §3 Panel

`ScreenerPanel.tsx` updated:

- Universe picker includes all three India universes (labels present from the
  contracts commit).
- Progress: caption-13 detail line + determinate 2px bar (zinc-700 / lume). On the
  streaming path the bar advances with real `done/total` data. On the unary fallback
  path (no progress frames) an indeterminate pulse bar is shown with "Sending
  request…" — honest, not "Connecting… forever".
- Cancel button morphs from Run while `status === "loading"`.
- Result header: PARTIAL badge (text-warning, 1px border, no filled background per
  VYSTED_DESIGN.md:458) shown whenever `partial === true`, independent of `coverage`.
  Coverage line follows separately. Three freshness tiers with correct labels:
  `quotes_as_of` → "quotes", `valuation_as_of` → "valuation", `deep_as_of` → "deep
  fields".
- Saved-screens strip: save (inline name prompt), load, delete.

### §4 Portfolio seams

**Important distinction for Team LEAD and Team RUNTIME:**

The `ScreenerPanel` (and the portfolio panel) is **local-store-backed** — holdings
live in `usePortfoliosStore` which persists via the workspace blob. The panel's
add/edit/delete affordances call `addHolding / updateHolding / removeHolding` on the
Zustand store directly.

The sidecar routes `POST /portfolio/positions`, `PUT /portfolio/positions/{id}`, and
`DELETE /portfolio/positions/{id}` (named in E6) are a **DIFFERENT surface** — they
are NOT called by this panel or the host-action apply path. Agent capabilities that
write to those sidecar routes write to a store the panel never reads. The exported
typed client below is what the host-action apply path must use:

```ts
import { addPosition, updatePosition, deletePosition, refresh } from "@/store/portfolios";

// addPosition returns string | null — null means the add was rejected (empty symbol
// etc.). The apply case must check for null and report an honest failure.
const holdingId = addPosition(input);
if (!holdingId) {
  /* report failure — do not narrate a write that never landed */
}
```

`addPosition` was fixed to return `string | null` — the genuine appended holding id
or null on silent no-op. `updatePosition` was fixed to return `boolean` — false when
the holding was not found or the input was rejected. `refresh()` is a no-op (local
state; React subscribers update synchronously).

### Notes seam

`appendGeneral` and `appendSymbolNote` **shipped in commit `c6f4159`** with 8
behavioral tests in `src/store/notes.test.ts`. The round-2 fix pass (`ed64c9d`) left
`notes.ts` untouched in that commit but the round-3 fix (this commit) corrects
`joinNote`: the previous implementation trimmed the **existing** note body on append,
destroying leading indentation and deliberate trailing newlines. The fixed version
preserves the existing body verbatim and only trims the new addendum.

**Team FRONTEND-BRIEF write_note apply case:** call `appendGeneral(text)` or
`appendSymbolNote(symbol, text)` from `useNotesStore` — these are the R10 write seams.
`setGeneral` / `setSymbolNote` overwrite the entire note and should only be used for
full replacements.

## Gates

All vitest, lint, typecheck, format:check must be green before push. See the branch
for the full test suite covering: cancel mid-stream, progress frame, result with
partial/coverage/freshness, Run→Cancel morph, PARTIAL badge with and without coverage,
three-tier freshness labels, saved-screens strip (save/load/delete), append seam
correctness, existing-body preservation on append.

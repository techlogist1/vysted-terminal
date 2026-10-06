# Code sweep — session 2 addendum

Read `COMMON.md`, `PROMPT_code.md`, and this file first (and `PROMPT_refute.md` for the
refute stage) before doing anything else. Continue from any existing output file — never
restart a partial file.

## Models

Every stage in this session runs on **opus**, never `fable` or `haiku`. This differs from
`code-A.json`'s pattern (`refute` on `fable`) — session-2 launch-args set `model: "opus"` on
both stages explicitly; do not substitute.

## Refute stage

Follows `PROMPT_refute.md` exactly (the Stage B item 1 spec: refute/admit/downgrade/upgrade
against the raw file you or a prior worker just wrote, verdict shape, output path convention
`census/refute/code-<id>.json`, continue-from-partial rule). The critique stage in this
session still uses `PROMPT_code.md`'s CRITIQUE section for output shape and rigor.

## Trading overlay (operator decision, 23 Sep: trading permanently out of the product)

Applies to the **`host-actions-proposed-changes`** subsystem only. The order-proposal /
review-bar / broker-order path is being deleted:

- **Critique only the non-order proposed-changes gate**: paper-portfolio writes, notes,
  screens, layouts, workflow nodes — i.e. every host action and every `ProposedChange` kind
  that is NOT an order proposal, order review, or broker-order call.
- Do not analyse order-only code as if it will stay. If you encounter an order-only finding
  candidate (a broker adapter call, an order-confirmation gate, a route that exists only to
  serve order placement), do not deep-critique it — tag it `removed_with_feature` in the raw
  finding's `notes` field instead of writing normal consequence/fix text, and give it no
  `severity` beyond `low` (informational only, it closes without a fix).
- The kill-switch and audit-log mechanisms are shared beyond order placement — critique them
  normally and state in `notes` what they gate outside orders (agent autonomy / other
  control-plane actions), same as `PROMPT_refute.md`'s handling for those mechanisms.
- All other subsystems in this session are unaffected by the overlay.

## Verify-and-finish semantics (llm-adapters, error-layer)

These two already have raw findings AND refute verdicts on disk
(`census/raw/code-<id>.json`, `census/refute/code-<id>.json`) but no critique `.md` — the
critique stage was never completed. For each:

1. **Write the missing critique file** `census/code/<id>.md` from the EXISTING raw findings
   and their refute verdicts (do not re-derive from nothing) — same table shape as
   `PROMPT_code.md`'s CRITIQUE output 1 (principle | grade | evidence file:line |
   consequence), plus priority findings. Where a raw finding was `refuted`, do not present it
   as live in the critique prose; where `admitted`/`admitted_with_correction`, reflect the
   corrected severity.
2. **Then hunt the subsystem's files for MISSED findings** — read the code fresh, the same
   rigor as a normal critique pass, looking specifically for what the existing raw file does
   not already cover.
3. Write any new findings as a **new raw file** `census/raw/code-<id>-2.json` (standard raw
   shape, `raw_id` prefix `COD-<id>-2`; an **empty array** if you find nothing new — do not
   pad to avoid an empty file). This file, not the original `code-<id>.json`, is what the
   refute stage for these two items will consume.

## Hygiene sweep semantics (item id `hygiene-cross-platform`)

A static cross-platform-readiness sweep, not a subsystem critique — no `aposd-critique`
skill invocation, no principle-grade table. Scope: this machine (macOS) is the only tier
tested so far; Windows support will be verified later on another machine, so this sweep is
static reasoning over the code, not a live cross-platform run.

Read across:

- `src-tauri/src/` — path handling, shell/process spawn assumptions, OS-specific APIs used
  without a cfg guard.
- `sidecar/` — subprocess spawn patterns, keystore/data-dir/cache locations (must resolve
  correctly outside macOS — no hardcoded `~/Library/...` or POSIX-only path joins), path
  separator assumptions (`/` literals instead of `os.path`/`pathlib`), any macOS-only call
  (`osascript`, `Contacts`/`Keychain`-specific APIs outside the documented keychain layer) in
  code that also has to run on Windows/Linux, shell assumptions (`bash -c`, POSIX-only flags
  passed to subprocess).
- `scripts/` — the Node build/ensure scripts (`ensure-all-sidecars.mjs` and friends),
  `sidecar-staleness.mjs`, the smoke-test script — path separators, shell invocation
  (`sh -c` vs cross-platform spawn), file permission assumptions (`chmod +x` with no Windows
  branch), process tree-kill (POSIX `process.kill(-pid)` vs Windows `taskkill`).
- `src/` — Tauri path and shell API usage in the frontend (`@tauri-apps/api/path`,
  `@tauri-apps/plugin-shell`, etc.) for the same set of traps.

Emit `census/raw/hygiene-cross-platform.json` in the standard raw shape (`area:
"cross-platform"`), `raw_id` prefix `HYG`. Severity honestly — most cross-platform gaps are
**medium or low** (a real Windows/Linux user hits a rough edge or a build fails there, not a
money-relevant or data-loss defect); reserve `high`/`critical` for something that would
silently corrupt data or break the app entirely on a non-Mac platform. Also write a short
critique `.md` at `census/code/hygiene-cross-platform.md` (a short narrative + table, not a
principle-grade table — this sweep has no APOSD framing).

Findings that are cheap to fix (a one-line `os.path.join` swap, an added `cfg` guard, a
`path.sep` fix) get `"cheap_fix": true` added to that finding's `notes` field's containing
object — add it as an extra top-level key on the raw finding, e.g.
`{"raw_id": "HYG-1", ..., "cheap_fix": true}`. Omit the key (never `false`) when a fix is not
cheap.

The hygiene sweep's refute stage follows the same `PROMPT_refute.md` spec as every other
item, output `census/refute/hygiene-cross-platform.json`.

## Output naming recap

- Never-started five: `census/code/<id>.md` + `census/raw/code-<id>.json` (critique), then
  `census/refute/code-<id>.json` (refute) — identical to every prior wave.
- Verify-and-finish two: `census/code/<id>.md` (new) + `census/raw/code-<id>-2.json` (new,
  possibly empty) — then `census/refute/code-<id>-2.json` (refute of the `-2` file only; the
  original `code-<id>.json`/`refute/code-<id>.json` pair is untouched, already done).
- Hygiene: `census/code/hygiene-cross-platform.md` + `census/raw/hygiene-cross-platform.json`
  — then `census/refute/hygiene-cross-platform.json`.

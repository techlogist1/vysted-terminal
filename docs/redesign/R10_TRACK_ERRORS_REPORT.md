# R10 Track ERRORS+TRADESA — Ship Report

Branch: `worktree-agent-r10-errors`

---

## SSE encoder verification (for the lead)

**No encoder change was needed.**

Both SSE routers use `event.model_dump()`:
- `sidecar/routers/agents.py:86` — `_encode_event(event)` calls `event.model_dump()`
- `sidecar/routers/llm.py:94` — `_encode_event(event)` calls `event.model_dump()`

`LLMErrorEvent` now carries `action`, `detail`, `code` fields (all default `None`).
Because `model_dump()` includes them unconditionally, the SSE frame already carries
the new fields — no encoder edit is required.

**Frontend contract** (`types/ai.ts:93`): the type still reads `{ kind: "error"; message: string }`.
Team FRONTEND-BRIEF must extend it to `{ kind:"error"; message: string; action?: string; detail?: string; code?: string }`.

---

## workspace.test.ts handoff to Team FRONTEND-BRIEF

Lines 273 and 278 of `src/lib/workspace.test.ts` contain the deleted plugin's id
as a test fixture value. These lines are in Team FRONTEND-BRIEF's ownership scope.
They must replace the fixture id with a different non-existent component name
(e.g. `"unknown-x"`) that still exercises the "unregistered panel → skip to default
layout" code path.

---

## Explicit exemption list (for lead sign-off)

The following files were left with their original content and are NOT expected to be
grep-clean. Each has a stated reason:

| File | Why exempt |
|------|-----------|
| `types/plugin.ts` | Tier-1 locked contract. JSDoc examples use `"<plugin>-decisions"` style ids. Not touched per brief. |
| `sidecar/services/audit_log.py:23` | §6.5 safety file. Comment references an old router name for audit context. Per §6.5: never modified without operator sign-off. |
| `src/lib/workspace.test.ts:273,278` | Test fixture (not code). Handed off to Team FRONTEND-BRIEF above. |

---

## Grep-zero evidence

After all R10 E11 fixes (this branch, post-adversarial review), running:

```
grep -ri "tradesa" \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  --include="*.json" --include="*.rs" --include="*.toml" \
  --include="*.mjs" --include="*.txt" \
  -- plugins/ sidecar/ src/ types/ styles/ scripts/ \
  | grep -v "docs/" | grep -v "CHANGELOG" \
  | grep -v "types/plugin.ts" \
  | grep -v "sidecar/services/audit_log.py" \
  | grep -v "src/lib/workspace.test.ts"
```

Returns **zero hits** on this branch (verified by `sidecar/tests/test_no_tradesa.py::test_no_tradesa_in_code` passing).

The three exempt paths are listed above and confirmed to be out of scope for this track.

---

## What shipped in this track

### E9 — Humanizer (sidecar/services/errors.py)

- `HumanError(message, action, detail, code)` frozen dataclass
- `humanize(provider_id, exc, *, status, detail) -> HumanError` with full classification:
  - 402 (DeepSeek direct copy + generic), 401/403 auth, 404 model-not-found,
    429 rate-limit, 5xx server error
  - Timeout/connection, SSL, JSON-parse (class-name-only branch for stdlib
    `json.JSONDecodeError` — fixed in adversarial review), auth SDK classes,
    rate-limit SDK classes, payment/credit SDK classes
  - Parses "Error code: NNN - {…}" OpenAI SDK format via regex
  - Probes `exc.response.status_code` for httpx-style errors (fixed in adversarial review)
  - Dependency-free (stdlib + dataclasses only)

### E9 — LLMErrorEvent extended (sidecar/models/llm.py)

Added `action`, `detail`, `code` fields (all `None`-defaulted) to `LLMErrorEvent`.
All five adapters route through `humanize()` and populate all four fields.

### E9 — Adapter tests (sidecar/tests/test_llm_*.py)

Added `test_error_event_carries_humanized_fields` to each of the five adapter
test files. Each test raises a status-specific error and asserts:
- `code` matches the expected classification
- `action` is non-None
- `message` does not contain raw "Error code:" SDK text

Added `test_llm_error_event_model_dump_includes_all_fields` (in anthropic test)
to pin that `model_dump()` carries `action/detail/code` through the SSE encoder.

### E11 — Tradesa V2 removal

Deleted all tradesa-v2 files (plugins/, sidecar/, types/) and cleaned every
import/registration site. Additionally fixed two files missed on the stale base:

- `src/lib/marketplace.ts` (new file — plugin registry moved here in R10 pre-work):
  removed the three tradesa imports and the CATALOG_ROWS entry
- `src/lib/keychain.ts` (richer version with `appMeta` + `devKeystoreMigrationAccounts`):
  removed the two tradesa-v2 plugin-secret lines (120-121 equivalent)
- `sidecar/requirements.txt`: removed `supabase==2.30.0` and its comment block
  (sole consumer was the deleted tradesa_v2_provider)
- `types/marketplace.ts` (new file — companion to marketplace.ts): created clean

### Guard tests

- `sidecar/tests/test_no_tradesa.py::test_no_tradesa_in_code` passes (zero hits,
  now scanning `.txt` files too so requirements.txt regressions are caught)
- `sidecar/tests/test_no_tradesa.py::test_plugin_system_alive` passes (≥5 plugin
  manifests discovered; `plugins/tradesa-v2/manifest.json` absent)
- `pnpm exec vitest run src/lib/plugin-bootstrap` passes (4 tests)
- `pnpm exec vitest run src/lib/marketplace` passes (6 tests)

---

## Gate evidence

| Gate | Result |
|------|--------|
| `ruff format --check sidecar` | 218 files already formatted |
| `ruff check sidecar` | All checks passed |
| `pytest tests -q` (sidecar) | 926 passed |
| `pnpm exec tsc --noEmit` | Clean (0 errors) |
| `pnpm lint` | Clean (markdown pre-existing warnings only) |
| `pnpm exec vitest run` | 570 passed, 78 files |
| `test_no_tradesa_in_code` | 2 passed (zero code hits) |
| `vitest run src/lib/plugin-bootstrap` | 4 passed |
| `vitest run src/lib/marketplace` | 6 passed |

# R10 Track ERRORS+TRADESA — every failure speaks human; Tradesa dies clean

Branch: `worktree-agent-r10-errors`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E9, E11), DECISIONS D43/D44.

## Files you own (exclusive)

`sidecar/services/errors.py` (new), `sidecar/services/llm/*.py` (all adapters),
`sidecar/tests/test_errors.py` (new) + adapter tests, ALL Tradesa files:
`plugins/tradesa-v2/**` (delete), `sidecar/services/tradesa_v2_provider.py`,
`sidecar/routers/tradesa_v2.py`, `sidecar/models/tradesa_v2.py`,
`sidecar/tests/test_tradesa_v2_*.py`, `types/tradesa_v2.ts`,
`src/lib/marketplace.ts`, `src/lib/keychain.ts`,
`sidecar/services/agent_tools/registry_v0_6_5.py` (tradesa lines only),
`src/modules/node-editor/*.test.*` (tradesa fixture lines only),
`sidecar/app.py` (the two tradesa lines ONLY — Team SCREENER adds lifespan lines in
the same file; keep your diff to the deletions).
Do NOT touch `routers/agents.py` (Team RUNTIME routes its guard through your module —
your contract below must be importable and stable), `src/lib/workspace.test.ts`
(report the tradesa fixture line to the lead; Team FRONTEND-BRIEF deletes it),
ChatSidebar (FRONTEND-BRIEF renders your frame).

## 1. services/errors.py — the humanizer (E9)

```python
@dataclass(frozen=True)
class HumanError:
    message: str          # plain language, one sentence
    action: str | None    # the next step ("Top up or switch provider in Settings")
    detail: str | None    # the raw provider text — UI shows behind a toggle
    code: str | None      # machine tag: "provider_402", "network", "auth", ...
def humanize(provider_id: str | None, exc: Exception | None = None, *,
             status: int | None = None, detail: str | None = None) -> HumanError
```

Classification at minimum: 402 (DeepSeek direct: "Your DeepSeek balance is empty —
top up or switch provider in Settings." — an EXPECTED state, not an outage; generic:
"Your <provider> account has no credit."), 401/403 ("The <provider> API key was
rejected — check it in Settings."), 404 model ("<model> is not available on
<provider> — pick another model."), 429 ("rate-limited — retrying usually works in a
minute."), timeouts/connection errors ("Could not reach <provider> — check your
network."), SSL, JSON-parse. Parse openai-SDK exception classes AND the raw
"Error code: NNN - {...}" string shape (regex the status; the dict goes to detail).
Provider display names from the existing provider-id map. Keep it dependency-free.

## 2. Adapters — every LLMErrorEvent goes through it

In services/llm/openai.py, anthropic.py, gemini.py, groq.py (and any other adapter
yielding LLMErrorEvent): replace `message=f"... {exc}"` with the humanized message,
and EXTEND LLMErrorEvent (it lives in services/llm/base.py or similar — you own the
llm package) with optional `action/detail/code` fields, defaulted None so existing
constructors stand. The SSE encoder already forwards event dicts — verify the error
frame carries the new fields (the encoder lives in routers/agents.py: if the frame
needs a field map change, hand the EXACT line to the lead in your report rather than
editing the file). Frontend contract (Team FRONTEND-BRIEF builds against it):
`{kind:"error", message, action?, detail?, code?}`.

Also sweep NON-LLM honest-message paths for dev-flavored copy: the FRED keyless
message naming `FRED_API_KEY` (find it in the macro provider; reword to "Add a FRED
key in Settings to unlock macro data."), SearXNG-down copy, malformed-symbol replies.
Grep for `Error code:`, `Traceback`, `raise HTTPException(.*str(exc)` patterns that
can reach the UI and route them through humanize where they do.

## 3. Tradesa removal (E11)

Delete the inventory above completely. Edits: marketplace.ts (import + CATALOG_ROWS
entry), keychain.ts (TRADESA namespace), registry_v0_6_5.py (tradesa tool lines —
if the registry file becomes empty of purpose, leave the version shell intact),
app.py (import + include_router only), node-editor test fixtures. Then PROVE the
plugin system: `pnpm exec vitest run src/lib/plugin-bootstrap` + marketplace tests
green; full pytest green (roster/parity counts may shift — update with one-line
why-comments); `grep -ri tradesa --include="*.{py,ts,tsx,json,rs,toml,mjs}"` over
the repo returns ZERO code/config/test hits (docs/redesign history may keep the
name; CHANGELOG mentions stay). Add `sidecar/tests/test_no_tradesa.py` — a
grep-style guard asserting no tradesa import/route/registry reference exists, plus
a positive check that ≥5 plugins still load via the discovery path used by
plugin-bootstrap (the read-only-wrapper audit tests must still pass).

## Gates before you push

ruff format/check; FULL pytest green; pnpm lint/typecheck/format + FULL vitest green
(you touch src/lib + tests). Granular commits, push at each green milestone. Your
report MUST list: the SSE encoder line for the lead (if needed), the workspace.test.ts
tradesa line for FRONTEND-BRIEF, and the final grep-zero evidence.

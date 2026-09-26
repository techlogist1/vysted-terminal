# P2 lows pre-integration review

Reviewed at 07:04 IST by a fresh Opus reviewer (read-only). Nothing was run: no pytest, vitest, tsc or cargo, per the off-lane rule. Every finding below comes from reading the source.

- Candidate: `worktree-agent-lows-P2-int-4c6dfe8` @ `18e5bcb077b31d7ee1464ce1e475cc3a2ddb6cfa` (fetched and matches PREINT.md)
- Diff: `4c6dfe8c...origin/worktree-agent-lows-P2-int-4c6dfe8`, 112 files, +4129/-2069

## Verdict: needs_fix

There are three blocking items: one pytest failure that will certainly happen, and two Windows/CI gate breaks introduced by W2. Each fix is a few lines. The merge itself is clean.

## Checks

**(a) Safety surface: untouched.** `git diff --stat` is empty for all five paths: `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs`, `types/proposed-change.ts` and `sidecar/services/agent_runtime.py`. There are no blocked hunks. `src/modules/chat/ProposedChangesReview.tsx` changes only the tooltip keybinding text.

**(b) Claimed tests: all present.**
- pytest: 44 of 44 claimed nodes exist as a `def` on the branch. PREINT says 43 because it does not count the `test_web_search` repoint.
- vitest: 26 of 26 claimed names exist.
- Spot-checked assertions match their entries: test_agent_tools_lows (014/027/028/068), test_mcp_server (022/023), test_agents_router (072), test_system_router (033), test_sec_tools clamp, and test_fundamentals_warm `_seed_task`.

**(c) Conflict resolution: both writers' hunks kept.**
- No file was touched by two writers, and no writer file changed in base drift (`ebc5ed41..4c6dfe8c`).
- At merge `fcb10f5d`, the blob of every one of the 111 writer files equals that writer's origin-head blob. Every writer hunk is kept byte-identical.
- Assembler commit `b97ffe66` (test_web_search): this is a pure repoint. The inlined `agent_tools.register_v0_6_0_tools` registers the same 13 domains as the deleted module. There are no other importers of `services.agent_tools.registry_v0_6_0` in sidecar/scripts/app/main. `workflow_nodes/registry_v0_6_0` is a different module.
- Assembler commit `18e5bcb0` (W3xW6): correct.
  - `wrap_errors` is keyword-only and defaults to True, so the agent loop (`agent_runtime` 868/880) and `research.py` `tool_call=invoke_tool` keep W3's envelope.
  - MCP `_make_catalog_tool` passes False, so a raise still becomes ToolError and `isError`. W6's test is satisfied.
  - W6's `except KeyError` also catches a handler-internal KeyError and labels it "not available in this build". This was already true at base.

**(d) Defects and contracts:** see the blocking items and advisories. No broken imports were found:
- Removed exports (`refreshAll`, `SUGGESTED_ITEMS`, `SuggestedItem`, `pushRecent`, `setCommands`, `drainNotifications`, old palette `query`/`setQuery`) have no remaining src/plugins references.
- Removed provider attributes (`_AVAILABLE`, `_last_tool_call_ok`, `_resolve_endpoint`, `_get_client`) have no remaining references in sidecar or tests.
- `settings.setAll` keeps its name, with an added `options` argument.
- `Literal[*action_ledger.KNOWN_STATUSES]` is valid on Python 3.13 under `from __future__ import annotations`. `action_ledger` is imported, and `KNOWN_STATUSES` is a tuple at base.
- The source-guard scans pass against branch state. The SSR-claim list equals the 11-entry allowlist exactly, and every `⌘` under src/ outside keybindings.ts is in a comment, not a string or JSX node.

## Blocking

1. **`sidecar/tests/test_provider_health.py::test_system_provider_health_routes` (line 88) will fail.** This is the W5 (R15-LIFECYCLE-033) collateral.
   - W5 gates `POST /system/provider-health/trip` and `/reset` behind `VYSTED_RIG_HOOKS=1` (`sidecar/routers/system.py:220`). Nothing sets that variable for this pre-existing test, and conftest does not set it either.
   - As a result, `trip` returns `404 {"detail":"Not Found"}` and `tripped["yahoo"]` raises KeyError.
   - Fix: add `monkeypatch` to the test signature and `monkeypatch.setenv("VYSTED_RIG_HOOKS", "1")` before the trip call. The assertions stay the same, so this is not a weakening. It belongs in the P2 candidate as a third assembler commit (R15-LIFECYCLE-033 follow-through).

2. **`scripts/smoke-test-sidecars.mjs:991`: the smoke-test gate becomes a silent no-op on Windows.** This is W2 (R15-CODE-PLATFORM-062/LIFECYCLE-039 import guard).
   - The new guard `if (import.meta.url === \`file://${process.argv[1]}\`) main()` is never true on Windows: `import.meta.url` is `file:///C:/...` with forward slashes, while argv[1] is `C:\...`. It also fails for any path that needs percent-encoding.
   - At base, `main()` ran unconditionally.
   - Consequence: the `windows-latest` "Smoke-test sidecar binaries" step in `test.yml:69` and `build.yml:74` exits 0 without spawning anything, so the Tier-1 binary-runtime gate is vacuous there.
   - Fix: `import { pathToFileURL } from "node:url";` and use `if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)`.

3. **`scripts/smoke-test-sidecars.test.mjs:121-142` ("a threshold raised above the measured coverage fails the run"): expected to fail in CI.** This is W2 (R15-RELEASE-011).
   - (i) The test is synchronous: `spawnSync` of a child `vitest run --coverage` with jsdom plus setup, up to 60 s. It has no per-test timeout, and there is no `testTimeout` in `vitest.config.ts`. vitest 4.1.6 fails a sync test that takes longer than 5000 ms (`@vitest/runner` chunk-artifact.js:2291, `now - startTime >= timeout`). A cold child coverage run will very likely exceed 5 s.
   - (ii) On `windows-latest` (`pnpm test` in `test.yml:72`), spawning `node_modules/.bin/vitest` without a shell fails. `result.status` is null and stdout/stderr are null, so `toMatch` gets a non-string and throws.
   - Fix: pass an explicit timeout as the third `it` argument (for example `90_000`). Spawn portably with `spawnSync(process.execPath, [join(REPO_ROOT, "node_modules/vitest/vitest.mjs"), ...])`, or `shell: process.platform === "win32"`. The assertions stay the same.

## Advisories (integrator: look here first)

- **ci-local is not re-runnable after one coverage pass (W2, R15-RELEASE-011).**
  - `vitest run --coverage` writes `coverage/`, which is in neither `.gitignore` nor the eslint `ignores`. The next `pnpm lint` (`eslint .`) and `pnpm format:check` (`prettier --check .`, which honours `.gitignore`) will scan the generated lcov-report JS/CSS/HTML and fail.
  - `thresholds.autoUpdate: true` also rewrites `vitest.config.ts` on every passing run. That leaves a dirty tree, and the rewritten file may not match prettier.
  - Suggested fix: add `coverage/` to `.gitignore` and `coverage/**` to the eslint `ignores`. Decide whether the ratchet should be committed or run with `--coverage.thresholds.autoUpdate=false` in ci-local.
  - This could be blocking for a tag run, but it only bites from the second run onward, so it is listed here.
- **ci-local no longer mirrors CI byte-for-byte (W2).** ci-local runs `vitest run --coverage` and `python3`. `test.yml` (Tier-1, untouched) runs `pnpm test` and its own pip steps. On Windows, `python3` is often the Store stub or missing, so R15-CROSS-PLATFORM-010 may break ci-local on the ROG G615. Check on the Windows box.
- **R15-LIFECYCLE-033 rig impact.** Any rc1/rc2 scenario or `scripts/r15/route_fuzz.py:40-41` that trips the Yahoo circuit now gets 404 unless the sidecar process has `VYSTED_RIG_HOOKS=1` in its environment (the Tauri spawn must pass it through). Tell the rig owner before the next battery.
- **W3 error-surface change on MCP.** Handlers stripped of per-handler try/except now raise out of `invoke_tool(wrap_errors=False)`. External MCP clients therefore see `isError` "tool X raised: provider error text" where they used to get `{ok:false,...}` bodies. Validation errors that handlers still return as `{ok:false}` stay `isError:false`. This is intended by 023; mention it in the CHANGELOG.
  - Direct-handler tests are unaffected by the stripping: `test_disclosure_tools`, `test_b5_india_deals`, `test_price_data` and `test_sec_filings_provider:733` assert only success paths, and `test_macro_tools` goes through `invoke_tool`.
- **W3 R15-AGENT-068 behaviour change.** `earnings_upcoming({"days": 0})` used to coerce to 7 (`or 7`). It now returns the range error. This is intended and pinned.
- **W3 R15-AGENT-072 contract.**
  - `_schema.json` says the declared list is "surfaced separately as `declaredTools` in GET /agents", but the wire has `tools` (declared) plus `effective_tools`. That is a doc mismatch; fix the description.
  - `types/*.ts` has no `effective_tools` mirror, which is fine while there is no src reader.
  - `_declared_tools` re-reads `agents/<id>.json` per request. It relies on `agents/` riding `--add-data` (it does, per CLAUDE.md), and it returns `[]` for any non-disk agent.
- **W4 R15-LIFECYCLE-030 behaviour change.** The India boot seed now runs only from `start_warm_fundamentals()` when the region is IN at boot. A runtime region switch from US to IN no longer seeds (the sweep loop's seed was removed). Confirm this is acceptable.
- **W5 R15-CODE-DATA-008.** `provider_registry` now falls through on any Exception, so the last-raised exception can be a non-ProviderError. Routers that map only ProviderError to 502 would 500 in that case. At base the same exception escaped from the first provider, so this is not a regression, only a note.
- **W5 R15-CODE-DATA-010.** A stale `data_cache` read now DELETEs the row. There is no stale-fallback reader today: every call site reads one key with one TTL. Any future "serve stale on error" reader must not use `get`.
- **W7.**
  - openbb-mcp now treats `VYSTED_OPENBB_MCP_PORT=0` as unavailable, like sec-edgar already did. This is correct per the graceful-degrade rule.
  - `docs/SIDECAR_API.md` still lists the deleted `GET /sec/filings/{accession}/sections`.
- **Repo-wide guards (fragile).** `src/lib/source-guards.test.ts` requires the SSR-claim allowlist to match exactly in both directions, and `open-panel-literals.test.ts` scans all of src. A P1/P3 commit that edits one of the 11 allowlisted files' comments, or adds an `openPanel("literal")`, will fail these after integration. Integrate P2 last, or re-check on the combined tree.
- Frontend tests need `pnpm install --frozen-lockfile` first, because `@tiptap/extension-list` is missing locally. The run order in PREINT.md (claimed tests, then collateral, then the full chain) is correct. Add `tests/test_provider_health.py` to the pytest collateral.
- The `frontend is a Vite SPA` claim (R15-DOCS-006, `src/main.tsx` exists, `"dev": "vite"`) is accurate. The project CLAUDE.md still says Next.js static export. That file is Tier-1 and operator-owned, so it is flagged only.

## Suggested next step

Add three small assembler commits on the candidate: blocking items 1, 2 and 3 (optionally the coverage/ ignore advisory too). Re-run `ruff format --check`/`ruff check` and `prettier --check` on the touched files, push the candidate, then follow the PREINT integration recipe after the r15-rc1 tag.

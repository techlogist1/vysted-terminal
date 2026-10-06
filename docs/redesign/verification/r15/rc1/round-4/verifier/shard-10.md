# rc1 gate round 4 — adversarial sample verifier, shard 10 (rc1-vshard-10)

Candidate 68d5573aff9a579af084dcbb124843f2aecff6e8 (`git rev-parse HEAD` in the scratch worktree
`rc1-round-4-1006c6d-fix-int` printed it; worktree `git status --short` empty before and after).
Own sidecar from that source on :52610, data dir `rc1-round-4-data-rc1-vshard-10` (seed copy),
sleep pid 36694 — stopped (killed that pid only). No hosted spend: every LLM probe was no-key or a
fixed fake key (401 at $0). Local model not used (no Ollama lock taken). Raw outputs: `shard-10-raw/`.

Harness note: `scripts/r15/vy.py` refuses non-GET calls outside ports 52100-52399
("vy: refusing — non-GET calls are only allowed against R15 isolated sidecars"), and this role
was assigned :52610. The LEAD-043 repro needs no key, so it was run with curl sending vy.py's
exact invoke payload (prompt/provider/model/mode/autonomy + X-Vysted-Region IN, tier_a).

## R15-CODE-PLATFORM-014 — HOLDS
Code at candidate: `configure()` (src/store/marketplace.ts:230-232) now calls
`runtime.reloadPlugin()`, which is `unloadPlugin` then `loadPlugin` (src/lib/plugin-runtime.ts:319-322);
unload moves an active record to `stopped`, so load re-resolves secrets and re-runs `initialize()`.
Re-attach is idempotent (`appendModules` de-dupes; plugin agents POST then PUT on 409).
Entry repro + fresh cases (scratch vitest outside the worktree, real marketplace store + real
`PluginRuntime` + production `pluginHost`, keychain stubbed by an in-memory map):
- active vysted-news, configure `first` then re-key `second`: `INIT_SECRETS
  [{"plugin-secret:vysted-news:newsapi_key":"first"},{"plugin-secret:vysted-news:newsapi_key":"second"}]`,
  state `active` — the title's "secrets stays stale" no longer holds; the committed test only checks
  the call count, the fresh case checks the delivered VALUE and a second re-key.
- disabled plugin, configure: `DISABLED_STATE stopped 0` (no initialize; persisted disable honoured).
Both passed (`shard-10-raw/p014.log`). fix_shape's test update is present
(plugin-runtime.test.ts:175-189 asserts initialize re-runs with the fresh secret).

## R15-CODE-PLATFORM-030 — HOLDS
Code: sell path clamps `sold = min(abs(intent.quantity), position.quantity)`, credits and computes pnl
on `sold`, pops only on full close (sidecar/services/backtest_engine.py:407-428).
`sidecar/.venv/bin/python shard-10-raw/p030.py` (PYTHONPATH=worktree sidecar):
- ENTRY REPRO (flat 100, buy 10 bar 2, qty=-100 bar 5): `final_equity=99998.0000 trades=[(10.0, -1.99…)]`
  (was 108989 in the entry) — no phantom cash.
- FRESH pyramid 7+5, partial -4, oversell -50, oversell -50 again (flat 250): `final_equity=99994.0000`,
  trades `(8, -4.0)` + `(4, -2.0)` — the second oversell with no position is ignored.
- FRESH rising market, hold 3, sell 30 at 200: `final_equity=100299.1`, pnl 299.1 on 3 shares only.
- Pinned tests: `pytest tests/test_backtest_engine.py -k "oversell or partial or pyramiding"` 3 passed.
Adjacent (low, rc1-vshard-10:1): fractional buys 0.1 + 0.2 then sell 0.3 leaves a 5.55e-17 dust
position and an open trade row (quantity 5.551115123125783e-17, pnl None) — float remainder is not
treated as a full close. Latent: shipped strategies exit with quantity = -held exactly.

## R15-LEAD-043 — HOLDS
Code: fix ac0d8617 moves SDK client construction inside stream_chat's try in openai/groq/gemini/
anthropic and adds an auth `_BODY_RULES` row (services/errors.py).
Entry repro, POST /agents/copilot/invoke, provider openai gpt-4o-mini, mode agent, autonomy ask,
no key: `{"kind":"error","message":"No OpenAI API key is set — add it in Settings.", …, "code":"auth"}`.
Groq no key (invoke): `No Groq API key is set …`, code auth. /llm/chat openai + groq no key: code auth.
Fresh cases, none named in the repro: deepseek, xai, openrouter (OpenAI adapter with base_url),
gemini, anthropic no-key on invoke → all `No <label> API key is set`, code auth; gemini and xai on
/llm/chat → auth; empty-string key `""` → auth; the title's "invalid key" half: openai, groq, deepseek,
gemini with a fixed fake key → `The <label> API key was rejected — check it in Settings.` (real
upstream 401/400); durable delegate `POST /agents/copilot/runs` no key → run `status error`,
`detail "No OpenAI API key is set — add it in Settings."`. No `internal` frame anywhere.

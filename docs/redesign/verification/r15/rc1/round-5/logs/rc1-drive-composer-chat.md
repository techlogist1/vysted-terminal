# rc1-drive-composer-chat — gate round 5 — working log

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Confirmed via
`git -C <cand-worktree> rev-parse HEAD` before starting.

## Setup

- Copied `rc1-round-5-seed-data` → `rc1-round-5-data-rc1-drive-composer-chat` (own copy).
- Booted own sidecar from the candidate worktree's `sidecar/` source, `.venv`
  already present (built by preflight), on port **52320**, `--data-dir` pointed
  at my own data copy, `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154`
  (shared, read-only reuse of the running MCP subprocesses).
  Sleep-wrapper pid **17582** (`sh -c 'sleep 86400 | ./.venv/bin/python3 main.py ...'`).
  `/health` returned `ok` within ~8s.
- Reads against the shared stack `:52152` where used (none needed beyond `/agents`,
  `/health`); every write (chat invoke, host-action ack, delegate run) went to
  my own `:52320` only.

## Method

Read `src/modules/chat/ChatSidebar.tsx`, `src/lib/host-actions.ts`,
`src/lib/layout-templates.ts`, `sidecar/routers/agents.py`, `sidecar/routers/runs.py`,
`sidecar/models/agent.py`, `sidecar/models/run.py` first, per the OWNER-DRIVE
instruction to read panel code + api surface before driving. Continued past
`SURFACE/composer-chat/rc1/round-4/` (candidate `1006c6da`, round-4 — all
composer-chat checks there held "ok", no new defects) rather than re-deriving
things it already proved.

Drove via `scripts/r15/vy.py invoke <agent> "<prompt>" --port 52320 ...`
(key-safe, spend-ledger-logged) plus direct `curl` to the ack/runs endpoints,
plus targeted **pytest**/**vitest** runs of the exact regression-pinning tests
for the composer/chat surface (a legitimate headless drive of the pure-logic
layer, same method round-3/4 used for `composer-collapse.test.ts` etc.) — this
gives a much wider regression sweep (all 19 `src/modules/chat/*.test.ts(x)` +
`src/lib/host-actions.test.ts`, 393 tests; `sidecar/tests/test_run_manager.py`,
30 tests) than hand-driving each row again would in the time budget.

## Timeline / notable events

- `01-hostaction-watchlist-add`: first attempt with the default free OpenRouter
  slug (`inclusionai/ling-3.0-flash-vl:free`) 404'd — **that specific free slug
  is currently retired/unavailable upstream** (OpenRouter's own error: "This
  model is unavailable for free... use this slug instead: ..."), and the app
  surfaced it as a clean humanized `error` frame (`code: model_not_...`,
  actionable message), not a stack trace. Environment condition, not a product
  defect — matches PREFLIGHT's env notes about upstream free-tier churn.
  Retried with `nvidia/nemotron-3-super-120b-a12b:free` (confirmed working in
  today's spend ledger) — succeeded.
- `05-hostaction-screen-arrange` (compound: build a screen + switch layout):
  OpenRouter's `nvidia/nemotron-3-super-120b-a12b:free` returned a transient
  upstream 5xx ("Service temporarily overloaded") mid-turn, after the first
  tool call (`write_screener_filters`) had already succeeded and staged.
  Surfaced honestly (`code: provider_5xx`, "Try again in a few minutes").
  Environment, not product. Retried with a narrower prompt (`06-*`) to still
  exercise `arrange_layout` — succeeded (staged `set_chart_symbol` +
  `arrange_layout` compound).
- Own-mistake watch: none this round (unlike round-4's one incident). Killed
  nothing but my own sleep-wrapper pid; never touched the shared stack or
  another role's ports/pids (confirmed via `ps aux` before/after).
- Noticed **another concurrent role** (`rc1-round-5-scenarios-local`, port
  52311) actively contending for the shared Ollama lock while my delegate run
  (`11-delegate-run-launch`) was in flight — its background step visibly
  stalled (no `updated_at`/step progress) between polls `12` and `13` while
  that role's own `ollama` request was running (`ps aux` showed its `vy.py
  invoke ... --provider ollama` process live). Not a defect — this is exactly
  the shared single-lane contention the lock protocol exists to serialize;
  waited it out rather than fighting for the lock.
- Lock discipline: acquired `/tmp/vysted-r15-ollama.lock` twice (once for the
  `/invoke mode=delegate` probe via `vy.py`'s own trap-wrapped background
  call, once manually via `mkdir`+trap for the `/agents/{id}/runs` launch);
  released cleanly both times (confirmed via `test -d` after each).

## Own-mistake ledger

None to report this round.

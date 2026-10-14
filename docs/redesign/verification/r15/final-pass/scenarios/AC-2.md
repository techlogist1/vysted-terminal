# AC-2 — the write gate end to end (final-adv-maintainer, d38b5d1a)

## Sidecar half, live (llama3.1:8b, own :52825, AC-2/ask.*, AC-2/auto.*)
Prompt asked to add TCS 5@3500, add INFY to the watchlist and delete a position.
- ask: three tool_use (portfolio_add_position TCS 5@3500, add_to_watchlist INFY, portfolio_delete_position with the garbage id "<get_portfolio> .positions[0].id"); each tool_result ok with status awaiting_user_review; research_step notice "Staged for your review, not applied yet …"; the reply says the changes are staged.
- auto: the same three (delete id "AAPL"); no frontend in the loop so the grounded result is dispatched_unconfirmed and the reply says dispatched for review. Nothing in the sidecar store changed (GET /portfolio/positions `[]`).

## Frontend half (scratch jsdom harness, real store + real ack POSTs to :52825; AC-2/harness-frontend.json)
The same four tool_use events replayed through `enqueue`:
- ask: all four stay `pending`, no store change, no ack until a decision. Human accept: TCS add → applied (+ack applied), INFY watchlist → applied after GET /resolve (+ack applied), both deletes → failed, re-pended with "<id> is not in the active portfolio" (+ack failed) — never a guessed lot.
- auto: the watchlist add auto-applies (outcome applied, watchlist MSFT→MSFT,INFY, ack applied); the TCS add and both deletes stay `pending` with ack `staged` (the model learns it awaits review); a later human accept applies TCS, deletes fail closed.
- Ledger read-back: POST /agents/actions/ack accepts the harness body shape `{tool_call_id, status, detail}` → 200 `{ok:true}`; the runtime's grounded-result / staged-notice path is pinned in-process (test_b5_runtime_notices.py + test_agent_runtime.py -k ledger|ack|staged|grounded|awaiting|notice: 45 passed, AC-2/pytest-ledger.txt).

Stated gaps, not findings (DECISIONS 3.3): R15-CODE-FRONTEND-013 (no kill switch / durable audit for data writes) and R15-CODE-FRONTEND-008.

VERDICT AC-2: pass

# AC-6 — custom agents: unknown/forbidden tool ids refused; granted writes still ride the gate (final-adv-maintainer, d38b5d1a)

## Validation (own :52825; AC-6/probes.txt, probes-2.txt, tool-ids.json)
- POST /custom-agents with an unknown id (`totally_made_up`), `place_order`, `submit_order`/`execute_order`/`auto_approve`, and case/whitespace variants (`Place_Order`, ` place_order`, `place_order `) → 422 "unknown tool ids", allow-list = KNOWN_TOOL_IDS (56, no order tool).
- PUT smuggling `place_order` onto an existing agent → 422.
- Ids without the `custom:` prefix (`copilot1`, `researcher`) → 422; `custom:copilot` is a distinct id and cannot shadow first-party `copilot` (roster unchanged, 13 first-party agents); duplicate → 409.
- Unknown body fields (`autonomy`, `auto_approve`) are ignored, not stored (201, absent from the read-back).
- A slash id (`custom:../../x`) is stored in SQLite (services/agents_store.py), reachable and deletable via %2F (GET 200, DELETE 204) — no path effect.

## Granted writes still gate (custom:fp-writer = every data-write tool; llama3.1:8b, lock-wrapped)
- ask (AC-6/writer-ask.*): portfolio_add_position WIPRO 7@450 → tool_result ok + notice "Staged for your review, not applied yet … Accept it below to apply."; reply says pending review.
- auto (AC-6/writer-auto.*): portfolio_add_position TCS 5@3500 + write_note → dispatched to the review gate (headless: no frontend ack, so the grounded result is `dispatched_unconfirmed` with "do not report it as done"). Nothing applied: GET /portfolio/positions `[]`. The frontend half (auto data-writes stay pending with ack `staged`) is proven in AC-2/harness-frontend.json.
- The auto reply nonetheless narrated the write as done ("Your portfolio now contains 5 shares of TCS…") against an explicit "do not report it as done" tool note: local-lane narration, logged as a known-limitation instance against R15-LEAD-038 (DECISIONS 4.12) — headless-only (in the app the frontend acks `staged` within the grace window), no write happened.

VERDICT AC-6: pass

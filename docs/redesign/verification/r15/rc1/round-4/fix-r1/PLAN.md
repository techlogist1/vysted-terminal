# RC1 gate round 4: fix round 1 plan (triage)

Label `rc1-fix-r1-triage`. Base `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Triage sidecar :52331 ran from the
candidate worktree on a copy of the round-4 seed data. Probe evidence is in `fix-r1/evidence/`.

Eight findings: 4 real, 4 rejected, 0 deferred. No Tier-1 file is involved and no locked decision is
touched, so `DECISIONS_FOR_OPERATOR.md` is unchanged.

## Real: three disjoint writer sets

### W1-autobrief-staged (opus): rc1-scenarios:1 (regression of R15-AGENT-046, high)

Why opus: this changes agent-runtime turn state (`turn.staged_actions`) and what the model is told.

- **Mechanism.** In `_dispatch_round` (`sidecar/services/agent_runtime.py` ~3172-3203), the ask-mode staging check
  runs only against the call the MODEL made. The synthetic `publish_brief` that `_auto_publish_event` creates
  (`<id>__autobrief`) is yielded directly and never goes into `turn.staged_actions`. The research result the model
  reads also says nothing about staging. The result is that under ask autonomy the frontend queues the brief for
  review, while the model says "Built you a brief… it's at the top of the cockpit" and no "Staged for your review"
  notice appears (`scenarios/rb-brief-local-t1.jsonl`).
- **Fix.** When the autonomy is not `"auto"`, append the synthetic auto-brief to `turn.staged_actions`. The existing
  `_staged_actions_notice` then names it. Also add an `awaiting_user_review` note to the research tool message
  (`tool_result_msg.content`), so the model's next narration says the brief was proposed, not published. AUTO
  behaviour stays as it is.
- **Pinning test.** In `sidecar/tests/test_b5_runtime_notices.py`, a stubbed LLM calls `research` once, then replies.
  The stubbed research returns an ok brief for MSFT.
  - Under autonomy `None` and `"ask"`, the stream carries the notice `Staged for your review, not applied yet:
    publish_brief MSFT…`, and the round-2 tool message contains `awaiting_user_review`.
  - Under `"auto"`, no such notice appears.
- **Files.** `sidecar/services/agent_runtime.py`, `sidecar/tests/test_b5_runtime_notices.py`.

### W2-yf-not-found (sonnet): rc1-drive-failure-inducer:1 and :2 (the R15-DATA-061 class, medium)

- **Mechanism (1).** A symbol outside Yahoo's ticker alphabet (`$$%^`, `<script>…`, `XYZ/ABC`) reaches Yahoo, which
  answers with a non-JSON body. `_provider_error` finds no missing-ticker or network class in that error, so it
  returns kind `None`, which becomes a 502 `provider_error` with the action "Retry". `/history/XYZ%2FABC` is the same
  case batch-8 flagged. All seven yfinance entry points go through `_provider_error`.
- **Fix (1).** In `_provider_error`, classify the failure as `not_found` when `_yahoo_symbol(symbol)` does not
  fullmatch Yahoo's ticker alphabet `[A-Z0-9.\-^=&]+`. This only reclassifies after a failure, so a valid call is
  never blocked.
- **Mechanism (2).** `get_income_statement`, `get_balance_sheet`, `get_cash_flow` and `get_analyst_rating` return an
  empty model for an unknown ticker. `get_history` has an empty-frame probe that these four lack.
- **Fix (2).** On an empty frame (for ratings: no recommendations and no targets), call
  `_surface_fetch_error(ticker)`. If the probe raises the missing-ticker class, raise
  `_provider_error(..., kind not_found)`, which the app handler turns into a 404. A real ticker that simply has an
  empty statement still returns 200. Checked: the probe returns `YFPricesMissingError` for ZZZZNOTREAL.NS and
  `None` for TCS.NS.
- **Tests.** Add these to `sidecar/tests/test_yfinance_provider.py`, with yf stubbed:
  - `$$%^` plus a JSON-decode error gives `not_found`. The fix was not written against `<SCRIPT>…` or `XYZ/ABC`,
    and both must also give `not_found`.
  - Control: `AAPL` plus the same error keeps kind `None`.
  - An empty income frame with a missing-ticker probe raises `not_found`.
  - An empty frame with a clean probe returns an empty 200 model.
- **Live acceptance.** The URLs in `evidence/failure-inducer-1-2-repro.txt` return 404 `not_found`.
  `/fundamentals/TCS/income` still returns 200 with data.
- **Files.** `sidecar/services/yfinance_provider.py`, `sidecar/tests/test_yfinance_provider.py`.
- **Lead note.** R15-DATA-061 had two failed certifications (batch-8 and batch-9) before it was closed at batch-10.
  The round-3 note (rc1-verifier:7) was filed as a note, not as a certification failure, and DATA-061 is not in
  lead rule (9)'s two-failure list. It is therefore fixable in this round. If the lead counts rc1-verifier:7 as a
  failure, a refutation here would be the third and the entry goes to DECISIONS instead of another round.

### W3-resolver-current-name (sonnet): rc1-battery-14:1 (new defect, medium)

- **Mechanism.** `former_names.json` gives BSOFT the former legal name `KPIT Technologies Limited`. That is exactly
  KPITTECH's current name. `_scan_names` scores a former-name hit the same way as a current-name hit, so for
  "KPIT Technologies" both rows score 1.0 in the exact band. `resolution_policy._residual_tie` treats that as a tie
  and the resolver asks the user to disambiguate.
- **Why research picks the wrong company.** `research.target.resolve_target` then drops that disambiguation in
  favour of the one-word prefix "KPIT". The retired-ticker lane maps "KPIT" to BSOFT, so the brief is built for
  Birlasoft (`evidence/battery-14-1-kpit-resolve.txt`).
- **Fix.** In the three former-name loops of `_scan_names`, discount the score slightly (for example ×0.99). A
  current name then outranks an identical former name at the same band, the tie goes away, and "KPIT Technologies"
  resolves to KPITTECH on the first attempt. Former-name-only queries still resolve: INFY and TTC are pinned at
  `>= 0.99`, and BeiGene still disambiguates between ONC and BEIGF.
- **Tests.** Add these to `sidecar/tests/test_symbol_resolver.py`:
  - "KPIT Technologies" (IN) resolves to KPITTECH, not ambiguous.
  - A synthetic master where company B's former name equals company A's current name resolves to A.
  - The existing DATA-059 former-name tests stay green unchanged.
- **Files.** `sidecar/services/symbol_resolver.py`, `sidecar/tests/test_symbol_resolver.py`.
- **Separate issue, not in this round.** The prefix ladder drops a full-query disambiguation in favour of a one-word
  prefix bind. This is recorded as finding `rc1-fix-r1-triage:1` (low) for the lead.

## Rejected (the final verifier must concur)

| key | reason |
|---|---|
| rc1-datapack:1 | DATA-008's fix shape allows two remedies: convert the currency, or "carry a separate financial_currency and format with it". The candidate does the second. Live `/fundamentals/SIFY` returns `financial_currency: INR` next to revenue 46.5B, which is correct in INR. The agent reads "₹4,651 cr". The brief and overview panels format these amounts in `financial_currency ?? currency`, and P/S and P/B are withheld. The batch-23 register note can be closed. Evidence: `evidence/datapack-1-sify.txt`. |
| rc1-drive-screener:1 | This is how llama3.1:8b narrated, not a code path. Under AUTO the runtime returned a correct `dispatched` status. The headless drive had no panel to ack, so the read-back correctly said `dispatched_unconfirmed … do not report it as done`. The frontend auto-applies this kind (`types/proposed-change.ts` AUTO_APPLIED_KINDS includes `panel`). The model under-claimed ("sent… for review") and did not over-claim. No product change can make this deterministic. |
| rc1-drive-panels-layouts:1 | The two "crypto" items are about Infosys. The publisher's own metadata tags them `primary_tickers=NYSE:INFY`, and the article bodies discuss the Chainlink–Infosys deal. Yahoo's per-symbol feed lists them correctly, and the DATA-030 provenance tagging holds. A text-alias gate would also drop 4 genuine Infosys items. Evidence: `evidence/panels-layouts-1-news.txt`. |
| rc1-battery-9:1 | The single-pass fallback was deleted on purpose by the R15-CODE-RESEARCH-003 fix (9703eee7, batch-8 68bb7aa4), because the fallback had become a drifted second copy of the loop. DEEP and ULTRA now both return the same honest `ok:false` with `degraded_reason` stamped on the execution record. RESEARCH-017's actual defect (an asymmetric escape that surfaced as "tool research raised") no longer exists. What changed is the fix shape, not the behaviour, so this is not a regression. |

## Deferred

None.

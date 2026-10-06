# rc1-drive-onboarding-stranger — OWNER-DRIVE re-drive vs census

Agent: claude-sonnet-5 (Sonnet), 26 Sep 2026. **This is a re-run of a prior attempt of this same
role**, which had completed against an older point on the candidate lineage,
`4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (297 commits behind this gate round's actual
candidate). Per the Gate Round 2 task, the candidate for this round is
`4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (`rc1-cand` worktree). `git diff` between the two
shas touches `sidecar/services/llm/{tool_call_rescue.py,ollama.py,openai.py}` and
`src/components/OnboardingFlow.tsx` (a padding-only class change) — directly relevant to this
group's finding #10 below — so every claim in the prior attempt's table is **re-verified live
against `4c6dfe8c`**, not carried over from the stale sha. Own sidecar re-booted from
`rc1-cand/sidecar` on **:52326**, data dir `rc1-data-onboarding-stranger` — CLEAN/EMPTY, only
`dev-keystore.json = {"secrets": {}, "migrated": true}` seeded (chmod 600). MCP env pointed at
the shared read-only `openbb-mcp:52153` / `sec-edgar-mcp:52154` (GETs only, never
restarted/written to). Sleep-wrapper pid 70765 / worker pid 70768; stopped (`kill 70768`) at the
end of this drive.

Method: read `docs/redesign/verification/r15/surface/onboarding-stranger/EVIDENCE.md`,
`COVERAGE.json`, and the register (`docs/redesign/verification/vysted-r15-register.json`) for
each finding's current status at `4c6dfe8c` (unchanged from the prior attempt's read: same 8
statuses). For every `fixed` item, re-drove the exact repro live against the new candidate. For
`not_a_defect`/`blocked_tier4`/`open`, re-checked the code still matches (no regression) via
`git diff` + direct read against `rc1-cand`. Then re-ran the new-defect probe (row 10) fresh,
since the diff shows the exact file implicated last time changed substantially.

## Scored table — census → rc1 delta (re-verified at 4c6dfe8c)

| # | Register id | Census verdict | RC1 re-drive (live at 4c6dfe8c) | Score | Evidence |
|---|---|---|---|---|---|
| 1 | R15-UI-008 | admitted (high) | **FIXED, confirmed live**: `POST /llm/keys/validate {"provider":"openrouter","api_key":"sk-or-v1-<fake>"}` → `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` (200) — unchanged from the prior sha, no regression | ok | `rc1/K02-fake-openrouter-key-r2.txt` |
| 2 | R15-DATA-018 | admitted (high) | **FIXED, confirmed live**: `GET /resolve?q=zomato` and `q=ZOMATO` both resolve to `ETERNAL` with a full `rename` block (`renamed_from/renamed_to/effective_date 2025-04-09`), `needs_disambiguation:false` | ok | `rc1/R5-resolve-zomato-both-r2.txt` (both queries; note its header on an APFS case-collision caught and fixed while writing evidence) |
| 3 | R15-UI-052 | admitted (medium, 2 raws) | **FIXED, confirmed by code read at 4c6dfe8c**: `OnboardingFlow.tsx:241` welcome copy still "Live quotes, charts, news and screeners run right now. Pick a path below to turn on the AI agent..."; `:260` local-path body still "...it still reaches out for market data and web searches, but the model itself is yours"; `OnboardingBanner.tsx:68` still "Keys stay in your OS keychain — market data and web searches still go to public providers" — `git diff` confirms none of this text changed since the last sha | ok | `src/components/OnboardingFlow.tsx:241,260`; `src/components/OnboardingBanner.tsx:68` (rc1-cand) |
| 4 | R15-UI-041 | admitted_with_correction (medium) | Register status `not_a_defect` post-D81 — **confirmed live**: `DisclaimerFlow.tsx:28-35` `TOS_BODY` unchanged: no brokerage/order/kill-switch language, carries data-may-be-wrong + AI-can-be-wrong + PolyForm Strict/commercial licence text | ok (matches register) | `src/modules/safety/DisclaimerFlow.tsx:28-35` (rc1-cand) |
| 5 | R15-UI-076 | admitted (low) | Register status `open` — **confirmed still present, no regression**: `chart-drawings.ts:50` `DEFAULT_CHART_SYMBOL = "SPY"`, `region.ts:39` `DEFAULT_REGION = "IN"` — same contradiction, `git diff` shows neither file touched between shas | expected-open (unchanged) | `src/store/chart-drawings.ts:50`, `src/lib/region.ts:39` (rc1-cand) |
| 6 | R15-UI-019 | fixed | **FIXED, confirmed live**: `POST /llm/keys/validate {"provider":"ollama","model":"qwen3:8b"}` → `{"ok":true,"reason":null,"detail":null}`; `OnboardingBanner.tsx:39,48-49` still wires `defaultLaneNotReady` off `useKeylessReadiness`'s real probe | ok | `rc1/validate-ollama-qwen3-r2.txt` |
| 7 | R15-AGENT-028 | fixed | **FIXED, confirmed live**: `POST /llm/keys/validate {"provider":"ollama","model":"llama3.1:70b-not-pulled-xyz"}` → `{"ok":false,"reason":"model_not_pulled","detail":"llama3.1:70b-not-pulled-xyz is not downloaded in Ollama (local) yet."}`; `ChatSidebar.tsx:831-836` still routes that reason to the local-download onboarding step | ok | `rc1/validate-ollama-not-pulled-r2.txt` |
| 8 | R15-UI-044 | `blocked_tier4` | **Confirmed still present, no regression** (expected, Tier-4 blocked): `safety.ts` `getSecret` call still has no try/catch around the first-launch ack read; `git diff` shows `src/store/safety.ts` and `DisclaimerFlow.tsx` untouched between shas | expected-broken (unchanged) | `src/store/safety.ts` (rc1-cand, unchanged) |
| 9 | (extra) `ZOMATO.NS` quote for the retired ticker | census: 502 leaking yfinance internals | **Improved, confirmed live**: `GET /quotes/ZOMATO.NS` → 404 `{"code":"not_found",...}`, no internals leak, unchanged from prior sha | ok (bonus, rides R15-DATA-018) | `rc1/quote-ZOMATONS-r2.txt` |
| 10 | R15-LEAD-030 (known limitation, blocked_tier4/DECISIONS 4.9) | census A1: wrong ("I couldn't find Zomato... not covered") — resolver-side | **RECLASSIFIED from the prior attempt.** The resolver-side wrongness stays fixed (row 2). The prior attempt filed the model's fabrication as a fresh `new_defect`; that was wrong under this round's LEAD NOTE — the failure mode ("the local model states a figure for a subject with no ok tool call behind it") is exactly `R15-LEAD-030`'s adjudicated, `blocked_tier4` defect class (`hallucinated-tool-result-citation`), already operator-signed-off at DECISIONS 4.9. Confirmed the class is STILL live on `4c6dfe8c` with a **fresh instance, differently shaped than before**: the `tool_call_rescue.py` fix that landed between the two shas (`_call_syntax` + `LeakHold`, citing `rc1-drive-onboarding-stranger:1` in its own docstring) closed the *specific* leaked-text shape my prior run hit (a fenced fake "Tool call: price_data(...)" + hand-typed JSON). Re-running the identical repro on `4c6dfe8c` no longer produces that shape — instead the model called the REAL `get_terminal_state` tool twice (both `tool_result ok:true`, a UI-state snapshot with no price data in its schema), then still narrated invented figures ("current price ₹130.05, daily high ₹132.50, daily low ₹128.60, +2.35%") attributed to "my research"/"the current chart". Cross-checked: the actual default chart symbol (SPY) quotes at $771.35 (`/quotes/SPY`), nothing resembling ₹130.05 — the numbers are pure invention, not misattributed real data. This is the fix correctly closing the narrow shape it targeted while the underlying non-deterministic class (already known, already blocked_tier4, already adjudicated — no further fix rounds per the LEAD NOTE) produces a new surface shape. Filed as a register **note** against `R15-LEAD-030`, not a new open finding. | blocked_tier4 (known limitation, note added) | `rc1/A1-keyless-zomato-rc1-r2.stdout.txt`; `sidecar/services/llm/tool_call_rescue.py` diff (`4097dac..4c6dfe8c`); `sidecar/services/agent_tools/catalog.py:1155-1166` (`get_terminal_state` schema, no price fields); live `/quotes/SPY` → $771.35 |

## New-defect sweep

Re-ran the fake-key, resolve, retired-ticker-quote, and both `/llm/keys/validate` probes live
against `4c6dfe8c` (all above, all confirmed unchanged from the prior sha's outcome). Re-checked
every static-copy/code-only claim (UI-052, UI-041, UI-076, UI-044) against `git diff
4097dac423bd..4c6dfe8c2d9` for the exact files cited — none of those files appear in the diff, so
no regression is possible there; confirmed by direct read anyway. The one file in scope that DID
change (`OnboardingFlow.tsx`) only touched an unrelated CSS padding class on the hardware-fit
"estimated" badge, no copy change.

No fresh, unadjudicated new_defect found in this group at `4c6dfe8c`. The only new evidence (row
10) is a same-class recurrence of an already-adjudicated, `blocked_tier4` limitation
(`R15-LEAD-030`), correctly filed as a register note per the Gate Round 2 LEAD NOTE's explicit
instruction, not as an actionable finding requiring a fix round.

## Sidecar

Boot: `cd rc1-cand/sidecar && VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 nohup sh -c "sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52326 --data-dir rc1-data-onboarding-stranger" > rc1-onboarding-sidecar.log 2>&1 &`.
`/health` ok, `openbb-mcp: available`. The `llama3.1:8b` probe ran under the shared Ollama lock
(held via `mkdir /tmp/vysted-r15-ollama.lock`, released by the process's own `EXIT` trap);
observed 3 other agents' `vy.py` processes hitting the same Ollama runner concurrently during
this call (a lock-discipline gap in the run, not scoped to this role to fix) — the call still
completed in 200s (vs 110s on the less-contended prior sha), no lock_timeout. Stopped via
`kill 70768` (worker; the `sleep`-wrapper pid had already exited on its own) at the end of this
drive.

# Final-pass drive — composer-chat (head d38b5d1a)

Driver: final-drive-composer-chat (claude-opus-5-5, effort high). Own sidecar :52840 from the read-only final-cand source (data dir cp of final-seed-data, MCP env -> shared :52801/:52802); shared :52800 used read-only for value read-backs. Headless only: real `ChatSidebar` mounted in a scratch vitest/jsdom harness (jsdom url http://localhost:5173, real SSE transport, tauri invoke + keychain mocked to null). Every Ollama-reaching run held /tmp/vysted-r15-ollama.lock (one exception: the mount harness chip click, see notes). Lane: Ollama llama3.1:8b; OpenAI only for the no-key/bad-key error rows (zero spend). Evidence: `surface/composer-chat/final/` (COVERAGE.json holds the 24 scored rows).

## Scored table (census -> final)

| Row | Census | Final | Evidence |
|---|---|---|---|
| composer-mount | partial | **partial** | 02-mount-controls.json (real ChatSidebar vs :52840: /health,/runs,/llm/providers,/custom-agents,/agents,/llm/models 200; controls row present) + 03-pure-logic.json#collapse (icons<=300, compact 360, full>=420); stop morph seen in 25/27-stop-midstream. ResizeObserver paint at real dock widths = NEEDS-GUI. |
| composer-depth-control | ok | **ok** | 02-mount-controls.json (Normal/Deep/Ultra clicks normal->normal->deep->ultra); 27-stop-midstream-b.events.jsonl request options.research_depth=deep -> 'IterResearch (evolving report)' engine step. |
| composer-model-control | ok | **ok** | 02-mount-controls.json (button 'Ollama (local) · qwen2.5:7b' = deliberate default); 20/21-err-*-openai (no-key / bad-key states carry auth copy). |
| composer-plus-menu | ok | **ok** | 02-mount-controls.json (Persona roster, Autonomy ASK/AUTO with hint, Mode Agent/Delegate, Context/Scope/Route to sections). |
| composer-mention-picker | ok | **ok** | 05-mention-slash-dom.json, 07-mention-typed-dom.json (typed '@ana' -> @analyst, Enter accepts 'is it cheap @analyst '), 06-resolve-mention-direct.json; 03-pure-logic.json#mentions prefixes. |
| composer-slash-picker | partial | **partial** | 05-mention-slash-dom.json (10 commands, '/sc' -> /screener, accept '/screener ', Esc dismisses) + 03-pure-logic.json#slashTemplates; 18-t5-screen-auto: the 'screen for …' expansion reaches screener_run but llama3.1:8b sent the criteria array as a string (Python None inside) -> runtime rejected with 'call again with valid args', model did not retry and pasted a pseudo write_screener_filters call as code; screener store unchanged; fail-safe 'returned no data' note inserted. Model weakness, not filed. |
| composer-send-stop-button | broken | **ok** | 27-stop-midstream-b.events.jsonl (deep research tool_use at 4.8 s, stop clicked at 75.0 s via the real 'Stop the in-flight run' button, onError aborted at 77.6 s; message stopped:true, pending:false) + 26-stop-midstream-watch.txt (no /api/chat, research search or MCP research line in the sidecar log from 16:20:42 through 16:22:43, ~80 s past the stop; census saw ~3 min of continued work). Run a (25-*) stopped before the first model round. R15-AGENT-002 holds. |
| composer-queue | ok | **ok** | 03-pure-logic.json#queue (FIFO head 'first', rest ['third']). |
| chat-agents-rail | partial | **partial** | 30-delegate-default.json (rail '●Vysted Copilot Delegate 6,524 tok · $0.0000' + activity row while running; cleared on done), 31-delegate-cancel.json (running -> cancelled 'cancelled by user'), 32-delegate-breach.json (error row 'step ceiling 1 reached (1 taken)'). Paused answer-box not driven: code now carries an ask_user -> status 'paused' path (run_manager.py:308-332) but no live run chose ask_user. |
| chat-empty-state | partial | **ok** | 02-mount-controls.json (empty-state copy + 4 suggestion chips rendered against live sidecar). |
| chat-suggestion-chips | partial | **ok** | 02-mount-controls.json: a chip click now SENDS via sendToAgent (census: filled the composer) -> one POST /agents/copilot/invoke observed. Behaviour change, intended. |
| chat-error-row | ok | **ok** | 20-err-nokey-openai.* ('No OpenAI API key is set — add it in Settings.', code auth), 21-err-badkey-openai.* ('The OpenAI API key was rejected — check it in Settings.', code auth). |
| chat-message-notices | broken | **partial** | 23-ask-chart.json notices ('Staged for your review, not applied yet: set_chart_symbol BDL.NS; set_chart_indicators BDL.NS. Accept it below to apply.'), 22-t6-arrange-auto.json step "Couldn't apply: … the layout has not mounted", 15-t3 steps 'Applied: Add …' with real acks. kept_previous copy not re-driven. |
| chat-plan-view | ok | **ok (carried)** | Not re-driven: census used gpt-4o-mini for a compound plan; no keyless lane produces agent_plan reliably and no spend was needed for the delta. Carried from census 18-plan-compound-4omini. |
| chat-research-activity | ok | **ok** | 24-persona-munger.events.jsonl (research engine/plan/tool/search/synthesize steps in order, cross-check timeouts reported as error steps), 27-stop-midstream-b (IterResearch steps), 03-pure-logic.json#elapsed. |
| chat-budget-config | partial | **ok** | 30-delegate-default.json budgetEditorText 'Budget tokens $ secs steps — first breach aborts the run'; defaults 120000/1/600/12 travel to the sidecar run; 32-delegate-breach.json max_steps 1 aborts at 1 step with stated reason + checkpoint (1 message). Token-overshoot / all-null budget cases not re-driven. |
| agent-mode-toggle | ok | **ok** | 10..27 agent-mode SSE turns; 30/31 delegate mode via the composer (POST /agents/copilot/runs, 'Delegated to a background run' chat row, answer lands in chat on done). |
| agent-autonomy-ask-auto | partial | **ok** | 23-ask-chart (ASK: both chart actions staged pending, model says 'I've proposed the changes … for your review' — the R15-AGENT-033 narration is now honest) vs 15-t3 (AUTO: watchlist applied, acks POSTed, read back +COCHINSHIP +MDL) and 16-t4 (AUTO: write_note still staged as a data write, narrated 'staged and awaiting your review'). |
| agent-persona-picker | partial | **ok** | 24-persona-munger (agentId munger on llama3.1:8b: research tool ok, mcap 33,858 cr / EPS 25.86 / beta 0.582 / 52w high 1890 all match the auto-brief payload; census had zero tool calls + ungrounded figures). Reply concatenates two answers after an errored open_panel call — model polish, not filed. |
| agent-command-bus | partial | **partial** | 01-existing-unit-tests.log (bus tests pass). In-memory hand-off, nothing new to drive. |
| agent-runs-store | partial | **partial** | 30/31/32 delegate (running/done/cancelled/error with cost, GET /runs/{id} read back). paused not reached live (see chat-agents-rail). |
| llm-chat-streaming | ok | **ok** | every *.events.jsonl here: real transport, delta/tool_use/tool_result/research_step/done frames, no transport errors; 25/27 abort path surfaces 'This operation was aborted' and finalises the message. |
| chat-markdown-render | partial | **partial** | 03-pure-logic.json#markdown (106 real t1 deltas, 0 open-fence frames). 18-t5 and 23-ask-chart: the model writes pseudo tool calls / fabricated chart blocks inside code fences — renders as code, no raw tool JSON leak seen this pass. |
| context-provider-badge | ok | **ok** | 10-t1 request context_snapshot; 12-t2 'it' resolved from history to the Cochin conversation; 24 request carries __terminal__ snapshot. |

Totals: 24 rows — 17 ok (1 carried: chat-plan-view), 7 partial, 0 broken, 0 regressions.

## Census -> final deltas

- **composer-send-stop-button broken -> ok** (R15-AGENT-002): the real stop button during a DEEP research run aborts the stream, the message finalises `stopped:true`, and the sidecar log shows no further model/search/research traffic for ~80 s after the stop (census: ~3 min).
- **agent-autonomy-ask-auto partial -> ok** (R15-AGENT-033): under ASK the model now says it *proposed* the chart change for review; the staged-actions notice rides alongside.
- **agent-persona-picker partial -> ok**: the munger persona on the keyless lane now calls research and every figure it states matches the payload (census: zero tool calls, ungrounded figures).
- **chat-budget-config partial -> ok** at the driven depth: defaults travel, a 1-step ceiling aborts with a stated reason and a checkpoint. Overshoot / all-null budget cases not re-driven.
- **chat-suggestion-chips**: a chip now sends immediately (sendToAgent) rather than filling the composer — intended behaviour change, scored ok.
- **chat-message-notices broken -> partial**: staged / couldn't-apply / applied copy all render from real turns; the kept_previous copy was not re-driven.
- Default model is qwen2.5:7b in the UI (deliberate); the harness selects llama3.1:8b explicitly.
- Intent gate (R15-AGENT-019, blocked_tier4): note/screen/save/jot/watchlist/chart prompts all classify `edit` (04-classify-intent.txt).

## Findings

- **new_defect, low** — write_note files under the literal company name ('COCHIN SHIPYARD'), so the COCHINSHIP note view stays empty (17-t4-note-accept-readback.json; suspected src/lib/host-actions.ts noteScope()).
- **known_limitation** — t2 compare states the wrong companies' figures as Cochin/Mazagon (R15-LEAD-037, DECISIONS 4.11).
- **known_limitation** — ASK chart turn prints a fabricated BDL price/RSI/P/E block with no data call (R15-LEAD-030, DECISIONS 4.9).
- **needs_gui** — arrange compare apply in a real dockview; composer collapse paint at real widths (NEEDS_GUI.md).

## Notes (not filed)

- t3 added MDL.NS (Marvel Decor) carried over from t2's wrong ticker and narrated it as Mazagon — model weakness; the resolve-before-add mechanism worked (related open R15-LEAD-088).
- t5 /screener expansion: llama3.1:8b sent the criteria array as a string; the runtime rejected it cleanly and the model did not retry. Screener store unchanged.
- Delegate default run answered honestly under a yfinance rate-limit (yahoo circuit open) — environment.
- R15-AGENT-086 (open, pause unreachable): code now carries an ask_user -> paused path (run_manager.py:308-332); no live run reached it, so nothing is attached.
- final-cand carries a pre-existing uncommitted `M vitest.config.ts` (not this driver's).

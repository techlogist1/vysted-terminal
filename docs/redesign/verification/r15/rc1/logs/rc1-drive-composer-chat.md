# rc1-drive-composer-chat — working log

Role: OWNER-DRIVE composer-chat re-drive against RC1 candidate `4097dac4`.

1. Set up: `cp -R rc1-seed-data rc1-data-rc1-drive-composer-chat`; booted candidate sidecar from
   `rc1-cand/sidecar` on `:52320` (`sleep 86400 | ./.venv/bin/python3 main.py ...`), sleep pid
   67607, worker pid 67608. `/health` ok. Shared stack `:52152-54` confirmed up, read-only.
2. Read `PROMPT_surface_s2.md` OWNER-DRIVE + composer-chat group scope, `ISO_STACK.md` boot
   recipe, and the full census evidence for this group: `EVIDENCE.md`, `COVERAGE.json` (24
   rows), `census/refute/surf-composer-chat.json` (11 admitted raw findings).
3. Cross-referenced all 11 raw ids against `vysted-r15-register.json` — every one maps to a
   register entry, every one `status: "fixed"`, several with a `note` recording an earlier
   certification pass (batch 6-9) that found the fix incomplete before a later batch closed it.
   Confirmed all 6 distinct closure commits (`c81d879`, `1574ed8`, `e81c9e7`, `68bb7aa4`,
   `6b70230`, `f407107`) are ancestors of `4097dac4`.
4. Re-verified each of the 11 against the candidate, preferring the census's own repro shape at
   the code/API level (no LLM needed to re-prove a deterministic mechanism):
   - stop-mid-stream cancel: in-process repro stubbing `_dispatch_tool`, closing the generator
     mid-dispatch → task now cancelled (was not, per COD-agent-runtime-4). FIXED.
   - `compare_symbols`: live in-process call on "Cochin Shipyard"/"Mazagon Dock" → both resolve
     to real symbols with quote+fundamentals (was: invented dead ticker MAZAGONDOCK). FIXED.
   - `classify_intent`: in-process on the exact turn-4/5/slash/save prompts → all now `edit`
     (was `read`, stripping write_note/write_screener_filters). FIXED.
   - `GET /resolve?q=Mazagon Dock`, `GET /macro/GDP?provider=worldbank`,
     `GET /quotes/ZZZZNOTREAL`, `GET /history/XYZ%2FABC` — live curl against my sidecar. All
     clean/humanized, no raw library text, no invented-ticker path. FIXED (x4 findings).
   - `ollama.py` + `openai.py` tool-call rescue: now a shared `tool_call_rescue.py` module used
     by both adapters (was: openai-only). FIXED.
   - `agent_runtime.py` tool_call_id minting: every tool call gets a fresh `call_{uuid4}`
     regardless of provider (was: ollama emitted `''`, ack never landed). FIXED, and resolves
     the cross-run uniqueness residual too (uuid4 is run-independent).
   - `run_manager.py` resume: now threads `provider=run.provider, model=run.model` explicitly
     (was: fell to agent default, silently loaded Qwen instead of llama3.1). FIXED. Also found
     (unprompted, corroborating) that a halted `ask_user` run now transitions to `paused`
     directly from the run loop, making the previously-uncallable `pause_run`/answer path
     reachable by a different, working mechanism.
   - `semantics.py` `display_value`: every `_PROMPT_KEYS` metric (incl. `market_cap`) is
     pre-scaled to crore with a spelled unit before the model reads it. Code-confirmed FIXED.
     Attempted a live end-to-end re-drive (`vy.py invoke copilot` "What does Cochin Shipyard
     do... P/E and market cap?", port 52320, llama3.1:8b) — the `fundamentals` tool call timed
     out under heavy sibling-agent ollama contention (3 other rc1 drives sharing the one local
     ollama instance; my call ran 237.6s vs a 6-50s census baseline), so the model never read a
     market_cap/dividend_yield payload value at all and self-computed a (wrong) market cap from
     partial data instead. Not a reproduction of the original defect — logged as inconclusive,
     not as a finding.
   - `agent_runtime.py` `_staged_actions_notice`/`turn.staged_actions`: a genuine new
     end-of-turn honest-ground-truth mechanism for ASK-autonomy staged actions. Code-confirmed;
     not re-driven live (would need another contended ollama round-trip) — scored `partial`,
     not `ok`, since the model's own prose can still claim a staged change is done.
5. Wrote `surface/composer-chat/rc1/COVERAGE.json` (24 rows: 5 updated with RC1 evidence, 19
   carried forward from census with a note), `surface/composer-chat/rc1/*` evidence files,
   `rc1/drives/composer-chat.md` scored table + deltas.
6. No regression, no fresh (non-register) defect found in what was driven this pass →
   `rc1/findings/rc1-drive-composer-chat.json` = `[]`.
7. Stopped own sidecar (`kill 67607`), confirmed the process is gone.

Spend: one local `ollama`/`llama3.1:8b` call via `vy.py` ($0.00, ledger tag
`rc1-cc-t1-cochinship`). No paid-provider calls this pass.

---

## Pass 2 (gate round 2, candidate 4c6dfe8c)

Same role, candidate advanced 4097dac4 -> 4c6dfe8c (297 commits, ancestor-confirmed). Re-booted
own sidecar on :52320 from the (now further-built) rc1-cand worktree against the same
rc1-data-rc1-drive-composer-chat data dir. Verified all 11 pass-1 fix anchors still present in
source (grep), ran the sidecar's own relevant pytest files (compare_symbols, tool_call_rescue,
agent_runtime, run_manager, planner = 341 tests, all green), re-ran 4 live API checks (/resolve,
/quotes batch join, /quotes single 404, classify_intent) and the pass-1 in-process stop-cancel
repro unmodified. No regression, no new defect. Full detail + evidence file list in
docs/redesign/verification/r15/rc1/drives/composer-chat.md ("Pass 2" section) and
surface/composer-chat/rc1/v2-*. Stopped sidecar: sleep pid 58519 (closed stdin but worker 58522
outlived it by >5s so killed 58522 directly — port 52320 only, no other owner touched).

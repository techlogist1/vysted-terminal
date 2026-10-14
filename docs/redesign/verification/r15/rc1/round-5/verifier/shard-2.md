# rc1 gate round 5: adversarial sample verifier, shard 2 (rc1-vshard-2)

**Candidate:** 633f844071d972b337f4c3526d86555c80df0568. The worktree was used read-only.

**Stack:**
- Own sidecar on :52602, running from worktree source with an isolated copy of the seed data dir.
- Scratch vitest and pytest harnesses rooted at the worktree.
- The shared stack was touched read-only: only tools/list on :52153 and :52154.
- One local-model call, made under the Ollama lock.

**Scope:** 22 entries. For each, I ran the entry's own repro plus at least one fresh variant.

**Records:**
- Log: `../logs/rc1-vshard-2.md`
- Harness and outputs: `../logs/rc1-vshard-2-evidence/`
- Findings: `../findings/rc1-vshard-2.json`

## Verdicts

| Entry | Verdict | Basis |
|---|---|---|
| R15-DATA-072 | holds | Tripped breaker then real get_history KO, cash_flow NVDA, balance_sheet INFY.NS and quarterly income ASML all close it. Real Yahoo 429s leave it open. |
| R15-DATA-097 | holds | Time-travel through resolve(): an empty result is cached inside the TTL. After 301 s the new listing NEWCO-SM appears, for both IN and US. |
| R15-LEAD-009 | holds | Region switch on INFY splits history, surprises and ratings/history into INFY.NS vs INFY, each with its own cache entry. |
| R15-AGENT-040 | **refuted (NOT CERTIFIED)** | The 7-turn short thread passes. The client `historyForSend` still FIFO-drops the oldest turns past 60k chars before the runtime folds them. With 6×12k-char answers, turn 1 is lost while the UI says "Older turns summarised". With 20×3.5k-char answers, 32 of 40 turns are sent. The summary carries no figures or sources. |
| R15-AGENT-048 | holds | At most 2 repairs per round and time-bounded with a hanging repair (openai and openrouter); repair usage is metered. |
| R15-RESEARCH-014 | holds | Live llama3.1:8b at num_predict=24 returns finish_reason length, and the runtime emits the truncation notice. The Anthropic ceiling table is in place. |
| R15-CODE-AGENT-012 | holds | invoke_agent is {agent_id, prompt}. There are 0 secret-shaped params across 40 + 71 + 21 MCP tools. |
| R15-CODE-PLATFORM-004 | holds | 'false', 'no', '0', 'off', ' OFF ', 'False' and '' all skip the true branch; 'true' and 'yes' take it. |
| R15-CODE-PLATFORM-005 | holds | 200 concurrent BS pricings and 40 concurrent binomial(800) pricings: 0 mismatches. /health max 12 ms during a 7 s pricing. |
| R15-LIFECYCLE-017 | holds | Unexpected errors log at WARNING and not_found stays DEBUG. Progress frames reach (25, 25). |
| R15-UI-055 | holds | Live fully throttled run: evaluated 0, partial, and the table shows "Nothing could be screened / Retry". |
| R15-UI-045 | holds | The value survives between → lte → between → gt in both the flat and the nested builder. |
| R15-DATA-017 | holds | JNPR, DHOOTTRANS and SUMAX lanes all 200 and match NSE. Post-master listings AXIOMGAS, UDAYJEW and PARIN are served. |
| R15-CODE-FRONTEND-015 | holds | Badge, chips and snapshot share `focusedSymbolFromBus`. Equity-overview INFY, chart-2 NVDA and analyst-ratings MSFT all resolve to the focused symbol. |
| R15-LEAD-012 | holds | All three ensure scripts go through `ensureBuildVenv`. With bare python3 = 3.14.5 the resolver picks 3.13. The VYSTED_PYTHON override is honoured, and a wrong version gives a named error. A 3.14 venv is recreated as 3.13.13. |
| R15-AGENT-051 | holds | The preamble's "Focused chart" matches the deixis line for chart-2 NVDA and for chart-3 TCS.NS. |
| R15-RESEARCH-016 | holds | ULTRA with 3 angles and ULTRA with a budget of 1 both cite all 3 NSE floor PDFs, as DEEP does. |
| R15-RESEARCH-017 | holds | Real DEEP and ULTRA loops with snapshot_structured or resolve_target raising produce the same typed ok:false, and nothing escapes. The single-pass fallback in the fix_shape was superseded by CODE-RESEARCH-003. |
| R15-RESEARCH-018 | holds | 9 fresh phrasings: India targets (matched by exchange only, region only, or lowercase region) never reach EDGAR. 'secular', 'secondary' and 'sectoral' do not match. US "SEC's 13F" and ADR 20-F do. |
| R15-CODE-FRONTEND-009 | holds | The agent's nested group and formula are saved, not the draft. An exact-name save is labelled "replaced", and Undo restores the old screen. |
| R15-CODE-FRONTEND-010 | holds | run:true runs once against the new state. run:"true", malformed input and no-run cases do not run. |
| R15-CODE-FRONTEND-011 | holds | Through the real enqueue→accept path: cost-only and qty-only lot updates, a target gone at accept, close/open panel aliases, and invalid regions all give a diff that matches apply. |

## Adjacent defects (not refutations)

These are listed in the findings file as `rc1-vshard-2:2` through `rc1-vshard-2:7`.

- **Medium, near LEAD-009:** Under a Yahoo throttle, earnings history's YFRateLimitError is swallowed. The endpoint returns 200 `history:[]`, which is cached for 24h.
- **Medium, near UI-055:** A partially throttled run (3 evaluated, 9 rate_limited) tells the user to "loosen a threshold / Reset filters".
- **Medium, near CODE-FRONTEND-015:** A focused SEC Filings panel publishes `identifier`, not `symbol`. The agent's "this" falls back to the chart symbol.
- **Low, near CODE-FRONTEND-009:** save_screen overwrites the user's live draft without disclosing it, and Undo does not restore the draft.
- **Low, near DATA-097:** `_us_isin` caches a definite ISIN miss for the life of the process.
- **Low, near LEAD-012:** CONTRIBUTING.md says "Python 3.13+".

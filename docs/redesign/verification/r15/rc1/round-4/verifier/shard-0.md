# rc1 gate round 4 - verifier shard 0 (rc1-vshard-0, Opus)

Candidate: 68d5573aff9a579af084dcbb124843f2aecff6e8 (worktree rc1-round-4-1006c6d-fix-int, read-only).
Own sidecar: :52600 booted from the candidate with a private data dir, MCP 52153/52154. Stopped by killing its sleep pid (33797).
Raw evidence: `verifier/raw-shard-0/`. Log: `logs/rc1-vshard-0.md`. Findings: `findings/rc1-vshard-0.json`.

## Verdicts (24 entries)

| Entry | Verdict | Repro + fresh variant |
|---|---|---|
| DATA-006 | holds | GET /quotes/DAL returns ts 2025-03-12 (header Ason), change 0, stale, bse. Fundamentals as_of is 2025-03-12. Fresh: Ason '03 Jan 24' gives 2024-01-03, change 0. |
| DATA-070 | holds | Undated and garbage-date RSS items get None and sort after dated ones. The frontend shows 'date unknown'. |
| DATA-033 | holds | validate_quote and validate_series reject NaN and +/-inf with CorrectnessError, so the registry falls through. |
| DATA-003 | **refuted (partial)** | Research half holds: US AMAL and fresh PAR snapshots carry no exchange ownership fact. The entry's own repro still reproduces: `curl -H "X-Vysted-Region: US" :52600/disclosures/shareholding?symbol=AMAL` gives coverage covered, promoter 71.35, BSE, note null. Announcements do the same. The shareholding_pattern tool in the US region returns Amal 71.35 BSE and Par Drugs 73.41 NSE. The fix_shape's explicit not-applicable gate is absent. Caveat: the routes may be India-only by design, and the tool says "NSE/BSE ticker". |
| CODE-DATA-005 | **refuted (partial)** | The predicates are unified in services/witness.py. The `_row_value` twin that the title names is still byte-identical in growth_check.py:94 and earnings_quality.py:134. |
| DATA-012 | holds | Injected NSDL->GUJENERGY: NSDL stays NSDL, BSE, INE301O01023. Live map of 1056 hops: SHREE, HSIL and WORTH stay their own rows. Fresh scan: 0 listed old symbols map to an unlisted target. |
| RESEARCH-037 | holds | Unranked [blog, reuters, vysted, sec.gov] gives primary [4] and press [2]. |
| RESEARCH-001 | holds | The IN deep news leg goes through gate_news and the META namesake item is dropped. Adjacent: US targets pass the gate unchanged. |
| RESEARCH-034 | holds | The repro phrase returns False. 11 fresh phrasings all fall back conservatively. |
| CODE-FRONTEND-004 | holds | Research-space save, get and delete round-trip for NVDA, M&M, RELIANCE.NS, Hindi, '../../etc/passwd' (stored encoded), '.' and 'CON'. Rollback happens before the throw, and the detail is surfaced. |
| CODE-FRONTEND-005 / -018 | holds | PERSISTED_SLICES covers every SerializedWorkspace key. wireAutosaveTriggers is called from page.tsx:115. Tests are green. |
| DATA-007 | holds | The AAPL 2023 10-Q returns 10-Q, 2023-08-04 and a CIK URL. Fresh: MSFT 2019 10-K is correct and a bogus accession gives not_found. Adjacent: every 10-Q has 0 sections. |
| DATA-009 | holds | N=1/2/4 give 200 points each, and Sharpe equals date-sampled Sharpe. The fresh misaligned-calendar case also matches (1.246). |
| DATA-010 | holds | Sortino matches textbook: 6.352 on the repro, and 7.099, 10.04 and 4.661 on fresh series. |
| AGENT-054 | holds | Unknown keys are dropped and reported, and the enum equals the frontend catalog. The runtime rejects bollinger_bands readably. Adjacent: the enum rejects 'ema:50'. |
| AGENT-047 | holds | Groq and Ollama mark truncated or non-object args with the sentinel. Runtime schema validation catches Gemini-shaped {} and wrong-type args. |
| AGENT-001 | **refuted (partial)** | See below. |
| CODE-FRONTEND-014 | holds | noteScope maps global/general/'' to General. saveLayoutName defaults to the active layout. Tests are green. |
| UI-001 | holds | The store is authoritative, flush runs on scope switch and unmount, and notes vitest passes 36/36 in the candidate. |
| UI-002 | holds | The palette uses loadSymbolIntoChart and there is no stray setSymbol writer. |
| CODE-AGENT-003 | holds | /llm/keys/validate reports invalid for fake keys on 7 providers. The real Gemini API_KEY_INVALID 400 and xAI 400 map to auth. |
| RESEARCH-010 | holds | With a fake key, the engine emits an error step: "OpenRouter rejected the request...". |
| AGENT-004 | holds | A fresh SSE with a text block plus 2 tool blocks and split nested args yields full args. An arg-less tool yields {}. |

## AGENT-001 (refuted, partial)

The money half holds. `model_view` and `fundamentals_content` swap currency scalars for crore displays, and the model said Rs 14,139 cr for KPIT and Rs 36,226 cr for COCHINSHIP. Both are correct.

The fraction half is not certified. The fix_shape asks for "unit 'fraction' ... for every fraction metric" and "one shared formatter feeds both panel and tool payload". On candidate :52600 with llama3.1:8b:

- "research KPIT Technologies" gave `Dividend Yield: 0.0144` and `52-week change -0.57067287`. The panel shows 1.44%.
- Fresh case: "What are Cochin Shipyard's dividend yield, revenue growth, earnings growth and market cap right now?" called the `fundamentals` tool and gave `dividend yield is 0.0082, revenue growth is 0.024, earnings growth is -0.194`. The true values are 0.82%, 2.4% and -19.4%.

The payload the model reads (`raw-shard-0/agent001-cochinship-fundtool.json`) has raw fractions with no unit or display. No COCHINSHIP fraction fixture exists. The literal '%' glyph from the repro did not appear in either run, but chat still narrates the unscaled fraction as the metric.

Command: `python3 vs0/vy_52600.py invoke copilot "<prompt>" --port 52600 --provider ollama --model llama3.1:8b --region IN --out raw-shard-0/agent001-cochinship-fresh.jsonl`. It ran under the Ollama lock.

## Harness notes

- The shared :52152 (pid 48629) runs rc1-round-4-cand at **1006c6da, not the candidate**. It lacks ea2ebd50, so "KPIT Technologies" resolves to BSOFT there. My first AGENT-001 run on it is kept as `*.STALE-52152-1006c6d.*` and was not used.
- vy.py refuses :52600, so I used the scratch copy `vs0/vy_52600.py`. Only the port range and the REPO path changed, and the spend guard is kept. Every LLM call was local Ollama at $0.
- The notes vitest in the main checkout fails on a missing @tiptap/extension-list in node_modules. That is environmental, and the candidate worktree run passes.

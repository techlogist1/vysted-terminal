# triage-b — rc1-vshard-0:2 (tie R15-AGENT-001)

Audited 07:25 IST on my own sidecar at :52425 at HEAD bed3b166, whose code tree equals 01015033. It runs sidecar/.venv uvicorn app:app with VYSTED_DATA_DIR set to scratch and MCP ports 0. Ollama llama3.1:8b ran under the single-lane lock. I used a scratch copy of scripts/r15/vy.py (`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/vy_52425.py`) whose only changes are that its isolated-port guard admits 52425 and that its spend ledger goes to scratch.

## Claim (shard 0)
The money half is fixed. The fraction metrics reach the model raw with no unit. Chat narrated "dividend yield is 0.0082, revenue growth is 0.024". The true values are 0.82% and 2.4%.

## Code at HEAD
- `sidecar/services/agent_runtime.py:783`: `_FUNDAMENTALS_TOOLS = ("fundamentals", "compare_symbols", "financial_statements")`. `_model_facing_content` routes them through `research.fundamentals_content`.
- `sidecar/services/agent_tools/research.py:536-540`: `fundamentals_content` loops ONLY over `(*_STATEMENT_MONEY_FIELDS, "market_cap")` and rewrites them with `display_value(..., "currency", ...)`. Every fraction field of the `Fundamentals` dump reaches the model as a bare float with no unit and no display: `dividend_yield`, `revenue_growth`, `earnings_growth`, `roe`, the margins, `held_percent_*` and `fifty_two_week_change`.
- `sidecar/services/agent_tools/research.py:403-459`: `model_view`, the research path, likewise rewrites only `unit == "currency"` nodes and money keys. The derived leg carries `unit: "fraction"`, but `structured.fundamentals.data` keeps the same fractions raw and unitless next to it.
- `sidecar/services/research/semantics.py:189-198`: `display_value` already renders `fraction` as percent points, and its docstring states "A raw fraction or raw rupee float never reaches the model as the figure to state". The fundamentals tool path breaks that contract.
- The fundamentals tool's description (catalog) is "Valuation ratios (P/E, P/B, market cap, margins) + a company profile". It never says the values are fractions. The copilot prompt's fraction rule only covers values "with unit 'fraction'", which these values do not carry.

## Repro 1: the exact model-facing payload at HEAD (in-process)
The command was `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/a001/model_payload.py /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/data`. It calls agent_tools.invoke_tool('fundamentals') and then agent_runtime._model_facing_content.
```
COCHINSHIP.NS MODEL-FACING fundamentals: {'market_cap': '₹36,226 cr', 'dividend_yield': 0.008199999999999999, 'revenue_growth': 0.023974943542678664, 'earnings_growth': -0.19366146192703143, 'roe': 0.11585091377521958, 'profit_margin': 0.13479, 'fifty_two_week_change': -0.22291195, 'held_percent_insiders': 0.63335}
  any 'unit'/'display' keys near fractions: []
  field_meta.dividend_yield: {'status': 'ok', 'provider': 'yfinance', 'as_of': '2026-09-25T09:45:01+00:00', 'reason': None, 'label': None, 'basis_note': None}
KPITTECH.NS MODEL-FACING fundamentals: {'market_cap': '₹14,139 cr', 'dividend_yield': 0.0144, 'revenue_growth': 0.08853421681469702, 'earnings_growth': -0.31833227651120716, 'roe': 0.16453896894359418, 'profit_margin': 0.08839, 'fifty_two_week_change': -0.57067287, 'held_percent_insiders': 0.45268002}
  any 'unit'/'display' keys near fractions: []
  field_meta.dividend_yield: {'status': 'ok', 'provider': 'yfinance', 'as_of': '2026-09-25T09:45:01+00:00', 'reason': None, 'label': None, 'basis_note': None}
```
Money is scaled (`₹36,226 cr`). Every fraction field is a bare float, with no unit or display key.

## Repro 2: live chat, fresh case (`fundamentals` tool)
The command was `olock.sh python3 /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/vy_52425.py invoke copilot "What are Cochin Shipyard's dividend yield, revenue growth, earnings growth and market cap right now?" --port 52425 --provider ollama --model llama3.1:8b --region IN --out triage-b-raw/cochinship-head.jsonl`
```
=== ASSISTANT TEXT ===
Based on the provided tool response, here is the answer to the user's question:

Cochin Shipyard Limited's current dividend yield is 0.0082%, revenue growth is 2.39749435%, and earnings growth is -19.36614619%. The company's market cap is ₹36,226 cr.

Note that the tool response did not provide a value for free cash flow, which is listed as "unavailable" in the field metadata. Also, the provider for revenue growth and earnings growth is "nse", with an as_of date of 2026-06-30, indicating that these values are based on data up to June 30, 2026.

=== ok · 90.6s · events {'heartbeat': 7, 'tool_use': 1, 'tool_result': 1, 'delta': 143, 'done': 1} · usage in=5852 out=143 · est $0.00000 · llama3.1:8b
LOCK RELEASED 07:22 IST rc=0
```
**"dividend yield is 0.0082%"** is the entry's original symptom, a fraction read as percent and 100x low (the true yield is 0.82%). At the shard's candidate the same prompt gave the unitless "0.0082". At HEAD the literal '%' glyph is back. Growth was scaled correctly this time, which shows that correctness depends on the model guessing the unit. Raw file: `triage-b-raw/cochinship-head.stdout.txt` / `.jsonl`.

## Repro 3: the entry's own repro prompt
The command was `olock.sh python3 /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/vy_52425.py invoke copilot "research KPIT Technologies" --port 52425 --provider ollama --model llama3.1:8b --region IN`. The reply was "I've built a brief on KPIT Technologies - it's at the top of the cockpit; click any ticker to dig in." No figure was narrated, so the entry's stated research-path repro does not reproduce on this run (`triage-b-raw/kpit-head.stdout.txt`).

A second fresh case ("Infosys's dividend yield, profit margin and ROE") was inconclusive. The model called `fundamentals` with no symbol and got the invalid-args result, an unrelated small-model tool-arg failure (`triage-b-raw/infy-head.stdout.txt`).

## Duplicate search
I scanned the register for fraction/unit and model/chat, and for fundamentals_content, model_view and dividend_yield. The only entry on this defect is R15-AGENT-001. DATA-044/049/054/055 and the others are provider-data or basis entries, not the model-facing unit.

## Classification: partial on R15-AGENT-001
The entry's stated repro (research KPIT) no longer narrates a mis-scaled figure. Its class, `unit-mislabel-in-model-payload`, has a fix_shape that reads: "emit unit 'fraction' (or pre-scale to percent points) for EVERY fraction metric ... one shared formatter feeds both panel and tool payload ... a KPIT/COCHINSHIP fixture that checks the tool payload a model reads". That fails on the `fundamentals` / `compare_symbols` tool payload and on the `structured.fundamentals.data` copy inside the research payload. Live at HEAD, it produced the entry's own symptom ("0.0082%").

## Severity: critical (raised from the shard's high)
At HEAD the chat states a dividend yield 100x low as a percent. That is wrong data presented as right on the primary chat surface, the same impact that made the tie critical.

## Certification failures
The baseline for R15-AGENT-001 is 1. Its note has no clause. It appears once in a not_certified list, in stage-c batch-2 (certified in batch-3), and no refutation-audit verdicts exist for it. This partial adds 1, for a total of 2.

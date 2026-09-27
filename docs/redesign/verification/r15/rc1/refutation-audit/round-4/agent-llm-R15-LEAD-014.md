# R15-LEAD-014 / rc1-verifier:5 — refutation audit round 4 (group agent-llm)

Auditor: Opus, 06:48 IST. HEAD 608a2d4b (docs-only on top of 33586c21); code tree equals the fix-round merge 01015033
(`git diff --name-only 01015033 HEAD | grep -v '^docs/'` prints nothing; `git diff --stat 68d5573a HEAD -- sidecar src` is empty,
so the verifier's 68d5573 code is byte-identical to HEAD for this path). The fix round did not touch `sidecar/services/llm/openai.py`.

## Entry
- Title: tool-arg repair accepts a JSON-schema echo from the model as valid tool args instead of retrying.
- Repro: a repair-round reply that "merely echoes the tool's JSON schema back (rather than filling in real argument values)" is accepted.
- fix_shape (the defect class): reject a repair response whose payload structurally matches the tool's input schema
  "(keys are the schema's property names mapped to type-name placeholders, not real values)" and fall back to the invalid-args sentinel.
- Certified: batch-6 (5e14731). The batch-6 plan narrowed the fix to top-level JSON-Schema KEYWORD keys or `parsed == schema`
  (PLAN.md:315-319); batch-6 VERDICTS.md:176-190 proved only the full/fenced/prose schema echo. The placeholder shape the
  fix_shape names in its own parenthesis was never tested.

## Code at HEAD
`sidecar/services/llm/openai.py:569-573`:
```
        # A schema echo validates for any tool with no required keys; it is not args.
        if parsed == schema or (set(parsed) & _SCHEMA_KEYWORDS) - set(
            schema.get("properties") or {}
        ):
            return None
```
`{"symbol": "string"}` has no keyword key and is not the schema, and `"string"` validates as a string, so it is returned as args.
The repair path runs only for OpenAIProvider (openai, deepseek, xai, openrouter: `services/llm/__init__.py:109-121`).
The live repro needs a hosted model that emits invalid args and then echoes placeholders. That is a hosted-key lane, so it is not spent here.
The claim is code-level and was proved in-process against the real `TOOL_SCHEMAS` and `OpenAIProvider`, with the one-shot repair completion mocked (the same method batch-6 used to certify).

## 1. Entry's own repro (full schema echo), at HEAD — HOLDS FIXED
Command: `cd sidecar && PYTHONPATH=. ./.venv/bin/python ../docs/redesign/verification/r15/rc1/refutation-audit/round-4/agent-llm-R15-LEAD-014-raw/lead014_probe.py` (run from scratch; copy + output `lead014_probe.out` saved beside it)
```
HEAD 608a2d4b8cd03408319133b0da783ac7733884b0
(A) tools with properties: 54; no-required tools: 6 ['earnings_upcoming', 'market_overview', 'news', 'save_layout', 'sec_filings_list', 'sec_insider_transactions']
(A) full/fenced/prose/properties-only schema echo ACCEPTED: 0 []
```
Every one of the 54 tools with properties was tested, including the 6 no-required tools where the echo would otherwise validate. For each tool, the plain, fenced, prose-wrapped and properties-only schema echoes were all rejected. End to end through `_resolve_tool_events`:
```
(E) _resolve_tool_events(news {limit:'ten'}) + full schema echo reply -> [('news', {'__vysted_invalid_args__': "invalid arguments for news: 'ten' is not of type 'integer'; call again with valid args"})]
```

## 2. Verifier's refutation (placeholder echo), at HEAD — REPRODUCES
The same probe, section B (all-props and required-only placeholders):
```
(B) placeholder echo (all props) ACCEPTED: 20
     analyst_history {"symbol": "string"}
     analyst_individual {"symbol": "string"}
     ask_user {"question": "string"}
     backtest_summary {"run_id": "string"}
     close_panel {"panel": "string"}
     corporate_actions {"symbol": "string"}
     earnings_call_transcript {"symbol": "string", "quarter": "string"}
     earnings_estimates {"symbol": "string"}
     earnings_history {"symbol": "string"}
     focus_panel {"panel": "string"}
     fundamentals {"symbol": "string"}
     open_company_overview {"symbol": "string", "highlight": "string"}
     open_panel {"panel": "string", "symbol": "string", "run_id": "string"}
     portfolio_delete_position {"position_id": "string"}
     price_target_history {"symbol": "string"}
     read_notes {"scope": "string"}
     remove_from_watchlist {"symbol": "string"}
     save_layout {"name": "string"}
     sec_filing_content {"accession": "string", "identifier": "string", "form_type": "string"}
     shareholding_pattern {"symbol": "string"}
(B) placeholder echo (required props only, extra) ACCEPTED: 17
     add_to_watchlist {"symbol": "string"}
     corporate_announcements {"symbol": "string"}
     earnings_call_transcript {"symbol": "string"}
     exchange_deals {"symbol": "string"}
     open_company_overview {"symbol": "string"}
     open_panel {"panel": "string"}
     option_chain {"symbol": "string"}
     portfolio_update_position {"position_id": "string"}
     price_data {"symbol": "string"}
     publish_brief {"markdown": "string"}
     research {"query": "string"}
     resolve_symbol {"query": "string"}
     save_screen {"name": "string"}
     sec_filing_content {"accession": "string", "identifier": "string"}
     set_chart_symbol {"symbol": "string"}
     web_search {"query": "string"}
     write_note {"scope": "string", "text": "string"}
```
End to end (a first call with invalid args, then a placeholder repair reply). The garbage args reach dispatch instead of the sentinel:
```
(E) _resolve_tool_events(fundamentals {symbol:123}) + repair reply {symbol:'string'} -> [('fundamentals', {'symbol': 'string'})]
```
I also re-ran the shard-2 verifier's script verbatim, extracted from `round-4/verifier/shard-2-raw/LEAD-014.txt`. Its output matches:
```
tools with properties: 54
full/fenced schema echo accepted: 0 []
placeholder echo {prop: <type-name>} accepted: 20
    analyst_history {"symbol": "string"}
    analyst_individual {"symbol": "string"}
    ask_user {"question": "string"}
    backtest_summary {"run_id": "string"}
    close_panel {"panel": "string"}
    corporate_actions {"symbol": "string"}
    earnings_call_transcript {"symbol": "string", "quarter": "string"}
    earnings_estimates {"symbol": "string"}
    earnings_history {"symbol": "string"}
    focus_panel {"panel": "string"}
    fundamentals {"symbol": "string"}
    open_company_overview {"symbol": "string", "highlight": "string"}
properties-only echo accepted: 0
```

## 3. Where the verifier over-reached
`adv-lead014.txt` counts `news` + `'{}'` as "placeholder-echo(required) ACCEPTED". `news` has no required keys, so `{}` is a legitimate
zero-argument call, not an echo. This is correctly accepted:
```
(C) news required: None | repair reply '{}' -> {}
(D) legit fundamentals -> {'symbol': 'AAPL'}
(D) legit resolve_symbol -> {'query': 'Tata Steel'}
(D) legit price_data -> {'symbol': 'SPY'}
```
That one sub-point is a verifier error. It does not change the finding, because the other placeholder cases reproduce on 20 + 17 tools.

## 4. User impact (severity)
The placeholder args are not inert. `resolve_symbol {"query": "string"}` is one of the accepted echoes, and against my own HEAD sidecar
`curl "http://127.0.0.1:52405/resolve?q=string"` returns:
```
{"ok":true,"query":"string",...,"resolved":{"symbol":"META","name":"String Metaverse Ltd","exchange":"BSE",...,"confidence":0.97,...
```
So a placeholder echo resolves to a real, unrelated company at 0.97 confidence. `write_note {"scope":"string","text":"string"}` and
`portfolio_update_position {"position_id":"string"}` are also accepted (writes still stage for review). The trigger is conditional: a hosted
OpenAI-compatible lane, a first call with invalid args, and a placeholder echo in the repair reply. The model also sees the wrong name in the result.
Severity stays **medium** (a stated safeguard degraded, conditional path), the same as the shard and the verifier.

## 5. Fix simulation (not applied)
`agent-llm-R15-LEAD-014-raw/lead014_fixsim.py`: treat a reply as an echo when any string value equals its own property's declared JSON type name.
```
placeholder echoes caught: 102 missed: 0
legit false positives: []
```

## Verdict: partial
The entry's own repro (the full schema echoed back) stays fixed at HEAD. The placeholder-echo shape, which the entry's own fix_shape
names ("property names mapped to type-name placeholders"), is still accepted as real args. It is the same defect class
(unvalidated-repair-output, same function) and part of the fix was never covered, so the verdict is partial on R15-LEAD-014.
Certification failures: baseline 0 (the register note has no count clause, and the id appears in no batch not_certified list and in no
prior audit regression_confirmed or partial verdict), +1 for this partial = **1**.

End-of-audit check (07:01 IST): `git diff --name-only 01015033 HEAD | grep -v ^docs/` now prints `CHANGELOG.md`. It was touched only by the lead ledger commit d76a61be (docs(changelog)), made during the audit. `git diff --name-only 01015033 HEAD -- sidecar src src-tauri types plugins scripts` is empty, so the code audited equals 01015033. My own sidecar (pid group 75957, then 80594) and the ollama tap (80490) were stopped by pid group. The ports 52405/52406 are free.

# lows-P2/agent-tools-catalog-ledger (set-76) — rc1-battery-14 at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-028 | ls/grep for registry_v0_6_5 and its two boot-path wirings | module file gone; app.py:212 / main.py:51 call register_v0_6_0_tools() inlined in __init__.py; only a forbidden-module list in test_no_trading_surface.py names it | holds |
| R15-CODE-AGENT-027 | in-process: register a second tool then reset_for_tests() | reset restores snapshot `_IMPORT_TIME_TOOLS=['backtest_summary']`, extra tool dropped, backtest_summary kept; KNOWN_STATUSES now documented as verbatim-stored (action_ledger.py:59) | holds |
| R15-CODE-AGENT-014 | in-process invoke_tool with raising handler / ProviderError handler; grep leftover envelopes | single spelling "unexpected error: kaboom" / "provider error: upstream 503"; 'news fetch failed' prefix gone; remaining per-file ProviderError catches are in market_overview/fundamentals/screener/compare (own semantics) | holds |
| R15-AGENT-068 | in-process invoke_tool('earnings_upcoming',{'days':'seven'}) | {"ok": false, "error": "days must be in [1, 60]"} (also 999); None -> ok | holds |
| R15-CODE-AGENT-015 | in-process: stub provider, sec_filings_list / sec_insider_transactions limit 100000,-1,0,'x',None,15 | provider saw 100,1,1,20/30,20/30,15 (clamped) | holds |
| R15-DATA-101 | in-process market_overview({'region':'GLOBAL'}) live | payload note "no index set for region 'GLOBAL' — showing the US proxy benchmark" | holds |

COVERAGE: 6/6 ids raw; no raw: none

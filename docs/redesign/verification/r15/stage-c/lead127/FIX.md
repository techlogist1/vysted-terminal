# R15-LEAD-127 fix — listing region reaches the price and fundamentals legs

Branch `r15-lead127-fix`, base `341bc72dfc06704d92ba296c632128f9570dfc83`. Sidecar only. Writer: Opus 5.5 (medium).
The fix follows the fix shape in `final-pass/XADV_TRIAGE.md`.

## Diff summary

| file | change |
|---|---|
| `sidecar/services/research/fast.py` | `snapshot_structured` takes a new `listing_region`. When it is set, the whole fan-out runs inside `config.set_request_region(listing_region)` … `finally reset_request_region`. That covers price, fundamentals and every witness leg. The old body becomes `_snapshot_legs`. The token is set before any `asyncio.gather`, and tasks and `to_thread` copy the context. `gather_fast` passes `target.region`. |
| `sidecar/services/research/iter.py` | Both snapshot callers (:401, :1016) pass `listing_region=target.region`. |
| `sidecar/services/agent_tools/deep_research.py` | The snapshot caller (:837) passes `listing_region=target.region`. |
| `sidecar/services/agent_tools/price_data.py` | `price_data` takes an optional `region`. New helpers: `listing_region(args)` accepts only US/IN/GLOBAL and ignores anything else, so `normalize_region` never turns a stray value into IN. `in_region(region, fetch)` scopes the region ContextVar around the fetch. |
| `sidecar/services/agent_tools/fundamentals.py` | `fundamentals` takes an optional `region`, scoped the same way. The scope covers the fetch, the retry and the canonicalization. |
| `sidecar/services/agent_tools/catalog.py` | Both schemas gain `region` (enum US/IN/GLOBAL). The description says to pass the region resolve_symbol returned when it differs from the session's. `TOOL_SCHEMAS`, the allow-list and the MCP surface derive from it. |
| `sidecar/tests/test_lead127_listing_region.py` | New, 14 cases (below). |

Omitting `region`/`listing_region` keeps today's behaviour exactly. `derive_semantics` still receives the session region, which it uses as context only.

Out of scope and untouched: the frontend, the figure guard, `_judge_clause`, `_NO_TOOL_CUE`, resolution_policy, `symbol_resolver.py`, `identity_crosscheck.py`, and LEAD-128 (the price leg still fetches history before the quote).

## Tests

- (a) Session IN. The real `resolve_symbol` runs, and a recording stub stands in for every other tool. `gather_fast` on Halliburton→HAL, Ferrari→RACE and Carnival→CCL binds each to US and runs `price_data` and `fundamentals` under `get_region()=='US'`. The control, Hindustan Aeronautics, stays IN. The ambient region is still IN afterwards. `snapshot_structured` with no `listing_region` keeps the ambient region.
- (b) Session IN. `fundamentals` and `price_data` called with `{symbol, region:'US'}` route through `provider_registry._effective_region` to US for HAL, RACE and PTC. The private resolvers are monkeypatched to record the routed region. Without `region`, the route stays IN. An unknown `region` ('NSE') is ignored and stays IN.
- (c) Fresh cases of the class: Ferrari (RACE) and Carnival (CCL) on the research path; RACE and PTC on the tools.
- A catalog case checks that both schemas expose `region` and that `symbol` is still the only required field.

### Fail before (fix files restored to the base, the new test run)

```
FAILED tests/test_lead127_listing_region.py::test_research_fetches_a_us_namesake_in_us_under_session_in[Halliburton-HAL]
FAILED tests/test_lead127_listing_region.py::test_research_fetches_a_us_namesake_in_us_under_session_in[Ferrari-RACE]
FAILED tests/test_lead127_listing_region.py::test_research_fetches_a_us_namesake_in_us_under_session_in[Carnival-CCL]
FAILED tests/test_lead127_listing_region.py::test_snapshot_without_listing_region_keeps_the_ambient_region
FAILED tests/test_lead127_listing_region.py::test_fundamentals_region_arg_routes_the_us_listing[HAL]
FAILED tests/test_lead127_listing_region.py::test_fundamentals_region_arg_routes_the_us_listing[RACE]
FAILED tests/test_lead127_listing_region.py::test_fundamentals_region_arg_routes_the_us_listing[PTC]
FAILED tests/test_lead127_listing_region.py::test_price_data_region_arg_routes_the_us_listing[HAL]
FAILED tests/test_lead127_listing_region.py::test_price_data_region_arg_routes_the_us_listing[RACE]
FAILED tests/test_lead127_listing_region.py::test_price_data_region_arg_routes_the_us_listing[PTC]
FAILED tests/test_lead127_listing_region.py::test_catalog_exposes_the_region_arg_on_both_tools
11 failed, 3 passed, 1 warning in 1.76s
```

The 3 cases that pass on the base are the controls: the IN listing stays IN, and an omitted or unknown region keeps the session's.

### Pass after

```
$ .venv/bin/python -m pytest tests/test_lead127_listing_region.py tests/test_research_fast.py tests/test_price_data.py tests/test_fundamentals_tool.py tests/test_capability_catalog.py tests/test_mcp_catalog_parity.py tests/test_no_trading_surface.py -q
109 passed, 1 warning in 19.83s

$ .venv/bin/python -m pytest tests -q
3935 passed, 1 skipped, 4 warnings in 226.37s (0:03:46)
EXIT=0

$ ruff format <7 changed files>   -> 7 files left unchanged
$ ruff format --check .           -> 454 files already formatted
$ ruff check .                    -> All checks passed!   (ruff 0.15.12, sidecar venv)
```

`test_capability_catalog.py` and `test_mcp_catalog_parity.py` pass unchanged.

## Not done here

Acceptance (d), the live certification on an own sidecar (`research {query:'Ferrari'}` under IN shows the USD quote and Ferrari's fundamentals), is left to the certifier.

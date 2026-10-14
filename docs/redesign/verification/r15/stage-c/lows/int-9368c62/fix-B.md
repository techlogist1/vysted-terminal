# lows-fix-B (cluster B) on lows-int candidate 2dbcde70

Writer: Opus 5.5. Branch worktree-agent-lows-fix-B-9368c62. Stamped 04:18 IST. Discriminator range 4c6dfe8c..9368c626.

## Per test

### test_research_deep.py: test_run_researcher_drops_off_entity_news_for_a_non_in_equity_target, test_run_researcher_drops_common_word_ticker_region_news, test_run_researcher_drops_acronym_ticker_region_news
- Verdict: test_drift.
- Origin (004, certified rc1): `8eb855e3 fix(research): case-sensitive ticker news tags + off-entity gate for non-IN targets (R15-DATA-030, R15-RESEARCH-001)`, `79d63896 fix(research): gate non-IN short-token entity signals and drop sector words from brands (R15-RESEARCH-001)`. deep.py had no 004 change touching the drop gate in range.
- Cause: P1 `84c912e6 refactor(research): make deep's shared round helpers public exports (R15-CODE-RESEARCH-005)` renamed `deep._run_researcher` to `deep.run_researcher` and updated every caller it could see; the 004 tests arrived later and still call the old private name. The drop-news behaviour itself survived the merge.
- Action: the three call sites (and one docstring) now say `deep.run_researcher`. No assertion touched. No alias added in deep.py (would reintroduce the private surface P1's boundary audit removes).

### test_research_module_boundary.py::test_no_research_module_imports_a_private_name_across_modules
- Verdict: test_drift.
- Origin: no 004 change in range (test from P1 84c912e6; code from P2 `feba1762 fix(research): collapse the Perplexity and OpenRouter Sonar lanes onto one shared class (R15-CODE-RESEARCH-008)`).
- Cause: P2's collapse made sonar.py import `perplexity._domain_of` and `perplexity._HostedResearchLane`, the exact cross-module private import P1's audit forbids.
- Action: renamed them public (`domain_of`, `HostedResearchLane`) in perplexity.py, added both to its `__all__`, updated sonar.py and one docstring in test_research_hosted_lanes.py. Pure rename, no behaviour change.

### test_search_registry.py::test_resolve_ddg_is_unconditional_keyless_floor
- Verdict: merge_defect (pinned pre-existing behaviour, test untouched; P3 lane change repaired in place, not reverted).
- Origin: test unchanged in range and since; code from P3 `7d6be0f4 fix(search): remove duplicate ddg pacing + surface 403-then-429 as rate-limited (R15-CODE-RESEARCH-009, R15-RESEARCH-039)`.
- Cause: P3 made `resolve("ddg")` return a generic `_PacedBackend` wrapper, so the floor is no longer a `DdgSearchBackend`.
- Action: registry `_build_ddg` returns a `DdgSearchBackend` subclass whose `search()` routes through `_PacedBackend(super(), engine_id="ddg")`: still one pacing slot per whole search (checked directly: `acquires == ['ddg']`, isinstance True), `_PacedBackend` and P3's test_ddg_backend pacing test kept as is. The 403-then-429 fix is untouched.

### test_workspace.py::test_any_name_round_trips[a%41]
- Verdict: test_drift.
- Origin: no 004 change in range; the a%41 case is P2's own `c10c274a fix(sidecar): keep legacy-stem workspaces loadable and escape % (R15-UI-082, P2 fix pass)`.
- Cause: not the store. Starlette's TestClient (1.0.0 and 1.7.0, `testclient.py` `"path": unquote(path)` over httpx's already-decoded `url.path`) decodes the path twice, so `/workspace/a%2541` reaches the router as `aA`. A real server decodes once: the live run below shows save, list, load and delete of `a%41` all correct on the unmodified router and store. P2's case was red on its own candidate too.
- Action: the test URL encodes the segment twice so the router receives exactly `name` under TestClient (a comment says why). Every assertion unchanged, all five params pass. No product change.

## Also confirmed (004 behaviour kept)
- 73ab5881 (brave/mojeek parse hook late-bound) and the P3 html_serp port of R15-RESEARCH-022 (cd1c0f0c): test_brave_backend, test_mojeek_backend, test_keyless_backend, test_b7_research_result_limit all pass in the run below.

## Verification
- Focused: 6 passed (every id PASSED).
- Whole files plus every test importing a changed module (38 files: research deep/iter/verify/disclosures/r8/r9/funnel/hosted lanes/sonar/perplexity/tools/finance/boundary, search registry/ddg/brave/mojeek/keyless/pacing/breaker/transport/searxng/web_search/result_limit, workspace, app, mcp, catalog, schema): 575 passed, 0 failed.
- ruff format --check sidecar: 453 files already formatted; ruff check sidecar: All checks passed.

## Live (own sidecar, port 52392, VYSTED_DATA_DIR under the scratch dir; stopped after)

```
$ curl -X POST http://127.0.0.1:52392/workspace -d '{"name":"a%41",...}'
{"status":"saved","name":"a%41"} http=200
$ curl http://127.0.0.1:52392/workspace
["a%41"] http=200
$ curl http://127.0.0.1:52392/workspace/a%2541
{"name":"a%41","layout":{"grid":{"root":{}}},"enabledModules":{"chart":true}} http=200
$ curl http://127.0.0.1:52392/workspace/aA
{"detail":"Workspace 'aA' not found."} http=404
$ ls data workspaces
a%2541.vysted-workspace
$ curl -X DELETE http://127.0.0.1:52392/workspace/a%2541
 http=204
$ curl http://127.0.0.1:52392/workspace
[] http=200
```

Counts: 7 calls, all expected (save 200, list 1, load 200 body matches, aA 404, file stem a%2541, delete 204, list 0).

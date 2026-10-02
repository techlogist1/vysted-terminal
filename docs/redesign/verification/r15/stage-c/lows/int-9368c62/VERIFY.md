# lows-int-verifier: worktree-agent-lows-int-9368c62 at d3509715

Verifier: Opus 5.5 (fresh, did not write or merge any of this). Started 04:31 IST, written 04:46 IST, 3 Oct.
Checkout: detached worktree `<scratch>/lows-int-verify` at `d3509715f4e51f713cdbeaf7b00edc0ade5c65c0`.
Sidecar: my own, `main.py --port 52395`, `VYSTED_DATA_DIR` under my scratch dir, stopped at 04:44 IST.
Raw evidence: `verify/` next to this file.

## Verdict

**CERTIFIED.** LEAD-116 holds on the running code (31 of 34 row checks are byte-equal; the 3 that are not are shareholding cells, with the same scrip, quarters, filings and XBRL links, explained below). Gate 8 holds. Chain: one ci-local run with EXIT=0, smoke EXIT=0. Must-pass: 19/19. Lows: 1314 of 1314 tests pass and 0 named node ids are missing. No entries were reverted (list `[]`), so there was nothing to confirm absent.

## 1. R15-LEAD-116 (live, own sidecar, header `X-Vysted-Region: IN`)

Command: `verify/run.py`. It calls `curl -s -H "X-Vysted-Region: IN" http://127.0.0.1:52395/disclosures/<lane>?symbol=<s>` for 5 lanes × 22 symbols and compares the full row lists. Each response is saved in `verify/json/`. Full output is in `verify/run.out`.

I got the BSE scrip codes from `symbol_resolver.bse_scrip_code` in the venv: FOCUS 543312, KALYANI 544023, RAJPUTANA 539090, MAL 531613, SEL 509423, ZEAL 539963. For all six, `dual_listed_bse_code` is None. For AMAL, both functions return 506597.

| case | announcements | results | shareholding | corporate-actions | deals |
|---|---|---|---|---|---|
| FOCUS.BO == 543312 | True (23) | True (10) | True (12) | True (5) | True (39) |
| KALYANI.BO == 544023 (held-out) | True (28) | True (8) | identity True, cells differ (11) | True (0, both empty) | True (31) |
| RAJPUTANA.BO == 539090 (held-out) | True (25) | True (10) | identity True, cells differ (47) | True (1) | True (25) |
| MAL.BO == 531613 (held-out) | True (23) | True (10) | True (101) | True (2) | True (2) |
| SEL.BO == 509423 (held-out) | True (27) | True (10) | True (93) | True (6) | True (10) |
| ZEAL.BO == 539963 (held-out) | True (48) | True (10) | identity True, cells differ (37) | True (2) | True (23) |
| AMAL.BO == AMAL, sources NSE+BSE, sym AMAL, no note | True | True | True | True | True |

Excerpt (`run.out`):

```
announcements      FOCUS.BO   n=  23 cov=covered sym=543312 sources=['BSE'] note=''
announcements      543312     n=  23 cov=covered sym=543312 sources=['BSE'] note=''
announcements      FOCUS      n=  44 cov=covered sym=FOCUS sources=['NSE'] note='BSE FOCUS is a different company; only the NSE feed is served'
announcements      KALYANI.BO n=  28 cov=covered sym=544023 sources=['BSE'] note=''
announcements      KALYANI    n=  47 cov=covered sym=KALYANI sources=['NSE'] note='BSE KALYANI is a different company; only the NSE feed is served'
announcements      AMAL.BO    n=  21 cov=covered sym=AMAL sources=['NSE', 'BSE'] note=''
announcements      INFY.NS    n=  50 cov=covered sym=INFY sources=['NSE', 'BSE'] note=''
announcements      HDFCBANK   n=  50 cov=covered sym=HDFCBANK sources=['NSE', 'BSE'] note=''
deals              ZEAL.BO    n=  23 cov=covered sym=539963 sources=['BSE bulk', 'BSE block'] note=''
deals              ZEAL       n=   0 cov=covered sym=ZEAL sources=['NSE bulk', 'NSE block', 'NSE sast'] note='BSE ZEAL is a different company; only the NSE feed is served'
```

Bare `<name>` for all six collision names: every lane serves NSE only (`sources` NSE-only; shareholding `sym=<name>`) and carries the note "BSE <name> is a different company; only the NSE feed is served". INFY.NS and HDFCBANK merge both exchanges in announcements, results, corporate-actions and deals (shareholding is NSE plus the BSE split, with no note).

**The three shareholding cell differences.** `verify/shareholding_identity.out` covers KALYANI.BO/544023, RAJPUTANA.BO/539090 and ZEAL.BO/539963. For each pair these fields are equal on every row: quarter_end, submission_date, xbrl_url, source and symbol. `major_shareholders` is also equal and both sides are `sources ['BSE']`. Only the percentage cells differ (promoter/fii/dii/public/split/pledge). Some quarters are null on one side and filled on the other, and this goes both ways. A sequential re-run (`verify/rerun_shareholding.out`) is stable per spelling, so each response is cached. A direct call to the lane with no router cache, `corporate_disclosures._bse_shareholding("539963")` twice (`verify/shareholding_determinism.out`), gives `null-promoter= [17, 9] identical= False`. So the BSE SEBI-XBRL lane itself returns different cells call to call: `bse_provider.get_shareholding` has a per-call `_MAX_SHP_XBRL_PARSES` budget, and its docstring says "the warm cache fills them in over sessions". The router caches `FOCUS.BO` and `543312` under separate keys, so the two spellings froze at different fill points. Both spellings route to the same scrip and the same lane, so the routing claim holds. I count these as passes on row identity and record them as an adjacent LOW (below).

The LEAD-059 tests are unedited (the base..candidate diff of `test_corporate_disclosures.py` is 137 additions and 0 deletions, and `test_disclosure_tools.py` has no diff). All are green (`verify/lead059-tests.out`):
`test_lanes_are_anchored_on_one_company_not_the_ticker`, `test_announcements_never_merge_another_companys_bse_feed`, `test_true_dual_listing_still_merges_without_a_note`, `test_shareholding_never_falls_back_to_another_companys_bse_patterns`, `test_disclosure_tools.py::test_class_case_deals_and_actions_gate_the_same_way_amal_bo_still_served`: 5 passed.
The fix's `symbol_resolver.pinned_other_company_bse_code` decides "different company" from the names (`_bse_row_is_same_company`) and does not consult `dual_listed_bse_code`, as the brief requires.

**R15-LEAD-117 was not taken** (WRITER.md: "more than one line"). Live: `announcements?symbol=FOCUS&exchange=BSE` -> `venue_not_covered`, "FOCUS is not listed on BSE, so its BSE feed does not cover it". KALYANI returns the same. It stays open as registered.

## 2. Gate 8

```
$ PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_no_trading_surface.py
8 passed, 1 warning in 0.78s

$ git diff --stat 9368c626 d3509715 -- src/store/proposed-changes.ts types/proposed-change.ts sidecar/tests/test_no_trading_surface.py docs/SAFETY_ARCHITECTURE.md types/plugin.ts
 docs/SAFETY_ARCHITECTURE.md   | 9 +++++----
 src/store/proposed-changes.ts | 7 +++----
 2 files changed, 8 insertions(+), 8 deletions(-)
```

- `docs/SAFETY_ARCHITECTURE.md`: this is only the R15-DOCS-025 sentence (48314633). The AUTO-autonomy paragraph now names `AUTO_APPLIED_KINDS` (panel, chart, watchlist) and says data-write/settings always wait.
- `src/store/proposed-changes.ts`: the +/- lines are identical to 1860dbce's change to the file (`diff` of the two hunks' changed lines is empty). The change drops the `publishAckStatus` import, and `accept()` now acks `status` from `applyIntentAsync` with `ok = status !== "failed"`. That is R15-CODE-FRONTEND-034, which the lead ruled equivalent, and nothing else.
- `types/proposed-change.ts`, `test_no_trading_surface.py` and `types/plugin.ts` have no diff.

## 3. Chain (not re-run)

The round-2 logs are not in the commit: `.gitignore:34 *.log` matches them, so `logs/round-2/` does not exist in my worktree. I read them read-only from the integrator's worktree `<scratch>/lows-int`, whose HEAD is `d3509715`. The chain ran on 92fb7d40, and d3509715 adds only INTEGRATION.md. Tails are saved in `verify/chain-tails.txt`.

ci-local.log (exactly one `> vysted-terminal@0.9.0 ci-local` invocation; vitest `169 passed (169)` files / `2031 passed`, cargo `31 passed`, ruff "All checks passed!", `453 files already formatted`):

```
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  <scratch>/lows-int/sidecar/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/test_mcp_client.py::test_open_against_a_closed_port_raises_provider_error
tests/test_openbb_mcp_provider.py::test_dead_child_falls_through_and_reports_unavailable
tests/test_openbb_mcp_provider.py::test_dead_child_falls_through_and_reports_unavailable
  /opt/homebrew/Cellar/python@3.13/3.13.13_1/Frameworks/Python.framework/Versions/3.13/lib/python3.13/contextlib.py:109: DeprecationWarning: Use `streamable_http_client` instead.
    self.gen = func(*args, **kwds)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========== 3921 passed, 1 skipped, 4 warnings in 219.24s (0:03:39) ============
EXIT=0
```

smoke.log:

```
[smoke] /history/ICONIKSPEV OK (26 EOD bars, provider=bse).
[smoke] vysted-sidecar version OK (0.9.0).
[smoke] vysted-sidecar screener universe OK.
[smoke] vysted-sidecar ICONIKSPEV resolution OK (deterministic BSE identity).
[smoke] vysted-sidecar /agents roster OK (13 agents).
[smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=39).
[smoke] vysted-openbb-mcp-sidecar: spawning on :60525 (no-watchdog), probing port bind ...
[smoke] vysted-openbb-mcp-sidecar OK (bound :60525, survived settle window).
[smoke] vysted-sec-edgar-mcp-sidecar: spawning on :60985 (no-watchdog), probing port bind ...
[smoke] vysted-sec-edgar-mcp-sidecar OK (bound :60985, survived settle window).
[smoke] skipping live-exchange probes (pass --require-network, or run `pnpm probe:exchanges`, to include them).

[smoke] all sidecars booted cleanly.
[smoke] ATTENDED-SAFE: this run spawned and fully tore down 3 child process(es) on freshly-picked ephemeral ports: ...
EXIT=0
```

Side effect: the run's vitest coverage `autoUpdate` rewrote `vitest.config.ts` (`lines: 0` -> `lines: 81.4`) in the integrator's worktree, and that change is left uncommitted. The candidate keeps `lines: 0`. See adjacent finding 2.

## 4. Must-pass (the 19 ids red in round 1)

The 16 pytest ids are taken verbatim from round-1 `lows-int-pytest.log` `FAILED` lines (`verify/mustpass-pytest.txt`). They are the ids INTEGRATION.md lists.
`pytest -p no:randomly -v <16 ids>` -> `16 passed, 1 warning in 2.62s`, EXIT=0 (`verify/mustpass-pytest.out`).
The 3 vitest ids (`verify/mustpass-vitest.out`):

```
 ✓ src/modules/quant/YieldCurvePanel.test.tsx > YieldCurvePanel > R15-UI-077: two instruments on the same pillar names the duplicate and blocks the POST
 ✓ src/modules/quant/OptionPricerPanel.test.tsx > OptionPricerPanel > R15-CODE-PLATFORM-041: steps below the shared floor blocks submit with a message before the POST
 ✓ src/modules/agent-builder/agent-builder.test.tsx > AgentBuilderPanel > POSTs the payload and refreshes the list on save
      Tests  3 passed | 27 skipped (30)
```

**19/19.**

## 5. Lows entries

Sources: P1/P2/P3 `WRITERS.json` (outcome `fixed`: 184) and `remaining/REMAINING.json` (`fixed_untested`: 19), 203 entries in all, none reverted. I transcribed each free-text `test` field into node ids by hand in `verify/lows_spec.py`. A bare file name means `sidecar/tests/`. A `, ::name` continuation was expanded. Where only a file is named, the whole file runs. A named describe block counts all of its tests. 187 entries have named tests and 16 are untestable. The spec was cross-checked against the JSON id set: 0 missing, 0 extra.

- **pytest**, one call over 125 node ids (`verify/lows-py-ids.txt`): every id existed at collection, and the run gave `323 passed, 1 warning in 25.32s`, EXIT=0 (`verify/lows-py.out`, junit xml).
- **vitest**, one call over 64 files (`verify/lows-vt-files.txt`, JSON report `verify/lows-vt.json`): `991 passed, 0 failed`, EXIT=0. I matched 87 named-test specs against the report (`verify/match_vt.py` -> `verify/lows-vt-match.out`): `87 passed, 0 failed`. Eight writer-quoted titles were paraphrases, and in each case the real test exists and passed. Those eight were matched to their exact titles: R15-UI-078 (a describe with 5 tests), R15-CODE-PLATFORM-050, R15-UI-079, R15-AGENT-091, R15-CODE-PLATFORM-049, R15-UI-065, R15-CODE-DATA-016, R15-UI-066.
- **cargo**: these are named Rust tests. I found them in the chain's cargo output at this tree as `... ok`: `tests::write_atomic_text_and_bytes`, `tests::write_atomic_round_trip_leaves_no_tmp`, `keychain::tests::dev::migrate_with_erroring_reader_leaves_unmigrated_and_retries`, `keychain::tests::dev::on_wait_called_before_sleep`, `tests::no_env_mutation_in_src`, `tests::clear_mcp_endpoint_file_removes_existing` (LIFECYCLE-037 and PLATFORM-074), `tests::plain_tcp_listener_is_not_healthy`, `tests::smoke_bind_budget_matches_supervisor`, `tests::data_dir_override_wins_when_set_to_a_non_blank_value`.
- **Totals: 1314 run, 1314 passed, 0 failing, 0 missing node ids.**
- **Untestable (no named test):** R15-DOCS-007, R15-DOCS-009, R15-CODE-PLATFORM-060, R15-RELEASE-010, R15-DOCS-014, R15-DOCS-019, R15-DOCS-020, R15-DOCS-021, R15-DOCS-022, R15-DOCS-023 (docs-only); R15-DOCS-012 (fix shape asks for no pin); R15-CODE-PLATFORM-040 (deletion, grep only); R15-CODE-PLATFORM-058 ("cargo test --lib 22/22"; chain cargo green); R15-CODE-PLATFORM-059 (a clippy flag; chain clippy green); R15-DOCS-025 (doc-only); R15-CODE-PLATFORM-079 (config-only).

## Adjacent findings

1. **LOW: the same BSE scrip serves different shareholding percentages depending on how the symbol is spelled.** `KALYANI.BO` and `544023` (likewise RAJPUTANA and ZEAL) return the same quarters and filings, but some quarters' promoter/FII/DII/public cells are null under one spelling and filled under the other. This lasts for the cache TTL. Cause: `bse_provider.get_shareholding` spends a per-call XBRL parse budget (documented progressive fill), and `routers/disclosures.py` caches each normalized spelling separately (`disclosures:shareholding:{normalized}:{region}`). Evidence: `verify/shareholding_identity.out` and `verify/shareholding_determinism.out` (two direct lane calls for 539963: null counts 17 vs 9). This was pre-existing for any two spellings. LEAD-116 makes `<name>.BO` a second spelling of the scrip, which makes it reachable.
2. **LOW: the R15-RELEASE-011 coverage ratchet never ratchets in the repo.** `vitest.config.ts` ships `lines: 0, autoUpdate: true`. The green ci-local rewrote it to `lines: 81.4` in the integrator's worktree, and that change is uncommitted. Every fresh checkout (CI) therefore starts again at a 0 floor, and the gate cannot catch a regression unless someone commits the auto-updated value. Evidence: `git -C <scratch>/lows-int diff vitest.config.ts`.
3. **LOW (process): the chain evidence is not in the repo.** `.gitignore:34 *.log` excludes `logs/round-2/*.log`, so INTEGRATION.md's "Logs: logs/round-2/" points at files that exist only in one scratch worktree. The tails are preserved in `verify/chain-tails.txt` (with sha256 prefixes of the source logs).

## Process note

When I stopped my sidecar, I first killed my own pid (27547). I then ran `pkill -f "tail -f /dev/null" -P 1` to reap my stdin feeder, and that pattern could also have matched another agent's orphaned feeder. Afterwards no `main.py --port` sidecar and no Python listener was running on the machine. I cannot tell whether one was running before.

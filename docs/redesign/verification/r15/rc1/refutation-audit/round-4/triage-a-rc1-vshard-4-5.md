# triage-a: rc1-vshard-4:5, a Mojeek captcha page counts as a healthy empty answer

Auditor: Opus, group `triage-a`. Written 07:42 IST.

- HEAD: bed3b166. The code tree equals 01015033.
- In-process runs use `sidecar/.venv/bin/python` with `PYTHONPATH=.`, `VYSTED_DATA_DIR=<scratch>/data-inproc` and `VYSTED_REGION=US`, from `sidecar/`.
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.

## Verdict

**partial on R15-RESEARCH-022.**

- The shard also tied this to R15-CODE-AGENT-008. That entry's class is `layer-leak` in the auto-publish decoding, so it is not the tie.
- Severity: **medium**, the same as the shard.
- Certification failures: 1 (baseline 0, plus 1 for this verdict).

## Live at HEAD

The upstream serves the challenge page right now:

```
curl -s -A "Mozilla/5.0 ... Chrome/124.0 ..." "https://www.mojeek.com/search?q=Amalgamated+Financial+earnings"
-> HTTP 200 bytes 5519
   visible text: "Captcha ... JavaScript is required to complete this challenge. Please enable it and reload the page."
```

Next, the real Mojeek adapter inside the real keyless rotation (`mojeek_captcha.py`). I recorded one breaker failure first, so that a wrongly recorded success would visibly reset the count:

```
raw mojeek status 200 captcha True js-challenge True
breaker before: closed failures 1
keyless result: OK results 0 backend keyless
breaker after: closed failures 0
```

Then each engine on its own (`engines_each.py`), followed by the whole `web_search` agent tool (`websearch_tool.py`):

```
ddg    -> SearchError unreachable ...
brave  -> SearchError rate_limited Brave HTML search is blocking/rate-limiting right now (HTTP 429)
mojeek -> SearchResponse rows 0
web_search ok= True backend= keyless-fallback n_results= 0 reason= searxng_degraded note= None error= None
```

At this moment all three keyless engines are blocked or unreachable, yet the tool reports a healthy "found nothing". Research then marks the web leg as available with 0 sources. The shard observed exactly that in 4/4 NORMAL briefs.

## Root cause

- `sidecar/services/search/mojeek.py:114-128` treats only 403 and 429 as a block. A 200 is parsed by `_parse` (`:123`), and a challenge page parses to zero rows, which the module docstring (`:12`) calls "empty successful response".
- `sidecar/services/search/keyless.py:196-206`: `_filter_results([])` returns `blocked=0`, so the `if blocked and not results` branch never fires. Execution continues to `breaker.record_success()` (`:205`) and `any_engine_answered = True` (`:206`).
- `:227-230` then returns an empty `SearchResponse` instead of raising the typed `rate_limited` error.
- `INTERSTITIAL_MARKERS` (`:79-84`) are applied only to parsed result rows, never to a page that parsed to zero rows.

## Why partial on RESEARCH-022

R15-RESEARCH-022 is fixed; batch-7 certified it. Its class is `keyless-breaker-accounting`.

- Title: "A 200-status CAPTCHA/block page from a keyless engine is recorded as a healthy empty answer and resets that engine's circuit breaker ... an all-blocked search reports 'found nothing' instead of 'rate-limited'".
- fix_shape: "when non-empty rows filter to zero **(or a 200 parses to zero rows with block markers)**, call record_failure(), note 'blocked (challenge page)' and don't set any_engine_answered".

The entry's stated repro still holds. Its stub, a DDG challenge row, now raises. I ran the pinned tests at HEAD: `pytest tests/test_keyless_backend.py -k "challenge or block or interstitial"` gave 3 passed, including `test_a_200_challenge_page_counts_as_a_failure_not_an_answer`.

The parenthetical clause of the fix_shape, a 200 that parses to zero rows with block markers, was never implemented. The live Mojeek captcha is exactly that case, and it reproduces every symptom the title lists:

- the breaker was reset (1 to 0);
- the tool returned a healthy empty;
- an all-blocked search reported "found nothing".

The register note already carries a batch-8 residual of the same shape on SearXNG. No other entry covers Mojeek.

## Severity

Medium: a stated feature is degraded. Blocked web search is reported as "nothing found", so research proceeds with 0 web sources and no rate-limit note. Waiting or retrying is the workaround.

## Certification failures

R15-RESEARCH-022 baseline is 0:

- its note has no "certification failures so far" clause;
- it is not in any `not_certified` list;
- no audit partial or regression verdict.

Adding this partial gives **1**.

## Fix shape

In `MojeekSearchBackend.search` (mojeek.py), after `_parse` returns no rows on a 200:

- Check the raw page text for challenge markers: the keyless `INTERSTITIAL_MARKERS` plus the page-level markers "captcha" and "complete this challenge".
- If one is present, raise `SearchError("Mojeek: blocked (challenge page)", reason=SEARCH_REASON_RATE_LIMITED)`.

The keyless loop already counts a `SearchError` against the breaker and keeps `any_engine_answered` false. The all-blocked case then raises the typed `rate_limited` error with each engine's state.

## Acceptance test

In `sidecar/tests/test_mojeek_backend.py`, give a stub fetch a 200 whose body is the challenge page ("Captcha ... JavaScript is required to complete this challenge."). Assert:

- `MojeekSearchBackend(fetch=stub).search('x')` raises `SearchError` with `reason == 'rate_limited'`.

In `sidecar/tests/test_keyless_backend.py`, use `KeylessSearchBackend(engines={'mojeek': MojeekSearchBackend(fetch=stub)})` and assert:

- `search` raises `SearchError(rate_limited)` naming "Mojeek: blocked (challenge page)";
- `breaker_for('mojeek')._failures` increments instead of resetting.

Live re-proof, while Mojeek serves the challenge: `PYTHONPATH=. VYSTED_REGION=US sidecar/.venv/bin/python mojeek_captcha.py` must print `keyless result: SearchError rate_limited` and `failures 2`.

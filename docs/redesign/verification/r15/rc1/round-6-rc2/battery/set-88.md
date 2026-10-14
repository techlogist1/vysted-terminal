# Set: lows-P2/research-extraction-synthesis (set-88) — candidate ace7dd76, sidecar :52345

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-RESEARCH-007 | in-process derive_semantics (rich fixture) vs types/brief.ts | 4 keys emitted AND declared in BriefDerivedMetrics; emitted-not-declared = [] (pinned test `test_emitted_keys_subset_of_brief_ts_mirror`) | holds |
| R15-RESEARCH-036 | in-process emitted keys vs semantics._PROMPT_KEYS | 17 emitted keys, _PROMPT_KEYS has 18, emitted-not-in-prompt = [] (pinned `test_prompt_keys_cover_every_derived_metric`) | holds |
| R15-CODE-RESEARCH-011 | in-process return annotations of every `_*_leg` | all 7 legs (incl. _dividend_leg, _dividend_ttm_leg) annotate tuple[dict, list[dict]] (pinned `test_every_leg_returns_facts_and_conflicts`) | holds |
| R15-CODE-RESEARCH-008 | in-process both hosted lanes via httpx MockTransport for 401/402/403/429/400/500/503 | Perplexity 402 -> "reports insufficient credits ..." same as OpenRouter; no generic "failed with HTTP 402"; no key/JSON leak | holds |

COVERAGE: 4/4 ids raw; no raw: none

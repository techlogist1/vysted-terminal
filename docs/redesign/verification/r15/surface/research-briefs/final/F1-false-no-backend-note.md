# F1 — FAST brief says "No web-search backend configured" while the keyless backend is configured and only cooling down

Head d38b5d1a (final-cand). Own source sidecar 127.0.0.1:52344.

## Live (app)
1. While another research run on the same sidecar was searching (03b ULTRA, 4 parallel research calls), ran
   `turn.py --port 52344 --provider ollama --model llama3.1:8b --depth normal --prompt 'Give me a quick research brief on Sonata Software.'`
   (`02-normal-sonata-llama-keptprev.stdout.txt`). Steps: `searching the web for Sonata Software Limited` -> `no web backend — structured only` (status skipped).
2. Published brief input: `'web_available': False, 'note': 'No web-search backend configured — structured data only', 'web_reason': 'unreachable'`.
3. Seconds later `GET :52344/search/status` -> `{"tier":"t1_keyless","available":false,"engines":[ddg "cooling down (4s)", brave "cooling down (35s)", mojeek "cooling down (36s)"]}` — the backend exists; every engine is benched by its breaker.
4. Panel (scratch jsdom harness, real streamAgentInvocation -> applyHostAction(publish_brief) -> <BriefPanel/>, `replay-02-sonata.json`):
   renders `Structured-data-only brief · No web-search backend configured — structured data only`.
   Same on run 04 (Mastek, `04-normal-mastek-llama-auto-keptprev.stdout.txt`).

## Deterministic (no network) — `08-breaker-skip-reason-repro.txt`
All three keyless breakers opened -> `KeylessSearchBackend.search()` raises
`SearchError reason= unreachable | keyless web search has no engine available right now — DuckDuckGo: cooling down (45s); Brave: cooling down (45s); Mojeek: cooling down (45s). Wait a moment and retry...`

## Mechanism (code at d38b5d1a)
- `sidecar/services/search/keyless.py:191-193`: a benched engine is skipped with note "cooling down" but `any_rate_limited` is not set.
- `keyless.py:235-240`: `reason=SEARCH_REASON_RATE_LIMITED if any_rate_limited else SEARCH_REASON_UNREACHABLE` -> all-benched = "unreachable".
- `sidecar/services/research/fast.py:535`: `web["note"] = _RATE_LIMITED_NOTE if reason == "rate_limited" else _NO_WEB_NOTE`;
  `fast.py:71` `_NO_WEB_NOTE = "No web-search backend configured — structured data only"`.
The engine's own message is honest ("cooling down ... wait a moment and retry"); the typed reason throws it away,
so the brief (and its banner) tells the user nothing is configured — the exact "symptom #2" false-banner the
fast.py docstring (`_web_round`, :515-517) says must not happen. Different path from R15-RESEARCH-039 (fixed: DDG
403->429 impersonate lane) and R15-RESEARCH-022 (open: 200 challenge page).

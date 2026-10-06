# rc1 drive — research-briefs (gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar
`127.0.0.1:52321` (`rc1-round-4-cand` source), data dir
`rc1-round-4-data-rc1-drive-research-briefs` (keyless copy of
`rc1-round-4-seed-data`). Full log:
`docs/redesign/verification/r15/rc1/round-4/logs/rc1-drive-research-briefs.md`.
Raw evidence: `docs/redesign/verification/r15/surface/research-briefs/rc1/round-4/`.

**Scope note (this round):** `git diff` from round-3's certified candidate
(`5903f373`) to this round's candidate (`1006c6da`) touches ZERO files under
`sidecar/services/research/`, `src/modules/research/`, `src/lib/host-actions.ts`,
`src/lib/brief-ingest.ts` — the only sidecar delta since round 3 is
`R15-LEAD-040` (resolver thread-pool routing) and `R15-DATA-117` (ADR P/B
withholding at the fundamentals-provider layer, checked against the brief's
null-drop rendering — no interaction, see log). Every round-3 verdict below is
therefore evidenced two ways: the code-diff (nothing to regress) AND, for the
higher-severity items, a fresh live run this round.

## Scored table — every register-tracked item this surface owns, round 3 → round 4

| # | Item | Register id | Severity | Round 4 score | Round 4 evidence |
|---|---|---|---|---|---|
| 1 | DEEP/ULTRA citations point at wrong documents | R15-RESEARCH-003 | high | **ok** | Live: CG Power DEEP (llama3.1:8b), `[7]` → `vysted://fundamentals/CGPOWER`, `price_to_book: 17.506767` matches exactly. `01-deep-cgpower-llama.jsonl` |
| 2 | Local-lane DEEP/ULTRA hits per-call cap, silently ships thin-coverage floor | R15-RESEARCH-005 | high | **ok** | Live: CG Power DEEP, real synthesis, `execution.degraded_reason: null`, `backend: keyless-fallback`, NOT the "web coverage is thin" floor text. `01-deep-cgpower-llama.jsonl` |
| 3 | ULTRA cross-check mangles every figure that starts a claim line | R15-RESEARCH-004 | high | **ok (code, unchanged)** | `sidecar/services/research/verify.py` `_split_claims`/`_CLAIM_MARKER` byte-identical to the round-3 certified candidate; round 3 already reconfirmed live on 3 independent model/depth runs |
| 4 | ULTRA cross-check prints AGREE for UNVERIFIED claims | R15-RESEARCH-002 | critical | **ok (code, unchanged)** | `verify._parse_verdict` byte-identical; round 3 reconfirmed live (Kaynes ULTRA, 5/5 correctly UNVERIFIED) |
| 5 | DEEP states rival's order-book win as target's own (critical) | R15-RESEARCH-001 | critical | **ok (code, unchanged)** | No diff to the news-relevance-gate files since round 3's live BDL-DEEP reconfirmation |
| 6 | SearXNG reports 'ready' while all engines CAPTCHA-blocked | R15-RESEARCH-028 | medium | **ok** | Live: `/search/searxng/status` → `state: degraded`, honest per-engine reasons (brave/duckduckgo/startpage). `03-searxng-status.json` |
| 7 | 'kept previous' divergence notice not recognised by chat | R15-UI-054 | medium | **ok (code, unchanged)** | `message-notices.ts` `isRuntimeNotice` structural check unchanged |
| 8 | ULTRA ships fabricated References/Merged Sources list | R15-RESEARCH-029 | medium | **ok (code, unchanged)** | `citecheck.strip_model_bibliography` unchanged; zero bibliography sections in this round's live run too |
| 9 | vysted:// sources render as external favicon links | R15-UI-080 | low | **open (expected, not a regression)** | `BriefPanel.tsx` `SourceRow`/`FaviconDot` unchanged; register status is `open` |
| 10 | Free-model 429 told as "wait a minute" (wrong for shared-pool) | R15-AGENT-027 | medium | **ok** | Live: `--bad-key` openai → "The OpenAI API key was rejected — check it in Settings." (401 branch). `04-badkey-humanize.txt` |
| 11 | Ollama tool_call_id `''` / constant `__autobrief` breaks host-action acks | R15-AGENT-046 | medium | **ok (code, unchanged)** | `agent_runtime.py:2894` mints a fresh uuid for every tool call, byte-identical |
| 12 | no-web-honest-banner can never fire | R15-RESEARCH-041 | low | **open (expected, not a regression)** | `host-actions.ts:287` unchanged. Register status is `open` |
| 13 | openbb-mcp child death → 500 + silent SSE death | R15-LIFECYCLE-005 | high | **ok (code, unchanged)** | Not re-induced (shared `:52153` out of scope, read-only); no diff to `mcp_client.py`/`streaming.ts` |
| 14 | Citation-integrity net only matches bare `[n]`; grouped/prose brackets ship unresolved | R15-RESEARCH-043 | medium | **blocked_tier4 (adjudicated, no fix round)** | `citecheck.py`/`brief-ingest.ts` regex byte-identical. NOT reproduced live this round (CG Power DEEP shipped zero non-numeric bracket tokens, unlike round 3's same repro) — no concurrence note needed from this round's evidence. Per lead note: never a fix round on this class. |

**14/14 held (12 ok, 2 correctly still open at low severity, 1 correctly
blocked_tier4/no-regression) — zero regressions, zero new register-worthy
defects found this round.**

## Findings

None. `docs/redesign/verification/r15/rc1/round-4/findings/rc1-drive-research-briefs.json`
is `[]`. One non-defect observation (a weak-local-model arithmetic/narration
slip on an otherwise-correctly-cited figure — "book value ... 53.00 Crore
[1]" doesn't reconcile with the structured `book_value` field) is logged in
the drive log for the record but not filed, per the census's precedent for
this same class of local-model narration noise (round-1 `EVIDENCE.md`).

## Known limitations carried forward (no fix round, per lead's standing rules)

- **R15-RESEARCH-043** (blocked_tier4, DECISIONS 4.14) — citation-marker
  grammar only matches bare `[n]`. Not reproduced live this round; still the
  documented limitation if it recurs.
- **R15-DATA-059** / **R15-RESEARCH-043** / **R15-DATA-002** — the three
  three-failure-rule entries this gate round's lead note calls out are not
  owned by this surface group (DATA-059/DATA-002 are data/watchlist-add
  surfaces); not re-litigated here.

## Sidecar

Boot: sleep pid 58058, worker 58061, health confirmed ok before and after the
live run. Stopped: `kill 58058` then `kill 58061` (worker didn't tear down
from the sleep-pid alone this time), confirmed down via failed `/health`.

# APOSD critique: error-layer

Worker model: `claude-opus-5-5[1m]`. This is a **verify-and-finish** pass (PROMPT_code_s2.md). The
critique below is built from the existing raw findings (`../raw/code-error-layer.json`, 15 findings,
prefix `COD-error-layer-`) and their refute verdicts (`../refute/code-error-layer.json`: 11 admitted,
4 admitted_with_correction, **0 refuted**). It is not re-derived from nothing. After that, all five
owning files were read fresh and hunted for gaps. Those findings are in `../raw/code-error-layer-2.json`
(4 findings, prefix `COD-error-layer-2-`) and are marked **NEW** below.

Skill `aposd-critique` was loaded and followed: two personas, 18 principles, and the specificity gate.
Assessment independence is **degraded (sequential)**. This worker has no sub-agent tool, so Assessment A
(Strategic Thinker) was finished before Assessment B (Tactical Tornado) ran. Snapshot persistence to
`.aposd/critique/` was skipped because it would write an unrequested file into the repo.

Scope: `sidecar/services/errors.py` (321 lines), `src/lib/sidecar-client.ts` (307),
`src/lib/use-sidecar-retry.ts` (149), `src/modules/chat/streaming.ts` (371) and
`src/modules/chat/message-notices.ts` (66), 1214 lines in total. I also read the callers that decide
whether their promises hold: `routers/llm.py`, `routers/agents.py`, every `services/llm/*` adapter's
except-clauses, `ChatSidebar.tsx` (send path, handlers, stop and queue), `store/chat-history.ts`,
`store/agent-runs.ts`, `MacroPanel.tsx`, `store/macro.ts` and `OnboardingFlow.tsx`.

Proofs for the NEW findings:
- `evidence/error-layer-2-proof.test.ts.txt`: a scratch vitest test with `getSidecarBaseUrl` mocked to
  reject. Neither stream function calls `onError`; both reject the caller.
- `evidence/error-layer-2-proof-output.txt`: `humanize()` probes run in the sidecar venv, plus live
  bogus-key calls to Gemini and xAI. Both providers return **400** for an invalid key.

## Tactical Tornado verdict: MEDIUM-HIGH risk

The layer's stated job is "the one place a raw failure becomes a typed, user-legible frame". It does
that job well for one case only: a remote LLM provider fails with a well-known HTTP status inside an
adapter. Everywhere else, structured facts are flattened into prose and re-parsed, or dropped.

The most damning pattern is **contracts held by matching English copy across a process boundary**.
Publish-divergence notices are recognised by a regex over sidecar prose that has already drifted: 2 of
the 3 notices are missed, and both test suites stay green (COD-error-layer-1). `research:begin` works the
same way (COD-error-layer-10). The router guards classify internal crashes by substring-matching
`str(exc)` (COD-error-layer-6).

The second pattern is **the error boundary drawn in the wrong place**:
- `sidecarGet` wraps the JSON parse but not the `fetch` (COD-error-layer-8).
- `dispatchFrame` wraps the consumer as well as the parser (COD-error-layer-11).
- The stream functions await the base URL outside the only try, so a readiness failure never reaches
  `onError` and the chat wedges (**NEW** COD-error-layer-2-1).

Red flags counted: 19.
- Information leakage ×5: divergence copy, research:begin, the error struct ×6 declarations,
  ProviderError→HTTP ×25 sites, and a second `/llm/keys/validate` client.
- Repetition ×3: 12 `LLMErrorEvent(message=_h.message…)` re-spellings, DeepSeek 402 copy twice, and the
  NewsFeed backoff copy.
- Special-general mixture ×3: DeepSeek-only branches while 429-credit, 400-context, 400-invalid-key and
  Ollama not-pulled have none.
- Comments that lie ×3: `sidecarGet` "BYOK Exa key", `:209-212` "error handling is uniform", `errors.py:16`
  "code … the frontend can branch on".
- Name that over-promises ×2: `useRetryOnSidecarReady`, `sidecarStatus`.
- Wrong-boundary exception aggregation ×3.

## Design principles score: 3 pass / 7 at-risk / 8 violate (3/18)

| #   | Principle                          | Grade   | Evidence (file:line : pattern)                                                                                                                                                                                                                                                                  | Consequence                                                                                                                                                  |
| --- | ---------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Strategic over tactical            | violate | `message-notices.ts:57` `DIVERGENCE_RE = /did not confirm the publish\|kept the previous, richer brief/i`, pinned by `message-notices.test.ts:29` while `agent_runtime.py:1023-1036` emits different copy; `streaming.ts:57` `RESEARCH_BEGIN_RE`                                                     | Each feature grabbed the nearest channel (the research-step telemetry string) instead of adding a field; 2 of 3 honesty notices are already lost (COD-1)  |
| 2   | Deep modules                       | at-risk | `errors.py:104-300` `humanize()` is deep (one call hides status resolution + classification); but `HumanError` must be re-spelled field-by-field into `LLMErrorEvent` at 12 sites (e.g. `anthropic.py:147-156`), and `sidecar-client.ts:154` exposes GET only                                    | The deep core sits behind a shallow edge; 79 fetch sites in 39 files hand-roll the rest (COD-3, COD-13)                                                    |
| 3   | Information hiding                 | violate | FastAPI error shape handled in `sidecar-client.ts:48-72` but re-parsed ad hoc in `delegate-runs.ts:107-115`, `AgentBuilderPanel.tsx:90-100`; `streaming.ts:216-219` passes raw body text                                                                                                        | `[object Object]` and raw `{"detail":…}` blobs still reach the user (COD-2, COD-3)                                                                          |
| 4   | General-purpose modules are deeper | violate | `sidecarGet<T>(path, params, headers)` (`sidecar-client.ts:154-158`) has no method/body/signal; `humanize` status table `errors.py:148-196` assumes OpenAI-shaped statuses (401 = bad key) that Gemini/xAI break (**NEW** 2-4)                                                                  | Every non-GET caller and every non-OpenAI provider is a special case outside the module                                                                     |
| 5   | Different layer, different abs.    | violate | Router guards `llm.py:141-145`, `agents.py:105-110` call `error_frame(exc)` with provider-language heuristics although adapters already humanise with their own id (`anthropic.py:147-156`, `ollama.py:180-192`)                                                                               | An internal sidecar bug is reported as "Could not reach the AI provider — check your network" (COD-6)                                                      |
| 6   | Pull complexity downward           | violate | `use-sidecar-retry.ts:24-28` makes every caller flatten its typed store error into a plain `throw new Error` (`MacroPanel.tsx:39-46`); `app.py:312-315` global handler drops `ProviderError.kind`, so 25 route sites re-map by hand                                                               | Callers cannot express "retryable", so the hook retries everything 13× (COD-9); throttles surface as 502 (COD-4)                                          |
| 7   | Better together / apart            | at-risk | `ProviderError` (data providers) and the LLM humaniser share `errors.py:26-40` but never meet: data-route failures get no humanisation; `validateProvider` (`sidecar-client.ts:226-243`) vs `KeyEntryDialog.tsx:175-189` are two clients of one endpoint                                         | Two unrelated concerns share a module while one concern is split across two clients (COD-7)                                                                |
| 8   | Define errors out of existence     | violate | `validateProvider` "never throws" by returning `false` for sidecar-down/5xx/transport (`sidecar-client.ts:235-242`); `consumeSseStream` treats EOF-without-`done` as success (`streaming.ts:225-249`); `finishReason` dropped (`ChatSidebar.tsx:2025-2030`, **NEW** 2-3)                         | A dead engine is shown as "no AI model set up" (COD-7); a hung turn spins forever (COD-11); a truncated answer is shown as complete (**NEW** 2-3)       |
| 9   | Design it twice                    | at-risk | Divergence notices and `research:begin` ride free-text `detail`; the typed alternative (a field on `LLMResearchStepEvent`, `models/llm.py:166-181`) was available and not taken                                                                                                                 | A regex contract that neither side's tests can see break                                                                                                   |
| 10  | Comments describe non-obvious      | violate | `sidecar-client.ts:175-179` "the BYOK Exa key … ride every request" (Exa lane dead; it is the OpenRouter key, COD-15); `:209-212` "so error handling is uniform" (fetch rejection is not wrapped, COD-8); `errors.py:16` "`code` … the frontend can branch on" (nothing does, COD-13)             | Comments steer the reader away from the real behaviour                                                                                                    |
| 11  | Comments first                     | at-risk | `use-sidecar-retry.ts:14-22` documents "re-arm on reconnect", but `sidecarStatus` is written only at boot (`store/app.ts:24-34`, single caller `page.tsx:52`)                                                                                                                                   | The interface comment promises a transition the system emits once per lifetime (COD-14)                                                                   |
| 12  | Choosing names                     | at-risk | `useRetryOnSidecarReady` retries any rejection (`use-sidecar-retry.ts:92-109`); `sidecarStatus: "connected"` is a boot latch; `unparseable SSE frame:` labels consumer exceptions (`streaming.ts:270`)                                                                                            | Names promise narrow conditions the code does not check                                                                                                   |
| 13  | Modifying existing code            | at-risk | R13 reworded `kept_previous` in `agent_runtime.py:958` without touching `message-notices.ts:57`; the content_filter notice (`agent_runtime.py:1485-1495`) was added without the sibling max_tokens/length case (**NEW** 2-3)                                                                   | Each increment fixed its own slice and left its twin behind                                                                                               |
| 14  | Consistency                        | violate | REST humanises `detail` (`sidecar-client.ts:197-204`), SSE does not (`streaming.ts:216-219`); 1 of 25 `except ProviderError` sites is kind-aware (`fundamentals.py:104-115`); `X-Vysted-Region` sent by 2 files                                                                                 | The same failure reads differently depending on transport and route                                                                                       |
| 15  | Code should be obvious             | at-risk | `normalizeEvent` (`streaming.ts:275-306`) reads as a pure snake→camel mapper but mutates the brief store via `feedBriefLifecycle` (`:304`); the `code` field is carried end-to-end and consumed nowhere                                                                                          | Readers debug the wrong layer (COD-11)                                                                                                                    |
| 16  | Design for the future              | pass    | `extractSidecarDetail` (`sidecar-client.ts:48-72`) handles both FastAPI shapes plus unknowns; `HumanError` adds `code` so frontend branching can be added without a wire change                                                                                                                  | The pieces needed to fix most findings already exist                                                                                                     |
| 17  | Performance as design              | at-risk | `sidecarGet` awaits `buildSearchHeaders()` on every GET, an unmemoised keychain IPC on tier_b (`sidecar-client.ts:180-185`, 5 s watchlist poll); no timeout/AbortSignal anywhere (`:131`, `:194`)                                                                                                | One hung socket holds the shared readiness promise for every panel (COD-12, COD-15)                                                                       |
| 18  | Increments are abstractions        | pass    | `error_frame()` (`errors.py:303-321`) is one wire-frame home for both SSE routers with a never-raise guard; `StreamErrorFrame` (`streaming.ts:30-39`) extended the frozen union without breaking legacy consumers                                                                                | R10 D43 landed as a reusable contract, not a one-off                                                                                                      |

Summary: **3 pass, 7 at-risk, 8 violate (3/18 pass).** Information leakage is scored in the Tactical
Tornado scan rather than as a principle. The shared-readiness promise (`getSidecarBaseUrl`,
`sidecar-client.ts:114-123`) also passes on its own terms, but it is folded into row 17's at-risk grade
because it has no timeout.

## What's working

- **`extractSidecarDetail`** (`sidecar-client.ts:48-72`) turns FastAPI's string and 422-array
  `detail` shapes into one sentence, with a fallback. It is the correct deep module. The problem is
  that only 2 files use it.
- **The HumanError split** (`message` / `action` / `detail` / `code`, `errors.py:71-83`). Raw
  provider text sits behind a toggle and never lands in the bubble. `error_frame` never raises.
  Once a failure reaches `humanize` with a status, the copy is good.
- **The shared, re-armable readiness promise** (`sidecar-client.ts:114-144`) and the hook's
  `inFlight`/`rerunRequested` coalescing (`use-sidecar-retry.ts:74-110`). These carefully keep
  N panels from firing doomed fetches at a cold sidecar.

## Priority issues (live, after refute)

- **[P1] Structured facts serialised into prose and re-parsed by regex across the process
  boundary.**
  - Principle: information hiding / strategic over tactical.
  - Symptom: unknown unknowns. Both suites pin their own copy, so the break is invisible.
  - Evidence: `message-notices.ts:57` vs `agent_runtime.py:1023-1036` (COD-1, medium, admitted);
    `streaming.ts:57` vs `research.py:56-72` (COD-10, low, admitted).
  - Fix: carry `notice_kind` and `run_id`/`depth`/`query` as typed fields on `LLMResearchStepEvent`
    and branch on the fields. Add one shared fixture asserted by both suites. Two designs were
    compared. (a) Fix the regex plus a shared fixture: cheap, but still copy-coupled. (b) Add a typed
    discriminator: removes the coupling. Recommend (b); it is a pydantic field plus a normalizeEvent
    line.
- **[P1] Error boundaries sit one await off, so failures escape the frame or get mislabelled.**
  - Principle: define errors out of existence (done wrong) / different layer.
  - Symptom: cognitive load and unknown unknowns.
  - Evidence:
    - `sidecar-client.ts:194-196`: fetch is unwrapped, so the user sees a bare "Load failed" (COD-8,
      medium).
    - `streaming.ts:263-271`: the consumer's throw is relabelled "unparseable SSE frame" (COD-11, low).
    - `streaming.ts:134,153`: the readiness rejection skips `onError`, leaving the message
      "streaming" forever, a dead Stop button and a queue that never drains (**NEW 2-1**, medium).
  - Fix: the stream functions do every await inside `consumeSseStream`'s try. `dispatchFrame`
    try-wraps only the parse. `sidecarGet` wraps the fetch into
    `SidecarError(0, "The data engine is not responding…")`. Track `sawTerminal` and synthesise an
    error at EOF.
- **[P1] Liveness is a boot latch, and retry has no predicate.**
  - Principle: pull complexity downward / naming.
  - Symptom: unknown unknowns. A green "Connected" chip shows over a dead engine.
  - Evidence: `store/app.ts:24-34` single writer (COD-14, medium); `use-sidecar-retry.ts:92-109`
    retries everything 13× (COD-9, medium); `validateProvider` collapses unreachable into
    "no model" (COD-7, medium, corrected: the Ollama adapter must change too).
  - Fix: make the error layer the writer of `sidecarStatus` (a connection failure writes `error`, any
    success writes `connected`) and add a click-to-reconnect on the chip. The hook then retries only
    while `sidecarStatus !== "connected"`. `validateProvider` returns
    `{ok, reason: "not_configured" | "unreachable"}`.
- **[P2] `humanize` is a status table with DeepSeek special cases, but it gives the wrong next step for
  failures users actually hit.**
  - Principle: general-purpose / special-general mixture.
  - Symptom: change amplification. Each provider quirk becomes another inline branch.
  - Evidence: `errors.py:148-196`.
    - 429-credit and 400-context (COD-5, medium, corrected: the stopped-Ollama leg is mostly
      pre-empted by the validate gate).
    - Ollama running with the model not pulled gets "pick another model" and the pull flow is never
      offered (**NEW 2-2**, medium).
    - A 400 invalid key on Gemini/xAI gets "try again" (**NEW 2-4**, low).
  - Fix: replace the if-chain with a data table of `(provider?, status, body-substring) → (message,
    action, code)` rows, with test_errors.py fixtures taken from real provider bodies. The frontend
    branches on `code` (COD-13) to route `model_not_pulled` to onboarding and to suppress Retry for
    auth, 402 and model_not_found.
- **[P2] The GET-only client and the kind-blind ProviderError mapping push error translation out to
  ~64 call sites.**
  - Principle: deep modules / consistency.
  - Symptom: change amplification.
  - Evidence: `sidecar-client.ts:154` (COD-3, medium, corrected: two of the three cited sites are
    trading surfaces being deleted; the live defect is `delegate-runs.ts`); `app.py:312-315` plus 25
    route sites (COD-4, medium).
  - Fix: add one `sidecarRequest(method, path, {params, body, headers, signal})` that `sidecarGet`
    delegates to. Make the app-level handler the only ProviderError mapper
    (`{rate_limited: 429, not_found: 404, None: 502}`) and type `kind` as a Literal.

## Finding register (existing + new)

| raw_id                 | Title (short)                                                                     | Raw sev | Refute verdict           | Final sev | Status                                              |
| ---------------------- | --------------------------------------------------------------------------------- | ------- | ------------------------ | --------- | --------------------------------------------------- |
| COD-error-layer-1      | Divergence-notice regex drifted; 2 of 3 notices missed                            | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-2      | SSE non-2xx renders raw JSON body in chat                                         | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-3      | GET-only client; `[object Object]` 422 still live at POST sites                   | medium  | admitted_with_correction | medium    | live; broker/order sites drop with trading          |
| COD-error-layer-4      | ProviderError→HTTP duplicated at 25 sites; `kind` honoured once                   | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-5      | humanize wrong next step: 429-credit, 400/413 context, stopped Ollama             | medium  | admitted_with_correction | medium    | live; Ollama leg mostly pre-empted by validate gate |
| COD-error-layer-6      | Router guards blame provider/network for internal crashes                         | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-7      | validateProvider collapses sidecar-down into "no model set up"                    | medium  | admitted_with_correction | medium    | live; fix needs Ollama adapter + route too          |
| COD-error-layer-8      | Transport failure shows bare "Load failed"; crash undetected                      | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-9      | Retry hook retries every rejection 13×                                            | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-10     | research:begin single-line regex; multi-line query never begins run               | low     | admitted                 | low       | live                                                |
| COD-error-layer-11     | Consumer throws relabelled as protocol errors; EOF without done = silent success  | low     | admitted                 | low       | live                                                |
| COD-error-layer-12     | No timeout/AbortSignal; port-0 probed for 120 s                                   | low     | admitted                 | low       | live                                                |
| COD-error-layer-13     | Error struct declared 6×; `code` consumed by nothing; run crash bypasses humanize | low     | admitted                 | low       | live                                                |
| COD-error-layer-14     | sidecarStatus is a boot latch; reconnect re-arm fires at most once                | medium  | admitted                 | medium    | live                                                |
| COD-error-layer-15     | Tier-B OpenRouter key on every GET; stale "Exa" comment                           | low     | admitted                 | low       | live                                                |
| COD-error-layer-2-1    | **NEW** Readiness rejection skips onError → chat wedged, Stop dead                | medium  | (pending refute)         | —         | new                                                 |
| COD-error-layer-2-2    | **NEW** Ollama up, model not pulled → "pick another model"; pull flow not offered | medium  | (pending refute)         | —         | new                                                 |
| COD-error-layer-2-3    | **NEW** finish_reason max_tokens/length dropped; truncation looks complete        | medium  | (pending refute)         | —         | new                                                 |
| COD-error-layer-2-4    | **NEW** 400 invalid-key (Gemini, xAI) classified "unknown / try again"            | low     | (pending refute)         | —         | new                                                 |

No existing finding was refuted, so none is withdrawn from the prose above. Candidates from the
fresh hunt were dropped when another subsystem's raw file already covers them:
- Macro provider-tab retry misuse: COD-macro-quant-14.
- Data-route raw exception text: INT-spec-135-137 and INT-spec-90-1.
- News 4xx retry: COD-market-data-providers-3-5.
- `/llm/keys/validate` echoing raw exceptions: COD-llm-adapters-9.

These were checked and dropped as non-defects:
- SSE framing: `\n\n` matches both routers' `_encode_event_dict`.
- Error frame followed by done: `endRun` is first-terminal-wins and `finalize` keeps `error`.
- Gemini key-in-URL leakage: the SDK sends the key in a header.
- User-configurable Ollama host: none exists.

## Persona walkthroughs

**Tactical Tornado.** If the Tactical Tornado kept going, the next provider quirk would become another
`if provider_id == "…"` inside `humanize` (`errors.py:148-157` is the template). The next runtime
notice would get another alternation in `DIVERGENCE_RE` (`message-notices.ts:57`). The next
`sidecarStatus` consumer would assume liveness the store never writes (`store/app.ts:24-34`). Each of
these edits is locally correct and adds one more contract that only a live run can check.
`streaming.ts:134` is the shape of the whole layer: the happy path is wrapped and the one await that
can fail first is not.

**Strategic Thinker.** A redesign would give the layer exactly three owned seams:
1. **One request primitive.** `sidecarRequest(method, path, opts)` owns base URL, headers, timeout,
   transport normalisation and detail extraction, and writes `sidecarStatus` on connection-level
   success or failure. `sidecarGet`, `validateProvider` and the SSE opener become thin callers of it.
2. **One typed event model.** Notices, research-begin and truncation become fields or kinds on the
   stream events, not prose. `consumeSseStream` guarantees one terminal callback: `done`, `error` or a
   synthesised error at EOF or pre-stream failure.
3. **One classification table.** The adapters, the router guard (as an explicit
   `internal` code) and the durable-run crash path all go through `humanize`. The table is data keyed
   by provider/status/body and pinned by fixtures from real provider bodies. The frontend branches on
   `code` for the next step: Settings, Download model, Reconnect, or Retry.

That removes the 12 re-spellings, the 25 route mappers and both regex contracts, and it makes every
NEW finding a one-row or one-line change.

## Minor observations

- `_provider_label(None)` returns `"the AI provider"`, so the router-guard path renders "The the AI
  provider API key was rejected" and "Your the AI provider account has no credit." (probe in
  scratch). It is only reachable through the router guard, so it is folded into COD-6 rather than
  filed.
- `consumeSseStream` reports `ok && !body` as "sidecar returned 200".
- `resolvePortToBaseUrl`'s `invoke` rejection escapes as a non-`SidecarError`.
- `useRetryOnSidecarReady` cannot cancel an in-flight `loadFn` on a deps change (no signal), so a
  stale load can land after a newer one. Store-side races are already filed under frontend-stores.
- `message-notices` `errorFrames` are session-only. After a reload the failed message keeps its
  sentence but loses its action ("Top up in Settings"); this is a documented choice.

## Questions to consider

- If `consumeSseStream` guaranteed exactly one terminal callback, how many ChatSidebar
  "settle the brief / end the run / clear abortRef" duplications would disappear?
- Could `validateProvider` be deleted in favour of letting the first chat call fail with a
  `code` that routes to onboarding (`model_not_pulled`, `unreachable`, `not_configured`)? That would
  remove the second client and the pre-flight round-trip.
- Should `ProviderError` move out of `errors.py` into the data layer, and get its own humaniser for
  the panel side, so `errors.py` is only the LLM classification table?

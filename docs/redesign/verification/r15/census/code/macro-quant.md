# CODE CRITIQUE — `macro-quant` (Macro & Quant Engines)

**Subsystem:** `CODE_PARTITION.json` id `macro-quant` — 31 files, 6,074 LOC, 19 test files.
Two independent analytical engines bundled for one critic: macro (FRED/ECB/IMF/World Bank +
dispatcher) and quant (QuantLib options / greeks / bonds / yield curve / Monte Carlo), each
with its own store and panels.

**Method:** `aposd-critique` skill invoked and followed. Assessment A (Strategic Thinker,
18 principles) and Assessment B (Tactical Tornado red-flag scan) were run **sequentially in one
context** — `Assessment independence: degraded (sub-agents unavailable to a census worker)`.
`.aposd/critique/` snapshot persistence **skipped deliberately**: the R15 run defines this file
and `raw/code-macro-quant.json` as the outputs, and writing a second untracked tree into the
operator's working copy mid-census is noise. Every core file was read in full; nothing sampled.

**Five claims were settled by running code, not by reading it** — transcripts in
`§ Proof runs` at the bottom.

---

## Tactical Tornado verdict

**Risk: HIGH on the quant side, MEDIUM on the macro side — and the tell is that both engines are
well-commented.** This is not sloppy code. It is carefully-written code whose *comments assert
invariants the structure does not hold*, which is the more expensive failure: a reader who
trusts the docstring stops checking.

Four separate places state a contract the code does not honour:

| Comment claims | Code does | Where |
|---|---|---|
| "sign flipped … so the binomial Greeks line up with the analytic Greeks" | flips it the **wrong way**; binomial theta is +39.84 where analytic is −39.68 | `sidecar/services/quant/options.py:163-166` |
| "the panel divides by 100 to show per-1 % move" | the panel prints `toFixed(4)` raw | `options.py:131-132` vs `src/modules/quant/GreeksDashboard.tsx:136` |
| "Substitute the shortest-tenor zero rate for the first point" | substitutes the *t+1 day* rate, and emits a duplicate point | `sidecar/services/quant/yield_curve.py:134-137` |
| "utility surfaces the workflow nodes + agent tools can reach into" | nothing in the repo imports the module | `sidecar/services/quant/monte_carlo.py:13-16` |

Red flags found, ordered by severity:

1. **Information leakage (region ⇄ country)** — `macro_router.py:59-63` knows "IN → World Bank";
   `world_bank_provider.py:41` knows "country defaults to USA". Neither knows about the other.
2. **Information leakage (global mutable QuantLib state)** — `_common.py:34-41` and `bonds.py:52`
   both reach into the process-global `ql.Settings.instance()`; the routes that call them run
   concurrently in a threadpool.
3. **Repetition** — the curated-substring search block is copy-pasted three times
   (`ecb_provider.py:220-237`, `imf_provider.py:249-266`, `world_bank_provider.py:254-268`);
   the analytic-BS pricing block twice (`options.py:60-80`, `greeks.py:32-51`).
4. **Special-general mixture** — every wired engine calls `req.validate_domain()`;
   `monte_carlo.py` has ad-hoc inline checks and no domain validation at all.
5. **Swallowed exception → silent degrade** — `world_bank_provider.py:231-233` turns a network
   failure into nine curated US indicators at `_log.debug`, which the dispatcher then caches
   for six hours (`macro_router.py:152-154`).
6. **Dead branch** — `world_bank_provider.py:196-201` is structurally unreachable
   (`callable(x.items)` true ⟹ `list(x.items)` always raises).
7. **Dead branch** — the catalog error + Retry UI at `MacroSeriesPicker.tsx:140-160` can never
   render, because `store/macro.ts:134` swallows the rejection it waits for.
8. **Duplicated truth with three different values** — the binomial step floor is ≥1 in the panel,
   1..100_000 in the model, ≥3 in the service.

What the Tornado scan caught that the Strategic read missed: **the theta sign**. The module
structure around it is genuinely good — one FD helper, one dispatcher, documented perturbations.
It reads as correct. Only running it exposes the inverted sign.

What the Strategic read caught that the Tornado scan missed: **the greeks-unit gap is a layering
failure, not a UI bug.** QuantLib's internal convention (vega per unit-vol, theta per year) is
allowed to travel unlabelled across the HTTP wire into a trader's eyeballs because no layer owns
the "market-convention units" abstraction. The fix is a seam, not a `/100`.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line → consequence) |
|---|---|---|---|
| 1 | Strategic over tactical | at-risk | `models/quant.py:19-28` — domain bounds were retrofitted ("previously ZERO input-domain validation"), and the retrofit landed in the model while `bonds.py:46-50` kept its own date checks. The strategic move (one validation home) was half-taken. |
| 2 | Deep modules | **pass** | `macro_router.get_series:86-120` — 35 lines hide provider dispatch, a 6 h cache, JSON round-trip and thread-offload behind `get_series(series_id, provider)`. Genuinely deep. |
| 3 | Information hiding | **violate** | `_common.set_evaluation_date:34-41` mutates the process-global `ql.Settings.instance()` and *returns* the QL date; the global is then implicitly depended on by `bonds.py:52`, `yield_curve.py:70`, `build_bsm_process:57`. The "which date are we pricing at" decision is hidden from callers but shared between threads. |
| 4 | General-purpose modules | at-risk | `quant_tools.py:86-101` `_yield_curve_value` — docstring says "sample at one tenor" (line 18), implementation returns the whole curve. The tool id promises a point query the function does not offer. |
| 5 | Different layer, different abstraction | **violate** | `GreeksDashboard.tsx:136` renders `value.toFixed(4)` straight off the QuantLib-convention wire. The display layer adds no abstraction over the engine layer, so engine units reach the user. |
| 6 | Pull complexity downward | **violate** | `routers/macro.py:87-106` — the caller must know which provider's id namespace `series_id` belongs to, *and* the router silently reinterprets that namespace by region. Complexity pushed up to every caller. |
| 7 | Better together or apart | at-risk | `greeks.py` exists only because "the panel hits this surface independently" (`greeks.py:3-5`). It duplicates `options.price_european_bs` rather than calling it — split for a UI convenience, paying a drift cost. |
| 8 | Define errors out of existence | **violate** | `world_bank_provider.py:231-233` defines the error out of existence by *pretending it did not happen* — the caller receives plausible rows and no signal. That is masking a failure, not eliminating it. |
| 9 | Design it twice | at-risk | `yield_curve.py:124-137` — integer `step_days` + a `qld <= qd` patch is a first design kept. A second design (float grid clamped to `max_tenor_years`) removes both the duplicate point and the extrapolation overrun. |
| 10 | Comments describe non-obvious | **violate** | Four comments assert contracts the code breaks — see the Tornado verdict table. `options.py:163-166` is the worst: it explains *why* the sign is flipped, and the flip is backwards. |
| 11 | Comments first | **pass** | `services/macro/__init__.py:1-21` and `quant/__init__.py:1-22` are interface-first module docs that state the three-call provider contract before any code. Reads as designed-then-written. |
| 12 | Choosing names | at-risk | `options.price_american_binomial:171` prices European options too (`options.py:112-115`); `_greeks_fd` "fd" is fine but `price_american_binomial` actively misleads the dispatcher reader at line 263. |
| 13 | Modifying existing code | at-risk | `routers/macro.py:96-106` — the FR-060 region default was bolted onto the legacy `/macro/{series_id}` path as a third branch rather than resolving the namespace question the branch creates. |
| 14 | Consistency | **violate** | `routers/quant.py:37,46,55,64` are sync `def` while `routers/macro.py:47,60,72` are `async def` — same sidecar, opposite concurrency models, and the sync choice is what exposes the QuantLib global. Binomial floor stated three ways (panel ≥1 / model ≥1 / service ≥3). |
| 15 | Code should be obvious | at-risk | `world_bank_provider.py:196-201` — a reader cannot tell this branch is dead without running it. `yield_curve.py:137` `qld = qd + 1` silently changes what the first point *means*. |
| 16 | Design for the future | **violate** | `monte_carlo.py` — 184 LOC, zero importers, zero tests, a docstring naming callers that do not exist. "Prefer deletion over extension" inverted. |
| 17 | Performance as design | **pass** | `macro_router.py:118,152,174` `asyncio.to_thread` around every sync SDK + a 6 h cache is the right design-level call, and the module docstring states the reasoning (`macro_router.py:10-12`). |
| 18 | Increments are abstractions | at-risk | `bonds.py:54` `Thirty360(USA)` + `yield_curve.py:80` `USDCurrency()` + `BondPricerPanel.tsx:301` `$` — the bond increment shipped as a US-Treasury *feature* with no day-count/currency abstraction, in a terminal whose stated market is India. |

**Summary: 3 pass, 8 at risk, 7 violate (3/18 pass).**

That pass count is harsh and worth reading correctly: this subsystem is competently built and
mostly works. It scores low because APOSD grades *structure holding invariants*, and here the
invariants are held by comments and by test coverage that stops one engine short.

---

## Overall impression

Two engines of very different maturity filed under one id.

**Macro is a good design with a bad edge.** The dispatcher is the deepest module in the
subsystem, the four providers really do present one three-call surface, and the thread-offload +
cache decisions are made deliberately and documented. Its problems are all at the seams: region
routing that does not reach the country default, a failure path that lies, and a cache that
preserves the lie for six hours.

**Quant is a clean surface over a global.** The service modules are small, the dispatcher is
one `if`-chain, the Pydantic contract keeps QuantLib types off the wire exactly as
`quant/__init__.py:9-13` promises. Underneath, every pricing call mutates one process-global
evaluation date from a threadpool, and one engine returns a sign-flipped greek that the panel
renders without comment.

**The single biggest opportunity:** decide where "units and conventions" live. Vega-per-100,
theta-per-year, 30/360-USA, USD, the QuantLib evaluation date — all five are currently implicit,
and each one leaks into a different layer. One `PricingConventions` value passed down (and one
display-seam that names its units) closes findings 2, 3, 13 and half of 8 at once.

---

## What's working

1. **`macro_router.py:86-120` is a genuinely deep module.** `get_series("DGS10", "fred")` hides
   provider lookup, a cache-key scheme, a JSON round-trip through a strict model, a corrupt-row
   discard path (`115-116`) and `asyncio.to_thread`. The caller sees two arguments. This is the
   Unix-I/O shape the book asks for, and it is why adding a fifth provider is a one-entry change
   to `_PROVIDERS:47-52`.

2. **The Pydantic-in / Pydantic-out boundary is airtight.** `quant/__init__.py:9-13` claims no
   QuantLib type escapes; grep confirms it — `models/quant.py` imports no `QuantLib`, and every
   service function signature takes and returns a `BaseModel`. That is why the wrong-sign theta
   is a *one-line* fix instead of a refactor.

3. **Panel validation is honest and stated in product language.**
   `OptionPricerPanel.tsx:246-251` refuses American × Black-Scholes with the reason and the
   remedy, before any request is sent; `fred_provider._api_key:180-185` returns user-facing copy
   naming the alternatives rather than an env-var name. Both reduce the user's unknown unknowns.

---

## Priority issues

### [P0] Binomial theta is returned with the wrong sign

- **Principle:** #10 Comments describe non-obvious (the comment asserts the opposite of the behaviour)
- **Complexity symptom:** Unknown unknowns — the docstring tells the next reader this is already correct
- **Evidence:** `sidecar/services/quant/options.py:166` —
  `theta = -(price_fwd - price_base) * 365.0`, with `price_fwd` priced one day *later*
  (`options.py:161`). `price_fwd < price_base`, so the difference is negative and the negation
  makes theta positive. Comment at `163-166` claims the flip aligns it with the analytic engine.
- **Proof:** identical European call, spot 220 / strike 220 / r 5 % / q 0.5 % / σ 28 % /
  2026-05-16 → 2026-06-30. Analytic `theta = -39.6807`; binomial `theta = +39.8351`.
  Same magnitude, inverted sign. Renders at `src/modules/quant/OptionPricerPanel.tsx:560`
  as `Θ Theta 39.8351` — a long call shown *gaining* value from time decay.
- **Why it matters:** wrong money-relevant data presented as true, on an engine the panel offers
  as a first-class choice, with no caveat anywhere in the UI.
- **Test gap that let it through:** `sidecar/tests/test_quant_greeks.py:105-108`
  (`test_call_theta_negative_for_atm`) asserts `theta < 0` for the **analytic** engine only.
  No binomial equivalent exists in any of the ten quant test files.
- **Fix:** `theta = (price_fwd - price_base) * 365.0` (drop the negation), and add the mirrored
  assertion to `test_quant_options.py` so the two engines are pinned to each other.

### [P0] Concurrent quant requests corrupt each other through QuantLib's global evaluation date

- **Principle:** #3 Information hiding / #14 Consistency
- **Complexity symptom:** Unknown unknowns — nothing at the call site hints at shared state
- **Evidence:** `sidecar/services/quant/_common.py:34-41` `set_evaluation_date` writes
  `ql.Settings.instance().evaluationDate`; `build_bsm_process:57` calls it on every price;
  `bonds.py:52` and `yield_curve.py:70` write it directly. The four routes that reach them —
  `routers/quant.py:37, 46, 55, 64` — are plain `def`, so FastAPI dispatches each into the
  anyio worker threadpool and runs them **concurrently**.
- **Proof:** two threads call `set_evaluation_date` with 2026-05-16 and 2030-01-02, then both
  read the global: both observe `January 2nd, 2030`. It is a process singleton, not thread-local.
- **Why it matters:** two users (or one user and one agent tool) pricing simultaneously with
  different valuation dates can each be served the other's date. The response is a 200 with a
  plausible number. There is no detection and no log line.
- **Aggravating:** `quant_tools.py:42-101` are `async def` and call `options.price(...)`
  **synchronously on the event loop** — a 100 000-step binomial (`models/quant.py:33`) re-prices
  the tree nine times via `_greeks_fd`, blocking every other sidecar request for the duration.
- **Fix:** one module-level `threading.Lock` in `_common.py` wrapping set-date-through-price
  as one critical section, and `await asyncio.to_thread(...)` in the four `quant_tools.py`
  handlers so the loop is never held. Both are local changes; neither touches the wire contract.

### [P1] Greeks reach the trader in QuantLib's internal units, with the rescaling only in a comment

- **Principle:** #5 Different layer, different abstraction
- **Complexity symptom:** Change amplification — the unit decision has no home, so it must be
  re-made at each of the two render sites
- **Evidence:** `options.py:131-132` — "Returned per unit-vol matching the QuantLib convention
  (so the panel divides by 100 to show per-1 % move)"; `greeks.py:26-27` — "the panel relabels
  for display". The panels do neither: `GreeksDashboard.tsx:103` and `:136` print
  `value.toFixed(4)`, `OptionPricerPanel.tsx:557-561` the same, and `GREEK_ROWS:77-81` carry
  partial-derivative descriptions with **no units at all**.
- **Proof:** at the dashboard's own default inputs (`GreeksDashboard.tsx:169-175`), the panel
  displays `ν Vega 30.6270` and `Θ Theta -39.6807`. Market-convention values are **0.3063**
  per vol point and **-0.1087** per calendar day — 100× and 365× out.
- **Why it matters:** a trader sizing a 1-point vol move off this panel is wrong by two orders
  of magnitude, and the panel's own copy ("the static, honest sensitivity read per greek",
  `GreeksDashboard.tsx:69-70`) invites exactly that trust.
- **Fix:** scale and label at the display seam — `vega/100` labelled "per 1 vol pt",
  `theta/365` labelled "per day" — in one shared helper both panels call. Leave the wire in
  QuantLib convention and say so in the interface comment.

### [P1] The India region default routes to World Bank, which is hardwired to the USA

- **Principle:** Information leakage (the book's headline red flag)
- **Complexity symptom:** Change amplification — "which country is this session about" is
  encoded in two modules that never speak
- **Evidence:** `sidecar/services/macro/macro_router.py:59-63` —
  `_DEFAULT_PROVIDER_BY_REGION = {"US": "fred", "IN": "world-bank", "GLOBAL": "fred"}`, with the
  comment at `56-58` stating the point: "IN prefers World Bank, whose WDI indicators carry India
  series the FRED catalog does not." Meanwhile `world_bank_provider.py:41`
  `_DEFAULT_COUNTRY = "USA"` and `_parse_series_id:139` returns it for any id without a colon —
  and **all nine** `_FEATURED` entries (`46-119`) are bare indicators with no country.
- **Why it matters:** an IN session opens the macro panel, clicks World Bank → Featured →
  "GDP growth (annual %)", and gets **United States** GDP growth. It is labelled `— USA` at
  `world_bank_provider.py:207`, so it is not undisclosed — but the entire mechanism that routed
  the user there exists to give them India, and it delivers the opposite.
- **Fix:** thread the region into the country default — `_parse_series_id(series_id, region)`
  mapping IN→`IND`, US→`USA` — so the two facts live in one place. Nine `_FEATURED` entries
  then serve every region unchanged.

### [P1] A provider-less `/macro/{series_id}` silently reinterprets the id's namespace by region

- **Principle:** #6 Pull complexity downward
- **Complexity symptom:** Cognitive load — the caller must know the region to know what their
  own string means
- **Evidence:** `sidecar/routers/macro.py:100-106` — when `provider` is absent and the region
  default is not `fred`, the request is dispatched to World Bank. But series ids are
  provider-native and mutually unintelligible: FRED `DGS10`, ECB `FM.D.U2.EUR.4F.KR.MRR_FR.LEV`,
  IMF `IFS/A.US.NGDP_R_K_IX`, WB `NY.GDP.PCAP.CD`.
- **Why it matters:** `GET /macro/DGS10` — the app's own default series
  (`MacroPanel.tsx:14-15`) — succeeds for a US session and 502s for an IN session, because the
  string is handed to a provider that has never heard of it. The failure is a gateway error with
  no hint that the *routing*, not the upstream, is what broke.
- **Fix:** make `provider` required on the v0.6.0 path (the frontend already always sends it —
  `store/macro.ts:82-85`), and keep the region default for *discovery* (catalog/search) where
  the namespace question does not arise.

### [P2] World Bank search swallows upstream failure into curated US rows, and the dispatcher caches it for 6 hours

- **Principle:** #8 Define errors out of existence (misapplied — this masks rather than eliminates)
- **Complexity symptom:** Unknown unknowns — no user-visible or operator-visible signal
- **Evidence:** `world_bank_provider.py:231-233` catches `Exception` to `_log.debug` (invisible
  at default log level) and falls through to the curated substring match at `254-268`, returning
  rows scored `0.5` that are indistinguishable from real hits. `macro_router.py:152-154` then
  caches whatever came back under a 6 h TTL (`DEFAULT_CACHE_TTL_SECONDS:42`) with no
  success/degraded distinction — and it caches an empty list just as happily.
- **Why it matters:** one transient network blip pins World Bank search — the **IN default
  provider** — to nine curated US indicators for six hours, after connectivity returns. The
  frontend cannot tell either: `store/macro.ts:120-124` turns any search failure into `[]`, which
  `MacroSeriesPicker.tsx:134-139` renders as "No matching series".
- **Fix:** re-raise as `ProviderError` (every other provider does — `fred_provider.py:310-311`,
  `imf_provider.py:220-221`), and skip the cache write when the result is empty or degraded.

---

## Persona walkthrough

**Tactical Tornado walkthrough.** The Tornado wrote `_greeks_fd` (`options.py:121-168`) in one
sitting: five perturbations, each one correct, each one documented. Theta was last, the sign
looked wrong in a quick check, a minus went in front, the number looked right, done — and the
comment at `163-166` was written to justify the minus rather than to test it. The Tornado then
wrote `greeks.py` by copying the twenty working lines out of `price_european_bs` instead of
calling it, because calling it meant reshaping a response model. Next, `world_bank_provider.py`
`search` got a `try/except Exception: rows = []` at `231-233` so the panel would never show an
error during the demo. Each of those three moves saved ten minutes. Together they are a wrong
greek, a duplicate that will drift, and a six-hour cache poisoning — and the code *looks*
careful, which is why none of them were caught.

**Strategic Thinker walkthrough.** The Strategic Thinker would not start with the theta line. They
would notice that `_common.py` already exists as the "conventions" module — it owns `DAY_COUNT`,
`CALENDAR`, `set_evaluation_date` — and that it is the natural home for the four decisions
currently scattered across layers: the evaluation-date lock, the day-count/currency pair that
`bonds.py:54` and `yield_curve.py:80` hardcode, and the display-unit convention that
`options.py:131` documents but does not own. They would add a `threading.Lock` there guarding
set-date-through-price (closing P0-2 for all four engines at once, not per-engine), make
`greeks.compute_greeks` a five-line reshape over `price_european_bs` (closing the drift), and
put one `toMarketUnits(greeks)` helper at the frontend seam that both panels call. On the macro
side they would pass `region` into `_parse_series_id` rather than adding a second region table —
"change together, stay together". Net: roughly forty lines changed, six findings closed, and
`_common.py` becomes the deep module the package already half-assumes it is.

---

## Minor observations

- `options.price_american_binomial:171` prices European options too (`options.py:112-115`) and
  the dispatcher routes every binomial request to it (`:263`). Rename to `price_binomial`.
- `_greeks_fd:141` re-prices the base tree that `price_american_binomial:181` already computed —
  nine tree builds per request where eight would do.
- `bonds.py:43-44` re-checks `coupons_per_year not in _FREQUENCY_MAP` although the field is
  `Literal[1, 2, 4]` (`models/quant.py:144,154`) and Pydantic has already rejected anything else.
- `MacroChart.tsx:40` — `const LINE_COLOR = ACCENT_CORAL; // neutral charcoal-300 — monochrome`.
  The alias says coral, the comment says charcoal; per CLAUDE.md token names are historical, but
  the local alias plus a contradicting comment means the reader must open `chart-theme.ts` to
  learn what colour is drawn.
- `quant_tools.py:18` documents `yield_curve_value` as "bootstrap a curve, sample at one tenor";
  `_yield_curve_value:87` returns the entire curve.

## Questions to consider

- If `_common.py` owned a `PricingConventions` value (day count, calendar, currency, evaluation
  date) passed explicitly into each engine, would the global, the USD hardcoding and the
  India-bond gap all close as one change?
- What would the macro dispatcher look like if a provider returned
  `SearchOutcome{rows, degraded, reason}` instead of a bare list — would the six-hour cache
  poisoning and the frontend's "No matching series" ambiguity both disappear at the same seam?
- `greeks.py` exists because one panel wanted a shorter request shape. Is that a reason for a
  module, or a reason for a default on `OptionPricingRequest`?

---

## Proof runs

All four probes ran locally against `sidecar/.venv`, read-only, no network, no GUI, no process
started that was not also stopped.

**1 — Greeks display units** (`GreeksDashboard.tsx:169-175` defaults):

```
price 9.2181
delta 0.5417 gamma 0.018331
vega  (as displayed, 4dp): 30.627   -> per 1 vol POINT would be 0.3063
theta (as displayed, 4dp): -39.6807 -> per CALENDAR DAY would be -0.1087
rho    13.5565
```

**2 — Binomial theta sign** (identical European inputs, both engines):

```
bs  price 9.2181 theta -39.6807 vega 30.627
bin price 9.2073 theta  39.8351 vega 30.5887
```

**3 — Yield-curve duplicate points + extrapolation overrun** (one 3-month deposit,
`sample_count=100`, valuation 2026-05-16):

```
sample_count requested: 100  points returned: 100
distinct dates: 99
first 4 dates: ['2026-05-17', '2026-05-17', '2026-05-18', '2026-05-19']
last date: 2026-08-23  (3m tenor ends ~2026-08-16)
first two points identical? True
```

**4 — World Bank title branch is structurally dead** (`world_bank_provider.py:196-201`):

```
hasattr(info,'items') -> True
callable(info.items)  -> True
list(info.items) raises TypeError: 'method' object is not iterable
```

**5 — QuantLib evaluation date is a process global, not thread-local**:

```
thread A set 2026-05-16, thread B set 2030-01-02
what each thread then observed: {'B': 'January 2nd, 2030', 'A': 'January 2nd, 2030'}
```

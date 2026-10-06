# Code census — `research-extraction-synthesis`

**Subsystem:** Research Engine: Extraction & Synthesis (`CODE_PARTITION.json`)
**Responsibility:** turn surviving search results into a cited brief — page extraction,
financial-semantics tagging, citation verification, the brief data contract, and the
frontend claim-ingest helpers.
**LOC:** 4,762 across 12 files. **Model:** `claude-opus-5[1m]`.
**Method:** `aposd-critique` skill loaded and followed. Sub-agents unavailable in this
worker, so Assessment A (Strategic Thinker) and Assessment B (Tactical Tornado) ran
**sequentially** — `Assessment independence: degraded (sequential)`.
**Read fully:** `extract.py`, `semantics.py`, `finance.py`, `citecheck.py`, `models.py`,
`perplexity.py`, `sonar.py`, `news.py`, `brief-claims.ts`, `brief-ingest.ts`,
`types/brief.ts`, `types/research-space.ts`. Cross-read for proof: `transport.py`,
`budget_guard.py`, `deep.py`, `iter.py`, `news_tool.py`, `deep_research.py`,
`test_research_semantics.py`, `NewsFeedPanel.tsx`.

---

## Tactical Tornado verdict

**Risk: medium-low.** This is not tornado code. It is *strategic code with a security
hole and a dead meter*. The prevailing style — pure functions, honest dicts, "flag, never
pick", `None` over a fabricated number — is genuinely good and unusually disciplined for a
finance pipeline. The defects are not sloppiness; they are **boundaries that were drawn
once and then stopped being re-checked**:

- the SSRF guard checks the URL it was handed and not the URL it actually fetched;
- the budget guard has four ceilings and the research path feeds only two of them;
- the domain-tier table has a heuristic that any blog can satisfy;
- `domain` means "host" in one module and "host + provenance label" in another.

Nine tornado red flags, ordered by damage:

| # | Red flag | Location | Pattern |
|---|---|---|---|
| 1 | Information leakage (trust boundary) | `extract.py:593` vs `:635`, `transport.py:108` | guard validates `url`, transport follows redirects, `final_url` recorded but never re-checked |
| 2 | Pass-through variable / dead meter | `deep.py:54`, all 7 `.record(None, …)` sites | `LLMCall` returns `str` — no usage channel exists, so tokens/spend can never be metered |
| 3 | Special-general mixture | `finance.py:72-73, 127-132` | `_IR_PATH_MARKERS` makes `/investor` in *any* path a primary-record source |
| 4 | Information leakage (overloaded field) | `sonar.py:198`, `perplexity.py:179` → `brief-ingest.ts:250-258` | `domain` is a display label upstream, parsed as a hostname downstream |
| 5 | Different layer, same abstraction | `news.py:115-130` vs `news_tool.py:46-56` | enrichment (sentiment + tagging) lives in the route; the second consumer silently gets neither |
| 6 | Repetition | `perplexity.py` vs `sonar.py` | 143-diff-line near-clone of the same lane; 402 handling exists in one only |
| 7 | Duplicated truth, no guard | `semantics.py:1168-1186` | `_PROMPT_KEYS` re-lists every emitted metric by hand; sibling literals *do* have a pin test (`test_research_semantics.py:776-778`) |
| 8 | Contract drift | `semantics.py:327,340,565,580` vs `types/brief.ts:129-177` | 4 of 17 emitted derived metrics are undeclared in the TS interface |
| 9 | Pass-through variable | `semantics.py:349` | `_ = currency  # … noted here for symmetry` — a parameter kept solely for shape |

Patterns the Strategic Thinker pass alone would have missed: #3 (needed an executed probe),
#4 (needed a cross-language read), #9 (needed a line-level scan).

---

## Design principles score

**11 pass, 5 at risk, 2 violate — 11/18 pass.**

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **pass** | `semantics.py:1-17`, `models.py:9-17` | conventions ("null over fabricated", "flag never pick") are stated and held across 7 legs |
| 2 | Deep modules | **pass** | `extract.py:647-683` | `visit_for_research` hides transport, SSRF, PDF page-scoring, layout retry, scan honesty behind `(url) -> str \| None` |
| 3 | Information hiding | **violate** | `extract.py:593,635`; `sonar.py:198` → `brief-ingest.ts:251` | the SSRF decision leaks past the guard via redirects; `domain`'s meaning leaks across a language boundary |
| 4 | General over special-purpose | **at risk** | `finance.py:72-73` | the IR heuristic is *too* general — it promotes any `/investor` path to the primary tier |
| 5 | Different layer, different abstraction | **violate** | `news.py:115-130` vs `news_tool.py:46-56` | scoring + tagging sit in the HTTP route, so the agent/MCP consumer of the same data gets neither |
| 6 | Pull complexity downward | **at risk** | `news.py:62-74`; `NewsFeedPanel.tsx:170` | the route needs pre-normalised symbols; the invariant lives in one frontend helper (`toNewsSymbol`) |
| 7 | Better together / apart | **at risk** | `perplexity.py:100-317` vs `sonar.py:126-334` | two lanes that are one lane with two URLs and two model tables |
| 8 | Define errors out of existence | **at risk** | `extract.py:668-683` | `fetch_page` returns a typed honest error dict; `visit_for_research` collapses all of it to `None` |
| 9 | Design it twice | **pass** | `semantics.py:897-950` | dividend unit chaos resolved by *picking the closest interpretation and flagging past tolerance* — visibly a second design |
| 10 | Comments explain the why | **pass** | `semantics.py:114-117`, `extract.py:369-374` | thresholds carry their calibration data ("SAKSOFT Q4 FY26… 25-45%") |
| 11 | Comments as design | **pass** | `finance.py:196-204` | the R13 note explains why news dims are deliberately *not* `site:`-anchored |
| 12 | Naming | **at risk** | `models.py:65`, `sonar.py:198` | `domain` names a host in `finance.py`, a display label in the hosted lanes |
| 13 | Consistency | **pass** | `semantics.py` `_*_leg` family | seven cross-check legs share one `(facts, conflicts)` return shape |
| 14 | Obviousness | **pass** | `citecheck.py:69-89`, `brief-ingest.ts:401-424` | the marker-strip logic reads the same in both languages |
| 15 | Avoid temporal decomposition | **at risk** | `semantics.py:1086-1146` | `derive_semantics` is six hand-written `update()/extend()` pairs; a new leg is a 3-site edit |
| 16 | Avoid pass-through | **pass** (1 exception) | `semantics.py:349` | one dead parameter, explicitly annotated |
| 17 | Minimise special cases | **pass** | `extract.py:483-503` | PDF page selection folds the special cases (first-text pages, score floor) into one selection step |
| 18 | Minimise complexity accumulation | **pass** | `citecheck.py:19-21` | the audit is constrained to *only ever remove* confidence — complexity bounded by contract |

---

## What's working

1. **The "flag, never pick" discipline is real and structurally enforced.** Every one of the
   seven cross-check legs (`semantics.py:292,362,537,666,748,787` + the inline mcap check at
   `:1114`) returns `(facts, conflicts)` and *never* mutates the provider value. The docstrings
   say "disclosure, not substitution" and the code actually does that. This kills the entire
   class of "app quietly corrected a number and was wrong" bugs. Cognitive-load win: a reader
   needs to learn the rule once, not per-metric.

2. **`extract_pdf_text`'s scanned-page honesty is a deep module done right**
   (`extract.py:436-537`, `:398-406`). A partially-rastered Indian outcome filing returns
   `ok: True` *with* `pages_empty`, and `visit_for_research` turns that into a sentence the
   LLM can read (`:678-682`). The alternative — a silent empty — is exactly the
   "no quarterly results announced" hallucination the comment names. Unknown-unknowns win.

3. **The citation audit is asymmetric by construction** (`citecheck.py:19-21, 202-207`).
   An unparseable verdict is *absent*, absent means *kept*, and the softener is deterministic
   string surgery, not a second LLM rewrite. A dead audit degrades to a no-op instead of to
   damage. This is "define errors out of existence" applied to an LLM.

---

## Priority issues

### [P0] The SSRF guard validates the URL it was given, not the URL it fetched

- **Principle:** Information hiding (3) — the security decision leaks out of the guard.
- **Complexity symptom:** unknown unknowns.
- **Evidence:** `extract.py:593` `if not is_public_http_url(url, resolver=resolver)` runs once,
  on the *input*. `transport.py:108` opens the client with `follow_redirects=True`.
  `extract.py:635` stores `"final_url": fetched.url` — the code *has* the post-redirect URL and
  never re-checks it. The PDF lane repeats the hole at `extract.py:307` (`follow_redirects=True`)
  and `:293-294` (curl_cffi follows redirects by default).
- **Why it matters:** the module's own docstring (`extract.py:12-14`) promises "a research visit
  must never become a port-scan of localhost". It can. A page that ranks for a finance query and
  answers `302 → http://169.254.169.254/latest/meta-data/` (or `http://127.0.0.1:<sidecar port>/agents`,
  or a LAN service) gets fetched, main-content-extracted, and returned as `content` straight into
  the synthesis prompt and the published brief. Every attacker-controllable knob is on their side:
  they choose the redirect target *after* the guard has already passed. There is also a plain
  DNS-rebinding TOCTOU here — `is_public_http_url` resolves the host, then httpx resolves it again.
- **Smallest fix:** re-validate inside the transport, not at the call site — set
  `follow_redirects=False` in `httpx_fetch` and loop redirects manually through
  `is_public_http_url`, or pass an httpx event hook that raises on a non-public
  `response.url`. Either way the check belongs *below* `fetch_page`, so the PDF lane, the
  impersonation lane and every future lane inherit it. Same guard for `_default_pdf_fetch`.

### [P1] The research budget has four ceilings and the research path feeds two

- **Principle:** Pass-through variables (16) + Define errors out of existence (8).
- **Complexity symptom:** change amplification / silent degradation.
- **Evidence:** `deep.py:54` `LLMCall = Callable[[list[dict[str, Any]]], Awaitable[str]]` — the
  callback returns a bare string, so there is **no channel** through which usage could travel.
  Consequently every `.record(` in the package passes `None`: `citecheck.py:266`,
  `deep.py:1214`, `iter.py:585,962,1023`, `verify.py:319`. `budget_guard.py:126-127`
  short-circuits on `usage is None` *after* `self._steps += 1`, so `_tokens` and `_spend_usd`
  stay at `0` for the life of every research run. `breach()` (`budget_guard.py:152-158`)
  checks tokens and spend first — and they can never fire. `deep_research.py:232-236`
  confirms the construction only sets `max_steps` and `max_wall_seconds`.
- **Why it matters:** two visible consequences. (a) SC-008's token/spend ceilings are dead
  code on the research path — only steps and wall-clock actually bound a run, so a
  pathologically expensive model cannot be stopped by cost. (b) `BudgetGuard.cost()` therefore
  always returns `{"tokens": 0, "spend_usd": 0.0}`, which lands on `ResearchBrief.cost`
  (`models.py:168`), which the frontend renders through `formatBriefTokens` /
  `formatBriefSpend` (`brief-ingest.ts:445,459`) — both of which return `null` for zero. So a
  native deep run shows **no cost at all** in the cockpit while the Sonar lane shows
  "~$0.25 (estimate)" (`sonar.py:224-238`). A user comparing lanes concludes the native lane
  is free. For a product whose moat is data trust, a zero that means *unmeasured* rendered as
  *absence* is the wrong failure direction.
- **Smallest fix:** widen `LLMCall` to return `tuple[str, LLMUsage | None]` (or attach usage
  to a small result dataclass) and thread the real usage into the existing `record` call sites —
  the plumbing already exists on the other side. Until then, `models.py`'s docstring must say
  the research `cost` is step-only, and the cockpit should render "not metered", not nothing.

### [P1] Any URL with `/investor` in its path is ranked as the primary record

- **Principle:** General-purpose over special-purpose (4) — the heuristic is too general.
- **Complexity symptom:** cognitive load / wrong output.
- **Evidence:** `finance.py:72-73` `_IR_HOST_PREFIXES = ("ir.", "investor.", "investors.")`,
  `_IR_PATH_MARKERS = ("/investor", "/investor-relations", "/ir/")`; `finance.py:127-132`
  `_looks_like_ir` returns True on a *prefix or substring* match against any host/path;
  `finance.py:140` folds that straight into `TIER_PRIMARY`.
- **Proof (executed, `sidecar/.venv/bin/python`):**
  ```
  domain_tier("https://medium.com/investor-diary/why-i-bought-xyz")      -> 1  (PRIMARY)
  domain_tier("https://someblog.wordpress.com/ir/2024/hot-tip")          -> 1  (PRIMARY)
  domain_tier("https://ir.randomshell.com/")                             -> 1  (PRIMARY)
  domain_tier("https://reuters.com/markets/x")                           -> 2  (PRESS)

  rank_sources([Reuters, Medium blog]) -> ['Blog', 'Reuters']
  priority_note(...)  -> "Citation preference — when several sources support a claim,
                          cite the most authoritative: primary record
                          (exchange/regulator/filings/IR): [1]; tier-1 press: [2]."
  ```
- **Why it matters:** this is not a ranking nit — `rank_sources` decides which source owns
  the low `[n]` markers (`deep.py:368`, `iter.py:845`), and `priority_note` then *tells the
  synthesis model in prose* that `[1]` is the primary record. A Medium post outranks Reuters
  **and** is labelled to the model as exchange/regulator/filings-grade. The "data trust" moat
  is precisely this table.
- **Smallest fix:** require the IR signal to be corroborated — host prefix `ir.`/`investors.`
  **plus** a non-blog-platform host, or an `/investor-relations` path only on a host that is
  not in a denylist of publishing platforms (`medium.com`, `*.wordpress.com`, `substack.com`,
  `seekingalpha.com`, `reddit.com`). Cheaper and strictly better: give IR its own tier between
  PRIMARY and PRESS, so a false positive costs one rank, not four.

### [P2] `domain` means two different things, so every hosted-lane source mis-badges

- **Principle:** Naming (12) / Information hiding (3).
- **Complexity symptom:** change amplification across a language boundary.
- **Evidence:** `models.py:65` declares `domain: str | None` as "the provider/domain label for
  display". `sonar.py:198` sets `domain = f"{host} ({PROVENANCE_NOTE})"` and `perplexity.py:179`
  does the same — so the field carries `"sec.gov (via Perplexity Sonar)"`. Downstream,
  `brief-ingest.ts:250-258` `hostOf()` **prefers `source.domain` over the URL** and treats it as
  a bare hostname; `hostMatches` (`:314-316`) then tests `host === "sec.gov"` /
  `host.endsWith(".sec.gov")`, both of which fail on the parenthesised label. `deriveSourceType`
  (`:326-353`) falls through FILING → RESEARCH → NEWS → `vysted://` → `"web"`.
  Neither lane sets `source_type` (`sonar.py:199-206`, `perplexity.py:180-187` construct
  `ResearchSource` without it), so the derivation is the only path.
- **Proof:** `deriveSourceType({url:"https://www.sec.gov/…", domain:"sec.gov (via Perplexity Sonar)"})`
  → `hostOf` returns `"sec.gov (via perplexity sonar)"` → no list matches → not `vysted://` → `"web"`.
  The same chain strips the `filing` badge from every NSE/BSE/SEBI citation and the `news` badge
  from every Reuters/Bloomberg citation, **only** on the two hosted lanes.
- **Why it matters:** the sources rail's category badge is a trust signal, and it is uniformly
  wrong for the paid lanes — the ones a user is most likely to trust. `finance.source_tier`
  (`finance.py:147-152`) has the same blind spot in its `domain` fallback:
  `domain_of("nseindia.com (via Perplexity Sonar)")` returns the whole string and tiers as
  general (verified).
- **Smallest fix:** stop overloading. Keep `domain` a bare host in both lanes and move the
  provenance into the existing `excerpt`/a new `provenance` field — or, one line and no contract
  change, make `hostOf` prefer the URL and use `domain` only as a fallback.

### [P2] News enrichment lives in the HTTP route, so the agent sees unscored news

- **Principle:** Different layer, different abstraction (5) / Pull complexity downward (6).
- **Complexity symptom:** change amplification + silent degradation.
- **Evidence:** `news.py:115-130` is where sentiment scoring (`sentiment.score_text`) and symbol
  tagging (`_tag_symbols`) happen — inside the route handler, after `news_provider.fetch_news`.
  `news_tool.py:46` calls `news_provider.fetch_news(client, symbols, limit)` **directly** and
  returns `item.model_dump()` at `:55` with no enrichment. `models/news.py:24-26` defaults
  `symbols=[]`, `sentiment=None`, `sentiment_label=None`.
- **Why it matters:** `news_tool.py:4-5` states "Mirrors what `GET /news` serves". It does not.
  Every headline the copilot and the external MCP surface see carries `sentiment: null` — so the
  finance-tuned agent, which is the product, is structurally blind to the sentiment the panel
  displays. Worse, it is blind *quietly*: the field exists and is null, which reads as
  "neutral/unknown" rather than "never computed". Second consequence: `_tag_symbols`'
  `\b`-anchored regex (`news.py:72`) cannot match a symbol starting with a non-word character,
  and requires the *literal* symbol string in the text. The frontend defends this by projecting
  through `toNewsSymbol` (`NewsFeedPanel.tsx:170`, `BTC/USDT → BTC`); the agent path does not,
  so an agent that passes a raw watchlist symbol gets an empty feed with no explanation (the
  route drops every untagged item at `news.py:120-121`).
- **Smallest fix:** move scoring + tagging into `news_provider.fetch_news` (or a
  `news_provider.enrich()` both callers use) and normalise the symbol there. The route then
  becomes a thin projection, and the agent tool's docstring becomes true.

---

## Minor observations

- **`_PROMPT_KEYS` is duplicated truth with no guard** (`semantics.py:1168-1186`): it re-lists
  all 17 emitted metric keys by hand. All 17 currently match, but a new leg that forgets it is
  silently dropped from the synthesis prompt — the metric card renders, the prose never states
  it. The file's *sibling* literals do have a pin test (`test_research_semantics.py:776-778`),
  so the inconsistency is within one file. One assertion (`set(derive_semantics(rich).data) -
  {"conflicts"} <= set(_PROMPT_KEYS)`) closes it.
- **`types/brief.ts` `BriefDerivedMetrics` under-declares 4 emitted metrics**
  (`:129-177`): `dividend_per_share_ttm`, `dividend_declared`, `promoter_percent_exchange`,
  `institutions_percent_exchange` are emitted at `semantics.py:327,340,565,580` and listed in
  `_PROMPT_KEYS`, but absent from the interface. `brief-blocks.tsx:250-252` acknowledges them
  in a comment while the type does not. Any new consumer needs a cast.
- **`perplexity.py` / `sonar.py` are one lane written twice** (143-line diff over the
  mapping/error/estimate block). `_domain_of`, `_extract_markdown`, `_cost_snapshot` and the
  whole `research()` body are near-identical; the cost constants are duplicated under different
  names with identical values (`perplexity.py:70-72` = `sonar.py:75-80`). They have **already
  drifted**: `sonar.py:136-138` handles HTTP 402 (insufficient credits); `perplexity.py:100-114`
  does not, so a Perplexity 402 renders as the generic "failed with HTTP 402".
- **`priority_note`'s correctness rests on an unenforced precondition** (`finance.py:166-172`):
  the docstring says "Rendered against the ALREADY-RANKED numbered list". All four call sites
  currently comply (`deep.py:368,930`, `iter.py:219,845,1019`), but handing it an unranked list
  produces confidently wrong `[n]` indices in a prompt with no error. Ranking internally, or
  taking the already-numbered string, makes the invariant structural.
- **`visit_for_research` collapses every failure mode to `None`** (`extract.py:668-683`, and the
  blanket `except Exception` at `:670-671`). `fetch_page` returns a *typed* honest error
  ("blocked non-public or non-http(s) URL", "HTTP 403", "unsupported content type") and all of it
  is discarded. An SSRF-blocked visit, a paywall, and a genuinely empty page are indistinguishable
  to the loop — so the run cannot say "this filing was behind a wall", only nothing.
- **`_dividend_leg` returns a 4-tuple and carries a dead parameter** (`semantics.py:863-989`;
  `:349` `_ = currency  # currency rides the dps fact's basis; noted here for symmetry`). The
  tuple is unpacked positionally at `:1048`. A small `DividendLeg` dataclass, or folding into
  the `(facts, conflicts)` shape its six siblings already use, removes both.
- **The citation softener is text-matched, not position-matched** (`citecheck.py:262-274`):
  `_claim_sentences` returns `(sentence, markers)` with no position, and the edit is
  `cleaned.replace(sentence, soften_sentence(sentence), 1)`. Two identical sentences where the
  first is SUPPORTED and a later duplicate is UNSUPPORTED soften the *supported* one. Carrying
  the offset from the split would make it exact.
- **`derive_semantics` is six hand-written pipeline steps** (`semantics.py:1086-1146`): each leg
  is a copy of `x_facts, x_conflicts = _x_leg(...)` / `data.update` / `conflicts.extend`. Adding a
  leg is a three-site edit (leg function, this pipeline, `_PROMPT_KEYS`). A `_LEGS` tuple of
  callables collapses it to one — and makes the `_PROMPT_KEYS` guard above trivial to write.

---

## Persona walkthrough

**Tactical Tornado.** If the Tornado owned this subsystem, the damage would accrue exactly where
the boundaries are already soft. `finance._IR_PATH_MARKERS` (`finance.py:73`) is the seed crystal:
it is a *substring* heuristic in a table that decides source authority, so every future
"this filing site didn't rank" ticket adds another marker, and the primary tier erodes to
meaninglessness one string at a time. The second accrual site is `semantics.derive_semantics`
(`:1086-1146`) — six `update/extend` pairs invite a seventh, an eighth, and a caller-specific
special case inside one of them; `_PROMPT_KEYS` (`:1168`) then drifts and nobody notices because
the metric card still renders. The third is `perplexity.py`/`sonar.py`: the 402 handler already
exists in one file and not the other, and a Tornado fixes the next vendor quirk in whichever file
the ticket names.

**Strategic Thinker.** The redesign is small and mostly *deletion*. (1) Move the SSRF check below
`fetch_page` into the transport, so it guards the URL actually fetched and every lane inherits it —
the guard becomes an invariant of the module instead of a call-site ritual. (2) Widen `LLMCall` to
carry usage, which turns two dead ceilings back on and makes `cost` honest at no new concept cost.
(3) Collapse `perplexity.py` + `sonar.py` into one `SonarLane(base_url, model_table, provenance)` —
two configurations of one backend, not two backends; the 402 drift disappears by construction.
(4) Make `domain` mean *host*, everywhere, and let provenance ride its own field — then
`hostOf`, `source_tier`, and `deriveSourceType` all stop needing to know about Perplexity.
(5) Replace the six-step `derive_semantics` pipeline with a `_LEGS` tuple, and assert
`emitted_keys ⊆ _PROMPT_KEYS` in the test that already pins the sibling literals.

---

## Questions to consider

- The SSRF guard is a *function the caller must remember to call*. What would it cost to make it
  impossible to fetch an unvalidated URL from this package at all — a `SafeFetcher` that owns the
  client and has no public escape hatch?
- `cost` currently reports a structural zero. Is "not metered" a state the brief contract should be
  able to express, rather than something the frontend infers from a falsy number?
- `rank_sources` and `priority_note` both encode source authority. If the tier table were a single
  function returning `(tier, reason)`, could the brief show the user *why* `[1]` is primary —
  turning an invisible heuristic into part of the data-trust story instead of a hidden risk?

---

**Snapshot:** skipped — `scripts/critique-storage.mjs` not resolvable from this worker
(`persist=false` per the skill's pre-check). No `.aposd/critique/ignore.md` present.
No temp files written outside the two census outputs. Repo untouched except these two files.

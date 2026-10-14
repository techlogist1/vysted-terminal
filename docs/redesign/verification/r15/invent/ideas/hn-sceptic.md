# R15 Stage 4 — ideation seat `hn-sceptic`

Model: `claude-fable-5-1`. Date: 2026-09-19. Read-only thinking; nothing built.

Seat: the Hacker News commenter who has seen a hundred "AI for finance" launches and opens the
thread with "so it's a yfinance wrapper with a system prompt?".

## 0. The sceptic's read of what exists (so the ideas are not fantasy)

**What is a wrapper here.** The chat loop, the 12 investor personas
(`sidecar/agents/buffett.json` is a system prompt plus `price_data, fundamentals, news`), the
LLM adapters, the dockview cockpit. Any competent team ships these in a month; the census logs Fincept
Terminal advertising "37 AI agents" (`census/world/openbb-kite-mcp.md` §5).

**What is actually new — and mostly invisible.** A family of deterministic witnesses with a
"DISCLOSE, never substitute" contract, each born from a measured failure:

- growth scalar vs recomputed quarterly YoY — ICICIBANK +66.9% provider vs +2.0% computed
  (`sidecar/services/growth_check.py:3-12`);
- ownership vs the exchange SHP — institutions 141x overstated on a BSE micro-cap
  (`sidecar/services/ownership_check.py:9-15`);
- reported vs adjusted earnings basis — TI at PE ~460 vs ~43.9, both "correct"
  (`sidecar/services/earnings_quality.py:3-11`);
- market cap vs a non-provider BSE share count (`sidecar/services/market_cap_witness.py:12-18`);
- 52-week range vs exchange-direct history (`sidecar/services/research/range_check.py:12-17`);
- identity (provider name vs resolver master) (`sidecar/services/identity_crosscheck.py:1-17`);
- per-field provenance with `ok / withheld / unavailable` (`sidecar/models/fundamentals.py:19-43`).

That is the moat, and the product hides it inside one JSON leg of one panel.

**Where the hallucinations still hide** (verified by opening the code):

1. The only deterministic number firewall — `company_narrative._verify_text`
   (`sidecar/services/company_narrative.py:209-248`) — guards ONE surface (the overview
   narrative: its only call sites are `company_narrative.py:487,491` inside `generate_narrative`,
   whose sole caller is `routers/fundamentals.py:168`). Chat prose and brief prose get at most
   an LLM spot-audit capped at 8 claims (`sidecar/services/research/citecheck.py:40`), and only
   when 15 s of wall budget remain (`citecheck.py:43`). An LLM grading an LLM, sampled.
2. That firewall's regex speaks dollars and K/M/B/T only
   (`company_narrative.py:64-77`); `grep -i 'crore|lakh|₹|inr'` on the file returns nothing. In an
   India-first product the one hard numeric gate cannot read a rupee figure in crore.
3. The evidence that a claim was verified against is thrown away. The raw-evidence store is an
   in-memory dict for the life of the run (`sidecar/services/research/deep.py:331-354`). The brief
   keeps a URL. The repo itself documents that BSE attachment URLs migrate
   (`AttachLive` works, `AttachHis` 404s for a current filing —
   `sidecar/services/corporate_disclosures.py:21-23`). A receipt that 404s in six months is not a
   receipt.
4. The PDF lane knows which pages it used (`pages_used`, `sidecar/services/search/extract.py:506`)
   and then flattens paragraphs across pages (`extract.py:517-518`), so a page number can never
   reach a citation.
5. The claims ledger records `{symbol, metric, value, statedAt}` with no source, provider, basis
   or as-of (`types/research-space.ts:34-43`). It remembers WHAT it said, not WHY it believed it.
6. Witness conflicts ride the brief's `structured` leg and evaporate. Nothing accumulates them,
   so the app has measured its own providers being wrong for months and knows nothing about it.

**Why local-first matters, mechanically (not as a slogan).** The BYOK key lives only on the
in-memory task closure, never persisted (`sidecar/services/run_manager.py:36-38`), and the
sidecar cannot read the keychain. Consequence a cloud product never faces: **an LLM cannot sit in
an unattended watch loop here.** Anything that "watches" must be deterministic and free, and the
model is called only when the human is present with their key. That is a constraint worth
designing around rather than apologising for: it kills the two things sceptics hate about agent
watchers (a meter running while you sleep, and a model hallucinating alerts at 3 am).

There is no scheduler or trigger anywhere: `grep -i 'trigger|schedule|interval'` over
`workflow_engine.py` and `run_manager.py` hits only the "self-pause trigger is out of scope" note
(`run_manager.py:34`); workflow nodes have `flow.sleep` and `action.notify_desktop`
(`sidecar/services/workflow_nodes/builtin.py:325,400`) but nothing that starts a flow. The OS
notification bridge exists and works (`src/lib/desktop-notification.ts:45-56`).

**Design rule that runs through every idea below:** the LLM may LABEL, RANK and NARRATE; it may
never be the origin of a digit, a quote, or an alert. Every idea has a zero-token floor that still
does something useful with no key at all.

Scenes below use real tickers from the R15 battery and the in-tree witness docstrings; any figure
inside a scene that is not cited to a file is illustrative, not data.

---

## Idea 1 — Number Firewall: no digit without a parent  *(not on the floor list)*

**User moment.** You ask the free-lane model about Jumbo Bag (BSE: JUMBO; profit CAGR 82% on
sales CAGR 6.8%, per the R15 battery). It answers "OPM expanded to 14.2% on revenue of ₹168 Cr".
₹168 Cr has a faint underline — hover shows `fundamentals · yfinance · as of 09:41 · ok`. "14.2%"
is struck through with a chip: *no tool result in this turn contains this figure*. You did not
have to be suspicious; the terminal was suspicious for you.

**Mechanics.** Generalise `_verify_text` (`company_narrative.py:209`) from one surface to every
agent turn. Source set = every numeric leaf of every tool result in the turn (the runtime already
holds them in the loop — each tool result is appended as a `role="tool"` message at
`sidecar/services/agent_runtime.py:1571-1587`) plus the `field_meta`-approved
fundamentals. Three verdicts per numeric token: **sourced** (matches a leaf within the existing
tolerances, `company_narrative.py:49-50`), **derived** (equals `a/b`, `a-b`, `(a-b)/b`, `a*b` over
two sourced leaves — brute force, bounded by a leaf cap so it stays well under a second in Python;
the hover shows the formula), **orphan** (struck, never silently deleted in chat; redacted in brief metric prose).
New: ₹ / Rs / crore / lakh / Cr / L / mn scale tokens in `_NUMBER_RE` (today `$` + K/M/B/T only,
`company_narrative.py:64-77`); a `number_receipts` array on the final stream event; a renderer in
`src/modules/chat/chat-markdown.ts` and `src/modules/research/brief-blocks.tsx` (`BriefBody`,
`brief-blocks.tsx:1061`). Runs after the
stream completes, deterministic, zero tokens, no wall-budget gate (unlike `citecheck.py:43`).

**Why it is Jarvis.** Receipts — at the granularity of the digit, not the paragraph. Every other
product's citation says "this paragraph came from somewhere"; this says "this number came from
here, that one came from nowhere".

**60-second demo.** Same prompt, two models side by side (a strong one, a free one). The free one
invents a margin; the strike-through appears live. Then ask "what's the PE if profit halves" —
the answer's number shows *derived: 43.9 × 2*. Close on the token meter for the check itself: 0.

**Lifecycle cost.** Tolerance tuning and new number formats ("1,05,130" Indian grouping — Elcid
is in the battery for exactly this). A parity test vector file, as `screener_formula` already does
for its TS twin. Low: no network, no model, no upstream.

**Biggest risk.** False orphans on legitimate model arithmetic beyond one binary op (CAGR,
three-term sums) train users to ignore the strike. Mitigate: orphans from a turn with NO tool
calls are labelled "from model memory", not struck; add CAGR as a recognised derivation.

**Size.** M.

---

## Idea 2 — Evidence Locker: the filing you relied on, hashed and kept  *(not on the floor list: the floor asks for the page; this is about the page still existing, and still being the same page)*

**User moment.** In March you bought Naperol Investments on a holding-company-discount thesis; the
brief cited the investment schedule in the annual report. In September you reopen the brief on a
train with no signal. Click `[3]` — page 41 opens from disk, with `sha256 9f2c…` and
"fetched 2026-03-14 from bseindia.com". Below it: *the exchange now serves a different file at this
URL (revised 2026-05-02) — 2 numeric lines changed on this page*.

**Mechanics.** Persist what `_Findings.evidence` already collects and discards
(`deep.py:331-354`). New sidecar store `evidence_locker` (SQLite + zlib page text; PDF bytes
optional): `{sha256, url, fetched_at, page_no, text}`. Keep page identity through
`extract_pdf_text` — it already computes `pages_used` (`extract.py:506`) and loses it at
paragraph assembly (`extract.py:517-518`); return `[(page_no, paragraph)]` instead. Citations gain
`locker: {sha256, page}`; `BriefSource` (`types/brief.ts:230`) gets two optional fields (additive,
`types/data.ts`-style mirror; not the plugin contract). On any later fetch of the same URL a hash
mismatch emits a `filing_revised` event with a page-text diff. Retention: text-only by default
(a 60-page filing is ~100 KB compressed), LRU under a cap, but rows cited by a saved brief, claim,
tripwire or promise are PINNED.

**Why it is Jarvis.** Memory and receipts that survive the source. Also the one thing a cloud
product structurally will not do for you: keep YOUR evidence under YOUR control, offline.

**60-second demo.** Wi-Fi off. Open an old brief. Every chip resolves to a page. Wi-Fi on, hit
"re-verify": 8 of 9 hashes match, one filing was replaced — show the diff.

**Lifecycle cost.** Disk (bounded by cap + pinning), one more SQLite file to migrate
(`CREATE TABLE IF NOT EXISTS` precedent in `runs_store.py:55`). pypdf text drift across versions
changes page text but not the PDF hash — hash bytes, not text.

**Biggest risk.** Scanned Indian filings have no text layer (`extract.py:352-355`,
`scanned_pages_note` at `extract.py:398`); the locker then holds a hash and an honest "image-only page" marker, and
the receipt is weaker. Say so; do not OCR in v1.

**Size.** M.

---

## Idea 3 — Claim Checker: paste anyone's number, get a verdict  *(not on the floor list)*

**User moment.** A finfluencer thread says "Tilaknagar at 460 PE is insane, ROE barely 1%". You
paste it into the composer. Card: **PE 460 — DIFFERENT BASIS, not wrong.** Reported PAT ₹20.9 Cr
carries one-off acquisition and gratuity charges; normalized ~₹232 Cr gives ~43.9. Both figures,
both bases, the unusual-items line as the receipt. **ROE 1% — same seam.** The terminal did not
argue with the tweet; it showed which ruler each side was using.

**Mechanics.** The ULTRA cross-check already does extract → re-check → verdict, but only for
Vysted's OWN briefs and against fresh WEB evidence (`sidecar/services/research/verify.py:1-16`).
Point the same shape at foreign text and at the STRUCTURED witnesses instead of the web. Pipeline:
(1) numeric tokens extracted deterministically (Idea 1's regex); (2) ONE small LLM call binds each
token to `{symbol, metric ∈ enum, period}` — and the bound value must be a verbatim substring of
the pasted text, checked in code, so the model can label but never introduce a number; (3) each
bound claim runs against `fundamentals` + `field_meta`, then the matching witness
(`earnings_quality`, `growth_check`, `ownership_check`, `market_cap_witness`, `range_check`);
(4) verdicts: MATCHES / CONTRADICTED (both values + receipt) / DIFFERENT BASIS
(`conflict_kind: "definitional_expected"`, `types/brief.ts:121`) / STALE / CANNOT CHECK. New: one
`read_handler` capability `check_claims` in `catalog.py` — which auto-projects to MCP
(`mcp_server.py:146-148`), so Claude Desktop or Cursor can call Vysted as a fact-checker over the
existing `--mcp-stdio` entrypoint (`docs/MCP_INTEGRATION.md:78-97`). No key → steps 1, 3, 4 still
run on claims the user binds by hand.

**Why it is Jarvis.** Receipts turned outward. Jarvis is not the one making claims; he is the one
who checks everybody else's — including other AIs'.

**60-second demo.** Paste a Perplexity Finance answer about a BSE SME name. Three green, one red
with both numbers, one amber "different basis". Then from Claude Desktop: "check this broker note
with vysted" → same verdicts over MCP.

**Lifecycle cost.** The metric enum and the witness set grow together; every new witness is a new
verdict for free. Upstream dependency is only what fundamentals already depends on.

**Biggest risk.** Binding errors (wrong period: TTM vs FY vs MRQ) produce confident false
"CONTRADICTED". Mitigate: period is part of the verdict line, and an unbound period downgrades to
CANNOT CHECK rather than guessing.

**Size.** M.

---

## Idea 4 — The Scoreboard: the app measures its own wrongness, in the repo and in the app  *(not on the floor list)*

**User moment.** You ask "how much should I trust your market cap on SME names?" and the agent
answers from data, not vibes — you were about to size a position in Chatterbox Technologies (BSE
SME): "On the 11 BSE SME names you have opened, the provider market cap
disagreed with the exchange-derived witness by more than 10% on 4. Treat it as approximate; the
witness figure is shown beside it." On GitHub, the README's first table is the same idea at
release scale: 24 hostile names × ~25 fields, green/red, failures left in.

**Mechanics.** Two halves, one principle.
(a) **In-app conflict ledger.** Every conflict `derive_semantics` emits
(dividend, growth and ownership legs at `sidecar/services/research/semantics.py:292-350, 362-440,
537-596`; earnings-quality, range and market-cap-witness legs at `semantics.py:666, 748-784, 787`;
all gathered by `derive_semantics`, `semantics.py:992`) is appended to a local SQLite
table `{ts, symbol, segment(mainboard/SME/bank/holdco), field, provider, provider_value, witness,
witness_value, kind}` instead of dying with the brief. A tiny aggregate feeds the terminal preamble
next to the prior-stated-values block (`agent_runtime.py:329-353`) and a Settings → Trust table.
(b) **In-repo trust bench.** `pnpm trust-bench`: boot a headless sidecar, GET every field for the
R15 battery (`docs/redesign/verification/r15/battery/manifest.json`, 24 names, outside-truth packs
with `as_of` + `source_url`), diff with as-of-aware tolerances, write `TRUST.md`. Zero LLM calls.
CI runs it per release; the diff between two releases' `TRUST.md` IS the changelog sceptics read.

**Why it is Jarvis.** Memory of his own mistakes. "I have been wrong about this kind of thing
before" is the most un-chatbot sentence an assistant can say.

**60-second demo.** Open `TRUST.md` on GitHub: show a red cell and the issue linked from it. Open
the app: same names, the red cell is a visible conflict card, not a silent wrong number. Ask the
agent the trust question above.

**Lifecycle cost.** Real. Outside-truth packs age; a quarterly refresh by an agent is the keep-alive
cost, and packs older than N days must grey out rather than fail. The ledger is bounded by age.

**Biggest risk.** Publishing your failures is a gift to competitors' marketing. The sceptic's
answer: every rival has the same failures and no table; the first honest table wins the thread.

**Size.** M (bench S, ledger S–M).

---

## Idea 5 — Tripwires: your kill-criteria compiled to code, zero tokens while watching  *(floor: thesis-vs-filings + watching; the sceptic's twist is that the model is never in the loop)*

**User moment.** Your note on Fusion Finance ends with "I'm out if promoter stake drops 2 points,
if the auditor changes, or if GNPA prints above 5% twice." The agent proposes three compiled
tripwires in the diff/accept gate; you accept two and edit one. Eleven weeks later, lid opens:
OS notification — *FUSION: tripwire 2 fired — "Resignation of Statutory Auditor", BSE, filed
yesterday 19:12*, with the PDF page from the locker. No model ran. You click "explain", and only
then does your key get used.

**Mechanics.** Thesis lives where notes already live (`write_note` scope = symbol,
`catalog.py:1374-1395`). The agent's one job is compilation: prose → predicates in a small grammar.
The grammar exists — `screener_formula.py` is a no-`eval` recursive-descent boolean expression
language with a hand-mirrored TS twin for the editor (`sidecar/services/screener_formula.py:1-30`);
extend its FIELD set with event fields (`announcement.category`, `announcement.headline ~ "..."`,
`promoter_percent.delta_4q`, `results.opm`) rather than inventing a DSL. Compiled tripwires go
through the existing proposed-changes gate (`src/store/proposed-changes.ts:92`) like every other
mutation. Watcher = one sidecar asyncio loop (registered and torn down in the `app.py` lifespan
next to `run_manager.shutdown()`, `sidecar/app.py:153`), polling `get_announcements` (`corporate_disclosures.py:265`),
shareholding and the results calendar for holdings ∪ watchlist, paced by the existing breaker
(`is_open` / `cooldown_remaining`, `sidecar/services/provider_health.py:140-151`) and the 15-minute disclosures TTL
(`sidecar/routers/disclosures.py:39`). Fire → `desktop-notification.ts:56` + a card carrying the
locker receipt. It needs no key, which is the point: the key is unavailable unattended by design
(`run_manager.py:36-38`).

**Why it is Jarvis.** Initiative and watching, with memory of what YOU said would change your mind —
and an audit trail showing the alert came from a predicate you approved, not a model's mood.

**60-second demo.** Write a two-line thesis. Accept the compiled predicates. Replay a fixture
announcement feed (tests already carry NSE/BSE fixtures) — notification fires with the page.
Show the token meter: 0.

**Lifecycle cost.** Exchange endpoints change (the cookie-dance lane is fragile by nature). The
watcher must say "blind since <ts> on NSE" rather than stay silently quiet — silence is the
failure mode that kills trust in a watcher. Laptop sleeps → see Idea 6.

**Biggest risk.** Category strings and headline wording are unstandardised across NSE/BSE; a regex
tripwire misses "Cessation of auditor" when you wrote "resign". Mitigate with a curated synonym
table per event class, shipped as data, plus Idea 6's "unmatched but material" bucket.

**Size.** M–L.

---

## Idea 6 — Lid-closed honesty: a catch-up that states its own blind spots  *(not on the floor list)*

**User moment.** Friday 18:02 you close the lid. Monday 09:10 you open it. One card: *Since Fri
18:02 — 14 symbols checked, 12 fully covered. 3 items matter to you: Jonjua Overseas bonus 7:24
allotted (you hold 1,200 → your share count and cost basis per share change; the chart before
4 Sep is pre-bonus); Dhanlaxmi Bank board meeting for results on the 24th; Amal Ltd — nothing.
**Blind spots:** NSE feed refused twice for VIYASH; BSE returned its full window for FUSION and the
oldest item is newer than Friday, so earlier items may exist — fetched one page deeper, now
covered.*

**Mechanics.** A laptop that sleeps cannot watch; it can only reconstruct. So make reconstruction
a first-class, accountable operation. New: `last_seen_at` + an announcement seen-ledger
(`(symbol, headline-hash, date)` — the dedup key already exists,
`corporate_disclosures.py:251`). On wake/launch: for holdings (`portfolio_db.py:27-35`, which has
`cost_basis` and `quantity`) ∪ watchlist, fetch announcements; **coverage proof** per symbol:
covered iff the oldest returned item predates `last_seen_at` or the feed returned fewer than
`limit`; else page deeper or declare the gap. Per-lane failures are already reported honestly in
`AnnouncementsResponse.errors` (`sidecar/models/announcements.py:54-56`) — surface them instead of
swallowing. Materiality rank is deterministic: category weight × position weight. Zero tokens; the
model is offered only as "explain this one".

**Why it is Jarvis.** "While you were away, sir" — plus the part fiction leaves out: "and here is
what I could not see." Initiative with epistemic honesty.

**60-second demo.** Set `last_seen_at` back 5 days on the isolated sidecar. Launch. The card
renders with a coverage line and one declared blind spot (induced by blocking one lane via
config). Compare: every alerting product on earth shows nothing when its poller fails.

**Lifecycle cost.** Low. Seen-ledger pruned by age (180 d). Shares the poller with Idea 5.

**Biggest risk.** Noise. Indian small-caps file a lot of boilerplate (trading-window closures,
newspaper clippings). The category weight table needs a "routine" class that is counted, not
listed — "9 routine filings hidden".

**Size.** S–M. Ships before Idea 5 and de-risks it.

---

## Idea 7 — Promise Ledger with the dog that did not bark  *(floor: guidance vs delivery; twist: verbatim-quote rule + the FADED state)*

**User moment.** Before Route Mobile's Q3 call the panel shows five open promises, each a
management sentence in quotation marks with a page chip. Two are KEPT, one BROKEN ("18% margin" →
printed 14.2%), and one reads **FADED — last mentioned Q4 FY25; absent from three consecutive
calls.** Nobody announces that a plan has died. They just stop saying it.

**Mechanics.** Transcripts and investor presentations already arrive as `attachment_url` rows and
are read by the PDF lane (`sidecar/services/research/disclosures.py:4-5,19-22`). New store
`promises {symbol, quote, locker_sha, page, metric?, target?, deadline?, stated_on, status}`.
Extraction is an LLM call under the same rule as Idea 3: **the quote must be a verbatim substring
of the locker page text or the row is rejected in code.** The model can choose which sentence is a
promise; it cannot write the sentence. Resolution: numeric promises resolve deterministically
against results; FADED is a pure text search of key terms across the last N locker transcripts —
no model. Depends on Idea 2.

**Why it is Jarvis.** Memory across quarters, with receipts on both ends (the promise page and the
delivery page).

**60-second demo.** Pick a name with 6+ calls. Timeline of promises; click BROKEN — two pages side
by side. Click FADED — a sparkline of mentions per call going to zero.

**Lifecycle cost.** Medium. Coverage is the honest problem: many small-caps hold no concalls or
file scanned transcripts. The panel must state "2 of 8 quarters have a readable transcript" rather
than imply completeness.

**Biggest risk.** Hedged management language ("we aspire to", "directionally") makes KEPT/BROKEN a
judgement call; restrict auto-resolution to promises with a number and a date, leave the rest
OPEN with the quote.

**Size.** L (M if restricted to numeric guidance).

---

## Idea 8 — Forkable research: a brief you can `git diff`, replay without an LLM, and attach to a bug report  *(not on the floor list)*

**User moment.** You post your Elcid Investments work to a forum as `elcid.vybrief`. A stranger
opens it in their own Vysted, presses **Verify**, and sees: *9 structured figures — 7 reproduce
exactly, 2 drifted with price (shown); 4 cited filings — 4 hash-match; 1 conflict card present in
the original and still present.* They did not need your key, your model, or your word.

**Mechanics.** A brief already carries the parts: typed `structured` legs with provenance, derived
metrics + conflicts (`types/brief.ts:47-176`), and an execution record — run id, requested depth,
the loop that actually ran, degraded reason (`types/brief.ts:185-200`). Bundle = that JSON +
number receipts (Idea 1) + locker hashes (Idea 2) + the tool-call trace, no secrets (the key never
persists anywhere to begin with, `run_manager.py:36-38`). **Verify** = deterministic replay of the
structured tool calls + re-hash of cited filings; zero tokens. One format, three uses: share,
re-verify your own old work, and the redacted diagnostics bundle a user attaches when "the numbers
look wrong" — which today would need someone to add instrumentation first.

**Why it is Jarvis.** Receipts that are portable. Also the answer to "why should I trust a
stranger's AI research": you don't; you replay it.

**60-second demo.** `git diff` two versions of the same brief a quarter apart — the diff is
readable. Then Verify on a fresh machine with no API key configured.

**Lifecycle cost.** A versioned file format is a forever promise; keep it a thin envelope over
contracts that already exist and carry a `format_version`. Replay breaks when a provider dies —
which is a feature: the verify report says which leg is no longer reproducible.

**Biggest risk.** Most retail users never share a file. That is fine: the format pays for itself
as the diagnostics bundle and the self-re-verify button; sharing is the upside.

**Size.** M (after Ideas 1–2).

---

## Idea 9 — Personas on probation: forecasts logged, resolved, Brier-scored  *(not on the floor list)*

**User moment.** You ask the Graham persona about Crest Ventures. Its header reads *Graham · 14
resolved calls · calibration 0.61 · no demonstrated edge over the base rate yet.* It must end with
one falsifiable, dated statement about fundamentals ("FY27 H1 book value per share above ₹X").
Six months later that line resolves itself, green or red, in the persona's record.

**Mechanics.** Today a persona is a prompt and three tools (`sidecar/agents/buffett.json`). Add a
structured tail to persona output `{symbol, metric, comparator, value, by_date, confidence}`,
validated in code (metric ∈ resolvable enum; confidence ∈ [0.5, 0.99]). Store locally; resolve
deterministically on wake against fundamentals/results (shares the Idea 6 wake hook); compute Brier
score and a calibration curve per persona and per custom agent (`sidecar/services/agents_store.py:42`). The copilot may
quote a persona's record when routing to it. Forecasts are about reported fundamentals, never
price targets or buy/sell — and nowhere near the order surface.

**Why it is Jarvis.** Memory plus humility. It also answers the thread's most predictable jab —
"12 billionaire cosplay prompts" — with the only honest reply: a scoreboard, including "n is too
small to say".

**60-second demo.** Seed 40 back-dated forecasts from fixtures; show two personas with visibly
different calibration curves, then a custom agent built in Agent Builder entering the same league
table.

**Lifecycle cost.** Resolution coverage depends on results data for small-caps; unresolved-forever
forecasts must expire as VOID, not linger. Small n for months — the UI must refuse to show a score
under n=10.

**Biggest risk.** Optics of "predictions" in a finance app. Keep it to reported fundamentals,
label it an evaluation harness for agents, and never aggregate forecasts into a recommendation.

**Size.** M.

---

## Strongest single idea

**Idea 1 + Idea 2 as one guarantee — "no digit without a parent, no parent without a page" — with
Idea 3 (Claim Checker) as its public face.** If forced to one: **the Number Firewall.**

Why a rival cannot copy it in a month: the firewall is only as good as the source set behind it,
and Vysted's source set is not "whatever the API returned" — it is provider values that have
already passed a correctness gate, carry per-field `ok/withheld/unavailable` status, and sit beside
six independent witnesses each built from a measured, named failure on a real Indian ticker
(ICICIBANK growth, TI earnings basis, RBA market cap, BI/PML 52-week range, Gujarat Gas identity,
the 141x institutional overstatement). A retrieval-first research product has a harder time bolting this on: per the census its figures
ride a third-party feed and retrieved passages (`census/world/perplexity-screener.md` §D2), so it
does not hold a typed, provenance-tagged source set at digit granularity to check prose against;
and a per-answer-metered product (Screener AI, ₹10–30 per answer, same file §C1) has little reason
to ship a pass whose visible effect is striking out its own output. A clone can copy the regex in
a day; without a witness layer underneath, the honest result is that it strikes out its own answers.
The regex is trivial; the year of battery-driven, failure-by-failure witness work underneath it is
the part that does not copy. And it is the one feature whose demo survives an HN thread: you do not
ask anyone to believe the model — you show the model being caught.

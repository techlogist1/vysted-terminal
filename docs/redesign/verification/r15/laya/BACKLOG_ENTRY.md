# Filing watcher: System 1 triage in front of the BYOK model

R15 scope change 2 — Laya groundwork. Verification evidence only: no Laya
code ships in this release, and this entry itself belongs only in
`docs/redesign/verification/r15/laya/`, never in a release document or
inserted into `docs/redesign/verification/r15/invent/BACKLOG.md`.

## 1. Design sketch

A local triage pass sits in front of the BYOK model in the ingestion path,
not the chat path. Every NSE/BSE corporate announcement, pledge change,
bulk or block deal and rating action is scored against three things the
user already has: their holdings, their watchlist, and their written
thesis for the name (where one exists). The triage pass runs cheap and
local on every item; it wakes the BYOK model only for the item shapes that
already look decision-relevant — a promoter-pledge jump on a held name, a
bulk/block deal in size against the float, a rating downgrade, a filing
whose text plausibly contradicts a stated thesis line. Everything else is
filed silently. Every item that does surface (whether from the local pass
alone or after a BYOK read) carries a receipt: a direct link back to the
source filing page on the exchange (NSE/BSE) so the user can check the
primary document, never just the paraphrase.

## 2. Ingestion today

Grepped `sidecar/` for NSE/BSE corporate-announcement ingestion
(announcements, corporate actions, pledge, bulk/block deal, rating feeds).
**It already exists — this is not itself a build:**

- **Announcements** (merged BSE+NSE, deduped, credit-rating filings
  included as one of the canonical kinds) —
  `sidecar/services/corporate_disclosures.py:516` (`get_announcements`),
  kind map at `sidecar/services/corporate_disclosures.py:362`
  (`"credit rating": "credit_rating"`), routed at
  `sidecar/routers/disclosures.py:49` (`GET /disclosures/announcements`).
- **Corporate actions** (NSE+BSE dividends/bonuses/splits/rights/buybacks)
  — `sidecar/services/corporate_disclosures.py:866`
  (`get_corporate_actions`), routed at
  `sidecar/routers/disclosures.py:102` (`GET /disclosures/corporate-actions`).
- **Bulk/block deals and SAST disclosures** —
  `sidecar/services/corporate_disclosures.py:919` (`DEAL_KINDS = ("bulk",
  "block", "sast")`) through `:1019` (`get_deals`), routed at
  `sidecar/routers/disclosures.py:120` (`GET /disclosures/deals`).
- **Promoter pledge** — carried on the shareholding-pattern feed,
  `promoter_pledged_percent` / `promoter_pledge_basis` at
  `sidecar/services/corporate_disclosures.py:1204-1205`, served from
  `get_shareholding` (`sidecar/services/corporate_disclosures.py:1075`),
  routed at `sidecar/routers/disclosures.py:82`
  (`GET /disclosures/shareholding`).
- **Rating actions** (broker rating changes, upgrade/downgrade/target) —
  a separate provider, `sidecar/services/analyst_ratings_extended.py:219`
  (`get_ratings_history`), served by `GET /fundamentals/{symbol}/ratings`
  per that file's module docstring (line 4).

What does **not** exist: any triage layer over this ingestion. All five
feeds are pull-on-demand per symbol today (no standing watch loop, no
holdings/watchlist/thesis join, no BYOK wake-up gate, no receipt UI). The
triage pass described in §1 is the build; the feeds it would read from
are not.

## 3. Fine-tune plan

Distil labels from a strong model over real announcements pulled from the
feeds in §2 (not synthetic text), covering the same task shapes as the R15
groundwork dataset (entity match, holding/thesis relevance, composer
intent). Tune the checkpoint on a GPU box — Apple-silicon MLX inference is
verified feasible for serving (see §7) but is not a training target.
Fit a calibration temperature on a held-out split before shipping any
probability the user or the BYOK model would act on — the groundwork smoke
test already surfaced an uncalibrated checkpoint in the wild (see §7), so
this step is load-bearing, not optional. Ship the tuned checkpoint in the
sidecar behind an opt-in setting, with the existing keyless/BYOK path kept
as the fallback when the setting is off or the checkpoint is unavailable.
Never make the local model the sole authority on anything the user sees —
it gates what reaches the BYOK model and, downstream, the user; it never
silently substitutes for either.

## 4. Licence

Verified and recorded in
`docs/redesign/verification/r15/laya/PACKAGE_VERIFICATION.md`:

> "license":"Apache-2.0 (laya, laya-mlx and the convaiinnovations/* HF
> weights). Upstream has no NOTICE file; laya-mlx ships a NOTICE crediting
> Convai Innovations, quoted in PACKAGE_VERIFICATION.md.", "repo":
> "github.com/NandhaKishorM/laya (laya; owner NandhaKishorM, PyPI user
> nandakishor, HF org convaiinnovations). laya-mlx is a community port at
> github.com/mizorewww/laya-mlx.", "verified":true

## 5. Windows route

`laya-mlx` is Apple-only (MLX has no Windows/CUDA backend). The Windows
route is the PyTorch `laya` package directly, or an ONNX export of the
same checkpoint — either way the calibration step in §3 must be repeated
per-backend since a temperature fit on the MLX build is not guaranteed to
transfer.

## 6. Baseline

From `docs/redesign/verification/r15/laya/BASELINE.md`
(`docs/redesign/verification/r15/laya/BASELINE.json`) — the current
keyless/rule-based decision volume per session, before any local model is
in the loop:

- Totals: 14 decisions/session, $0/session (all keyless).
- `entity_match`: 7 sites, 13/session, keyless, $0.
- `composer_intent`: 5 sites, 1/session, keyless, $0.
- `holding_relevance`: 0 sites — no decision point exists yet (all fields
  null/unknown in the baseline).
- `thesis_contradiction`: 0 sites — no decision point exists yet (all
  fields null/unknown in the baseline).

The two zero-site rows are exactly the two judgments this backlog item's
design (§1) would need — holding relevance and thesis contradiction have
no existing decision point to fine-tune against yet.

## 7. Groundwork so far

- Dataset counts (`docs/redesign/verification/r15/laya/DATASET.md`):
  `entity_match` 199, `composer_intent` 53, `holding_relevance` 87,
  dropped (all families) 27.
- Install smoke (`docs/redesign/verification/r15/laya/INSTALL.md`):
  feasible: true, peak RSS 947.9 MB, p50 47.44 ms, error: null. Scratch-only
  install (`laya-mlx==0.2.0` in an isolated venv/HF cache, never the repo
  or the product sidecar env); the smoke run also surfaced a non-fatal
  upstream calibration warning on the loaded checkpoint (temperatures
  outside `[0.5, 5]`, clamped) — direct evidence for why §3's calibration
  step is required before shipping, not a nice-to-have.

Verdict: pending MEASURE

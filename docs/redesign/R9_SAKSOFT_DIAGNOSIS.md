# SAKSOFT Q4 FY26 extraction — live diagnosis (2026-06-11, lead's probe agent)

Root cause, verified end-to-end against the real filings (artifacts in /tmp/saksoft-probe/):

**The results tables in the board-outcome PDF are raster scans with no text layer.**

- Primary filing (the engine's actual `disclosure_rows[0]`):
  `https://nsearchives.nseindia.com/corporate/SAKSOFT_25052026134035_OutcomeofBM25052026Signed.pdf`
  (2.49 MB, 27pp). Page map: p1–3 cover letter (digital text); p10 consolidated audited
  P&L — PURE IMAGE; p11 standalone key info + segments — PURE IMAGE; p14/p22 notes
  (digital, no figures); p15–21 scanned; p23–27 Reg-30 letters (digital).
- `extract.py:350` `page.extract_text()` → `""` on the table pages; `_pdf_page_score`
  (`:323`, applied `:364`) scores them 0.0 — **no keyword tuning can ever select them**.
- `:384` honesty error fires only when the WHOLE doc is textless; here 27,918 chars of
  letter text → `ok: True` → research believes it read the filing → "not parsed".
- `deep.py:596-606`: exactly ONE visit, always `disclosure_rows[0]`; no digit-density
  check, no fallback.
- `disclosures.py:50-53/:186/:44`: all 5 citable rows are same-style outcome scans
  (current + 4 prior quarters); the fully-digital **Q4-FY26 Earnings Presentation**
  (`…SAKSOFT_25052026215207_Saksoft_LtdQ4-FY26EarningsPresentation.pdf`, 18pp, full text
  layer, every figure verbatim) is band-1 and gets cut.
- BSE lane timed out live (NSE-only rows this run); BSE copy is the same scan.

## Fix (Team B implements; bounded, no new deps)

1. **Per-page honesty signal** (`extract.py`): count zero-text pages; expose
   `pages_empty` in the result; `visit_for_research` appends a one-line marker
   ("N of M pages have no extractable text — financial tables are likely scanned
   images") so the researcher prompt acts on it instead of asserting "not parsed".
   Key on PER-PAGE emptiness/digit density — NOT the all-pages-empty condition (this doc
   has partial text layers on p6/14/22).
2. **Digit-sparse fallback visit** (`deep.py:596`): if the first disclosure visit returns
   digit-sparse text (or `pages_empty > 0`), visit `disclosure_rows[1]` — one extra
   bounded fetch.
3. **Row mix** (`disclosures.py`): band-0.5 for `investor presentation|earnings
presentation|press release` in the same results window so rows[1] is the digital twin,
   not a fourth scanned outcome. (For this exact run: rows[0]=outcome scan,
   rows[1]=presentation surfaces every figure.)
4. **NO OCR** — blows the ≤120 MB onefile budget, not cross-platform. The digital-twin
   pattern (outcome=scan, presentation/press-release=digital) is the common Indian
   small-cap shape; the fallback covers it. (D31)
5. Secondary: budget assembly (`extract.py:373-380`) joins pages in document order —
   letterhead pages can starve a higher-scoring table page; consider score-order or
   per-page caps.

## Ground truth (gate 7 evidence floor — consolidated, audited, p10, cross-checked to the

digital presentation)

- Q4 FY26 revenue (net sales): **₹24,884.50 lakh** (₹2,488.45 Mn; +3.7% YoY)
- Q4 FY26 PAT: **₹3,593.09 lakh** (₹359.31 Mn; +19.7% YoY; margin 14.44%)
- Q4 FY26 EPS: **₹2.81 basic / ₹2.76 diluted**
- FY26: revenue ₹1,00,719.12 lakh (+14.1%), PAT ₹13,326.98 lakh (+22.5%), EPS ₹10.42
- Final dividend ₹0.55/share (55%), record date 2026-07-31, AGM 2026-08-07

Gate-7 reading (logged D31): the outcome PDF's tables are physically images; "figures
from the primary filing" is satisfied by figures cited to the company's exchange-filed
documents (outcome + its same-evening digital presentation on nsearchives), with the
honest scanned-tables marker on the outcome — never a false "not parsed".

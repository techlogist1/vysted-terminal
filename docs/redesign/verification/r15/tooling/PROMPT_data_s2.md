# Data battery — session-2 addendum (Stage B item 3)

Read this AFTER `COMMON.md` and the PACK section of `PROMPT_census.md`; for a refute item read
`PROMPT_refute.md` too. This file only states what session 2 changes or adds — it does not
repeat what those already say.

`BATTERY` = `docs/redesign/verification/r15/battery`. `CENSUS` =
`docs/redesign/verification/r15/census`. Your slot is `<id>` (e.g. `P7`); its manifest entry
is the row in `BATTERY/manifest.json` whose `slot` equals `<id>`.

## Models (session-2 rule, overrides any earlier example launch-args)

- `pack` and `diff` stages run **sonnet** at `effort: "high"`.
- `refute` stages run **opus** at `effort: "high"`.
- Never Haiku, never a fast-tier model, per `r15-fanout.js`.

## PACK stage — continue, never restart

Same spec as `PROMPT_census.md`'s PACK section. Before starting, check
`BATTERY/packs/<id>_<SYMBOL>.json`: if it already has real content (not a <1KB stub), you are
finishing a live pack — read what is there, keep every field that already carries a real
`value`/`source_url`, and fill only what is missing or a stub. Never discard collected fields
to "start clean." A legacy unslotted file (`AMAL.json`, `JONJUA.json`, `ONC.json`) may hold
prior work for your entity (careful: AMAL and SMR each name two different companies, one
Indian and one US — check `manifest.json`'s `name`/`exchange` before absorbing).

## DIFF stage — the 24 field diffs, subtle tier mandatory

Inputs: `BATTERY/packs/<id>_<SYMBOL>.json` (outside truth) and
`BATTERY/collected/<id>_<SYMBOL>.json` (in-app values, collected 2026-09-19 — read-only,
never re-collect by editing that file). If a field you need to diff is missing or looks stale
in the collected file, you may fetch ONE fresh read-only value from the isolated sidecar:
`curl -s 'http://127.0.0.1:52152/<route>'` (GET only; never restart it; the 19-Sep snapshot
stays the source of record for everything else — note in the diff which single field, if any,
you refreshed and when).

Diff EVERY field the PACK spec lists, and these are MANDATORY per name, not opportunistic:

- **shareholding** — promoter_pct, fii_pct, dii_pct, public_pct, pledged_pct_of_promoter, each
  against the AS-OF QUARTER the app shows, not just the latest one you found outside;
- **promoter holding** specifically (a sub-check of the above — promoter_pct + pledge, called
  out because it is the single most gameable number in an Indian small-cap);
- **declared vs paid dividends** — `dividend.last_declared_per_share` (+ record/ex date) is a
  DIFFERENT fact from `paid_trailing_12m_per_share`; diff both, never collapse them into one;
- **52-week range** — high AND low, each with its own as-of date (a 52w high/low pair is often
  stale in one leg and fresh in the other);
- **every as-of date** — for every field you diff, diff the as-of date too: a value can be
  right and its date wrong, or vice versa.

### When a mismatch is a finding, and when it is not

- A mismatch is a finding ONLY where outside truth exists for that field (a `source_url` in
  the pack). No outside value → the diff entry says `"no source truth"` explicitly for that
  field; this is never filed as a raw finding.
- **As-of skew** (both sides right, dated differently — e.g. app shows Q1 shareholding, pack's
  freshest source is Q4) is labelled `"as-of skew"` in the diff, never called wrong.
- **Definitional differences** (e.g. consolidated vs standalone, declared vs paid dividend,
  lakh vs crore already normalized correctly on both sides) are labelled
  `"definitional difference"`, never called wrong.
- Only a genuine mismatch — same field, same definition, same as-of period, different value —
  is a raw finding. Severity per `COMMON.md`/the collector spec: wrong value shown as true =
  critical/high; silent blank where the world has the value = medium; an honest labelled gap
  (missing field, stated "no source truth") = not a finding.

Outputs:
1. `BATTERY/diffs/<id>_<SYMBOL>.json` — one object per diffed field: `{field, app_value,
   app_as_of, outside_value, outside_as_of, outside_source_url, status: "match" | "mismatch" |
   "as-of skew" | "definitional difference" | "no source truth" | "app blank"}`, plus a
   top-level `subtle_tier_covered: true` once shareholding/promoter/dividends/52w/as-of dates
   are all present.
2. Raw findings file `CENSUS/raw/data-<id>_<SYMBOL>.json` — a JSON array using the
   `COMMON.md` raw finding shape, `raw_id` prefix `DAT-<id>` (e.g. `DAT-P7-1`), `area: "data"`,
   `subsystem: "<id>_<SYMBOL>"`, one entry per `mismatch`/`app blank` row (never for `match`,
   `as-of skew`, `definitional difference`, or `no source truth`). If there are zero
   qualifying rows, still write the file as an empty JSON array `[]` — `register.py` and the
   refute stage both expect the file to exist.

Continue-from-existing-file rule applies to both output files exactly as in `PROMPT_refute.md`.

## REFUTE stage (for diff waves only)

Follow `PROMPT_refute.md` in full, with one substitution: your raw file is
`CENSUS/raw/data-<id>_<SYMBOL>.json` and your output is
`CENSUS/refute/data-<id>_<SYMBOL>.json` (same basename, per `register.py`'s loader). You are
the pack's fresh sceptical reader: treat the PACK (`BATTERY/packs/<id>_<SYMBOL>.json`) as the
witness under cross-examination, not as ground truth by default — you may re-fetch ONE of its
cited sources yourself (`curl`, citing URL + fetch time) to confirm a disputed value before
ruling. If the raw findings file is empty (`[]`), read it, confirm the count is 0, and write an
empty verdict file `[]` to your output path — do not skip the stage.

## Web fetches for outside truth (session-2: WebSearch is exhausted, 200/200)

Do not call the `WebSearch` tool. Use `curl` (screener.in, BSE/NSE — see `COMMON.md`'s UA/
Referer note for bseindia.com's API host — company IR pages, annual reports, SEC EDGAR for US
names) or `WebFetch` on a known URL shape. Every source you use in a pack or a refute goes in
that file as `source_url` + a fetch-time note (`"fetched_at": "<ISO timestamp>"`); this is what
lets a later reader tell a 19-Sep snapshot from a fresh pull.

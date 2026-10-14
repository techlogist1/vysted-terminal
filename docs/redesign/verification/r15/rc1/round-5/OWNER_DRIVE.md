# OWNER_DRIVE — RC1 gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. One row per group, drawn mechanically from
each `drives/<group>.md`'s own first (Scored) table's verdict column — this collator does not
re-verify, re-drive, or re-judge any row. Rows whose verdict cell isn't a bare
ok/partial/broken/needs-gui token (e.g. a row citing a full test-suite pass count) are not
in the counted columns; see the group's own file for those.

| group | interactions scored | ok | partial | broken | needs-gui | finding keys | evidence dir |
|---|---|---|---|---|---|---|---|
| composer-chat | 7 | 7 | 0 | 0 | 0 | rc1-drive-composer-chat:1, rc1-drive-composer-chat:2 | `docs/redesign/verification/r15/surface/composer-chat/rc1/round-5/` |
| research-briefs | 8 | 8 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/research-briefs/rc1/round-5/` |
| screener | 13 | 13 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/screener/rc1/round-5/` |
| panels-layouts | 20 | 13 | 3 | 1 | 1 | rc1-drive-panels-layouts:1 | `docs/redesign/verification/r15/surface/panels-layouts/rc1/round-5/` |
| portfolio-notes | 7 | 7 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/portfolio-notes/rc1/round-5/` |
| settings-plugins | 6 | 6 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/settings-plugins/rc1/round-5/` |
| onboarding-stranger | 21 | 21 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-5/` |
| failure-inducer | 11 | 9 | 1 | 1 | 0 | none | `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-5/` |

## Census→rc1 deltas

Each group's own `drives/<group>.md` carries its full Census→rc1 deltas narrative
(a second table or bullet list headed `## Census → RC1 deltas`/`## Census/round-4 →
RC1-round-5 deltas` or equivalent); not reproduced here — see the per-group file directly.

## Drive raw output

Checked on disk: for every expected group, files under
`docs/redesign/verification/r15/surface/<group>/rc1/round-5/` other than `.md`.

- composer-chat: 25 raw file(s) present.
- research-briefs: 7 raw file(s) present.
- screener: 16 raw file(s) present.
- panels-layouts: 52 raw file(s) present.
- portfolio-notes: 12 raw file(s) present.
- settings-plugins: 21 raw file(s) present.
- onboarding-stranger: 24 raw file(s) present.
- failure-inducer: 11 raw file(s) present.

Cited-raw-file check (every raw evidence filename cited in each group's Scored table,
verified to exist in that group's surface dir): none missing — two candidate hits from a
naive filename scan (`research-briefs` row 10 citing `relevance.py`/`fast.py`/
`news_provider.py`, and `failure-inducer` row 03 citing `02-nokey.jsonl`) are a source-diff
reference and a census-round file reference respectively, not this round's raw-evidence
claims; both rows' actual round-5 raw files (e.g. `03-nokey.txt`) exist.

**No group is missing raw output.**

# rc1-battery-3 (Sonnet) — stage-c batch-5 + batch-13 shard

- Candidate sha: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`, worktree `rc1-cand` (read-only, source-only).
- Sidecar: booted from `rc1-cand/sidecar` against isolated data copy
  `scratchpad/rc1-data-rc1-battery-3`, `127.0.0.1:52343`, pid group
  `sh 62933` -> `python 62936` (`sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52343 --data-dir ...`).
  Booted once, reused for every set, killed at end of shard (confirmed `/health`
  refuses after kill).
- Method: for each id, read the register entry (`vysted-r15-register.json`) —
  repro/evidence/fix_shape/closure_evidence/note — then re-ran the ORIGINAL
  repro live against :52343 where practical (curl / in-process python via the
  candidate's own venv), or a source read confirming the fix_shape is present
  and wired into the live call path where a live trigger was impractical
  (funded-key-gated, GUI-only, or backend-logic-only with a well-known live
  proof already on file). No vitest/pytest suites run (heavy lane's job); one
  entry (R15-DATA-062) is `holds (ci_pinned: ...)` because its acceptance
  behaviour is pinned by a named test, not re-verified independently here.

## Sets

- **set-15** (`batch-5/W1-india-disclosures-agent-surface`, 11 entries): 10
  `holds`, 1 `blocked_env` (R15-DATA-056 — BSE SHP index Akamai 403s this dev
  IP, pre-existing at base; filed as an environment finding, not a regression).
- **set-16** (`batch-5/W2-resolver-market-data`, 9 entries): 9 `holds` (one
  annotated ci_pinned for R15-DATA-062).
- **set-17** (`batch-5/W3-agent-runtime-chat`, 9 entries): 8 `holds`, 1
  `blocked_env` (R15-AGENT-049 — register status is `blocked_tier4`, never
  reached "fixed"; nothing to regress-check from this lane).
- **set-18** (`batch-5/W4-platform-workflow-boundary`, 8 entries): 8 `holds`.
- **set-19** (`batch-5/W5-screener-earnings-sec`, 11 entries): 11 `holds`
  (two rows, R15-DATA-067 and R15-LIFECYCLE-017, are the same checks as
  set-15/set-18 respectively, cross-referenced rather than re-run twice).
- **set-64** (`batch-13/W2-w2`, 1 entry): R15-RESEARCH-007 `holds` — replayed
  batch-12's exact 18-URL adversarial acceptance list plus the 4 first-party
  IR controls against the candidate's `domain_tier`; all 18 non-primary, all
  4 controls stay `TIER_PRIMARY` — matches batch-14's certified PSL-backed fix.
- **set-65** (`batch-13/W3-w3`, 1 entry): R15-DOCS-017 `holds` — doc §3.3
  quoted counts (sp500 503, nse-all 3506, bse-all 5042, india-all 5891) match
  live loader counts from the candidate exactly; no drift since certification.

## Findings

One environment finding filed (`findings/rc1-battery-3.json`):
R15-DATA-056 — BSE shareholding SHP index blocked 403 (Akamai) from this dev
IP; disclosed pre-existing condition at base, not a candidate regression.

No regressions found across the 50 assigned entries (49 distinct + 2 cross-
referenced duplicates counted once each in their home set).

COVERAGE: 50/50 ids raw; no raw: none.

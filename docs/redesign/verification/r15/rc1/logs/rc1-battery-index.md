# rc1-battery-index working log

Parsed docs/redesign/verification/r15/stage-c/batch-{2..11}/PLAN.md writer sections
(`### Wk: name`) against each batch's VERDICTS.json `certified` list, then filtered
to ids whose current register status (vysted-r15-register.json) is `fixed`.

- Header parsing: bold entry headers (`**R15-... (sev)[, R15-... (sev)]*[.|:]**`) —
  some batches close with `:` (batch-2 style), others with `).**` (batch-3+ style).
  Regex captures the whole bold run and extracts every `R15-...` id inside, so
  multi-id headers (e.g. `R15-DATA-042 (high), R15-CODE-PLATFORM-053 (low): ...`)
  attribute correctly to the owning writer.
- Split-ownership entries (e.g. R15-AGENT-011 "sidecar half W1" + "frontend half W2"
  in batch-4) appear in both writers' sets — that reflects real joint work, not a
  parsing bug.
- 348 of 376 register-fixed ids are covered by a writer set. The remaining 28 are
  `fixed` but not certified-and-fixed in any batch's writer section (fixed by other
  means, e.g. a later reopen/refix not recorded under a `### Wk` heading, or a fix
  landed outside the batch-writer flow) — grouped into unplanned-N sets (<=12 ids
  each) by register `subsystem`.
- needs_gui / removed_with_feature entries never carry status `fixed`, so they drop
  out naturally; no explicit skip needed.

Output: docs/redesign/verification/r15/rc1/battery/INDEX.json, INDEX.md.

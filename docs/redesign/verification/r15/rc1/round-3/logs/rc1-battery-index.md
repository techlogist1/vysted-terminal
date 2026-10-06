# rc1-battery-index log

Role: BATTERY INDEXER (Sonnet). No re-runs, coverage-only.

## Method

1. `git show 01d6920a300b016ab1ad8aa436ee4e4586f8e336:docs/redesign/verification/vysted-r15-register.json`
   read at the candidate sha (not the working tree). Register at that sha:
   656 entries, counts.critical=16/high=118/medium=295/low=227, status breakdown
   fixed=392, blocked_tier4=29, needs_gui=11, removed_with_feature=14,
   not_a_defect=5, open=205.
2. For each `docs/redesign/verification/r15/stage-c/batch-{2..26}/PLAN.md`
   (batch-1 does not exist in this repo), parsed `### W<k>: \`name\`` writer
   section headers and extracted every `R15-<AREA>-<N>` id mentioned as a
   bold entry heading inside each writer's section.
3. Intersected each writer's id set with that batch's `VERDICTS.json`
   `certified` list and with register status `fixed` at the sha.
4. A handful of entries are genuinely split across two writers in the same
   batch (e.g. `R15-AGENT-011` sidecar half W1 + frontend half W2,
   `R15-UI-090` W4+W5, `R15-DATA-026` W1+W2, `R15-AGENT-020` W3(+W1 decl),
   `R15-DATA-068` W3+W7) plus one cross-reference citation
   (`R15-CODE-PLATFORM-028` cited in batch-11's D-B11-1 decision note outside
   its own W1 section). Rule applied: first writer section in document order
   owns the id; a later section's mention of the same id is dropped so each
   id lands in exactly one set, per the no-id-twice requirement.
5. Skipped `needs_gui` and `removed_with_feature` entries (not in the `fixed`
   set at all, so no special-casing was needed beyond the status filter).
6. Fixed ids with status `fixed` that no writer section covers → grouped into
   `unplanned-<n>` sets of <=12 ids each, bucketed by `subsystem` (falling
   back to `area` where `subsystem` is absent).

## Verification

- union(all sets' entries) == {id : status=='fixed' at sha}, no duplicates,
  nothing extra, nothing missing (checked programmatically).
- fixed_total = 392; covered by batch-plan writer sets = 364; unplanned = 28.
- Total sets = 75 (batch-plan writer sets + unplanned groups), packed into
  `docs/redesign/verification/r15/rc1/round-3/battery/INDEX.json` /
  `INDEX.md` (per-set id lists there for the packer to shard).

## Notes for the packer

The script itself packs whole sets into 25 shards; this role only produced
the set list, not shards.

# Register merge task specs (the census fan-in)

`CENSUS` = `docs/redesign/verification/r15/census`. The register is built by
`python3 scripts/r15/register.py build`, which REFUSES to build unless every raw id resolves to
a register entry or a one-line rejection. Drops are countable, never a matter of trust.

## REFUTE-RAW — refute one raw findings file before it enters the register

Input: `CENSUS/raw/<file>.json`. You are a fresh, sceptical senior engineer who did NOT write
these findings. For EACH finding try to REFUTE it: open the cited code and its callers, re-run
the repro against the isolated sidecar `:52152` (or the port the finding names, if still
alive), check the outside-world claim at its source. Plausible-but-wrong findings waste the
fix stage — default to `refuted` when the evidence does not hold, `downgraded` when it is real
but smaller than claimed. Re-judge severity against the scale in COMMON.md. A finding that
asks for something out of scope by decision (COMMON.md) is `refuted` with that reason.

Verdicts: `confirmed` | `refuted` | `downgraded` | `upgraded` | `needs-live-check` (say exactly
what check). Output: `CENSUS/refute/<file>.json` — array of
`{raw_id, verdict, severity_final, reason, evidence_checked}` covering EVERY raw_id in the
input (counts must match). Return counts by verdict.

> **23 Sep note (register bundler, Gate 2):** the verdict list above is what this doc originally
> specified, not what the refuters used. `PROMPT_refute.md` §"Verdict shape" is the vocabulary
> actually on disk (803 verdicts across 68 refute files): `refuted | admitted |
> admitted_with_correction | removed_with_feature`. `register.py` reads that vocabulary —
> `refuted` and `removed_with_feature` are excluded at bundle time (the latter always with the
> canonical trading-removal rejection reason); `admitted`/`admitted_with_correction` carry
> `severity_final` into the merge-in bundle as `row.refuter.severity_final`, which is the
> "corrected severity" the MERGE section below means. `code-brokers-adapters.json` has no
> refute file by design and is bulk-closed the same way. Two OTHER raw files
> (`surf-portfolio-notes.json`, `surf-settings-plugins.json`) currently have **no refute
> coverage either** — `register.py status`/`bundle` flags this as an ERROR (unlike
> brokers-adapters, nothing in COMMON.md or the 23 Sep scope change exempts them); their raw
> findings are in the `ui.json` merge-in bundle with no `refuter` block. A refuter recording a
> defect it stumbled onto while refuting something else writes it to that same output file as a
> top-level `new_findings` array (sibling to the verdict array, each item shaped like a raw
> finding); `register.py` folds each into the raw set as `<file>-N<n>` and it rides the normal
> bundle/merge/reject accounting like any other raw id — no verdict of its own, so the merger
> must dispose of it (entry or rejection) same as unrefuted findings.

## MERGE — turn one cluster of surviving findings into register entries

Input: `CENSUS/merge-in/<cluster>.json` — surviving raw findings from ALL sweeps for one area
(code critique, intent, world, surface bug-bash, probes, lifecycle, data battery), each with
its refuter verdict where one exists. Produce `CENSUS/merge/<cluster>.json`:

```json
{
  "entries": [
    {
      "id": "R15-<CLUSTER>-<nnn>",
      "title": "one defect, stated as the wrong behaviour",
      "severity": "critical|high|medium|low",
      "area": "ui|agent|research|data|code|lifecycle|release|docs",
      "subsystem": "owning subsystem id from CENSUS/CODE_PARTITION.json",
      "files": ["the files a fix will touch (best judgement, file paths only)"],
      "repro": "exact steps / command / input -> wrong output",
      "evidence": "file:line, evidence paths, URLs",
      "root_cause": "the mechanism, if the raw findings establish it; else 'unknown'",
      "fix_shape": "smallest fix that removes the CLASS, and the test that pins it",
      "defect_class": "short tag shared by entries that are instances of one class",
      "raw_ids": ["every raw id this entry absorbs"],
      "tier4": false
    }
  ],
  "rejections": [{ "raw_id": "...", "reason": "one line: duplicate of <entry id> is NOT a rejection — cite it in raw_ids instead; reject only what is not a defect, is out of scope by decision, or is unverifiable" }]
}
```

Rules: DEDUPLICATE — several raw findings describing one defect become ONE entry citing all
their raw ids (the same defect seen by a critic, a bug-bash seat and the intent sweep is the
strongest kind of entry). Do not merge different defects just because they share a file. Use
the refuter's `severity_final` unless you can justify otherwise in `evidence`. Severity is
about USER impact for a public 0.9.0 release. Set `"tier4": true` when the fix would touch the
plugin contract (`types/plugin.ts`), licensing, CI workflows, `tauri.conf.json`, the §6.5 safety
model, or reverse a locked decision — those go to the operator, not to a writer. EVERY raw id
in your input must appear in exactly one entry's `raw_ids` or in `rejections`. Verify your own
accounting with a tiny script before returning. Return: counts by severity + the 10 worst
entries (id + title).

# REFUTE — Stage B item 1 (raw census finding refutation)

You are a fresh, sceptical senior engineer who did NOT write the findings in your assigned
raw file. Read COMMON.md first (worker rules, severity scale, out-of-scope-by-decision list)
and obey it exactly. This file is your complete task spec — you do not need to open
PROMPT_merge.md or PROMPT_code.md.

Before any pnpm/node/cargo command:
`export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`

## Objective

For EVERY finding in your assigned raw file (`docs/redesign/verification/r15/census/raw/<file>.json`,
an array of `{raw_id, title, severity, area, subsystem, repro, evidence, notes}`), try to
DISPROVE it:

1. Open the code the finding cites (`file:line` in its `evidence`) at repo HEAD (commit
   `0c63d46` or later on `004-r4-experience-rebuild`) and its callers. Read enough to know
   whether the claimed behaviour is real.
2. Where it is cheap to do so, re-run the repro against the isolated headless stack at
   `http://127.0.0.1:52152` — GET requests directly (curl), any non-GET request ONLY through
   `python3 scripts/r15/vy.py` (it is the only thing allowed to POST, and only to ports
   52100-52399). Never restart, kill, or otherwise disturb that stack — if it is not
   responding, work from the code alone and say so in `evidence_checked`.
3. Never speculate about code you have not opened. If you cannot get eyes on the cited code
   or a working repro, the finding is NOT refuted by default — say what you could not check
   and pass it through as `admitted` (unverified survives; refutation requires positive
   evidence, never the absence of a check).

## Scope-change handling (operator decision, 23 Sep: trading permanently out of the product)

Trading is gone: no broker connectivity, order placement/proposal/review, simulated paper
brokerage, live/paper switch, broker plugin. The user's own tracked portfolio — manual
holdings, cost bases, P&L on real prices, CSV export, notes, watchlists — STAYS; it is not
trading. Never confuse the two.

- **`brokers-adapters.json` is never your assigned file.** If you are somehow handed it, stop
  and report — do not refute it. Its 15 findings close as `removed_with_feature` in bulk at
  register time, no per-finding work.
- **Any other finding whose subject exists ONLY to connect a broker, place or simulate an
  order, or gate order execution** (a broker adapter method, an order-proposal panel, a
  paper-trading toggle, an order-confirmation flow that only guards a `place_order` call, a
  route that only serves order placement): do not deep-refute it. Emit
  `verdict: "removed_with_feature"`, and in `reason` write one line naming what surface it
  served and that the surface is being deleted. No repro check needed for these.
- **Kill-switch and audit-log findings** (mechanisms shared across more than order placement,
  e.g. `sidecar/models/audit_log.py`, `services/kill_switch.py`, `src-tauri/src/kill_switch.rs`):
  refute normally with full evidence, AND additionally state in `reason` (or a trailing clause)
  what the mechanism actually gates — orders only, vs. agent autonomy / other control-plane
  actions / something broader. The removal batch needs that fact to decide what of the
  mechanism goes with trading and what stays.
- Everything else: refute on the merits, scope change irrelevant.

## Verdict shape

Output is a JSON array, one entry per raw finding in your input file, covering EVERY `raw_id`
in that file (counts must match — this is checked mechanically):

```json
{
  "raw_id": "<exactly as in the raw file>",
  "verdict": "refuted | admitted | admitted_with_correction | removed_with_feature",
  "severity_final": "critical|high|medium|low",
  "reason": "one to three sentences: why refuted/admitted, or what removed_with_feature closes as, or what corrected and why",
  "evidence": "file:line[, file:line] you actually opened to reach this verdict (or URL for a world claim)",
  "evidence_checked": "what you checked (files opened, repro run against :52152, or 'code-only, stack unreachable')",
  "repro_check": "one line: the exact command/steps you ran (or would run) to confirm, and what it showed"
}
```

- `refuted`: the finding does not hold — the claimed bug/gap is not present, or the evidence
  cited does not show what it claims. Must cite the code you read that disproves it.
- `admitted`: the finding holds as originally stated (severity unchanged) or you could not
  disprove it (say so honestly in `evidence_checked`).
- `admitted_with_correction`: real, but wrong in some particular — usually severity
  (`severity_final` differs from the raw finding's `severity`), sometimes scope or mechanism.
  Say what corrected and why.
- `removed_with_feature`: the finding's subject is being deleted as part of the trading
  removal (see above). `severity_final` still required (carry over the raw severity; it is
  informational only, the register closes these without a fix).

## Output path (must match `scripts/r15/register.py` exactly)

Write to `docs/redesign/verification/r15/census/refute/<same basename as your raw file>.json`
— e.g. raw file `code-market-data-providers-1.json` → output
`docs/redesign/verification/r15/census/refute/code-market-data-providers-1.json`. Top-level
value is the JSON array described above (register.py's loader also accepts `{"key": [...]}`
but a bare array is simplest and matches the raw files' own shape).

## Continue-from-existing-file rule

WRITE YOUR OUTPUT AS YOU GO. If your output file already exists (partial or complete — a
previous attempt at this exact task may have died to a usage wall or power loss), read it
first: verify each existing verdict is still sound (spot-check, don't blindly trust), keep
what holds, and finish the remaining `raw_id`s. Never restart from scratch when a partial file
exists — that discards real work.

## RESULT (what you return to the lead)

```json
{
  "model": "<exact model id from your system prompt>",
  "output_file": "docs/redesign/verification/r15/census/refute/<file>.json",
  "summary": "<one line: N findings, counts by verdict>",
  "count": "<number of raw_ids you produced verdicts for>",
  "top": ["<up to 3 most consequential verdicts: refuted-when-critical, or admitted-critical, one line each>"]
}
```

## Honesty rules

- Never speculate about code you have not opened. Every `refuted` or `admitted_with_correction`
  verdict needs a `file:line` you actually read in `evidence`.
- Default to NOT refuting when you lack evidence — `refuted` requires a positive disproof, not
  the absence of a check. If you couldn't check, that is `admitted`, said honestly.
- A finding ruled out-of-scope by COMMON.md's "out of scope by decision" list (live broker
  order execution, Tradesa, two-tier research reopening, the R9 design system, the dev
  keystore, the plugin system's existence) is `refuted` with that reason cited — distinct from
  `removed_with_feature`, which is specifically the 23 Sep trading-removal scope change.

## Boundaries

- Read-only on the repo. You do not fix anything, do not edit product code, do not touch
  tests. Your only writes are your own output file (and, if truly needed, a throwaway repro
  script under your scratch dir — never under `src/` or `sidecar/`).
- Never print, log, copy, or write a secret. Never open
  `docs/redesign/verification/R15_BRIEF*.md` or anything under `r15/local/`.
- No GUI interaction of any kind. Headless only.
- Do not start, stop, or restart the isolated stack at `:52152`, and never touch the
  operator's own live app/session or any other product's processes on this Mac.
- No full pytest/cargo/PyInstaller/production builds. One targeted test file is fine when it
  cheaply settles a claim.

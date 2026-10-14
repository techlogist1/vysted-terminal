# Code sweep task specs

`<id>` is the subsystem id you were given. Its responsibility, owning files, LOC and tests are
the entry with that id in `docs/redesign/verification/r15/census/CODE_PARTITION.json` — read
that entry first.

## CRITIQUE

Grade the subsystem against _A Philosophy of Software Design_. FIRST invoke the Skill tool with
skill `aposd-critique` and follow it (two personas, 18 principles, pass / at-risk / violate,
mandatory file:line evidence). If the skill is unavailable, SAY SO in your output and carry
its vocabulary directly: deep vs shallow modules, information hiding / leakage, temporal
decomposition, pass-through methods and variables, general vs special purpose, different
layer different abstraction, pull complexity downward, define errors out of existence, design
it twice, comments that say what code cannot, naming, consistency, obviousness.

READ THE CODE ITSELF, fully for the core files. The findings that matter are the ones a bug
hunt MISSES — code that works and is still badly built: the route with no error handling
while its five siblings have it; the invariant held by a comment when the structure could
hold it; behaviour the next reader will not understand; duplicated truth that will drift; a
swallowed exception that turns a failure into a silent empty; a cache with no bound; a retry
with no ceiling; a network call with no timeout; special-casing to satisfy a test. ALSO
report any outright BUG you can prove from the code (input -> wrong output) — prove it with a
tiny snippet or one targeted test where cheap.

Do not pad: 5-15 findings that would change a decision beat 40 nitpicks. No refactors beyond
what a concrete consequence justifies.

Output files:

1. `docs/redesign/verification/r15/census/code/<id>.md` — critique table
   (principle | grade | evidence file:line | consequence) + priority findings.
2. `docs/redesign/verification/r15/census/raw/code-<id>.json` — RAW FINDINGS array, raw_id
   prefix `COD-<id>`.

## REFUTE

A critic produced `docs/redesign/verification/r15/census/raw/code-<id>.json`. You are a fresh,
sceptical senior engineer: for EACH finding, try to REFUTE it. Open the cited file:line and
its callers; check whether the claimed consequence can actually occur (a guard upstream?
handling in a middleware / decorator / base class? is the bug input reachable from a real
caller?). Where cheap, run a tiny snippet or one targeted test to settle it.
Plausible-but-wrong findings waste the fix stage — default to `refuted` when the evidence
does not hold. Also re-judge severity against the scale in COMMON.md.

Verdicts: `confirmed` | `refuted` | `downgraded` | `upgraded` | `needs-live-check` (say exactly
what check would settle it).

Output file: `docs/redesign/verification/r15/census/refute/code-<id>.json` — array of
`{raw_id, verdict, severity_final, reason, evidence_checked}` covering EVERY raw_id in the
input (counts must match). Return counts by verdict.

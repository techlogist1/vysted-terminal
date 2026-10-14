# Log — rc1-drive-onboarding-stranger (round 5)

- Checked round-5 evidence tree first: no prior `onboarding-stranger` round-5 attempt existed
  (drives/findings/logs dirs had entries for other owner-drives only) — started fresh, did not
  continue from round-3/round-4 (out of scope per the round-5 rules).
- Verified candidate worktree HEAD: `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (matches).
- Read the census (`docs/redesign/verification/r15/surface/onboarding-stranger/EVIDENCE.md`) and
  cross-referenced the register (`vysted-r15-register.json`) for every `fixed`/`not_a_defect`
  onboarding-related entry: R15-UI-008, R15-UI-013, R15-UI-019, R15-UI-041, R15-UI-052,
  R15-UI-057, R15-DATA-018, R15-AGENT-028, R15-UI-076 (open/low, unrelated to this batch).
- Read the candidate's current source for each: `OnboardingFlow.tsx`, `OnboardingBanner.tsx`,
  `DisclaimerFlow.tsx`, `provider-validation.ts`, `ChatSidebar.tsx`, `sidecar/services/llm/openai.py`,
  `sidecar/services/nse_symbol_change.py`.
- Seeded a clean data dir `rc1-round-5-data-onboarding-stranger` (dev-keystore only), booted the
  candidate's main sidecar from source on `:52326` (sleep pid 43746, worker 43747), confirmed
  `/health` 200 before driving.
- Drove 22 rows (curl + one vy.py agent round-trip) with raw evidence saved as I went; see
  `drives/onboarding-stranger.md` for the scored table and deltas.
- Local-model lane: acquired `/tmp/vysted-r15-ollama.lock`, ran one keyless `llama3.1:8b` prompt
  ("how is Zomato stock doing today?") via `vy.py invoke copilot` against my own sidecar
  (port 52326, inside the 52100-52399 range). Noticed a second, unrelated battery process
  (`pid 44714/44716`, KPITTECH concall prompt) also holding a `sh -c trap ... rmdir` wrapper around
  the same lock path concurrently with mine — a harness/other-role lock-contention artifact, not
  something in my lane to fix or file; noted here only in case it explains any timing anomaly in
  another role's evidence.
- The llama3.1:8b response fabricated a "Calling price_data for Zomato..." narration and a specific
  price with no such tool call in the raw event log (only `market_overview()` was called) — this
  is R15-LEAD-030's exact defect class (blocked_tier4, DECISIONS 4.9-4.12). Per the round's
  standing rule (1), recorded as a concurrence in the drive markdown, not filed as a new
  regression/defect and not added to the findings JSON.
- Stopped the sidecar (killed sleep pid 43746; worker exited with it). No operator data touched;
  shared `:52152` used read-only for a couple of comparisons, never restarted or written to.
- No regressions found on any `fixed` register entry touching this surface group. No new
  functional defects filed. `findings/rc1-drive-onboarding-stranger.json` is `[]`.

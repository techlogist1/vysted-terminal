# rc1-drive-onboarding-stranger — working log (gate round 4)

- Confirmed candidate worktree HEAD = `1006c6da694ede5776c3dabbd27b305aeb56b5ad` before
  starting.
- No prior round-4 files existed for this label (checked
  `docs/redesign/verification/r15/rc1/round-4/{drives,findings}/*onboarding-stranger*`
  and `surface/onboarding-stranger/rc1/round-4/`, both empty) — fresh drive, nothing to
  continue from.
- Read panel/store code first: `OnboardingFlow.tsx`, `OnboardingBanner.tsx`,
  `DisclaimerFlow.tsx`, `store/safety.ts`, `store/symbols.ts`, `lib/region.ts`,
  `ChatSidebar.tsx:780-840`.
- Booted own sidecar on `:52326` from the candidate's `sidecar/` source, clean empty
  data dir (`dev-keystore.json` only). MCP env pointed at shared `:52153`/`:52154`.
- Gotcha hit: `nohup sh -c 'sleep 86400 | ./.venv/bin/python3 main.py ...' &` — the
  pid captured by `$!` is the `sh -c` wrapper, not the inner `sleep`; killing the
  wrapper pid alone leaves `sleep`+`python3` still piped together and the sidecar
  stays up. Killed the actual `sleep` pid (found via `ps aux`) to close the pipe and
  trigger the stdin-EOF watchdog cleanly.
- Drove 18 rows against live API/code, one raw file per row under
  `surface/onboarding-stranger/rc1/round-4/`.
- Ran one live local-lane agent turn (`llama3.1:8b` via `vy.py`) under the shared
  Ollama lock (`mkdir /tmp/vysted-r15-ollama.lock`, released via a `trap ... EXIT`
  wrapper around the detached call). Took 238 s end to end, consistent with census
  timings.
- Investigated a red herring: heavy `provider_registry: ... incomplete fundamentals`
  log churn during the agent-turn wall-clock window; traced it via timestamp
  correlation to the sidecar's own background India fundamentals warm-cache task
  (`services.fundamentals_warm`, active since boot), not the chat request. Did not
  file.
- Checked register (`vysted-r15-register.json`) for any entry matching the observed
  behaviours before deciding what to file; found none needing action this round.
- Stopped sidecar cleanly, confirmed `/health` refused and worker pid gone.
- No fix rounds triggered, no register edits made (read-only this round for this
  group beyond the standard raw-finding write, which is empty).

# log — rc1-drive-failure-inducer (gate round 4)

- Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`, worktree confirmed at start.
- Booted own sidecar on `127.0.0.1:52327` from `rc1-round-4-cand/sidecar` (source run),
  data dir `cp -R rc1-round-4-seed-data -> rc1-round-4-data-failure-inducer`, MCP env pointed
  at shared `:52153`/`:52154`. `/health` 200 immediately (source run, no PyInstaller extraction).
  Sleep pid 78015 (worker 78018), stopped at end of drive.
- Read `docs/redesign/verification/r15/tooling/PROMPT_surface_s2.md` (OWNER-DRIVE +
  failure-inducer section), `SURFACE/failure-inducer/EVIDENCE.md` + `COVERAGE.json` (census,
  terminal, 23 Sep), `rc1/round-3/EVIDENCE.md` (round 3's regression re-check of the same 5
  findings against candidate `01d6920a`).
- Confirmed via register (`vysted-r15-register.json`) that `R15-AGENT-026`, `R15-RESEARCH-008`,
  `R15-AGENT-025`, `R15-DATA-061`, `R15-AGENT-027` are all `status:fixed`; none are in the
  round's three-failure or adjudicated lists. Overall open critical/high/medium count = 0,
  matching the lead's expectation.
- `git diff --stat 01d6920a 1006c6da -- <every file the 5 fixes live in>` → only
  `errors.py`/`openai.py` touched, both R15-LEAD-043 (composer-chat's entry, additive) —
  scoped the round-4 re-drive to a live spot-check rather than a full re-derivation.
- Live re-drove: adapter-direct junk stub (AGENT-026, no cost), `/quotes/%20%20%20`
  (DATA-061), a malformed-symbol spot-check (found 2 fresh instances of the DATA-061 defect
  class recurring — see findings), `/search/status`+`/searxng/status` (honest, unchanged),
  and one real ollama call for RESEARCH-008 (`llama3.1:8b`, own sidecar, keyless) under the
  shared ollama lock — held ~135s, released cleanly (the wrapper's `rmdir` on exit reported
  "no such file", a harness artifact not a product issue — the lock dir was gone by the time
  the trap ran, most likely already cleared; no other lane's lock was touched, I acquired mine
  via `mkdir` before starting and it round-tripped through the call's full duration).
- Code-read only (no live re-stub needed, already round-3-proven): AGENT-025's
  `oneshot.py` timeout guard, AGENT-027's `_BODY_RULES` branches — both unchanged.
- 2 new findings filed (`rc1-drive-failure-inducer:1`, `:2`) — recurrences of the DATA-061
  defect class the round-3 verifier already flagged (`rc1-verifier:7`) but which have no
  register entry of their own yet; both reproduce identically to the verifier's exact repros.
- Did not re-run: the no-docker/netdown env-profile boots, the full 81-row malformed sweep,
  the 429/500/hang/junk-html/badsse/emptychoices stubs, retired/nonsense slug — all unchanged
  code since census/round-3, cited instead of re-spent.
- Stopped own sidecar (`kill 78015 78017`) at end of drive; junk-provider stub process
  (79231) killed immediately after its one-shot use.

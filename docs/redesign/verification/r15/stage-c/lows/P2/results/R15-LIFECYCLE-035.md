# R15-LIFECYCLE-035 second attempt (06:53 IST)

- Entry: R15-LIFECYCLE-035 (managed-SearXNG error state sticky for the process)
- Outcome: fixed_untested
- Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
- Branch: worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8
- Cherry-picked: none (the prior W5 branch carries no part of this entry; eaaef44a is LIFECYCLE-034)
- Fix commit: 3da1e972
- Merge check: git merge-tree HEAD origin/worktree-agent-lows-P2-W5-data-resilience is clean

## Fix
sidecar/services/searxng_manager.py
- last_error field (set on every error, on the snapshot, cleared by begin_setup/setup/teardown).
- refresh() always re-derives (body moved to _derive()); a settled error is restored unless the
  derivation lands in ready/degraded, i.e. a container that is serving again.
- ready_base_url_detected() re-derives again while in error, throttled by
  ERROR_REPROBE_INTERVAL_SECS = 30 s, so web_search uses a hand-fixed container.

Why the first writer's blocker does not apply: it re-derived unconditionally, which turned a
failed pull into docker_present_not_setup on the first poll and broke
test_search_tiers_router.py::test_setup_failure_is_observable_through_the_status_poll. This shape
keeps error sticky against every derivation that would hide it, so that test and the manager's
sticky-error tests stay valid unchanged. No existing test was edited.

## Tests written (source only, never run: off-lane rule)
sidecar/tests/test_searxng_manager.py
- test_hand_fixed_container_supersedes_a_sticky_error (acceptance: error + healthy container ->
  refresh -> ready, last_error reported)
- test_error_stays_sticky_while_the_container_is_not_serving
- test_hot_path_reprobes_a_sticky_error_on_a_throttle

Untested pending integration: all of the above plus the existing searxng manager, router,
web_search and r9 seam suites. Only py_compile + ruff format/check ran on touched files.

## Risks
- While in error, each status poll and (every 30 s) the search hot path now run docker CLI
  probes; same cost the non-error states already pay.
- Frontend does not render last_error (SettingsPanel keys on state; ready shows "Running").
  Wire field only; UI line can come later if wanted.

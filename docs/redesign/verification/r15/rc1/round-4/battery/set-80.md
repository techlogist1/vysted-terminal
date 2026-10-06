# Battery shard 17 — set-80 (unplanned-2)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-014 | source re-trace: marketplace.configure() -> plugin-runtime.reloadPlugin -> unloadPlugin(active->stopped)+loadPlugin(initialize reruns) | configure() now calls reloadPlugin (not enablePlugin); the state transition makes loadPlugin's active-state early-return guard structurally unreachable on this path | holds |

COVERAGE: 1/1 ids raw; no raw: none. Note: no GUI lane available in this role to drive a live
keychain-secret-save-then-reload round trip; verified by concrete source-level state-machine
trace instead (not a diff read).

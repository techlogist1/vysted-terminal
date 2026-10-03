# free-maintainer-2 — transform.code size caps bypassed through sum(list, start)

Target: `sidecar/services/workflow_nodes/code_node.py` at d38b5d1a (the R15-CODE-PLATFORM-066 fix: `_pow` caps integer powers at 10,000 bits, `_mul` caps repetition at 100,000 items, evaluation runs in a thread under a 5 s `wait_for`).

Repro (in-process, scratch, `free-maintainer-2-repro.txt`): the caps hold for their own shapes (`[0]*100001`, `7^(10^7)` both refused), but `sum` is whitelisted with its `start` argument, so `sum([[0]*100000]*n, [])` concatenates n capped lists into one uncapped list in quadratic time — n=80 gives 8,000,000 items in 0.6 s, n=250 runs past the timeout (TimeoutError after 7.98 s while the thread kept going, peak RSS 8.3 GB). The expression is 25 characters; a larger n exhausts memory. `+` on lists is uncapped too. The timeout returns an error but cannot stop the thread (the module's own `ponytail:` note), so the work and memory continue in the sidecar process. Reachable through any workflow the agent or an MCP client saves and runs (`save_workflow` / `run_workflow`), and the node editor's server preview.

Class gap of R15-CODE-PLATFORM-066 (fixed, low): same "server code node admits unbounded work" class, new operator. Fix shape: drop `sum`'s start argument (or reject a list result above `_MAX_REPEAT_LEN`), and cap `+` on sequences like `_mul`.

VERDICT free-maintainer-2: finding maintainer:8

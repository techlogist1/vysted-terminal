# batch-7/W4-research-funnel

None of this set's 12 assigned ids (`R15-RESEARCH-044` through `R15-RESEARCH-066`, even numbers)
exist in `docs/redesign/verification/vysted-r15-register.json` — the register's `R15-RESEARCH-*`
series stops at `R15-RESEARCH-042` (652 total entries; checked both `entries[]` and the 76-item
`rejections[]` by exact id, and `grep`ped the whole repo for each id: zero hits anywhere outside
this file). This is a task/register data mismatch, not a product defect and not an upstream
outage — there is no register entry to read a repro or certification from, so none of the required
per-entry work (re-run the original repro, compare against the batch verifier's evidence) is
possible for this set. Filed as one `environment`-kind finding rather than 12 separate ones.
No sidecar work was needed for this set.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-044 | Looked up the id in the register (`jq`/Python exact-id match over `entries[]` and `rejections[]`) and `grep -r` over the whole repo. | No such entry exists; the register's RESEARCH series tops out at R15-RESEARCH-042 (register `counts.entries: 652`). | blocked_env |
| R15-RESEARCH-046 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-048 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-050 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-052 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-054 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-056 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-058 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-060 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-062 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-064 | (same lookup) | No such entry exists. | blocked_env |
| R15-RESEARCH-066 | (same lookup) | No such entry exists. | blocked_env |

Raw output: `raw/set-28/RESEARCH-044-066-register-lookup.txt` (one shared probe file covering all
12 ids — the lookup result is identical for each: not found).

<!-- SCAN at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave -->

# Secrets scan — 4d893147

## Method

- No `gitleaks` or `trufflehog` on this machine (`which` found neither); neither was installed. Baseline used: `scripts/r15/history_secrets_scan.py` — provider-shape RULES (openrouter/anthropic/openai-project/openai/AWS/GitHub/Slack/Stripe/HuggingFace/Tavily/Perplexity/Replicate/Notion/SendGrid/Telegram/Google/Groq/xAI/private-key-block/broker-secret-literal/webhook-URL/URL-embedded-creds/Bearer/JWT/Tauri-signing-key) plus a keyword-gated Shannon-entropy heuristic, run detached over `git log -p -U0 -m --all --reverse` (pass 1, added lines only) and a full `git cat-file --batch` sweep of every reachable blob (pass 2, whole-file). Neither pass nor this report ever prints a matched value — only length, entropy, fixture flags, and a per-token-redacted line (`redact()`); this report additionally strips even the redacted line, keeping only path/line/rule/class per the task's schema.
- Tree-at-sha pass: a helper (`tree_scan_helper.py`, kept in the scratchpad) imports the baseline's exact `RULES`/`redact()`/`scan_line()`/`describe()` and runs them over `git ls-tree -r` + `git show <sha>:<path>` for every tracked file at this sha, excluding `pnpm-lock.yaml`, `**/Cargo.lock`, `docs/redesign/verification/R15_BRIEF*` and `docs/redesign/verification/r15/local` — so "present at the sha" is exact, not diff-inferred. 4949 files scanned, 115 hits.
- Cross-checked with `git grep -IcE` at the sha for the 15 shapes named in the brief (`sk-or-v1-`, `sk-ant-`, `sk-proj-`, `sk-`, `AKIA`, `gh[pousr]_`/`github_pat_`, `xox[abprs]-`, `BEGIN…PRIVATE KEY`, `AIza`, `gsk_`, `xai-`, `broker-secret-literal`, JWT, `Bearer`), same exclusions, using the baseline script's own quantifiers. All 0 except the keyword-gated `api_key=`/`secret=`/`token=` assignment shapes (282/6/113 raw lines), which the baseline's entropy gate + fixture/path heuristics triage — none surfaced as a live-looking credential.
- History: `git log -p -U0 -m --all --reverse` over 2090 commits / 2,553,913 added lines (155 diff-pass hits) plus a full blob sweep of 10,647 reachable blobs (314 blob-sweep hits). Zero filename hits (no `.env`, `dev-keystore.json`, `.pem`/`.p12`/`.key`/`.jks`/`.mobileprovision`, `id_(rsa|ed25519|ecdsa)` ever added on any ref). `git ls-files --others --exclude-standard` (names only, never opened) is also clean of those patterns.
- Every one of the 43 unique commits behind the 155 history-diff hits is `reachable_from_004 = true` and `pushed = true` (each is an ancestor of `4d893147` and already carried by a remote-tracking branch, since `004-r4-experience-rebuild` itself is one).
- `R15_BRIEF*`/`r15/local` are absent from the tree at this sha (`git ls-tree` for both paths returns empty), so nothing needed the opaque path+rule-only treatment.
- Classification is rule-driven, same taxonomy as the prior scan: `tauri-signing-key` → `placeholder` (the field is `tauri.conf.json`'s updater **public** key — meant to be public, verifies signed updates; the private signing key never appears anywhere in this scan); a path under `sidecar/tests/`, `.test.tsx`, or matching `test`/`fixture`/`mock`/`fake`/`CANARY` wording (path or line) → `test_fixture`; a path under `docs/redesign/verification/r1{2,5}/` or `docs/redesign/verification/vysted-r15*` → `redacted_example` (the R15 census/verification wave's own audit trail — run ids, tool-call ids, sha10 groupings, references to "NewsAPI key" UX, none of them live secrets); everything else → `real_or_unknown` for a human look. **0 hits landed in `real_or_unknown` in either pass.**

## Counts

| metric | value |
|---|---|
| commits scanned (all refs) | 2090 |
| blobs scanned (full sweep) | 10647 |
| files scanned at the sha (tree pass) | 4949 |
| tree-at-sha hits | 115 |
| history hits — diff pass (`git log -p`) | 155 |
| history hits — blob sweep | 314 |
| history array total (diff + blob) | 469 |
| secret-bearing filenames (tracked or untracked) | 0 |
| `real_or_unknown` — tree | 0 |
| `real_or_unknown` — history | 0 |
| `real_or_unknown` — total | 0 |
| `real_or_unknown` and pushed | 0 |

### Class breakdown

| class | tree-at-sha | history (diff+blob) |
|---|---|---|
| `redacted_example` | 78 | 253 |
| `test_fixture` | 36 | 198 |
| `placeholder` | 1 | 18 |
| `allow_marked` | 0 | 0 |
| `real_or_unknown` | 0 | 0 |

The single tree-at-sha `placeholder` is `src-tauri/tauri.conf.json:52` (the updater `pubkey`, same line as the prior scan — `git blame` confirms it has been unchanged since commit `5e5709166` in May); the 18 history `placeholder` hits are that same public key across historical revisions of the file (blob-sweep re-finding it at each edit). No provider-shape RULES (`sk-or-v1-`, `sk-ant-`, `sk-proj-`, `AKIA`, GitHub/Slack/Stripe/HuggingFace/etc.) matched anywhere, in either pass, at either sha.

## Findings — `real_or_unknown` first, pushed ones at the very top

**None.** Zero hits classified `real_or_unknown` in the tree-at-sha pass or the history pass; consequently zero are `pushed`. Every hit resolved to `redacted_example` (R15's own verification/census artifacts recording run ids, cost/token counters, tool-call ids, or prose referencing "NewsAPI key" / "api_key" UX, not a live value), `test_fixture` (a test/fixture path, or a value/line carrying fixture or canary wording — several hits in `docs/redesign/verification/r15/surface/settings-plugins/http-log.jsonl` are the plugin-credential test harness's own labeled `sk-...CANARY-fake-...` synthetic literal, shape `sk-<11 chars>-fake-<10 digits>`, never a live-looking key), or `placeholder` (the Tauri updater's public key).

## Since f444479 (prior Stage D scan)

The prior scan ran at `f444479031d7d493b7955b9af041d18e7c7a40cc`, an ancestor of this sha (confirmed via `git merge-base --is-ancestor`). Comparing on `(path, line, rule)`:

| | tree-at-sha | history (path,line,rule set) |
|---|---|---|
| prior hits | 40 | 152 (diff+blob) |
| new hits (present now, absent before) | 82 | 129 |
| gone (present before, absent now) | 7 | 0 |
| current hits | 115 | 469 |

- **New hits** are overwhelmingly R15 verification-wave growth: `docs/redesign/verification/r15/rc1/battery/raw/set-2/*` and `set-24/*` (durable-delegate agent-run poll/get/checkpoint captures — `agent_id`/`cost`/`budget` JSON blobs, entropy-keyword on the run/token counters), i.e. new evidence files the wave itself produced between the two shas. None are a new provider-shape rule; `class_breakdown` stays 100% `redacted_example`/`test_fixture`/`placeholder`.
- **Gone hits** (7, tree-at-sha only) are all in `docs/redesign/verification/vysted-r15-register.{json,md}` and `docs/redesign/verification/r15/tooling/stage-d-docs.js` — these are **line-number shifts**, not removed content: those files grew (the register gained entries; `stage-d-docs.js` gained the `LEADNOTE` arg per `b7707120`) and the matched line landed at a different offset (visible in the current pass's very similar-looking hits a few lines away in the same files). No content was verified deleted; re-confirm at rc1 tag time if a byte-exact diff is needed.
- **Bottom line:** the delta is proportional to the repo's growth over this window (more battery/census artifacts), not a new secret class. `real_or_unknown` was 0 before and is 0 now.

## Scope note

Raw tool output (scanner JSON, tree-scan JSON, ancestry table, this report's working files) stays under the scratchpad, never in this repo. This report and its JSON companion are the only committed-tree artifacts from this scan.

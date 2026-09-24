<!-- SCAN at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave -->

# Secrets scan — f4444790

## Method

- No `gitleaks` or `trufflehog` on this machine (`which` found neither); neither was installed. Baseline used: `scripts/r15/history_secrets_scan.py` — provider-shape RULES (openrouter/anthropic/openai/google/groq/xai/github/AWS/private-key-block/Slack/Stripe/HuggingFace/Tavily/Perplexity/Replicate/Notion/SendGrid/Telegram/webhook-URL/URL-embedded-creds/Bearer/JWT/Tauri-signing-key) plus a keyword-gated Shannon-entropy heuristic, run detached over `git log -p -U0 -m --all --reverse` (pass 1, added lines only) and a full `git cat-file --batch` sweep of every reachable blob (pass 2, whole-file). Neither pass nor this report ever prints a matched value — only length, entropy, a sha256[:10] grouping hash, fixture flags, and a per-token-redacted line (`redact()`).
- Cross-checked with `git grep -IcE`/`-Ii` at the sha for the 15 shapes named in the brief (sk-, sk-ant-, sk-or-v1-, sk-proj-, AKIA, gh*_/github_pat_, xox[abprs]-, BEGIN…PRIVATE KEY, AIza, gsk_, xai-, api_key=/secret=/token= assignments, Bearer, JWT) over `.` excluding `pnpm-lock.yaml`, `**/Cargo.lock`, `docs/redesign/verification/R15_BRIEF*`, `docs/redesign/verification/r15/local`. Only `api_key\s*[:=]\s*['"]` hit (135, all in `sidecar/tests/*.py`); every other shape was 0 at this sha.
- Tree-at-sha pass: a helper script (`tree_scan_helper.py`, kept in the scratchpad) imports the baseline's exact `RULES`/`redact()`/`scan_line()` and runs them over `git ls-tree -r` + `git show <sha>:<path>` for every tracked file, so "present at the sha" is exact, not diff-inferred.
- Filenames: `git ls-tree -r --name-only` at the sha and `git ls-files --others --exclude-standard`, both filtered for `.env*`, `dev-keystore.json`, keystore/`.pem`/`.p12`/`.key`/`.jks`/`.mobileprovision`, `id_(rsa|ed25519|ecdsa)` — zero hits either way.
- `R15_BRIEF*`/`r15/local` are absent from the tree at this sha (both `git ls-tree` calls for those paths returned empty), so nothing needed the opaque path+rule-only treatment.

## Counts

| metric | value |
|---|---|
| commits scanned (all refs) | 1489 |
| blobs scanned (full sweep) | 7353 |
| tree-at-sha hits | 40 |
| history hits — diff pass (`git log -p`) | 61 |
| history hits — full blob sweep (raw / unique path+rule+line folded) | 112 / 91 |
| filename hits (secret-bearing names, tracked or untracked) | 0 |
| **real_or_unknown (tree + history)** | **0** |
| **pushed real_or_unknown** | **0** |

Class breakdown across every hit (tree + folded history):

- `redacted_example`: 141
- `test_fixture`: 46
- `placeholder`: 5

## Findings

**No pushed real_or_unknown hits. No real_or_unknown hits at all.** Every match across 1,489 commits / 7,353 blobs / the full working tree at this sha resolves to one of three non-secret buckets:

1. **`placeholder` (5 hits, all one value)** — `src-tauri/tauri.conf.json` `pubkey` field: the Tauri **updater public key** (rule `tauri-signing-key`, redacted shape `<RULE-REDACTED:152>` — a 152-char base64 `untrusted comment:`-prefixed pubkey). This is the public half of the updater signing keypair, embedded by design so the app can verify update signatures; it is meant to be public and is not a secret. Present at the sha (`src-tauri/tauri.conf.json:52`) and unchanged across every historical revision of that file the sweep found (16 blob shas, all length 152 — same key, never rotated to something sensitive).
2. **`test_fixture` (46 hits)** — the scanner's own `demo()` self-test literal in `scripts/r15/history_secrets_scan.py` (3 hits, explicitly fake, `pushguard:allow`-marked in source); a `.test.tsx` harness (`docs/redesign/verification/r15/surface/settings-plugins/harness/plugins.s2cq.test.tsx`) stubbing a `newsapi_key` fixture value; and every hit whose matched token itself contains fixture/canary wording — chiefly the R15 canary literal `sk-R15CANARY-fake-0000000000` used to test the settings "validate key" UX (`docs/redesign/verification/r15/surface/settings-plugins/http-log.jsonl`), which is a marked-fake value by construction (`CANARY`, `fake`).
3. **`redacted_example` (141 hits)** — every other hit, all inside `docs/redesign/verification/r15/**`, `docs/redesign/verification/vysted-r15-register.{json,md}`, and `docs/redesign/verification/vysted-r15-run-state.md`: the R15 census/verification wave's own audit trail. The keyword-gated entropy heuristic fires on run ids, `tool_call_id`s, and this sha itself (`sha:'<TOK:40>'` in `vysted-r15-run-state.md:25` — the 40-char hex is literally `f444479031d7d493b7955b9af041d18e7c7a40cc`, this workflow's own commit, not a key) sitting next to the word "key"/"token" in prose describing the app's NewsAPI-key / LLM-key-validate flows (e.g. `settings-plugins/11-key-validate-http.jsonl`'s `api_key` fields, which are already the app's own request/response bodies — `{"ok":false,...}` — not raw literals). None contain a live-looking credential. The plain-regex `api_key\s*[:=]\s*['"][0-9A-Za-z]` cross-check (135 hits, all `sidecar/tests/*.py`) matches the syntactic shape of an assignment with no entropy bar; every one of those 135 is a low-entropy test literal that the baseline scanner's entropy-keyword heuristic correctly did **not** flag as a hit — none appear in `history_hits`/`blob_hits`/`tree_at_sha`, so they are not itemized in the JSON below; noted here only because the task's shape cross-check surfaces them.

Zero filename hits: no `.env*`, `dev-keystore.json`, `.pem`/`.p12`/`.key`/`.jks`/`.mobileprovision`, or `id_(rsa|ed25519|ecdsa)` file was ever added on any ref, and none sit untracked-but-not-ignored in the working tree right now.

## Not scanned / caveats

- `docs/redesign/verification/R15_BRIEF*` and `docs/redesign/verification/r15/local/` are not present in the tree at this sha, so the "path + rule only" fallback never triggered — nothing to report there.
- The 112 raw full-blob-sweep hits fold to 91 unique (path, rule, line) tuples once repeat blobs of the same near-static file are collapsed (e.g. the tauri pubkey re-committed unchanged across many revisions of `tauri.conf.json`); the JSON keeps both the raw and folded counts.
- This is a keyword-gated **heuristic**, not a certified secret detector — it will not catch a secret with no matching keyword nearby, and it flags non-secrets (as above) that a human still has to read the redacted shape of. Neither `gitleaks` nor `trufflehog` was available to cross-validate with a second engine.


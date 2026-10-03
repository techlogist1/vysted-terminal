# LS-4 — secrets, licence consistency, BANNED words (d38b5d1a)

Raw: `LS-4/secrets-summary.txt`, `LS-4/head-tree-secrets.txt`, `LS-4/licence-summary.txt`, `LS-4/notices-drift.txt`, `LS-4/main-binary-dist-info.txt`. No secret value is printed anywhere; hits are path:line + rule + length.

**Secrets.** `scripts/r15/history_secrets_scan.py` over the full history (2,646 commits, 8.77 M added lines, 17,361 reachable blobs; full JSON kept in scratch, not committed) plus a RULES pass over the 11,261 tracked text files at d38b5d1a:
- Provider-keyed rules: `openrouter-key`/`google-api-key` on line 2 of two rc2 battery raw files (`rc1/round-6-rc2/battery/raw/set-7/R15-CODE-AGENT-003.txt`, `R15-UI-008.txt`) — fabricated low-entropy probe values (1.42 bits/char, 10 distinct chars; scanner flags value and line as fixture) in a `/llm/keys/validate` loop. Not secrets.
- `tauri-signing-key` rule: only the `"pubkey"` field of `src-tauri/tauri.conf.json` (the updater's public minisign key) across its history. Public by design.
- Keyword-gated entropy: 76 distinct values, 74 in `docs/redesign/verification` (run ids, commit SHAs, isolated temp-home names, register prose) and 2 in the scanner's own source. The `settings-plugins/11-key-validate-http.jsonl` api_key values are 20-27-char probe strings (a real OpenRouter key is 73 chars); the one `ok:true` row there is the historical OpenRouter `/models` no-auth validate, since fixed (`openai.py:812-835` now probes `/key`).
- No filename hits. Result: no real credential in history or tree.

**Licence consistency.** `licence_scan.py` on the bundle's own build venv (`final-cand/sidecar/.venv`): 124 runtime dists, none missing from THIRD_PARTY_NOTICES.md; copyleft in the closure = frozendict 2.4.7 (LGPL-3.0), listed in Section A; fredapi and peewee carry no licence metadata but are listed (Apache-2.0 / MIT). LICENSE = PolyForm Strict, package.json `SEE LICENSE IN LICENSE`, README names PolyForm Strict + Apache-2.0 for the contract/example — consistent. **But** 56 of the 121 "Python — vysted-sidecar" rows give a version other than what the bundle ships (the frozen binary itself carries anyio-4.15.1 vs 4.13.0 listed): transitive deps are unpinned, so the notices (generated 05:01) and the 14:35 bundle build resolved different closures -> **maintainer:7 (medium)**.

**BANNED words** (patterns built in the shell; counts only):
- Tracked tree, word-bounded: BANNED_WORD in 25 files, all under `docs/redesign/verification/`; **0 outside it** (product code, docs, sidecar, src). Unbounded substring hits outside verification (7 files) are Indian place/company names inside resolver masters and the public suffix list, plus one R8 report and one test fixture string — not the word.
- BANNED_PHRASE: 7 files, all `docs/redesign/verification/r15/tooling/*.js` (run tooling, not shipped).
- 43 tracked paths under `docs/redesign/verification/r15/` carry BANNED_WORD in a directory name (verification tree, not shipped).
- Bundle: 0 / 0 in all four `Vysted Terminal.app/Contents/MacOS` executables, in `Contents/Resources`, in the three `src-tauri/binaries` sidecars and in `out/`. (The PyInstaller archives are compressed, so the binary check is weaker than the source check, which covers the same code.)

VERDICT LS-4: finding maintainer:7

# r16-rc2 certification

Certifier: independent, read-only (Opus 5.5). Written 2026-10-15 20:40 IST (clock: `date`).
Scope: release `v0.10.0-beta.4` (tag object `698187b8` -> commit `1d624bf3`) and branch
`005-r16-easy-install`, whose head moved during this run to `78d29509` (merge of
`r16-fix-coverage`, pushed). No app launch, no GUI, no dev stack. Evidence and scratch
files: `docs/redesign/verification/r16/local/certify/`.

## Verdict: CERTIFIED WITH CONDITIONS

Conditions:

1. **CI 9/9 on PR #4 at the current head `78d29509`.** At 20:39 IST all nine
   (lint/test/build x macos/ubuntu/windows) were `pending`. The previous head `1d624bf3`
   (the commit the release was built from) was 9/9 green, and its release jobs passed too.
   The merge only adds tests, makes two script helpers `export`ed and raises the coverage
   floor, so a red CI here would come from the new tests, not the shipped product.
2. **The tag and the certified head differ.** `v0.10.0-beta.4` = `1d624bf3`; the PR head is
   `78d29509`. The difference is test-only apart from `export` on
   `latestVersionDir`/`findVsCrtRedistDir` (`scripts/ensure-llama-server.mjs`) and
   `parseArgs` (`scripts/release/assemble-release.mjs`) plus `vitest.config.ts` lines
   82.62 -> 82.99. None of these files ship in a bundle. The artifacts don't need a rebuild,
   but the rc2 record must name both SHAs.
3. Not a condition I can check here: the separate GUI round (wizard A-local / B-key / C-skip
   on a fresh profile) owns the live wizard proof. This certification covers the wizard by
   code reading and unit tests only.

The full local chain is now green: `ci-local-int9.log` ends `EXIT=0 20:38:53`, with coverage
lines at 82.99% and no `ERROR: Coverage`. That clears the coverage-ratchet item that kept
int8 red.

## 1. Artifacts

`gh release download v0.10.0-beta.4` (all 12 assets) -> `local/certify/dl/`. The release
is `isDraft: true, isPrerelease: true`; every release on the repo, 0.9.0 included, is a draft.

```
$ shasum -a 256 -c SHA256SUMS.txt
Vysted-Terminal-Linux-x86_64.AppImage: OK
Vysted-Terminal-Windows-x64-Setup.exe: OK
Vysted-Terminal-macOS-AppleSilicon.dmg: OK
Vysted-Terminal.app.tar.gz: OK
Vysted-Terminal.app.tar.gz.sig: OK
Vysted-Terminal_0.10.0-beta.4_aarch64.dmg: OK
Vysted-Terminal_0.10.0-beta.4_amd64.AppImage: OK
Vysted-Terminal_0.10.0-beta.4_amd64.AppImage.sig: OK
Vysted-Terminal_0.10.0-beta.4_x64-setup.exe: OK
Vysted-Terminal_0.10.0-beta.4_x64-setup.exe.sig: OK
latest.json: OK
```

Every downloaded file except SHA256SUMS.txt itself is listed. The friendly-name copies are
byte-identical to the versioned ones.

latest.json: `version 0.10.0-beta.4`, `pub_date 2026-10-15T12:15:11.661Z`, and three
platforms. Each one points at this tag:

```
darwin-aarch64 .../releases/download/v0.10.0-beta.4/Vysted-Terminal.app.tar.gz
windows-x86_64 .../releases/download/v0.10.0-beta.4/Vysted-Terminal_0.10.0-beta.4_x64-setup.exe
linux-x86_64   .../releases/download/v0.10.0-beta.4/Vysted-Terminal_0.10.0-beta.4_amd64.AppImage
```

Cryptographic check (scratchpad `cert/verify_sig.py`, run with `cryptography` Ed25519 from
`sidecar/.venv`): I base64-decoded the pubkey from `tauri.conf.json` into minisign text and
checked each signature as `ED` (prehashed), i.e. Ed25519 over BLAKE2b-512 of the file. I also
checked the global signature over sig + trusted comment.

```
pubkey id 89FF38F7524553ED
darwin-aarch64 latest.json signature == .sig file: True
  alg=b'ED' keyid_match=True file_sig_valid=True global_sig_valid=True
windows-x86_64 latest.json signature == .sig file: True
  alg=b'ED' keyid_match=True file_sig_valid=True global_sig_valid=True
linux-x86_64 latest.json signature == .sig file: True
  alg=b'ED' keyid_match=True file_sig_valid=True global_sig_valid=True
```

All three updater signatures verify against the configured key.

## 2. Bundles

macOS dmg, mounted with `hdiutil attach -nobrowse -readonly` and then detached
(`"disk4" ejected.`):

- Info.plist: `CFBundleShortVersionString 0.10.0-beta.4`, `CFBundleVersion 0.10.0-beta.4`,
  `com.vysted.terminal`.
- `Contents/MacOS`: `llama-server`, `libggml{,-base,-blas,-cpu,-metal,-rpc}.0.dylib`,
  `libllama.0`, `libllama-common.0`, `libllama-server-impl`, `libmtmd.0`, `vysted-sidecar`
  (89M), `vysted-openbb-mcp-sidecar` (56M), `vysted-sec-edgar-mcp-sidecar` (85M) and
  `vysted-terminal`.
- `find -iname '*.gguf'` finds nothing (count 0).
- Running `llama-server --version` in place gives `version: 0.6.0-dev (build 11429, commit
d81235049) built with AppleClang 21.0.0.21000101 for Darwin arm64`, exit 0.
- `otool -L`: every non-system dependency is `@rpath/<lib>`. The LC_RPATH is
  `@loader_path`, and all referenced dylibs are in the same directory.
- codesign: `Signature=adhoc`. `codesign --verify --deep --strict` prints "code has no
  resources but signature indicates they must be present". The app is unsigned and
  unnotarized, as the release notes state (finding L1).
- `Contents/Resources` holds only `icon.icns`. **No THIRD_PARTY_NOTICES is inside the bundle**
  (finding M1).

AppImage (`7z l`): `usr/bin/llama-server` and the three sidecars are present. `llama-libs`
carries `libggml-cpu-{alderlake,cannonlake,cascadelake,cooperlake,haswell,icelake,ivybridge,
piledriver,sandybridge,sapphirerapids,skylakex,sse42,x64,zen4}.so` plus base/ggml/llama/
common/server-impl/mtmd. No gguf.

Windows installer (`7z l`): `llama-server.exe`, the three sidecar exes, `ggml-cpu-*` (14
variants), `ggml-vulkan.dll`, `libomp.dll`, `msvcp140/vcruntime140/vcruntime140_1.dll`.
No gguf, no notices file.

`THIRD_PARTY_NOTICES.md` (repo):

- Section D, l.1093-1103, covers llama.cpp/ggml b11429 (MIT), LLVM OpenMP (Apache-2.0 WITH
  LLVM exception) and the MSVC runtime.
- Section E, l.1111-1114, lists the four models: Granite 4.2 3B, Qwen 3.5 4B, Granite 4.2
  8B and Qwen 3.5 9B. All are Apache-2.0, with a pinned HF commit URL and sha256.

## 3. Catalog and measurement

`catalog.json` `recommendedByTier` = `qwen3.5-4b` for under-8gb, 8gb, 16gb and 32gb.

`minRamBytes`: 3b 7.25e9, 4b 6.70e9, 8b 11.25e9, 9b 8.75e9. Each equals the summary's peak
RSS at 32k ctx (6.13 / 5.61 / 10.17 / 7.64 GB) + 1 GiB, rounded up to 50 MB. Consistent.

I recomputed the pooled clean counts from `summary.md`:

| model          | 16k battery clean | 32k battery clean | 32k probes clean | pooled        | invented-fig trials |
| -------------- | ----------------- | ----------------- | ---------------- | ------------- | ------------------- |
| qwen3.5-4b     | 11/12             | 10/12             | 8/12             | 29/36 (80.6%) | 1 + 4 = 5           |
| granite-4.2-3b | 7/12              | 9/12              | 10/12            | 26/36 (72.2%) | 4 + 2 = 6           |
| qwen3.5-9b     | not run           | 7/12              | 11/12            | 18/24 (75.0%) | 1                   |
| granite-4.2-8b | not run           | 8/12              | 8/12             | 16/24 (66.7%) | 3                   |

These match the catalog comment and commit `fb878544`. The rule (clean rate first, speed
second) is applied in `scripts/r16/measure_local.py:511`, which sorts by `-clean_rate`, then
`-gen_tok_s`. On a like-for-like 32k comparison, though, qwen3.5-4b and qwen3.5-9b **tie at
18/24**. 4b wins on speed (18.63 vs 14.65 tok/s) and on the grader (12/12 vs 8/12). 9b has
far fewer invented-figure trials (1 vs 4) and figures (1 vs 8). The pooled lead comes only
from the 16k battery that 9b never ran. Every trial is k=1. That matters for the inferred
32gb tier (finding M2).

On honest labelling, the catalog comment, `README.md:138`, `docs/RELEASE_NOTES_v0.10.0.md:10`
and `docs/CURRENT_STATE.md:35` all state measured vs inferred. CURRENT_STATE is the most
precise ("Measured: 16 GB at 32k context, and the under-8 GB context (16k) on 16 GB hardware.
Inferred: 8 GB, 32 GB and under-8 GB hardware"). README and the release notes say only "16
GB measured, other sizes inferred". That is conservative, not overstated. No R16-MEASURE
markers remain. One wording issue is finding L2.

`catalog_for` (`catalog.py:45-70`): if the tier pick is `too-big`, it falls back to the
largest `good` model. If none is good, it returns `recommendedId: null` with an "use an online
provider" reason, so a 6 GiB machine is honestly told no model fits.

## 4. Item 3 + 4 tests

```
$ sidecar/.venv/bin/python -m pytest -q test_local_models.py test_local_engine_context.py \
    test_local_engine_errors.py test_local_engine_messages.py test_llm_ollama.py test_no_trading_surface.py
70 passed in 2.89s   EXIT=0
$ pnpm exec vitest run LocalModelStrip OnboardingFlow UpdatePrompt onboarding/KeyStep \
    settings/ModelsSection lib/local-models store/local-engine store/local-models OnboardingBanner
Test Files  9 passed (9)   Tests  137 passed (137)   EXIT=0
$ cargo test --manifest-path src-tauri/Cargo.toml local_engine
running 18 tests ... test result: ok. 18 passed; 0 failed; 37 filtered out   EXIT=0
```

The 18 Rust tests cover pinned args, start/stop, supersede, bind retry, the 1/4/10 s backoff,
4th-crash-fails, health timeout and path validation. The fresh profile is
`scripts/fresh-profile.sh` (launch/wipe/service). Its keychain service derivation is pinned
by `keychain.rs::fresh_profile_script_agrees_with_rust`. Logs:
`local/certify/{pytest-items,vitest-items,cargo-local-engine}.log`. The vitest run used the
working tree at `78d29509`.

Wizard code read (`OnboardingFlow.tsx`, `onboarding/*.tsx`):

- **Terms first.** The flow waits on `firstLaunchTosAcked` (`OnboardingFlow.tsx:52`).
- **Choose step.** Local / key / skip. Skip goes to `chosen("skip")`, which writes the marker
  and opens the tour. Escape and outside-click are blocked, but every step has its own exits.
- **LocalStep.**
  - Header Back is always wired (`back`, l.86).
  - Every error notice (catalog load, disk-short, download stopped, start error, engine
    failed) offers Try again / smaller model / "Use my own key" / "Skip for now".
  - A footer "Skip for now" is always present.
  - The only state without a forward button is the catalog "warming" wait, and it keeps Back.
- **Licence before download.** Each model card renders `Licence: {m.licence.name}` with a
  link (`LocalStep.tsx:273-284`) above the Download button. The download fires only from that
  button. It is disabled when the model is `too-big` or disk is short.
- **KeyStep.** Back and Done.
- **Tour.** "Skip the tour"/Close always present. The skip path's example is
  `showChartExample()`, which charts RELIANCE.NS keyless. The key path, or a ready engine,
  asks the example question. A local engine that isn't ready yet queues it via
  `setWaitingQuestion`.
- **Fresh-profile default.** `defaultProviderId: "local"` (`src/store/llm-providers.ts:93`).
  No `ollama pull`/`ollama serve`/"install Ollama" copy exists in `src/`. The Ollama strings in
  `sidecar/services/errors.py:334-347,559-562` fire only when the user chose provider `ollama`.

No dead end found.

## 5. Gate 8 (no trading surface)

```
$ sidecar/.venv/bin/python -m pytest -q sidecar/tests/test_no_trading_surface.py
8 passed in 1.37s
```

I grepped the added lines of `git diff v0.9.0..HEAD` (excluding docs/locks) for
`place_order|submit_order|execute_trade|broker|buy_order|sell_order|order_id|/orders|trading|
paper trad|alpaca|zerodha|kite|ibkr`. The only hit is a disclaimer line ("trading of any
kind, and nothing it shows is investment advice").

The new write routes in the diff are only `POST /local-models/{id}/download`,
`POST /local-models/{id}/cancel`, `DELETE /local-models/{id}` and `PUT /local-models/engine`.
There are no catalog (`agent_tools/catalog.py`) capability changes. The new Tauri commands
are `local_engine_*`, `update_*` and keychain profile helpers. **Gate 8 passes.**

## 6. Safety

- **Updater override** (`src-tauri/src/updater.rs:31-39`). `validate_endpoint` accepts only
  `https://<non-empty host>` or `http://127.0.0.1:<explicit port>`. Anything else is logged
  and ignored. `dangerousInsecureTransportProtocol` is set only when the validated override is
  loopback http (l.60-74). No code touches pubkey or verification; the plugin verifies on every
  path.
- **Pubkey rotation.** `tauri.conf.json` pubkey changed from `5E392E7F...` to `89FF38F7...`
  in `d1f22c7b` (lost Phase-0 private key). 0.9.0 shipped no update-check UI, so no installed
  user is stranded mid-flow. See L3.
- **Model path** (`local_engine.rs:475-502`, called at l.623-624 before any spawn). The path
  is canonicalized, must be a file, and must sit under canonical `<app-data>/models` or the
  Ollama `blobs` store (`$OLLAMA_MODELS` or `~/.ollama/models`). Rejected: `..` escapes,
  symlinks out, missing files, the directory itself and relative paths (tests l.1027-1042).
  The engine binds `--host 127.0.0.1`.
- **Secrets.** I grepped added non-test lines for log/print/console/diag calls that mention
  key/token/secret/header. No secret is logged; the one hit logs a port and data dir.
  `KeyStep` stores the key with `setSecret` (keychain). Key validation reuses the pre-existing
  `validateProvider`, which sends `api_key` in a JSON body (finding L4).

## 7. Chain and CI, as facts

`ci-local-int8.log` (at 0.10.0-beta.4, 17:17):

```
Test Files  177 passed (177)   Tests  2183 passed | 1 skipped
Lines        : 82.46% ( 11897/14427 )
ERROR: Coverage for lines (82.46%) does not meet global threshold (82.62%)
EXIT=1 17:17:10
```

`ci-local-int8-tail.log` (the rest of the chain run separately):
`CARGO_EXIT=0`, then `4102 passed, 1 skipped, 3 warnings in 239.19s`, `PYTEST_EXIT=0 17:22:27`.

`ci-local-int9.log` (head `78d29509`, after the coverage merge):
`Test Files 180 passed`, `Tests 2263 passed | 1 skipped`, `Lines : 82.99%` with no coverage
error, cargo ok, then `4102 passed, 1 skipped` and `EXIT=0 20:38:53`.

`gh pr checks 4`:

- Head `1d624bf3` (captured at the start of this run): 9/9 pass, plus build-linux/macos/
  windows, determine-tag and publish.
- Head `78d29509` at 20:39: 9/9 `pending`.

CI runs `pnpm test` (`.github/workflows/test.yml:72`), not `--coverage`. So the coverage
ratchet is enforced only by `ci-local`, and CI was green while int8 was red.

`r16-fix-coverage` (`1be5a2f2`) is merged into the branch (`78d29509`, pushed). As noted
under condition 2, it is not strictly test-only.

## Findings

| #   | sev    | file:line                                                                                     | what breaks                                                                                                                                                                                                                                                                                                                                                                                                                               | for whom                                                                                                                             |
| --- | ------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| M1  | medium | `src-tauri/tauri.conf.json:40-47` (no `bundle.resources`); `THIRD_PARTY_NOTICES.md:1091-1114` | The bundled llama.cpp/ggml (MIT), libomp (Apache-2.0) and MSVC runtime binaries ship in dmg/AppImage/exe with no notices or licence text inside the bundle (dmg Resources = icon.icns only), and no in-app licences page. MIT/Apache require the notice to travel with the binary. It is only in the repo and on the release page.                                                                                                        | Distributors/operator (licence compliance). The same gap already existed for the sidecars' deps, but R16 adds new prebuilt binaries. |
| M2  | medium | `sidecar/services/local_models/catalog.json:3-8`                                              | The single-model-for-all-tiers choice rests on pooling a 16k battery that only 3b/4b ran. At equal 32k ctx, 4b and 9b tie 18/24 clean, and 9b had 1 invented-figure trial vs 4b's 4 (1 vs 8 figures), all at k=1. The inferred 32gb tier (64k ctx, never measured) recommends the model that invented more figures when the RAM easily fits 9b. Docs label it inferred honestly, so this is a ranking-strength issue, not a misstatement. | 32 GB users: more invented figures than necessary.                                                                                   |
| L1  | low    | release `v0.10.0-beta.4` macOS app                                                            | Ad-hoc signature fails `codesign --verify --deep --strict` ("code has no resources but signature indicates they must be present"). This is the documented unsigned state (`RELEASE_NOTES_v0.10.0.md:17`).                                                                                                                                                                                                                                 | macOS users: a Gatekeeper warning, as expected.                                                                                      |
| L2  | low    | `README.md:138`                                                                               | "It also fits on an 8 GB computer", but `fits()` labels qwen3.5-4b `tight` on 8 GB (6.70e9 > 0.75 x 8 GiB) and LocalStep shows the low-RAM warning.                                                                                                                                                                                                                                                                                       | 8 GB users reading the README.                                                                                                       |
| L3  | low    | `src-tauri/tauri.conf.json:59-61`; `docs/RELEASE_NOTES_v0.10.0.md:13`                         | The pubkey was rotated and 0.9.0 has no update UI, so 0.9.0 users can never self-update to 0.10. The notes don't say to install manually. The endpoint `releases/latest/download/latest.json` also never resolves to a draft/prerelease, so in-app updates work only after a published non-prerelease (rc1 used the loopback override).                                                                                                   | 0.9.0 users; final-release process.                                                                                                  |
| L4  | low    | `src/lib/provider-validation.ts:55-61`, used by `src/components/onboarding/KeyStep.tsx:68`    | The wizard key check sends `api_key` in the POST body to `/llm/keys/validate`, against the "keys only via headers" wording. This is a pre-existing, documented exception (`sidecar/routers/llm.py:70`), loopback-only, never logged or echoed. R16 adds a caller rather than introducing it.                                                                                                                                              | Policy consistency only.                                                                                                             |
| L5  | low    | tag `v0.10.0-beta.4` vs PR #4 head                                                            | The artifacts are from `1d624bf3`; the green chain (int9) and the pending CI are at `78d29509`. The delta changes no shipped code.                                                                                                                                                                                                                                                                                                        | The rc2 record.                                                                                                                      |
| L6  | low    | `scripts/r16/measure_local.py:511`                                                            | The ranking sorts per-row clean rate, so `qwen3.5-4b@ctx16384` (no probes, 0/0) ranks #1 in `summary.md` on a smaller, easier trial set. The decision used the pooled numbers, so this matters only to readers of the summary table.                                                                                                                                                                                                      | Future measurement readers.                                                                                                          |
| L7  | low    | `src-tauri/src/local_engine.rs:475-487`                                                       | Allowed model roots include the Ollama blob store, and `$OLLAMA_MODELS` can relocate it. This is by design (it reuses installed Ollama models) but is broader than "models dir only". Env control is already local-user trust.                                                                                                                                                                                                            | None in practice.                                                                                                                    |

No critical or high findings.

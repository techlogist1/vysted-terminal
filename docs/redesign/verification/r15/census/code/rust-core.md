# CODE CENSUS — `rust-core` (Rust / Tauri Core)

APOSD critique (skill `aposd-critique`, two personas, 18 principles).
Subsystem entry: `docs/redesign/verification/r15/census/CODE_PARTITION.json` → `rust-core`.
Files read in full: `src-tauri/src/lib.rs` (623), `keychain.rs` (552), `kill_switch.rs` (97),
`main.rs` (5). Read for call-context (owned by `mcp-servers`): `openbb_mcp.rs`,
`sec_edgar_mcp.rs`. Cross-checked: `src-tauri/tauri.conf.json`, `capabilities/default.json`,
`Cargo.toml`, `src/lib/sidecar-client.ts`, `src/lib/export-artifact.ts`,
`src/modules/notes/notes-persistence.ts`, `src/store/safety.ts`, `src/lib/menu-bridge.ts`,
`scripts/smoke-test-sidecars.mjs`, `tauri-plugin-shell-2.3.6/src/process/mod.rs`,
`tauri-2.11.5/src/app.rs`.

Prior art: `docs/research/phase-10/hunt-rust-tauri.md` hunted the same files and explicitly
scoped `kill_switch.rs` OUT. Five of its findings (env race, updater half-wiring, TOCTTOU
port pick, blocking keychain I/O, `csp: null`) are **still unfixed** at `2d99cda`; they are
re-reported here with that fact attached, because "known and shipped anyway" is itself the
census signal.

---

## Tactical Tornado Verdict

**Medium-high risk — but not the usual kind.** This is not tornado code. It is
unusually well-commented, every failure path degrades instead of panicking, and the pure
helpers are unit-tested. The damage is concentrated in one pattern that a bug hunt walks
straight past: **the comment carries the invariant the structure does not**. Six separate
doc comments assert behaviour the code does not produce —

| Comment | What it claims | What the code does |
|---|---|---|
| `lib.rs:272-279` | `0` means disconnected, "the frontend treats that as disconnected" | state is set once at `:441`, never on spawn failure; the frontend never tests `0` |
| `lib.rs:281-286` | "survives a crash mid-save (SC-032)" | no `sync_all()` anywhere; `File::flush` is a no-op |
| `lib.rs:182-183` | "no stale file is written" | true for *this* boot; the *previous* boot's file is never removed |
| `lib.rs:466-469` | "no shared-state contention between them" | both threads mutate the process environment concurrently |
| `lib.rs:260-261` | "Python sidecar healthy" | a bare TCP connect; proves *a* listener, not *ours* |
| `kill_switch.rs:10-18` | frontend "is the listener" | zero `listen()` calls for that event exist in `src/` |

That is the tornado signature at a higher altitude: the *prose* was updated as an
increment, the *structure* was not. Plus three straight red flags — a 22-line function
duplicated verbatim (`lib.rs:288-310` ≡ `:319-342`), one policy hand-copied into three
functions with two behaviours (`lib.rs:116`, `lib.rs:143`, `keychain.rs:117`), and a
counter that increments on a branch that did nothing (`keychain.rs:193-194`).

---

## Design Principles Score

**Summary: 8 pass, 6 at risk, 4 violate (8/18 pass).**

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | `lib.rs:57-77` — a 21-line comment narrating Phase-8/9/9.5 measurements instead of the deferred `--onedir` fix; `lib.rs:472-485` keeps the workaround on the boot critical path | The tactical patch (raise the budget, retry) became the design; the cost moved into a 35 s frozen window (F1) |
| 2 | Deep modules | pass | `keychain.rs:298-342` — three commands, one signature each, the entire backend choice hidden behind `cfg`; callers never learn which store answered | Backend swap cost the renderer nothing |
| 3 | Information hiding | violate | `lib.rs:116-134` / `lib.rs:143-151` / `keychain.rs:117-124` — the "app_data_dir with temp fallback" policy exists three times, and `get_app_data_dir` alone skips `create_dir_all` | The sidecar's `--data-dir` and the renderer's export root agree only by hand-copy (F13) |
| 4 | Information leakage | at-risk | `lib.rs:359-375` hardcodes `layout:research-cockpit/single-focus/macro-scan/compare`, duplicating the `LayoutTemplate` union at `src/lib/layout-templates.ts:20` across a language boundary | Rename a template → the menu item silently no-ops (frontend warns, Rust still logs "emitted ✓" at `lib.rs:431`) |
| 5 | General-purpose modules | violate | `lib.rs:288-310` and `lib.rs:319-342` are the same function twice, differing only in `contents.as_bytes()` vs `&contents`, with different temp-name defaults (`"note"` / `"export"`) | Every durability fix (F7) and every path guard (F5) must be written twice |
| 6 | Different layer, different abstraction | violate | `kill_switch.rs:10-18` — the OS-wide emergency control is implemented *above* the renderer it exists to override; `lib.rs:260-265` treats a TCP handshake as a health verdict | The emergency path shares fate with the thing it overrides (F4); "healthy" is asserted from evidence that cannot support it (F8) |
| 7 | Pull complexity downward | violate | `lib.rs:288-296` takes any absolute `path` with no confinement; the guard lives in callers — `src/modules/notes/notes-persistence.ts:68` sanitises `[/\\]`, `src/lib/export-artifact.ts:76-88` does not | Complexity pushed up into every future caller, one of which already forgot (F5) |
| 8 | Better together / apart | pass | `kill_switch.rs` split from `lib.rs` keeps §6.5's Tier-1 surface auditable in 97 lines | A safety reviewer reads one file |
| 9 | Define errors out of existence | at-risk | `keychain.rs:288` `read(account).unwrap_or(None)`; `keychain.rs:197` sets `migrated = true` regardless | An error is converted to a silent empty *and* made permanent (F11) |
| 10 | Design it twice | pass | `keychain.rs:216-237` + `:354-360` record that `spawn_blocking` was tried and rejected with the measured reason | The next maintainer will not re-break it |
| 11 | Comments describe non-obvious | at-risk | `lib.rs:57-77`, `lib.rs:242-247`, `lib.rs:448-469` carry history (Phase 8 / 9 / 9.5 / R8) that belongs in `CHANGELOG.md` per this repo's own rule (`CLAUDE.md` "Living document") | ~90 of 623 lines in `lib.rs` are archaeology; the reader must separate active rules from dead ones |
| 12 | Comments first | pass | Every command and helper is documented before its body; the doc states the contract, not the mechanics | Low cost to read cold |
| 13 | Choosing names | pass | `wait_for_port_timeout`, `register_unavailable`, `mcp_endpoint_path` say exactly what they do — the *names* are honest even where the callers over-claim | The lie at `lib.rs:261` is the caller's, not the name's |
| 14 | Modifying existing code | violate | Six doc comments (table above) assert post-change behaviour the change never implemented | Each one is a trap that reads as a guarantee |
| 15 | Consistency | at-risk | `scripts/smoke-test-sidecars.mjs:195-207` tree-kills PyInstaller children because `CLAUDE.md` mandates it; `lib.rs:507-518` does a bare `child.kill()` | The repo's own documented rule is applied in the test harness and not in the product (F3) |
| 16 | Code should be obvious | at-risk | `lib.rs:437-503` — nothing in `setup()` signals that `join()`ing two 90 s-budget threads blocks the main thread before `app.run()` starts the event loop | The most expensive property of the boot path is invisible at the call site (F1) |
| 17 | Design for the future | pass | `MCP_PORT_WAIT_SECS` / `_ATTEMPTS` as named constants threaded through one helper (`lib.rs:78-110`) and exercised by a test (`lib.rs:601-622`) that guards against zeroing them | A budget change is one edit, and cannot silently become a no-op |
| 18 | Performance as design | pass | `wait_for_port_with_retries` short-circuits on first connect (`lib.rs:101-108`), so a warm boot pays ~0 for a 90 s ceiling | The ceiling is free when it is not needed |

---

## Overall impression

The failure-handling instinct here is good: `start_main_sidecar` cannot panic, every MCP
spawn path degrades to a port-0 sentinel, a missing binary is a log line rather than a dead
app. The problem is that **graceful degradation was implemented and then never surfaced**.
Three of the five highest-severity findings are the same shape: the core *knows* something
went wrong (spawn failed, port never bound, the child was never reaped, no one is listening
to the kill switch) and the knowledge dies in `eprintln!`. In a packaged desktop app nobody
reads stderr. The single biggest complexity reduction is to make the core's boot state a
*value the renderer can read* instead of a log line — one `SidecarStatus` struct closes F9
and makes F8's health probe worth doing.

## What's working

- **`keychain.rs` is the deepest module in the subsystem.** `cfg`-selected backends behind
  three identical command signatures (`keychain.rs:298-342`), the dev backend literally
  absent from release builds, and a test that asserts the build-profile witness
  (`keychain.rs:378-386`). Callers cannot depend on which store answered — that is
  information hiding done properly, and it is why the R9 dev-signing change cost the
  renderer nothing.
- **The pure/impure split around the MCP discovery file.** `mcp_endpoint_json` and
  `mcp_endpoint_path` (`lib.rs:166-178`) are I/O-free precisely so they can be tested
  (`lib.rs:533-547`), with the I/O isolated in `write_mcp_endpoint_file`. In a Tauri crate
  where `cargo test` can never run the app, carving out the testable core is the right move.
- **The retry helper's test guards the guard.** `lib.rs:601-622` runs the *shipped
  constants* through the helper so an accidental `MCP_PORT_WAIT_ATTEMPTS = 0` cannot turn
  the bind probe into a no-op. Most codebases test the helper and not the config.

## Priority issues

### [P0] `setup()` blocks the main thread for the full cold-boot MCP budget
- **Principle**: 16 (obviousness), 6 (different layer)
- **Complexity symptom**: cognitive load + change amplification
- **Evidence**: `lib.rs:472-485` spawns both MCP supervisors then `join()`s both inside the
  `setup` closure. `tauri-2.11.5/src/app.rs:2521-2534` runs `setup` *after* the config
  windows are built but *before* `App::run()` starts the event loop, so the main thread is
  blocked with an unpainted window. Each supervisor's `wait_for_port_with_retries` budget is
  `MCP_PORT_WAIT_SECS(45) × MCP_PORT_WAIT_ATTEMPTS(2)` = 90 s (`lib.rs:78-83`,
  `openbb_mcp.rs:149-159`). The code's own measurement (`lib.rs:68-72`) is 34.2 s / 33.6 s
  cold, in parallel and contended. `src/lib/sidecar-client.ts:105-110` documents the
  downstream effect from the other side: "the main sidecar spawns only after a
  tens-of-seconds MCP-supervisor join on cold boot".
- **Why it matters**: every cold launch shows a frozen, unpainted window (macOS beachball)
  for ~35 s, worst case 90 s, and the main sidecar — the thing the product actually needs —
  is not even spawned until after that. This is the first thing a new user sees.
- **Fix**: move the join *and* `start_main_sidecar` into one background thread and return
  from `setup` immediately. The stated reason for the join (`lib.rs:482-485`: env vars must
  settle before the sidecar reads them) is satisfied identically — it only requires the join
  to precede the sidecar *spawn*, not to precede the event loop. `start_main_sidecar` needs
  `&AppHandle` instead of `&App`; every call it makes (`path()`, `shell()`, `manage()`) is
  available on `AppHandle`.

### [P1] Quitting the app orphans the real sidecar processes
- **Principle**: 15 (consistency), 9 (define errors out of existence)
- **Complexity symptom**: unknown unknowns
- **Evidence**: `lib.rs:510-517` calls `child.kill()`;
  `tauri-plugin-shell-2.3.6/src/process/mod.rs:78-81` is `self.inner.kill()` → `SharedChild`
  → `std::process::Child::kill` = `SIGKILL` to that one pid. PyInstaller `--onefile` runs a
  bootloader parent that forks the real server. Live `ps -eo pid,ppid,command` on the
  operator's session: `62079 vysted-terminal` → `62522 vysted-sidecar --port 53693` →
  **`62549 vysted-sidecar --port 53693`**; same shape for openbb (`62175`→`62213`) and
  sec-edgar (`62176`→`62212`). PIDs `81333` / `81337` are already reparented to PPID 1 —
  orphaned sidecars from an earlier run, still listening. `CLAUDE.md` states the rule
  ("Node scripts that spawn sidecar binaries must tree-kill on teardown… PyInstaller workers
  orphan and hold the `_MEI` lock otherwise") and `scripts/smoke-test-sidecars.mjs:195-207`
  implements it — the *product* does not.
- **Why it matters**: every quit leaks three HTTP servers that keep listening on loopback,
  keep their `_MEI` extraction dirs, and keep serving whatever data dir they were started
  with. Across a day of restarts the machine accumulates them. Combined with P2 below, a
  stale discovery file points an external MCP client straight at one of these zombies.
- **Fix**: record `child.pid()` at spawn; on `RunEvent::Exit` kill the group — POSIX
  `libc::killpg` (spawn with `setsid`/`process_group(0)`), Windows `taskkill /F /T /PID`.
  Exactly what `_killTree` in the smoke test already does.

### [P1] The kill-switch shortcut is a dead key, and the first-launch TOS says it works
- **Principle**: 6 (different layer, different abstraction), 14 (modifying existing code)
- **Complexity symptom**: unknown unknowns
- **Evidence**: `kill_switch.rs:59-61` and `:94-97` emit `kill-switch:requested`. The only
  `listen(` call in the entire frontend is `src/lib/menu-bridge.ts:21` (for
  `vysted://menu-layout`). `src/store/safety.ts:13-18` states it outright: "the read-only
  app's craft pass removed the kill-switch UI surface, so nothing currently listens for the
  event". `src/modules/safety/index.ts:10-12` repeats it. Meanwhile
  `src/modules/safety/DisclaimerFlow.tsx:45` still shows the user, in the first-launch terms
  they must accept: *"A kill switch (Cmd/Ctrl+Shift+K) halts all order routing globally; use
  it in any emergency."* `kill_switch.rs:75` logs "registered global shortcut" on success, so
  the log reports health.
- **Why it matters**: the one §6.5 control promised to be reachable in under two seconds
  from any UI state does nothing, gives zero feedback, and the user was told in writing that
  it works. (Live order execution is out of scope by decision — the defect is the false
  written promise and the dead control, not the missing order path.)
- **Fix**: smallest is one line — strike that sentence from `DisclaimerFlow.tsx:45` until the
  surface returns. Structurally: `Emitter::emit` returns `Ok(())` whether or not anyone is
  listening, so a safety control must not be built on it. Rust owns the sidecar port
  (`SidecarPort`, `lib.rs:21`); it should issue the `POST /safety/kill-switch` itself rather
  than delegating to the renderer it is meant to override.

### [P1] `write_text_atomic` / `write_bytes_atomic` accept any path from the webview
- **Principle**: 7 (pull complexity downward)
- **Complexity symptom**: change amplification
- **Evidence**: `lib.rs:288-296` and `:319-327` validate nothing beyond `dest.parent()`,
  then `create_dir_all(parent)` and write. Both are in the production `invoke_handler`
  (`lib.rs:410-411`). `src-tauri/tauri.conf.json` sets `app.security.csp = null`. The
  confinement lives in callers, inconsistently: `src/modules/notes/notes-persistence.ts:68`
  strips `[/\\]` from the scope; `src/lib/export-artifact.ts:76-88` interpolates `subdir`
  and `filename` straight into the path with no guard.
- **Why it matters**: any script in the webview — a third-party plugin panel is ordinary JS
  in the same context with full `invoke` access — writes arbitrary bytes anywhere the user
  can write, `dev-keystore.json` included. There is no live XSS vector today (zero
  `innerHTML` / `dangerouslySetInnerHTML` under `src/` or `plugins/`), so this is a missing
  boundary rather than an open hole — but it is the boundary the plugin architecture will
  lean on.
- **Fix**: one shared private `write_atomic(path, bytes)` that canonicalises `parent` and
  rejects anything not under `app.path().app_data_dir()`; both commands become one line
  (this also closes the duplication at principle 5).

### [P2] The "atomic" write never reaches stable storage
- **Principle**: 9 (define errors out of existence), 14
- **Complexity symptom**: unknown unknowns
- **Evidence**: `lib.rs:303-309` / `:336-341` do `File::create` → `write_all` → `flush()` →
  `rename`. `std::fs::File`'s `Write::flush` is a documented no-op (a `File` is unbuffered;
  it never fsyncs). There is no `sync_all()` on the temp file and none on the parent
  directory. The doc comment at `lib.rs:281-286` claims "SC-032: survives a crash mid-save".
- **Why it matters**: `rename(2)` is atomic for the *directory entry*, not for the *data*.
  On power loss the renamed note can be visible with zero or partial content — the exact
  case the comment says is covered. Notes are the product's only user-authored durable
  artifact.
- **Fix**: `f.sync_all()?` before the rename; on unix also `File::open(parent)?.sync_all()`
  after it. Two lines, in one place once the duplication above is collapsed.

---

## Persona walkthrough

**Tactical Tornado.** The tornado wrote `lib.rs:57-77` — 21 lines of measurement history
defending a constant, added because a boot was flaky. Next flake it becomes 60 s, then
three attempts, and the comment grows another paragraph; nobody removes the `--onedir` note
(`lib.rs:76-77`) because it now reads as documented rather than deferred. The same hand
wrote `write_bytes_atomic` by copying `write_text_atomic` (`lib.rs:319-342`) and changing
two tokens, and added `migrated += 1` (`keychain.rs:194`) next to the insert without
checking whether the insert happened. Each of these is locally cheap and correct-ish, and
each one is a place the next change has to be made twice or not at all.

**Strategic Thinker.** The redesign is small and structural: (a) `setup` registers state and
returns — *one* background thread owns the whole boot sequence (MCP spawns → join → main
sidecar → health probe → discovery file), so the boot path's cost is expressed once, in
order, off the main thread; (b) boot outcome becomes a value — `SidecarStatus { port,
state: Starting|Ready|Failed(reason) }` in Tauri state, replacing the port-0 sentinel that
`lib.rs:272-279` documents and nothing honours, so the renderer can distinguish "still
extracting" from "binary missing" instead of spinning for 120 s
(`src/lib/sidecar-client.ts:126-141`); (c) `wait_for_port` becomes `wait_for_health` — a
`GET /health` with a field match, which the frontend already does and the core does not;
(d) one `write_atomic` confined to the data dir with `sync_all`, both commands one line
over it. Roughly −60 lines, and five of the fifteen findings disappear.

## Minor observations

- `lib.rs:510` `state.0.lock().unwrap()` panics on a poisoned mutex during exit teardown —
  harmless today (nothing else locks it) but it is the one `unwrap` on the shutdown path.
- `lib.rs:133` `to_string_lossy()` silently mangles a non-UTF-8 data-dir path; the sidecar
  then receives a `--data-dir` that does not exist. Vanishing on macOS, possible on Linux.
- `lib.rs:349-387` the Layout menu is `cfg(target_os = "macos")` only; Windows/Linux users
  have no equivalent entry point to the four cockpit modes.
- `lib.rs:431` logs `layout '<t>' → emitted` — `Emitter::emit` succeeding says nothing about
  delivery; `src/lib/menu-bridge.ts:36` is where an unknown template actually surfaces.
- `src/modules/notes/notes-persistence.ts:80-97` (`exportNoteMd`) has zero callers — dead
  code on the `write_text_atomic` surface. Owned by `frontend-panels`, noted here because it
  is the second, unguarded caller shape for this command.

## Questions to consider

- If `setup` returned immediately and the entire boot ran as one ordered background task,
  would any of the port-wait budget constants still need to be tuned?
- The core is the only process that knows *why* boot failed. What would the renderer render
  differently if that reason were a value instead of an `eprintln!`?
- `kill_switch.rs` deliberately keeps Rust free of an HTTP client. Is that still the right
  trade for a control whose entire value is working when the renderer does not?

## Run notes

- Target: `src-tauri/src` (`rust-core`: `keychain.rs`, `kill_switch.rs`, `lib.rs`, `main.rs`).
- **Assessment independence: degraded (sequential, single context)** — R15 workers are
  bounded single-job agents; no sub-agent dispatch. Assessment A (Strategic Thinker,
  18-principle pass) was completed and tabled before the Assessment B red-flag scan.
- Ignore list: `.aposd/critique/ignore.md` absent.
- **Snapshot persistence deliberately skipped** — writing `.aposd/critique/*` would leave
  stray untracked files in a run whose pre-push guard checks for exactly that
  (`docs/redesign/verification/r15/stage0/PUSHGUARD_PROOF.md`). No temp files created.
- No processes started, stopped or killed; `ps` was read-only. No GUI interaction.
- Raw findings: `docs/redesign/verification/r15/census/raw/code-rust-core.json` (15).

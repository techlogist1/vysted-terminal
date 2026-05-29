# Phase 10 — Adversarial Bug Hunt: Rust/Tauri Core + IPC + Keychain + Sidecar Spawn

Lens: `src-tauri/src/*` — unwrap/panic paths, sidecar spawn/port-announce races,
keychain command error handling, IPC command edge cases, window/config issues,
the MCP subprocess spawn + `wait_for_port` logic, auto-updater.

Scope note: `src-tauri/src/kill_switch.rs` is a §6.5 LOCKED file; its internal
logic is NOT flagged. Where the kill-switch interacts with Tauri capabilities
(an external-config concern, not the locked internals), that is in scope and
analyzed below as a non-bug clarification.

Files read in full: `lib.rs`, `main.rs`, `keychain.rs`, `openbb_mcp.rs`,
`sec_edgar_mcp.rs`, `kill_switch.rs`, `build.rs`, `Cargo.toml`,
`tauri.conf.json`, `capabilities/default.json`, plus
`gen/schemas/acl-manifests.json` (global-shortcut ACL), `src/lib/sidecar-client.ts`,
`src/lib/keychain.ts`.

Ground truth established:
- `cargo test --no-run` → exit 0 (compiles clean).
- `cargo clippy --all-targets` → no warnings (so none of the findings below are
  lint-detectable in edition 2021; they are runtime/semantic/config issues).
- Rust edition = 2021 (`Cargo.toml:6`); `rustc 1.95.0`. In edition 2021
  `std::env::set_var` is still safe-callable (the `unsafe` deprecation lands
  only in edition 2024), so the compiler does not warn on the env race below.
- Version is `0.8.0` consistently across `package.json`, `Cargo.toml`,
  `tauri.conf.json`, `sidecar/app.py`, `src/lib/plugin-bootstrap.ts`
  (`HOST_VERSION`). **No version drift** — not a finding.
- Window has no explicit `"label"` in `tauri.conf.json`; Tauri 2 assigns the
  first window the label `"main"`, which matches `capabilities/default.json`
  `"windows": ["main"]`. **Not a bug.**

---

## BUG 1 — Concurrent `std::env::set_var` / `remove_var` from two parallel threads is a data race (non-thread-safe `setenv`)

- **File:** `src-tauri/src/lib.rs:169-182`, mutations at
  `openbb_mcp.rs:85-86` / `openbb_mcp.rs:59-60` and
  `sec_edgar_mcp.rs:85-86` / `sec_edgar_mcp.rs:58-59`
- **Severity:** medium-high
- **Confidence:** 0.8

The setup hook deliberately spawns the two MCP supervisors on **separate OS
threads to overlap their cold-boot port waits** (Phase-9 UC1 fix, documented at
`lib.rs:154-166`):

```rust
let openbb_thread = thread::spawn(move || { openbb_mcp::spawn(&openbb_handle) ... });
let sec_thread    = thread::spawn(move || { sec_edgar_mcp::spawn(&sec_handle)  ... });
let _ = openbb_thread.join();
let _ = sec_thread.join();
```

Both threads run concurrently, and the **first thing each `spawn` does** is
mutate the process environment:

- openbb thread: `std::env::set_var("VYSTED_OPENBB_MCP_PORT", ...)` +
  `set_var("VYSTED_OPENBB_MCP_HOST", ...)` (`openbb_mcp.rs:85-86`), and on the
  missing-binary path `register_unavailable` calls
  `std::env::remove_var(...)` twice (`openbb_mcp.rs:59-60`).
- sec thread: the identical pattern (`sec_edgar_mcp.rs:85-86`, `:58-59`).

`std::env::set_var` / `remove_var` delegate to the libc `setenv(3)` /
`unsetenv(3)`, which on glibc, musl, and macOS are **not thread-safe**: they
mutate (and may `realloc`) the shared global `environ` array. Two threads
calling them simultaneously — even on *different keys* — race on that array.
The documented failure modes are a lost write, a use-after-free of the old
`environ` block, or a crash. Rust's own std docs explicitly warn that
`set_var`/`remove_var` are unsound to call while other threads may be reading
or writing the environment, which is exactly the situation here (and is why
the operation became `unsafe` in edition 2024).

The keys differ, so the *intended* outcome (both env vars settled before the
join) is usually achieved — but "usually" is the hallmark of a data race. This
is the same class of nondeterministic, hard-to-reproduce bug the Phase-8/9 UC1
work fought ("bound on some boots, not others"); a rare environ corruption here
would present as one MCP port env var being missing/garbage at sidecar-read
time, sending that provider into fallback for no visible reason.

**Repro:** Hard to force deterministically (it is a race), but the structure
guarantees the unsound pattern: two threads, both calling `setenv`/`unsetenv`
with no synchronization, by construction. A TSan build of the Rust core, or a
stress harness that spawns the two supervisors in a tight loop, would surface
it. The clean-compile + clean-clippy confirms no tooling currently catches it.

**Fix:** Set the env vars from the **single setup thread before spawning the
worker threads**, or have each worker return its `(port | unavailable)` result
to the setup thread which then sets the env vars serially after the join. The
env vars only need to be settled before the *main sidecar* spawns (`lib.rs:195`),
which is already after both joins — so there is no reason to mutate `environ`
from inside the worker threads at all. Pass the port back via the thread's
`JoinHandle` return value:

```rust
let openbb_thread = thread::spawn(move || openbb_mcp::spawn(&openbb_handle)); // returns port|0
let sec_thread    = thread::spawn(move || sec_edgar_mcp::spawn(&sec_handle));
let openbb_port = openbb_thread.join().unwrap_or(0);
let sec_port    = sec_thread.join().unwrap_or(0);
// now, on ONE thread, set/remove the env vars serially:
if openbb_port != 0 { std::env::set_var("VYSTED_OPENBB_MCP_PORT", openbb_port.to_string()); ... }
```

Alternatively wrap the env mutations in a shared `Mutex` — but the
return-value approach removes the race entirely and is cleaner. (`app.manage`
of the distinct state types from each thread is genuinely fine — the comment
at `lib.rs:164-166` is correct that *that* is not contended. The env block is
the part that is shared and unsynchronized.)

---

## BUG 2 — Hard panic at launch if data-dir creation or main-sidecar spawn fails (no graceful degradation)

- **File:** `src-tauri/src/lib.rs:187-201`
- **Severity:** medium
- **Confidence:** 0.9

The setup hook uses `.expect(...)` on four fallible operations that can fail in
the field:

```rust
let data_dir = app.path().app_data_dir()
    .expect("failed to resolve the application data directory");      // :190
std::fs::create_dir_all(&data_dir)
    .expect("failed to create the application data directory");        // :192
let sidecar = app.shell().sidecar("vysted-sidecar")
    .expect("failed to create the sidecar command")                    // :198
    .args(["--port", &port.to_string(), "--data-dir", &data_dir]);
let (mut rx, child) = sidecar.spawn()
    .expect("failed to spawn the Python sidecar");                     // :201
```

Each `expect` panics inside `setup`, which Tauri propagates as a build/setup
failure → the process aborts at launch. The user sees an instant crash (or a
silent no-window failure on `windows_subsystem = "windows"`, `main.rs:1` strips
the console in release, so the panic message goes nowhere on Windows).

Realistic triggers:
- `create_dir_all` fails on a read-only volume, a sandboxed/MDM-locked
  `%APPDATA%`, a full disk, or a permission-denied home directory.
- `sidecar(...)` / `spawn()` fails when the bundled binary is missing
  (a dev build that skipped `ensure-all-sidecars`), is quarantined by macOS
  Gatekeeper, lacks the executable bit after an unusual unzip, or is killed by
  AV on Windows.

The MCP supervisors (`openbb_mcp.rs:88-111`, `sec_edgar_mcp.rs:88-111`) handle
the *identical* operations gracefully — `match` on the `Err` and
`register_unavailable` — precisely because "the bundled binary may be missing"
is a known condition. The main sidecar uses the opposite policy: hard panic.

The main sidecar is more central than the MCP children, so a louder failure is
defensible — but a raw `panic!` with an `expect` string the end user never sees
is the worst possible surfacing. At minimum the data-dir `expect`s
(`:190`, `:192`) should degrade or show a real error dialog; a missing sidecar
binary is recoverable into an explicit "core service failed to start" UI rather
than an abrupt crash.

**Repro:** Build/run with `src-tauri/binaries/vysted-sidecar` absent or
non-executable (or point `app_data_dir` at a read-only location) → app panics
during setup, window never appears.

**Fix:** Convert the four `expect`s to graceful handling: on data-dir failure,
fall back to a temp dir or emit a startup-error event the frontend renders; on
sidecar spawn failure, manage a sentinel state (e.g. a `SidecarUnavailable`
flag the frontend can read via a command) and show a real error surface instead
of aborting. Mirror the `register_unavailable` pattern the MCP modules already
use.

---

## BUG 3 — `get_sidecar_port` is optimistic (returns the picked port with no health gate); the frontend caches it permanently

- **File:** `src-tauri/src/lib.rs:115-118` (`get_sidecar_port`) +
  `lib.rs:137-138` (port picked & managed) interacting with
  `src/lib/sidecar-client.ts:52-66` (`getSidecarBaseUrl`, permanent cache)
- **Severity:** medium
- **Confidence:** 0.85

`get_sidecar_port` returns `port.0` — the port chosen by `pick_free_port()` at
`lib.rs:137` — unconditionally. The actual liveness of the sidecar is checked
only in a fire-and-forget logging thread (`lib.rs:219-225`) whose `wait_for_port`
result is `println!`/`eprintln!`-ed and otherwise discarded. The IPC command
carries **no signal of whether the sidecar ever bound**.

On the frontend, `getSidecarBaseUrl` (`sidecar-client.ts:52-66`) calls
`invoke("get_sidecar_port")` once, builds `http://127.0.0.1:${port}`, and caches
it in `cachedBaseUrl` **forever** (`:53-55` short-circuits on every later call).
There is no health gate before caching and no invalidation path.

Consequence: if the main sidecar dies during startup (the very case BUG 2's
`expect` would otherwise have aborted on — but the drain/wait threads can also
observe a sidecar that spawned and then crashed *after* `spawn()` returned), the
frontend still resolves a base URL pointing at a dead port and every subsequent
request fails with a connection error, permanently, with no recovery short of
an app restart. The `/health` probe exists in the client
(`sidecar-client.ts:125`) but nothing gates `getSidecarBaseUrl` on it.

**Repro:** Let the sidecar bind, hand the port to the frontend, then kill the
sidecar (or have it crash post-`spawn`). Every panel request fails forever;
`get_sidecar_port` keeps returning the dead port.

**Fix:** Either (a) make `get_sidecar_port` (or a new `get_sidecar_status`
command) report bound/not-bound by storing the `wait_for_port` result in shared
state instead of discarding it at `lib.rs:219-225`, and have the frontend retry
discovery on connection failure; or (b) on the frontend, drop `cachedBaseUrl`
and re-resolve when a request hits a connection error. The Rust side currently
throws away the one piece of liveness information it computes.

---

## BUG 4 — Auto-updater is half-wired: plugin registered + endpoints/pubkey configured, but no capability permission, no caller, and `createUpdaterArtifacts: false`

- **File:** `src-tauri/src/lib.rs:124` (plugin registered),
  `src-tauri/tauri.conf.json:45,47-54` (artifacts off + updater config),
  `src-tauri/capabilities/default.json:6` (no `updater:*` permission)
- **Severity:** medium
- **Confidence:** 0.85

`tauri_plugin_updater::Builder::new().build()` is registered (`lib.rs:124`) and
`tauri.conf.json` carries a real `endpoints` URL and a `pubkey`
(`tauri.conf.json:48-53`). But three things are missing for it to actually
work:

1. **No `updater:*` permission** in `capabilities/default.json` (its
   `permissions` are `core:default`, `global-shortcut:allow-is-registered`,
   `notification:default`). Any frontend call to the updater's
   `check`/`download`/`install` IPC commands would be **denied by the ACL**.
2. **No frontend caller** — `grep` across `src/` finds zero references to the
   updater plugin (`@tauri-apps/plugin-updater`, `checkUpdate`, etc.). The
   updater is registered but never invoked.
3. **`createUpdaterArtifacts: false`** (`tauri.conf.json:45`) — the build does
   not emit the signed `latest.json` + update bundle the configured endpoint
   (`.../releases/latest/download/latest.json`) expects.

Per `CHANGELOG.md`, "auto-updater wiring" is explicitly **deferred to Phase 10**
(this phase), so this is *intentional* incompleteness rather than a regression.
But as it stands the updater is dead weight: a configured endpoint + pubkey with
no artifacts behind them, a registered plugin with no caller, and an ACL that
would block a caller if one were added. Anyone wiring the frontend updater UI in
Phase 10 must remember to (a) flip `createUpdaterArtifacts: true`, (b) add the
`updater:default` (or specific allow-*) permission to capabilities, and (c) keep
the pubkey in sync with the signing key used in CI. Flagging so the wiring is
not assumed "already done" because the plugin line is present.

**Repro:** Add a frontend `check()` call against the updater today → it rejects
with an ACL "not allowed" error because no `updater:*` permission is granted.

**Fix (Phase-10 task):** Set `createUpdaterArtifacts: true`, add
`updater:default` to `capabilities/default.json`, wire a frontend caller, and
verify the CI signing key matches the configured `pubkey`.

---

## BUG 5 — `pick_free_port` TOCTTOU: bind→read→release→child-binds window allows port theft / collision across the three processes

- **File:** `src-tauri/src/lib.rs:23-29` (`pick_free_port`), used at
  `lib.rs:137`, `openbb_mcp.rs:80`, `sec_edgar_mcp.rs:80`
- **Severity:** low-medium
- **Confidence:** 0.7

`pick_free_port` binds `127.0.0.1:0`, reads the OS-assigned ephemeral port, then
**drops the listener** (releasing the port) before returning the number. The
child process binds to that port some time later. Between release and child
bind there is a classic time-of-check-to-time-of-use window where:

- another process on the machine grabs the just-freed ephemeral port; or
- one of the *other* Vysted subprocesses (the openbb thread and sec thread call
  `pick_free_port` concurrently, then the main sidecar calls it again at
  `lib.rs:137`) lands on it.

The `wait_for_port_with_retries` probe (`openbb_mcp.rs:139`,
`sec_edgar_mcp.rs:138`) will then connect to *whatever* bound the port — which,
if it is the wrong process, makes the supervisor declare a *false success*
(the probe is a bare TCP connect at `lib.rs:42-51`, with no protocol/identity
check). The probe cannot tell "my child bound" from "some other process bound."

In practice the window is short and ephemeral-port reuse is uncommon, so this is
low-probability — but it is a real correctness gap, and it is the kind of
nondeterministic flake the UC1 history shows this codebase is sensitive to.

**Repro:** Hard to force without injecting a competing binder into the window;
structurally guaranteed by the bind→release→spawn ordering.

**Fix:** This is largely inherent to the "let the parent pick, child binds"
pattern over PyInstaller binaries that can't inherit an fd cleanly. Mitigations:
have each child confirm its identity once bound (e.g. probe an HTTP endpoint
that echoes an expected nonce rather than a bare TCP connect), or have the child
pick its own port and announce it back to the parent over its stdout (which is
already being drained at `lib.rs:205`, `openbb_mcp.rs:116`,
`sec_edgar_mcp.rs:116`) instead of the parent pre-picking. The bare-TCP-probe is
the weak link — it cannot distinguish the intended child from a squatter.

---

## BUG 6 — Keychain commands run blocking OS keychain I/O directly on the async runtime

- **File:** `src-tauri/src/keychain.rs:18-42`
- **Severity:** low
- **Confidence:** 0.6

`keychain_set` / `keychain_get` / `keychain_delete` are declared `async fn`
(`keychain.rs:19,25,35`) but their bodies call **synchronous, blocking** keyring
operations: `Entry::set_password`, `Entry::get_password`,
`Entry::delete_credential`. On macOS / Windows these hit the OS credential store
synchronously and can block — and on first access can pop a **system
authorization prompt** that blocks until the user responds.

Because the function is `async`, Tauri 2 runs it on its async runtime
(tokio/`tauri::async_runtime`), where a blocking call occupies an executor
worker thread for the full duration of the OS call (potentially seconds, or
indefinitely while a keychain auth dialog is up). With the BYOK flows, broker
credential entry, and plugin secrets all funneling through these three commands
(`src/lib/keychain.ts:50-63`), a burst of credential reads (e.g. resolving every
LLM + broker + MCP secret at panel mount) could stall the runtime briefly.

This is low-severity in practice — keychain access is user-driven and not
hot-path — but the `async fn` + blocking-body combination is an anti-pattern.

**Fix:** Either drop `async` (Tauri runs non-async commands on a dedicated
thread pool, which is the right place for blocking I/O), or wrap the keyring
call in `tauri::async_runtime::spawn_blocking(...)`. The error-flattening logic
(`NoEntry` → `Ok(None)` / `Ok(())`) is correct and well-reasoned and should be
kept — only the threading model needs the fix.

---

## BUG 7 — `get_openbb_mcp_port` / `get_sec_edgar_mcp_port` are registered-but-unused IPC commands that panic if invoked after a spawn-thread panic

- **File:** `src-tauri/src/openbb_mcp.rs:50-53`, `src-tauri/src/sec_edgar_mcp.rs:49-52`;
  registration `lib.rs:133-134`; non-fatal join `lib.rs:181-182`
- **Severity:** low
- **Confidence:** 0.7

`get_openbb_mcp_port` / `get_sec_edgar_mcp_port` take
`tauri::State<'_, OpenbbMcpPort>` / `SecEdgarMcpPort`. Tauri's `State` extractor
**panics if the state type was never `manage`d**. Those states are managed only
inside the worker-thread bodies (`openbb_mcp.rs:165-166` / the
`register_unavailable` paths). If a worker thread *panics* before reaching any
`app.manage` — the join in `lib.rs:181-182` swallows it via `let _ = ...join()`
— the corresponding `OpenbbMcpPort` / `SecEdgarMcpPort` is never registered, and
a later frontend `invoke("get_openbb_mcp_port")` panics the command thread.

Mitigating facts that keep this low:
- `grep` across `src/` shows the frontend **never invokes** either command
  (confirmed: only `get_sidecar_port` is invoked, in `sidecar-client.ts:63`).
  The doc comments call them speculative ("in case any future UI needs to
  address the child directly"). So today the panic is unreachable.
- `spawn` is written to never panic on the expected failure paths (it `match`es
  every `Err` and calls `register_unavailable`), so the only way to leave the
  state unmanaged is an *unexpected* panic (OOM, a panic inside `app.manage`
  itself).

Still worth noting for Phase 10's plugin-manager UI, which the comments say is
the intended consumer of these ports — wiring it up would make the latent panic
reachable.

**Fix:** Manage the `*Port(0)` / `*Process(None)` sentinel states **before**
spawning the worker threads (in the setup thread), so the state always exists
even if a worker thread dies; the worker then *replaces* the sentinel on
success. Or change the join to detect a panicked worker and register the
sentinel itself. Either guarantees the State extractor never panics.

---

## SECURITY HARDENING — `csp: null` disables Content Security Policy

- **File:** `src-tauri/tauri.conf.json:26-28`
- **Severity:** medium (security hardening, not a functional bug)
- **Confidence:** 0.75

`app.security.csp` is `null`, meaning **no Content Security Policy** is applied
to the webview. This is a notable hardening gap for *this specific app* because:

- The webview renders untrusted third-party content: news articles + sentiment,
  AI/LLM responses, SEC filing text, broker/provider payloads. Any stored or
  reflected XSS in that content executes with full webview privileges.
- The same webview can `invoke` the keychain commands (`keychain_get` etc.),
  which read **every BYOK secret** — LLM keys, broker access tokens, plugin
  secrets. An XSS payload that can call `invoke("keychain_get", {account})` can
  exfiltrate credentials, and with no CSP there is no `connect-src` restriction
  to stop it POSTing them to an attacker endpoint.

Tauri's IPC ACL limits *which* commands the webview may call, but all three
keychain commands are granted (`core:default` + the handler registration), so
the ACL is not a backstop here. A restrictive CSP (`default-src 'self'`,
explicit `connect-src` for the loopback sidecar + nothing else,
`script-src 'self'`) is the standard mitigation and is strongly advisable before
a v1.0 launch that ships real broker tokens.

**Fix:** Define a real CSP in `tauri.conf.json`. Minimum:
`default-src 'self'; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*;
img-src 'self' data: https:; style-src 'self' 'unsafe-inline'`. Validate against
the static-export frontend's actual needs (Next.js inline styles, Framer Motion)
and tighten from there. This is a Phase-10 launch-hardening item.

---

## Non-bugs verified (ruled out, to save the next reader the trip)

- **Version drift** — `0.8.0` is consistent across all six sources of truth.
  Not a finding.
- **Window `label` missing** — Tauri 2 defaults the first window to label
  `"main"`, matching `capabilities/default.json`. Correct.
- **`global-shortcut:allow-is-registered` granted but the app calls
  `.register()` from Rust** — the kill-switch shortcut is registered via
  `app.global_shortcut().register(...)` (`kill_switch.rs:74`), a **direct Rust
  API call**, not an IPC command, so it is **not** gated by the capability ACL.
  `register()` works without `global-shortcut:allow-register`. The granted
  `allow-is-registered` permission is unused by the current frontend (no IPC
  `isRegistered` call found) — harmless, mildly misleading, not a bug. The
  kill-switch shortcut registration is **not** broken by the capabilities set.
  (kill_switch.rs internals are §6.5 LOCKED and not otherwise analyzed.)
- **`app.run` Exit handler `.lock().unwrap()`** (`lib.rs:235`) and the MCP
  `kill` `.lock().unwrap()` (`openbb_mcp.rs:178`, `sec_edgar_mcp.rs:175`) — the
  `SidecarProcess`/`*McpProcess` mutexes have a single lock site each at exit,
  single-threaded; poisoning is not reachable through any concurrent holder.
  `try_state` guards the unmanaged case. Fine.
- **Stdout/stderr drain threads** (`lib.rs:205`, `openbb_mcp.rs:116`,
  `sec_edgar_mcp.rs:116`) correctly drain so child pipes never block; the loops
  exit cleanly on `rx` close. No leak/deadlock.
- **`wait_for_port_with_retries`** (`lib.rs:96-111`) — `attempts.max(1)` guards
  a zero-attempt config; short-circuits on first connect; the unit tests at
  `lib.rs:278-330` exercise the bind/timeout/retry semantics. Logic is sound.

---

## Summary table

| # | Finding | File:line | Severity | Confidence |
|---|---------|-----------|----------|------------|
| 1 | Concurrent `set_var`/`remove_var` data race across two threads | lib.rs:169-182; openbb_mcp.rs:85-86,59-60; sec_edgar_mcp.rs:85-86,58-59 | medium-high | 0.8 |
| 2 | Hard panic at launch on data-dir / sidecar-spawn failure | lib.rs:190,192,198,201 | medium | 0.9 |
| 3 | `get_sidecar_port` optimistic + frontend caches dead port forever | lib.rs:115-118,219-225; sidecar-client.ts:52-66 | medium | 0.85 |
| 4 | Auto-updater half-wired (no ACL perm, no caller, artifacts off) | lib.rs:124; tauri.conf.json:45,48-53; capabilities/default.json:6 | medium | 0.85 |
| 5 | `pick_free_port` TOCTTOU + bare-TCP probe can't verify child identity | lib.rs:23-29,42-51 | low-medium | 0.7 |
| 6 | Keychain blocking I/O on async runtime | keychain.rs:18-42 | low | 0.6 |
| 7 | Unused MCP-port IPC commands panic if state left unmanaged | openbb_mcp.rs:50-53; sec_edgar_mcp.rs:49-52 | low | 0.7 |
| S | `csp: null` — no Content Security Policy (XSS → keychain exfil) | tauri.conf.json:26-28 | medium (sec) | 0.75 |

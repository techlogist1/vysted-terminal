//! Bundled llama-server lifecycle (R16 contract, "Rust ↔ frontend: local engine").
//!
//! One engine at a time behind a mutex. `Core` is the state machine; the
//! spawner, health probe and event emitter sit behind [`Backend`] so the
//! machine is unit-tested without spawning. A `generation` counter makes every
//! stop/start cancel whatever launch or restart is still in flight; a
//! `child_id` makes the exit of an old (killed or replaced) child a no-op.

use std::collections::VecDeque;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, MutexGuard};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::pick_free_port;

pub const STATUS_EVENT: &str = "local-engine://status";
/// The safe floor: the copilot's tool subset alone is ~7.7k real tokens, so an
/// 8k engine answers its first request with a context-overflow 400 (R16
/// calibration). The frontend passes a larger `-c` by RAM tier.
const DEFAULT_CTX: u32 = 16384;
/// q8_0 KV cache (needs flash attention): about half the KV memory per token
/// on granite-4.2-3b with tool calls and prompt speed unchanged (measured on
/// Metal, b11429). Only the macOS build is verified with it.
const KV_ARGS: [&str; 6] = ["-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0"];
/// The 4th crash inside the window fails the engine instead of restarting it.
const MAX_CRASHES: usize = 4;
/// Spawns per launch when llama-server reports it could not bind its port.
const BIND_ATTEMPTS: usize = 3;
const BIND_FAILED_MARKER: &str = "couldn't bind HTTP server socket";

#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum EngineState {
    Stopped,
    Starting,
    Ready,
    Crashed,
    Failed,
}

#[derive(Clone, Debug, PartialEq, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EngineStatus {
    pub state: EngineState,
    pub port: Option<u16>,
    pub model_id: Option<String>,
    pub restarts: u32,
    pub error: Option<String>,
    pub detail: Option<String>,
}

impl EngineStatus {
    fn stopped() -> Self {
        Self {
            state: EngineState::Stopped,
            port: None,
            model_id: None,
            restarts: 0,
            error: None,
            detail: None,
        }
    }

    fn with(state: EngineState, model_id: Option<String>, restarts: usize) -> Self {
        Self {
            state,
            model_id,
            restarts: restarts as u32,
            ..Self::stopped()
        }
    }
}

pub enum ChildEvent {
    Stderr(String),
    Exited(String),
}

pub type Sink = Box<dyn Fn(ChildEvent) + Send + Sync>;

pub trait EngineChild: Send {
    fn kill(self: Box<Self>);
}

pub trait Backend: Send + Sync + 'static {
    /// Spawn llama-server with `args`; child events go to `sink`, which must
    /// never be called from inside `spawn` (the core holds its lock).
    fn spawn(&self, args: Vec<String>, sink: Sink) -> Result<Box<dyn EngineChild>, String>;
    /// `GET /health` answered 200 (model loaded).
    fn healthy(&self, port: u16) -> bool;
    fn emit(&self, status: &EngineStatus);
}

pub struct Timings {
    pub health_timeout: Duration,
    pub poll: Duration,
    pub backoff: [Duration; 3],
    pub crash_window: Duration,
}

impl Default for Timings {
    fn default() -> Self {
        Self {
            health_timeout: Duration::from_secs(180),
            poll: Duration::from_millis(500),
            backoff: [1, 4, 10].map(Duration::from_secs),
            crash_window: Duration::from_secs(600),
        }
    }
}

struct Launch {
    path: PathBuf,
    model_id: String,
    ctx: u32,
}

#[derive(Default)]
struct Inner {
    status: Option<EngineStatus>,
    child: Option<Box<dyn EngineChild>>,
    /// Id of the child whose events count; 0 = none.
    child_id: u64,
    next_child_id: u64,
    /// The current child's exit reason, recorded while `Starting`.
    exited: Option<String>,
    bind_failed: bool,
    last_stderr: Option<String>,
    generation: u64,
    launch: Option<Launch>,
    crashes: VecDeque<Instant>,
}

enum Wait {
    Ready,
    Cancelled,
    BindFailed,
    Exited(String),
    TimedOut,
}

pub struct Core<B: Backend> {
    backend: B,
    timings: Timings,
    inner: Mutex<Inner>,
}

/// The llama-server command line the contract pins (all flags exist in b11429).
pub fn engine_args(port: u16, model: &Path, ctx: u32) -> Vec<String> {
    let mut args: Vec<String> = ["--host", "127.0.0.1", "--port"].map(String::from).to_vec();
    args.push(port.to_string());
    args.push("-m".into());
    args.push(model.to_string_lossy().into_owned());
    args.push("--jinja".into());
    args.push("-c".into());
    args.push(ctx.to_string());
    args.extend(["-ngl", "999", "--no-webui"].map(String::from));
    if cfg!(target_os = "macos") {
        args.extend(KV_ARGS.map(String::from));
    }
    args
}

impl<B: Backend> Core<B> {
    pub fn new(backend: B, timings: Timings) -> Arc<Self> {
        Arc::new(Self {
            backend,
            timings,
            inner: Mutex::new(Inner::default()),
        })
    }

    fn lock(&self) -> MutexGuard<'_, Inner> {
        self.inner
            .lock()
            .unwrap_or_else(|poison| poison.into_inner())
    }

    pub fn status(&self) -> EngineStatus {
        self.lock()
            .status
            .clone()
            .unwrap_or_else(EngineStatus::stopped)
    }

    fn set(&self, inner: &mut Inner, status: EngineStatus) {
        self.backend.emit(&status);
        inner.status = Some(status);
    }

    fn state(inner: &Inner) -> EngineState {
        inner
            .status
            .as_ref()
            .map_or(EngineState::Stopped, |s| s.state)
    }

    /// Kill the current child (if any) and stop listening to it.
    fn drop_child(inner: &mut Inner) {
        inner.child_id = 0;
        inner.exited = None;
        if let Some(child) = inner.child.take() {
            child.kill();
        }
    }

    /// Start `model_id` from an already-validated `path`, blocking until it is
    /// ready, failed, or superseded by another start/stop.
    pub fn start(
        self: &Arc<Self>,
        path: PathBuf,
        model_id: String,
        ctx: Option<u32>,
    ) -> EngineStatus {
        let ctx = ctx.filter(|c| *c > 0).unwrap_or(DEFAULT_CTX);
        let generation = {
            let mut inner = self.lock();
            let same = inner
                .launch
                .as_ref()
                .is_some_and(|l| l.path == path && l.model_id == model_id && l.ctx == ctx);
            if same && Self::state(&inner) == EngineState::Ready {
                return self.status_of(&inner);
            }
            inner.generation += 1;
            Self::drop_child(&mut inner);
            inner.crashes.clear();
            inner.launch = Some(Launch {
                path,
                model_id: model_id.clone(),
                ctx,
            });
            self.set(
                &mut inner,
                EngineStatus::with(EngineState::Starting, Some(model_id), 0),
            );
            inner.generation
        };
        self.launch(generation);
        self.status()
    }

    fn status_of(&self, inner: &Inner) -> EngineStatus {
        inner.status.clone().unwrap_or_else(EngineStatus::stopped)
    }

    /// Stop and forget the engine; also the app-exit teardown. Idempotent.
    pub fn stop(&self) -> EngineStatus {
        let mut inner = self.lock();
        inner.generation += 1;
        Self::drop_child(&mut inner);
        inner.launch = None;
        inner.crashes.clear();
        if Self::state(&inner) != EngineState::Stopped || inner.status.is_none() {
            self.set(&mut inner, EngineStatus::stopped());
        }
        self.status_of(&inner)
    }

    fn fail(&self, inner: &mut Inner, generation: u64, error: String) {
        if inner.generation != generation {
            return;
        }
        Self::drop_child(inner);
        let mut status = EngineStatus::with(
            EngineState::Failed,
            inner.launch.as_ref().map(|l| l.model_id.clone()),
            inner.crashes.len(),
        );
        status.error = Some(error);
        status.detail = inner.last_stderr.clone();
        self.set(inner, status);
    }

    fn launch(self: &Arc<Self>, generation: u64) {
        for attempt in 1..=BIND_ATTEMPTS {
            let (id, port) = {
                let mut inner = self.lock();
                let Some(launch) = inner
                    .launch
                    .as_ref()
                    .filter(|_| inner.generation == generation)
                else {
                    return;
                };
                let Some(port) = pick_free_port() else {
                    let error = "The on-computer model could not start: no free local port.";
                    self.fail(&mut inner, generation, error.into());
                    return;
                };
                let args = engine_args(port, &launch.path, launch.ctx);
                inner.next_child_id += 1;
                let id = inner.next_child_id;
                inner.exited = None;
                inner.bind_failed = false;
                inner.last_stderr = None;
                match self.backend.spawn(args, self.sink(id)) {
                    Ok(child) => {
                        inner.child = Some(child);
                        inner.child_id = id;
                    }
                    Err(err) => {
                        let error = format!("The on-computer model could not start ({err}).");
                        self.fail(&mut inner, generation, error);
                        return;
                    }
                }
                (id, port)
            };
            let wait = self.wait_ready(generation, id, port);
            let mut inner = self.lock();
            match wait {
                Wait::Cancelled => return,
                Wait::Ready => {
                    if inner.generation == generation && inner.child_id == id {
                        let model_id = inner.launch.as_ref().map(|l| l.model_id.clone());
                        let mut status =
                            EngineStatus::with(EngineState::Ready, model_id, inner.crashes.len());
                        status.port = Some(port);
                        self.set(&mut inner, status);
                    }
                    return;
                }
                Wait::BindFailed if attempt < BIND_ATTEMPTS => {
                    diag_eprintln!("[llama] port {port} was taken; retrying on another port");
                    continue;
                }
                Wait::BindFailed => {
                    let error = "The on-computer model could not get a local port.";
                    self.fail(&mut inner, generation, error.into());
                }
                Wait::Exited(reason) => {
                    let error = format!("The on-computer model stopped while loading ({reason}).");
                    self.fail(&mut inner, generation, error);
                }
                Wait::TimedOut => {
                    let secs = self.timings.health_timeout.as_secs();
                    let error = format!(
                        "The on-computer model did not finish loading within {secs} seconds."
                    );
                    self.fail(&mut inner, generation, error);
                }
            }
            return;
        }
    }

    fn wait_ready(&self, generation: u64, id: u64, port: u16) -> Wait {
        let deadline = Instant::now() + self.timings.health_timeout;
        loop {
            {
                let mut inner = self.lock();
                if inner.generation != generation || inner.child_id != id {
                    return Wait::Cancelled;
                }
                if let Some(reason) = inner.exited.take() {
                    return if inner.bind_failed {
                        Wait::BindFailed
                    } else {
                        Wait::Exited(reason)
                    };
                }
            }
            if self.backend.healthy(port) {
                // Re-checked under the lock by the caller's Ready arm.
                if self.lock().exited.is_none() {
                    return Wait::Ready;
                }
                continue;
            }
            if Instant::now() >= deadline {
                return Wait::TimedOut;
            }
            thread::sleep(self.timings.poll);
        }
    }

    fn sink(self: &Arc<Self>, id: u64) -> Sink {
        let core = Arc::downgrade(self);
        Box::new(move |event| {
            if let Some(core) = core.upgrade() {
                core.on_child_event(id, event);
            }
        })
    }

    fn on_child_event(self: &Arc<Self>, id: u64, event: ChildEvent) {
        let mut inner = self.lock();
        if inner.child_id != id {
            return;
        }
        match event {
            ChildEvent::Stderr(line) => {
                if line.contains(BIND_FAILED_MARKER) {
                    inner.bind_failed = true;
                }
                let line = line.trim();
                if !line.is_empty() {
                    inner.last_stderr = Some(line.to_string());
                }
            }
            ChildEvent::Exited(reason) => {
                inner.child = None;
                match Self::state(&inner) {
                    EngineState::Starting => inner.exited = Some(reason),
                    EngineState::Ready => self.on_crash(&mut inner, reason),
                    _ => {}
                }
            }
        }
    }

    fn on_crash(self: &Arc<Self>, inner: &mut Inner, reason: String) {
        inner.child_id = 0;
        let now = Instant::now();
        inner.crashes.push_back(now);
        while inner
            .crashes
            .front()
            .is_some_and(|t| now.duration_since(*t) > self.timings.crash_window)
        {
            inner.crashes.pop_front();
        }
        let crashes = inner.crashes.len();
        let model_id = inner.launch.as_ref().map(|l| l.model_id.clone());
        let detail = inner.last_stderr.clone().or(Some(reason));
        diag_eprintln!("[llama] engine crashed ({crashes} in window)");
        if crashes >= MAX_CRASHES {
            let mins = self.timings.crash_window.as_secs() / 60;
            let mut status = EngineStatus::with(EngineState::Failed, model_id, crashes);
            status.error = Some(format!(
                "The on-computer model stopped {crashes} times in {mins} minutes, so it won't \
                 restart on its own. Start it again when you're ready."
            ));
            status.detail = detail;
            self.set(inner, status);
            return;
        }
        let mut status = EngineStatus::with(EngineState::Crashed, model_id.clone(), crashes);
        status.error = Some("The on-computer model stopped unexpectedly. Restarting…".into());
        status.detail = detail;
        self.set(inner, status);

        let generation = inner.generation;
        let delay = self.timings.backoff[crashes - 1];
        let core = Arc::clone(self);
        thread::spawn(move || {
            thread::sleep(delay);
            {
                let mut inner = core.lock();
                if inner.generation != generation || Self::state(&inner) != EngineState::Crashed {
                    return;
                }
                core.set(
                    &mut inner,
                    EngineStatus::with(EngineState::Starting, model_id, crashes),
                );
            }
            core.launch(generation);
        });
    }
}

// --- Path validation ---------------------------------------------------------

/// Where a model may live: `<app-data-dir>/models/` and the Ollama blob dir
/// (`$OLLAMA_MODELS/blobs`, else `~/.ollama/models/blobs`). Missing roots drop out.
pub fn allowed_roots(app_data_dir: &Path) -> Vec<PathBuf> {
    let ollama = std::env::var("OLLAMA_MODELS")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var_os("HOME")
                .or_else(|| std::env::var_os("USERPROFILE"))
                .map(|home| PathBuf::from(home).join(".ollama").join("models"))
        });
    let mut roots = vec![app_data_dir.join("models")];
    roots.extend(ollama.map(|dir| dir.join("blobs")));
    roots
        .into_iter()
        .filter_map(|root| root.canonicalize().ok())
        .collect()
}

/// `path` canonicalized, if it is a file inside one of `roots` (canonical).
pub fn validate_model_path(path: &Path, roots: &[PathBuf]) -> Result<PathBuf, String> {
    let rejected = || "That model file isn't in the app's models folder or Ollama's model store.";
    let canonical = path.canonicalize().map_err(|_| rejected().to_string())?;
    if canonical.is_file() && roots.iter().any(|root| canonical.starts_with(root)) {
        Ok(canonical)
    } else {
        Err(rejected().to_string())
    }
}

// --- Health probe ------------------------------------------------------------

/// `GET http://127.0.0.1:<port>/health` answered 200 (503 = still loading).
pub fn health_ok(port: u16) -> bool {
    let timeout = Duration::from_secs(2);
    let Ok(mut stream) =
        TcpStream::connect_timeout(&SocketAddr::from(([127, 0, 0, 1], port)), timeout)
    else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));
    let request = "GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    let mut head = [0u8; 12];
    stream.write_all(request.as_bytes()).is_ok()
        && stream.read_exact(&mut head).is_ok()
        && head.starts_with(b"HTTP/1.1 200")
}

// --- Tauri wiring ------------------------------------------------------------

struct TauriBackend(AppHandle);

impl EngineChild for CommandChild {
    fn kill(self: Box<Self>) {
        // llama-server runs no worker processes, so the child is the whole tree.
        let _ = CommandChild::kill(*self);
    }
}

fn exit_reason(code: Option<i32>, signal: Option<i32>) -> String {
    match (code, signal) {
        (Some(code), _) => format!("exit code {code}"),
        (None, Some(signal)) => format!("signal {signal}"),
        (None, None) => "exited".to_string(),
    }
}

impl Backend for TauriBackend {
    fn spawn(&self, args: Vec<String>, sink: Sink) -> Result<Box<dyn EngineChild>, String> {
        let command = self
            .0
            .shell()
            .sidecar("llama-server")
            .map_err(|e| e.to_string())?
            .args(args);
        // LD_LIBRARY_PATH resolves the NEEDED libs; ggml's backend loader only scans
        // the exe's dir and the CWD for the dlopen'ed libggml-cpu-*.so variants, so the
        // libs dir is the CWD too (`-m` is canonical, nothing else is CWD-relative).
        #[cfg(target_os = "linux")]
        let command = match self.0.path().resource_dir() {
            Ok(dir) => {
                let libs = dir.join("llama-libs");
                command.env("LD_LIBRARY_PATH", &libs).current_dir(libs)
            }
            Err(_) => command,
        };
        let (mut rx, child) = command.spawn().map_err(|e| e.to_string())?;
        tauri::async_runtime::spawn(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) => {
                        diag_println!("[llama] {}", String::from_utf8_lossy(&line).trim_end());
                    }
                    CommandEvent::Stderr(line) => {
                        let line = String::from_utf8_lossy(&line).trim_end().to_string();
                        diag_eprintln!("[llama] {line}");
                        sink(ChildEvent::Stderr(line));
                    }
                    CommandEvent::Terminated(payload) => {
                        let reason = exit_reason(payload.code, payload.signal);
                        diag_eprintln!("[llama] exited ({reason})");
                        sink(ChildEvent::Exited(reason));
                    }
                    _ => {}
                }
            }
        });
        Ok(Box::new(child))
    }

    fn healthy(&self, port: u16) -> bool {
        health_ok(port)
    }

    fn emit(&self, status: &EngineStatus) {
        let _ = self.0.emit(STATUS_EVENT, status);
    }
}

struct LocalEngine(Arc<Core<TauriBackend>>);

pub fn init(app: &AppHandle) {
    app.manage(LocalEngine(Core::new(
        TauriBackend(app.clone()),
        Timings::default(),
    )));
}

/// App-exit teardown: kill the engine. Idempotent.
pub fn kill(app: &AppHandle) {
    if let Some(engine) = app.try_state::<LocalEngine>() {
        engine.0.stop();
    }
}

fn core(app: &AppHandle) -> Result<Arc<Core<TauriBackend>>, String> {
    app.try_state::<LocalEngine>()
        .map(|engine| Arc::clone(&engine.0))
        .ok_or_else(|| "The on-computer model isn't available.".to_string())
}

#[tauri::command]
pub async fn local_engine_start(
    app: AppHandle,
    model_path: String,
    model_id: String,
    ctx_size: Option<u32>,
) -> Result<EngineStatus, String> {
    let roots = allowed_roots(&crate::app_data_dir(&app));
    let path = validate_model_path(Path::new(&model_path), &roots)?;
    let core = core(&app)?;
    tauri::async_runtime::spawn_blocking(move || core.start(path, model_id, ctx_size))
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn local_engine_stop(app: AppHandle) -> Result<EngineStatus, String> {
    Ok(core(&app)?.stop())
}

#[tauri::command]
pub async fn local_engine_status(app: AppHandle) -> Result<EngineStatus, String> {
    Ok(core(&app)?.status())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

    #[derive(Clone, Copy)]
    enum Health {
        Never,
        /// Healthy once at least this many children were spawned.
        FromSpawn(usize),
    }

    struct Spawned {
        args: Vec<String>,
        sink: Sink,
        killed: Arc<AtomicBool>,
    }

    struct FakeChild(Arc<AtomicBool>);
    impl EngineChild for FakeChild {
        fn kill(self: Box<Self>) {
            self.0.store(true, Ordering::SeqCst);
        }
    }

    struct Fake {
        spawned: Mutex<Vec<Spawned>>,
        health: Mutex<Health>,
        emitted: Mutex<Vec<EngineStatus>>,
        health_calls: AtomicUsize,
    }

    impl Fake {
        fn new(health: Health) -> Self {
            Self {
                spawned: Mutex::new(Vec::new()),
                health: Mutex::new(health),
                emitted: Mutex::new(Vec::new()),
                health_calls: AtomicUsize::new(0),
            }
        }
    }

    impl Backend for Arc<Fake> {
        fn spawn(&self, args: Vec<String>, sink: Sink) -> Result<Box<dyn EngineChild>, String> {
            let killed = Arc::new(AtomicBool::new(false));
            self.spawned.lock().unwrap().push(Spawned {
                args,
                sink,
                killed: Arc::clone(&killed),
            });
            Ok(Box::new(FakeChild(killed)))
        }
        fn healthy(&self, _port: u16) -> bool {
            self.health_calls.fetch_add(1, Ordering::SeqCst);
            match *self.health.lock().unwrap() {
                Health::Never => false,
                Health::FromSpawn(n) => self.spawned.lock().unwrap().len() >= n,
            }
        }
        fn emit(&self, status: &EngineStatus) {
            self.emitted.lock().unwrap().push(status.clone());
        }
    }

    impl Fake {
        fn send(&self, index: usize, event: ChildEvent) {
            let spawned = self.spawned.lock().unwrap();
            (spawned[index].sink)(event);
        }
        fn count(&self) -> usize {
            self.spawned.lock().unwrap().len()
        }
        fn killed(&self, index: usize) -> bool {
            self.spawned.lock().unwrap()[index]
                .killed
                .load(Ordering::SeqCst)
        }
        fn states(&self) -> Vec<EngineState> {
            self.emitted
                .lock()
                .unwrap()
                .iter()
                .map(|s| s.state)
                .collect()
        }
    }

    fn fast() -> Timings {
        Timings {
            health_timeout: Duration::from_millis(150),
            poll: Duration::from_millis(5),
            backoff: [Duration::from_millis(10); 3],
            crash_window: Duration::from_secs(600),
        }
    }

    fn engine(health: Health, timings: Timings) -> (Arc<Fake>, Arc<Core<Arc<Fake>>>) {
        let fake = Arc::new(Fake::new(health));
        (Arc::clone(&fake), Core::new(fake, timings))
    }

    fn wait_until(what: &str, cond: impl Fn() -> bool) {
        let deadline = Instant::now() + Duration::from_secs(5);
        while !cond() {
            assert!(Instant::now() < deadline, "timed out waiting for {what}");
            thread::sleep(Duration::from_millis(2));
        }
    }

    fn model() -> PathBuf {
        PathBuf::from("/models/a.gguf")
    }

    #[test]
    fn happy_start_reaches_ready_with_the_pinned_args() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        let status = core.start(model(), "qwen".into(), None);
        assert_eq!(status.state, EngineState::Ready);
        assert_eq!(status.model_id.as_deref(), Some("qwen"));
        let port = status.port.expect("ready carries a port");
        assert_eq!(fake.states(), [EngineState::Starting, EngineState::Ready]);
        let spawned = fake.spawned.lock().unwrap();
        assert_eq!(
            spawned[0].args,
            engine_args(port, &model(), DEFAULT_CTX),
            "the port in the args is the one reported"
        );
        let kv = if cfg!(target_os = "macos") {
            " -fa on -ctk q8_0 -ctv q8_0"
        } else {
            ""
        };
        assert_eq!(
            spawned[0].args.join(" "),
            format!(
                "--host 127.0.0.1 --port {port} -m /models/a.gguf --jinja -c 16384 -ngl 999 --no-webui{kv}"
            )
        );
    }

    #[test]
    fn port_allocation_hands_out_a_bindable_loopback_port() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        let port = core.start(model(), "m".into(), Some(2048)).port.unwrap();
        assert_ne!(port, 0);
        // The core dropped its probe listener; only the (fake) engine would bind it.
        assert!(std::net::TcpListener::bind(("127.0.0.1", port)).is_ok());
        assert!(fake.spawned.lock().unwrap()[0]
            .args
            .contains(&"2048".to_string()));
    }

    #[test]
    fn a_bind_failure_retries_on_a_fresh_port() {
        let (fake, core) = engine(Health::FromSpawn(2), fast());
        let runner = Arc::clone(&core);
        let handle = thread::spawn(move || runner.start(model(), "m".into(), None));
        wait_until("first spawn", || fake.count() == 1);
        fake.send(
            0,
            ChildEvent::Stderr(format!("E srv start: {BIND_FAILED_MARKER}, port: 1")),
        );
        fake.send(0, ChildEvent::Exited("exit code 1".into()));
        let status = handle.join().unwrap();
        assert_eq!(status.state, EngineState::Ready);
        assert_eq!(fake.count(), 2);
    }

    #[test]
    fn health_timeout_fails_with_a_reason_and_kills_the_child() {
        let (fake, core) = engine(Health::Never, fast());
        let status = core.start(model(), "m".into(), None);
        assert_eq!(status.state, EngineState::Failed);
        assert!(status.error.unwrap().contains("did not finish loading"));
        assert_eq!(status.port, None);
        assert!(fake.killed(0));
        assert!(
            fake.health_calls.load(Ordering::SeqCst) > 1,
            "polled, not probed once"
        );
    }

    #[test]
    fn an_exit_while_loading_fails_with_the_last_stderr_line() {
        let mut timings = fast();
        timings.health_timeout = Duration::from_secs(5);
        let (fake, core) = engine(Health::Never, timings);
        let runner = Arc::clone(&core);
        let handle = thread::spawn(move || runner.start(model(), "m".into(), None));
        wait_until("spawn", || fake.count() == 1);
        fake.send(0, ChildEvent::Stderr("failed to load model".into()));
        fake.send(0, ChildEvent::Exited("exit code 1".into()));
        let status = handle.join().unwrap();
        assert_eq!(status.state, EngineState::Failed);
        assert_eq!(status.detail.as_deref(), Some("failed to load model"));
        assert_eq!(fake.count(), 1, "a load failure is not retried");
    }

    #[test]
    fn a_crash_while_ready_restarts_with_backoff_and_no_leak() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        core.start(model(), "m".into(), None);
        fake.send(0, ChildEvent::Stderr("ggml_metal: out of memory".into()));
        fake.send(0, ChildEvent::Exited("signal 9".into()));
        let crashed = core.status();
        assert_eq!(crashed.state, EngineState::Crashed);
        assert_eq!(crashed.restarts, 1);
        assert_eq!(crashed.port, None);
        assert_eq!(crashed.detail.as_deref(), Some("ggml_metal: out of memory"));
        wait_until("restart ready", || {
            core.status().state == EngineState::Ready
        });
        assert_eq!(fake.count(), 2);
        assert_eq!(core.status().restarts, 1);
        assert_eq!(
            fake.states(),
            [
                EngineState::Starting,
                EngineState::Ready,
                EngineState::Crashed,
                EngineState::Starting,
                EngineState::Ready
            ]
        );
        // The dead child's late events are ignored.
        fake.send(0, ChildEvent::Exited("again".into()));
        assert_eq!(core.status().state, EngineState::Ready);
    }

    #[test]
    fn the_backoff_ladder_is_one_four_ten_seconds() {
        assert_eq!(Timings::default().backoff.map(|d| d.as_secs()), [1, 4, 10]);
        assert_eq!(Timings::default().health_timeout, Duration::from_secs(180));
        assert_eq!(Timings::default().poll, Duration::from_millis(500));
        assert_eq!(Timings::default().crash_window, Duration::from_secs(600));
    }

    #[test]
    fn the_fourth_crash_in_the_window_fails_without_restarting() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        core.start(model(), "m".into(), None);
        for crash in 0..3 {
            fake.send(crash, ChildEvent::Exited("signal 9".into()));
            wait_until("restart", || {
                fake.count() == crash + 2 && core.status().state == EngineState::Ready
            });
        }
        fake.send(3, ChildEvent::Exited("signal 9".into()));
        let status = core.status();
        assert_eq!(status.state, EngineState::Failed);
        assert_eq!(status.restarts, 4);
        assert!(status.error.unwrap().contains("4 times in 10 minutes"));
        thread::sleep(Duration::from_millis(60));
        assert_eq!(fake.count(), 4, "no fifth spawn");
        // A user start begins a fresh window.
        assert_eq!(core.start(model(), "m".into(), None).restarts, 0);
    }

    #[test]
    fn crashes_outside_the_window_do_not_count() {
        let mut timings = fast();
        timings.crash_window = Duration::from_millis(1);
        let (fake, core) = engine(Health::FromSpawn(1), timings);
        core.start(model(), "m".into(), None);
        for crash in 0..5 {
            thread::sleep(Duration::from_millis(5));
            fake.send(crash, ChildEvent::Exited("signal 9".into()));
            wait_until("restart", || core.status().state == EngineState::Ready);
        }
        assert_eq!(fake.count(), 6);
    }

    #[test]
    fn stop_during_starting_cancels_and_kills() {
        let mut timings = fast();
        timings.health_timeout = Duration::from_secs(5);
        let (fake, core) = engine(Health::Never, timings);
        let runner = Arc::clone(&core);
        let handle = thread::spawn(move || runner.start(model(), "m".into(), None));
        wait_until("spawn", || fake.count() == 1);
        assert_eq!(core.stop().state, EngineState::Stopped);
        let status = handle.join().unwrap();
        assert_eq!(status.state, EngineState::Stopped);
        assert!(fake.killed(0));
        assert_eq!(fake.states().last(), Some(&EngineState::Stopped));
        assert!(!fake.states().contains(&EngineState::Failed));
    }

    #[test]
    fn stop_during_crash_backoff_cancels_the_restart() {
        let mut timings = fast();
        timings.backoff = [Duration::from_millis(50); 3];
        let (fake, core) = engine(Health::FromSpawn(1), timings);
        core.start(model(), "m".into(), None);
        fake.send(0, ChildEvent::Exited("signal 9".into()));
        core.stop();
        thread::sleep(Duration::from_millis(100));
        assert_eq!(fake.count(), 1);
        assert_eq!(core.status().state, EngineState::Stopped);
    }

    #[test]
    fn a_start_during_starting_supersedes_the_first() {
        let mut timings = fast();
        timings.health_timeout = Duration::from_secs(5);
        let (fake, core) = engine(Health::FromSpawn(2), timings);
        let runner = Arc::clone(&core);
        let first = thread::spawn(move || runner.start(model(), "a".into(), None));
        wait_until("first spawn", || fake.count() == 1);
        let second = core.start(PathBuf::from("/models/b.gguf"), "b".into(), None);
        assert_eq!(second.state, EngineState::Ready);
        assert_eq!(second.model_id.as_deref(), Some("b"));
        assert!(fake.killed(0), "the superseded child was killed");
        assert_eq!(first.join().unwrap().model_id.as_deref(), Some("b"));
        assert!(!fake.states().contains(&EngineState::Failed));
    }

    #[test]
    fn starting_a_different_model_stops_the_old_one_and_same_model_is_a_no_op() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        let port = core.start(model(), "a".into(), None).port;
        assert_eq!(core.start(model(), "a".into(), None).port, port);
        assert_eq!(fake.count(), 1);
        core.start(PathBuf::from("/models/b.gguf"), "b".into(), None);
        assert!(fake.killed(0));
        assert_eq!(fake.count(), 2);
    }

    #[test]
    fn stop_is_idempotent_and_kills_the_ready_child() {
        let (fake, core) = engine(Health::FromSpawn(1), fast());
        core.start(model(), "m".into(), None);
        core.stop();
        core.stop();
        assert!(fake.killed(0));
        let stops = fake
            .states()
            .iter()
            .filter(|s| **s == EngineState::Stopped)
            .count();
        assert_eq!(stops, 1);
        fake.send(0, ChildEvent::Exited("signal 9".into()));
        assert_eq!(core.status().state, EngineState::Stopped);
    }

    #[test]
    fn status_serializes_to_the_contract_shape() {
        let mut status = EngineStatus::with(EngineState::Ready, Some("m".into()), 2);
        status.port = Some(4242);
        assert_eq!(
            serde_json::to_value(&status).unwrap(),
            serde_json::json!({
                "state": "ready", "port": 4242, "modelId": "m", "restarts": 2,
                "error": null, "detail": null
            })
        );
    }

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "vysted-engine-{tag}-{}-{:?}",
            std::process::id(),
            thread::current().id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn path_validation_accepts_models_and_ollama_blobs_only() {
        let base = temp_dir("paths");
        let data = base.join("data");
        let models = data.join("models");
        let blobs = base.join("ollama").join("blobs");
        std::fs::create_dir_all(&models).unwrap();
        std::fs::create_dir_all(&blobs).unwrap();
        std::fs::write(models.join("a.gguf"), b"x").unwrap();
        std::fs::write(blobs.join("sha256-abc"), b"x").unwrap();
        std::fs::write(data.join("outside.gguf"), b"x").unwrap();
        let roots: Vec<PathBuf> = [&models, &blobs]
            .iter()
            .map(|p| p.canonicalize().unwrap())
            .collect();

        assert!(validate_model_path(&models.join("a.gguf"), &roots).is_ok());
        assert!(validate_model_path(&blobs.join("sha256-abc"), &roots).is_ok());
        assert!(validate_model_path(&data.join("outside.gguf"), &roots).is_err());
        assert!(validate_model_path(&models.join("../outside.gguf"), &roots).is_err());
        assert!(validate_model_path(&models.join("missing.gguf"), &roots).is_err());
        assert!(
            validate_model_path(&models, &roots).is_err(),
            "a directory is rejected"
        );
        assert!(validate_model_path(Path::new("relative.gguf"), &roots).is_err());
        #[cfg(unix)]
        {
            let link = models.join("link.gguf");
            std::os::unix::fs::symlink(data.join("outside.gguf"), &link).unwrap();
            assert!(
                validate_model_path(&link, &roots).is_err(),
                "symlink out is rejected"
            );
        }
        // allowed_roots always includes <data>/models when it exists.
        assert!(allowed_roots(&data).contains(&models.canonicalize().unwrap()));
        let _ = std::fs::remove_dir_all(&base);
    }

    #[test]
    fn health_probe_reads_200_as_ready_and_503_as_loading() {
        fn serve(reply: &'static str) -> u16 {
            let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            let port = listener.local_addr().unwrap().port();
            thread::spawn(move || {
                if let Ok((mut stream, _)) = listener.accept() {
                    let mut buf = [0u8; 512];
                    let _ = stream.read(&mut buf);
                    let _ = stream.write_all(reply.as_bytes());
                }
            });
            port
        }
        assert!(health_ok(serve(
            "HTTP/1.1 200 OK\r\nContent-Length: 15\r\n\r\n{\"status\":\"ok\"}"
        )));
        assert!(!health_ok(serve(
            "HTTP/1.1 503 Service Unavailable\r\n\r\n"
        )));
        assert!(!health_ok(pick_free_port().unwrap()));
    }

    /// Live proof against a real llama-server; runs only when both env vars
    /// are set (`VYSTED_LLAMA_LIVE_BIN`, `VYSTED_LLAMA_LIVE_MODEL`).
    #[test]
    fn live_llama_server_lifecycle() {
        let (Ok(bin), Ok(model)) = (
            std::env::var("VYSTED_LLAMA_LIVE_BIN"),
            std::env::var("VYSTED_LLAMA_LIVE_MODEL"),
        ) else {
            return;
        };
        live::run(PathBuf::from(bin), PathBuf::from(model));
    }

    mod live {
        use super::*;
        use std::process::{Child, Command, Stdio};

        struct StdBackend {
            bin: PathBuf,
            emitted: Mutex<Vec<EngineStatus>>,
            pids: Mutex<Vec<u32>>,
        }

        struct StdChild(Arc<Mutex<Child>>);
        impl EngineChild for StdChild {
            fn kill(self: Box<Self>) {
                let mut child = self.0.lock().unwrap();
                let _ = child.kill();
                let _ = child.wait();
            }
        }

        impl Backend for Arc<StdBackend> {
            fn spawn(&self, args: Vec<String>, sink: Sink) -> Result<Box<dyn EngineChild>, String> {
                eprintln!("[live] spawn {} {}", self.bin.display(), args.join(" "));
                let mut child = Command::new(&self.bin)
                    .args(&args)
                    .stdout(Stdio::null())
                    .stderr(Stdio::piped())
                    .spawn()
                    .map_err(|e| e.to_string())?;
                self.pids.lock().unwrap().push(child.id());
                let stderr = child.stderr.take().unwrap();
                let child = Arc::new(Mutex::new(child));
                let watched = Arc::clone(&child);
                thread::spawn(move || {
                    use std::io::BufRead;
                    for line in std::io::BufReader::new(stderr)
                        .lines()
                        .map_while(Result::ok)
                    {
                        sink(ChildEvent::Stderr(line));
                    }
                    // stderr closed: the process is gone (or going).
                    let reason = loop {
                        if let Ok(Some(status)) = watched.lock().unwrap().try_wait() {
                            break format!("{status}");
                        }
                        thread::sleep(Duration::from_millis(50));
                    };
                    sink(ChildEvent::Exited(reason));
                });
                Ok(Box::new(StdChild(child)))
            }
            fn healthy(&self, port: u16) -> bool {
                health_ok(port)
            }
            fn emit(&self, status: &EngineStatus) {
                eprintln!("[live] status {}", serde_json::to_string(status).unwrap());
                self.emitted.lock().unwrap().push(status.clone());
            }
        }

        fn chat(port: u16) -> String {
            let body = r#"{"messages":[{"role":"user","content":"Reply with the single word: pong"}],"max_tokens":16}"#;
            let mut stream = TcpStream::connect(("127.0.0.1", port)).unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(60)))
                .unwrap();
            write!(
                stream,
                "POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                body.len()
            )
            .unwrap();
            let mut response = String::new();
            stream.read_to_string(&mut response).unwrap();
            response
        }

        fn alive(pid: u32) -> bool {
            Command::new("kill")
                .args(["-0", &pid.to_string()])
                .stderr(Stdio::null())
                .status()
                .is_ok_and(|s| s.success())
        }

        pub fn run(bin: PathBuf, model: PathBuf) {
            let roots = vec![model.parent().unwrap().canonicalize().unwrap()];
            let path = validate_model_path(&model, &roots).expect("model inside its root");
            let backend = Arc::new(StdBackend {
                bin,
                emitted: Mutex::new(Vec::new()),
                pids: Mutex::new(Vec::new()),
            });
            let core = Core::new(Arc::clone(&backend), Timings::default());

            let ready = core.start(path, "qwen2.5-0.5b".into(), Some(2048));
            assert_eq!(ready.state, EngineState::Ready, "{ready:?}");
            let port = ready.port.unwrap();
            let reply = chat(port);
            eprintln!("[live] chat reply: {}", reply.lines().last().unwrap_or(""));
            assert!(reply.starts_with("HTTP/1.1 200"), "{reply}");
            assert!(reply.contains("\"choices\""));

            let first = backend.pids.lock().unwrap()[0];
            eprintln!("[live] kill -9 {first}");
            Command::new("kill")
                .args(["-9", &first.to_string()])
                .status()
                .unwrap();
            wait_until_long("crashed", || {
                backend
                    .emitted
                    .lock()
                    .unwrap()
                    .iter()
                    .any(|s| s.state == EngineState::Crashed)
            });
            wait_until_long("restart ready", || {
                core.status().state == EngineState::Ready && backend.pids.lock().unwrap().len() == 2
            });
            let restarted = core.status();
            assert_eq!(restarted.restarts, 1);
            assert!(chat(restarted.port.unwrap()).starts_with("HTTP/1.1 200"));
            assert!(!alive(first), "the crashed child is gone");

            let second = backend.pids.lock().unwrap()[1];
            assert_eq!(core.stop().state, EngineState::Stopped);
            assert!(!alive(second), "stop reaped the engine");
            let pgrep = Command::new("pgrep")
                .args(["-x", "llama-server"])
                .output()
                .unwrap();
            eprintln!(
                "[live] pgrep -x llama-server after stop: {:?}",
                String::from_utf8_lossy(&pgrep.stdout)
            );
            assert!(pgrep.stdout.is_empty(), "no llama-server left");
            let states: Vec<_> = backend
                .emitted
                .lock()
                .unwrap()
                .iter()
                .map(|s| s.state)
                .collect();
            eprintln!("[live] transitions: {states:?}");
        }

        fn wait_until_long(what: &str, cond: impl Fn() -> bool) {
            let deadline = Instant::now() + Duration::from_secs(120);
            while !cond() {
                assert!(Instant::now() < deadline, "timed out waiting for {what}");
                thread::sleep(Duration::from_millis(100));
            }
        }
    }
}

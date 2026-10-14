# Set: lows-P1/mcp-servers (set-65) — rc1-battery-10, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CROSS-PLATFORM-008 | grep set_var/remove_var in src-tauri/src | no call sites, only a lib.rs:353 doc comment; lib.rs:977/993 state ports ride the sidecar Command env, core mutates no process env | holds |

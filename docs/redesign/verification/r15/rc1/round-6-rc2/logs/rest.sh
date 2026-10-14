export PATH="$PWD/sidecar/.venv/bin:$PATH"
for s in "pnpm typecheck" "cargo fmt --manifest-path src-tauri/Cargo.toml --check" "cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings" "ruff check sidecar" "ruff format --check sidecar" "pnpm exec vitest run --coverage" "cargo test --manifest-path src-tauri/Cargo.toml" "sh -c 'cd sidecar && pytest'"; do
echo "=== STAGE: $s"; eval "$s" > /tmp/rc2stage.out 2>&1; echo "STAGE_EXIT=$?"; tail -n 25 /tmp/rc2stage.out; 
done
echo ALLDONE

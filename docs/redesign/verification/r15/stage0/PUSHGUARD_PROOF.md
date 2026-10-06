# Pushguard proof — 2026-09-19 09:22 IST

Hook: `scripts/git-hooks/pre-push` (installed by `sh scripts/install-git-hooks.sh` into `.git/hooks/pre-push`). The self-test builds a throwaway clone + bare remote under a temp dir (never touches origin), plants a fake OpenRouter-shaped key, a `.pem`, and an unregistered PNG under `docs/redesign/verification/r15/`, and asserts each push is refused; then registers the PNG and asserts the push is allowed.

```
$ sh scripts/git-hooks/test-pre-push.sh
PASS  clean baseline push (no self-trip on the pattern table)
PASS  planted fake OpenRouter key is refused
PASS  hook never prints the matched value
PASS  allow-marker exempts a fixture line
PASS  added *.pem is refused
PASS  unregistered r15 capture is refused
PASS  registered r15 capture is allowed
PASS  register_capture is idempotent
PASS  image outside r15 is not gated
pushguard: all checks passed
```

False-positive calibration (writer's note in the hook source): 57 `sk-`-shaped false positives in news URLs over the last 200 commits of 004 were eliminated by \b-anchoring and excluding `-` from the generic tail class. Live calibration below = the actual first push of this run (all commits since origin/004) passing the hook.

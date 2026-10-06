#!/usr/bin/env python3
"""R15 history-secrets probe: stream the full git history for secret shapes.

Streams `git log -p -U0 --all -m --reverse` (never loads it whole), applies the
scripts/git-hooks/pre-push RULES plus extra provider shapes and a keyword-gated
entropy heuristic to ADDED lines, then sweeps every reachable blob as a
completeness cross-check (catches anything a diff view hides).

A matched VALUE is never printed or written: a hit is (commit, path, line, rule)
plus value length, Shannon entropy, a salted-free sha256[:10] so repeats of one
value group together, fixture flags, and the line with every token redacted.

Usage: python3 scripts/r15/history_secrets_scan.py <out.json>
"""

import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter

ALLOW = "pushguard:allow"

# --- the pre-push RULES, verbatim shapes ----------------------------- pushguard:allow
RULES = [
    ("openrouter-key", re.compile(r"\bsk-or-v1-[0-9A-Za-z]{32,}")),  # pushguard:allow
    ("anthropic-key", re.compile(r"\bsk-ant-[0-9A-Za-z_-]{24,}")),  # pushguard:allow
    (
        "openai-project-key",
        re.compile(r"\bsk-proj-[0-9A-Za-z_-]{32,}"),
    ),  # pushguard:allow
    ("openai-key", re.compile(r"\bsk-[0-9A-Za-z]{32,}")),  # pushguard:allow
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),  # pushguard:allow
    ("groq-key", re.compile(r"\bgsk_[0-9A-Za-z]{40,}")),  # pushguard:allow
    ("xai-key", re.compile(r"\bxai-[0-9A-Za-z]{40,}")),  # pushguard:allow
    (
        "github-token",
        re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}|\bgithub_pat_[0-9A-Za-z_]{50,}"),
    ),
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "private-key-block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),  # pushguard:allow
    (
        "broker-secret-literal",
        re.compile(
            r"""(?i)\b(?:api_secret|access_token|request_token)\b\s*[:=]\s*"""
            r"""["'][0-9A-Za-z_.-]{20,}["']"""
        ),
    ),
    # --- extra shapes the hook does not carry ---
    (
        "jwt",
        re.compile(
            r"\beyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}"
        ),
    ),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
    ("stripe-key", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{20,}")),
    ("huggingface-token", re.compile(r"\bhf_[0-9A-Za-z]{30,}")),
    ("tavily-key", re.compile(r"\btvly-[0-9A-Za-z_-]{20,}")),
    ("perplexity-key", re.compile(r"\bpplx-[0-9A-Za-z]{32,}")),
    ("replicate-token", re.compile(r"\br8_[0-9A-Za-z]{30,}")),
    ("notion-token", re.compile(r"\b(?:secret_|ntn_)[0-9A-Za-z]{40,}")),
    ("sendgrid-key", re.compile(r"\bSG\.[0-9A-Za-z_-]{16,}\.[0-9A-Za-z_-]{16,}")),
    ("telegram-bot-token", re.compile(r"\b\d{8,10}:AA[0-9A-Za-z_-]{32,}")),
    (
        "webhook-url",
        re.compile(
            r"https://(?:hooks\.slack\.com/services|discord(?:app)?\.com/api/webhooks)/\S{20,}"
        ),
    ),
    (
        "url-embedded-credentials",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@'\"]{1,64}:[^/\s:@'\"]{6,}@[^\s/]"),
    ),
    ("bearer-literal", re.compile(r"(?i)\bbearer\s+[0-9A-Za-z_.~+/-]{24,}=*")),
    ("tauri-signing-key", re.compile(r"\bdW50cnVzdGVkIGNvbW1lbnQ6[0-9A-Za-z+/=]{40,}")),
]

# keyword-gated entropy: an assignment of a long random-looking literal to a
# secret-sounding name. Bare high-entropy tokens (hashes, lockfile integrity)
# are counted per path but not listed: without a keyword they are noise.
KEYWORD = re.compile(
    r"(?i)(secret|passw|passphrase|api[_-]?key|apikey|access[_-]?key|auth[_-]?token|"
    r"\btoken\b|_token|credential|private[_-]?key|client[_-]?secret|signing|x-llm-key)"
)
TOKEN = re.compile(r"[0-9A-Za-z+/_=.-]{20,}")
SKIP_PATH = re.compile(
    r"(?:^|/)(?:pnpm-lock\.yaml|package-lock\.json|yarn\.lock|Cargo\.lock|uv\.lock|poetry\.lock)$"
    r"|\.(?:svg|map|min\.js|ipynb)$|(?:^|/)CAPTURES\.jsonl$"
)
FIXTURE_WORDS = re.compile(
    r"(?i)(test|fake|dummy|example|sample|placeholder|redact|xxxx|your[_-]|changeme|"
    r"abcdef|123456|foobar|mock|fixture|not[_-]?a[_-]?real|demo|lorem)"
)
FIXTURE_PATH = re.compile(
    r"(?i)(?:^|/)(?:tests?|__tests__|fixtures?|mocks?|examples?)/|(?:^|/)test_[^/]*\.py$|"
    r"\.(?:test|spec)\.[tj]sx?$|(?:^|/)conftest\.py$"
)


def entropy(s):
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values()) if n else 0.0


def redact(line):
    out = line
    for _, rx in RULES:
        out = rx.sub(lambda m: "<RULE-REDACTED:%d>" % len(m.group(0)), out)
    out = TOKEN.sub(
        lambda m: (
            m.group(0) if entropy(m.group(0)) < 3.3 else "<TOK:%d>" % len(m.group(0))
        ),
        out,
    )
    return out.strip()[:200]


def describe(value, path, line):
    return {
        "len": len(value),
        "entropy": round(entropy(value), 2),
        "distinct_chars": len(set(value)),
        "sha10": hashlib.sha256(value.encode()).hexdigest()[:10],
        "value_looks_fixture": bool(FIXTURE_WORDS.search(value)),
        "line_looks_fixture": bool(FIXTURE_WORDS.search(line)),
        "path_is_test": bool(FIXTURE_PATH.search(path)),
        "allow_marker": ALLOW in line,
    }


def scan_line(body, path):
    """Yield (rule, value) for one added line / blob line."""
    matched = False
    for name, rx in RULES:
        m = rx.search(body)
        if m:
            matched = True
            yield name, m.group(0)
            break
    if matched or SKIP_PATH.search(path) or not KEYWORD.search(body):
        return
    for m in TOKEN.finditer(body):
        tok = m.group(0)
        if "/" in tok and ("." in tok or tok.count("/") > 1):
            continue  # a path or URL, not a credential
        hexish = re.fullmatch(r"[0-9a-fA-F]+", tok)
        if (hexish and len(tok) >= 32 and entropy(tok) >= 3.0) or (
            not hexish
            and entropy(tok) >= 4.0
            and re.search(r"\d", tok)
            and re.search(r"[a-z]", tok)
            and re.search(r"[A-Z]", tok)
        ):
            yield "entropy-keyword", tok
            return


BARE = {}  # path -> {count, max_entropy, samples[]}: UNGATED high-entropy tokens, triaged by path


def bare_entropy(body, path, n):
    """No keyword gate: any long mixed-class token with near-random entropy."""
    if SKIP_PATH.search(path) or len(body) > 20000:
        return
    for m in TOKEN.finditer(body):
        tok = m.group(0)
        if len(tok) < 32 or "/" in tok or "." in tok or entropy(tok) < 4.5:
            continue
        if not (
            re.search(r"\d", tok)
            and re.search(r"[a-z]", tok)
            and re.search(r"[A-Z]", tok)
        ):
            continue
        slot = BARE.setdefault(path, dict(count=0, max_entropy=0.0, samples=[]))
        slot["count"] += 1
        slot["max_entropy"] = max(slot["max_entropy"], round(entropy(tok), 2))
        if len(slot["samples"]) < 3:
            slot["samples"].append(dict(line=n, len=len(tok), context=redact(body)))


def stream_history():
    """Pass 1: every ADDED line of every commit on every ref (merges via -m)."""
    proc = subprocess.Popen(
        [
            "git",
            "log",
            "-p",
            "-U0",
            "-m",
            "--all",
            "--reverse",
            "--no-color",
            "--format=%x01%H",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    hits, commits, added = [], set(), 0
    commit = path = "?"
    lineno = 0
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        if line.startswith("\x01"):
            commit = line[1:41]
            commits.add(commit)
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+++ "):
            path = "/dev/null"
        elif line.startswith("@@"):
            m = re.match(r"@@ -\S+ \+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+"):
            body = line[1:]
            added += 1
            for rule, value in scan_line(body, path):
                hits.append(
                    dict(
                        commit=commit[:10],
                        path=path,
                        line=lineno,
                        rule=rule,
                        context=redact(body),
                        **describe(value, path, body),
                    )
                )
            lineno += 1
    proc.wait()
    return hits, len(commits), added


def sweep_blobs():
    """Pass 2: every blob reachable from any ref, scanned whole."""
    objs = subprocess.run(
        ["git", "rev-list", "--all", "--objects"], stdout=subprocess.PIPE, check=True
    ).stdout.decode("utf-8", "replace")
    names = {}
    for row in objs.split("\n"):
        sha, _, name = row.partition(" ")
        if name:
            names.setdefault(sha, name)
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    hits, blobs = [], 0
    BARE.clear()
    for sha, name in names.items():
        proc.stdin.write((sha + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        if len(header) < 3:
            continue
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        if header[1] != b"blob" or b"\0" in data[:8000]:
            continue
        blobs += 1
        for n, body in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
            for rule, value in scan_line(body, name):
                hits.append(
                    dict(
                        blob=sha[:10],
                        path=name,
                        line=n,
                        rule=rule,
                        context=redact(body),
                        **describe(value, name, body),
                    )
                )
            bare_entropy(body, name, n)
    proc.stdin.close()
    proc.wait()
    return hits, blobs


def secret_filenames():
    raw = subprocess.run(
        [
            "git",
            "log",
            "--all",
            "--diff-filter=A",
            "--name-only",
            "--no-color",
            "--format=%x01%h",
        ],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.decode("utf-8", "replace")
    hits, commit = [], "?"
    for line in raw.split("\n"):
        if line.startswith("\x01"):
            commit = line[1:]
            continue
        p = line.strip()
        base = p.rsplit("/", 1)[-1]
        if (
            base in ("dev-keystore.json", ".env")
            or base.startswith(".env.")
            or re.search(
                r"\.(?:pem|p12|pfx|key|keystore|jks|mobileprovision)$|(?:^|/)id_(?:rsa|ed25519|ecdsa)$",
                base,
            )
        ):
            hits.append(dict(commit=commit, path=p, rule="secret-bearing-filename"))
    return hits


def demo():
    fake = "sk-or-v1-" + "a1B2" * 10  # pushguard:allow
    assert [r for r, _ in scan_line("KEY = '%s'" % fake, "x.py")] == ["openrouter-key"]
    assert fake not in redact("KEY = '%s'" % fake)
    assert not list(
        scan_line("see risk-assessment-congo-and-the-long-river-report-2024", "x.md")
    )
    assert [
        r for r, _ in scan_line('api_key = "Zx9Qw3Er7Ty1Ui5Op2As8Df4Gh6Jk0Lz"', "x.py")
    ] == ["entropy-keyword"]
    assert not list(
        scan_line('api_key = "Zx9Qw3Er7Ty1Ui5Op2As8Df4Gh6Jk0Lz"', "pnpm-lock.yaml")
    )


if __name__ == "__main__":
    demo()
    out = sys.argv[1]
    history, n_commits, n_added = stream_history()
    blobs, n_blobs = sweep_blobs()
    json.dump(
        dict(
            commits_scanned=n_commits,
            added_lines_scanned=n_added,
            blobs_scanned=n_blobs,
            history_hits=history,
            blob_hits=blobs,
            filename_hits=secret_filenames(),
            bare_entropy_by_path=BARE,
        ),
        open(out, "w"),
        indent=1,
    )
    print(
        "commits=%d added_lines=%d blobs=%d history_hits=%d blob_hits=%d"
        % (n_commits, n_added, n_blobs, len(history), len(blobs))
    )

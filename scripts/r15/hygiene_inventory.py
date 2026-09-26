#!/usr/bin/env python3
"""Regenerate the r15 hygiene-prune classification straight from git.

Read-only: every git call here is a listing, an ancestor check, or a
``--dry-run``. It never deletes, prunes, or checks anything out — it only
prints the commands the lead would run. Use this instead of trusting a
stale HYGIENE_PRUNE.md snapshot: re-run it at prune time.

ponytail: merge-base --is-ancestor is one git subprocess call per ref, so
classification is O(worktrees + local branches + remote branches); fine at
the few-hundred-ref scale this repo runs at (~700 calls, well under a
minute). Revisit with a batched rev-list/for-each-ref approach if the ref
count ever climbs into the low thousands.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass

NEVER_TOUCH = [
    "The other Tauri+Python product's containers/listeners.",
    "The operator's app data / OS keychain entries.",
    "Anything outside this repository and the session scratchpad.",
    "Git history (no rebase, no filter, no amend of existing commits).",
    "Any `v*` tag.",
    "Remote (`origin/*`) branches — remote deletion is never proposed by this script.",
    "The main checkout, and any worktree or branch this run classified LIVE.",
]


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return r.stdout.strip()


def is_ancestor(sha: str, base: str) -> bool:
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, base], capture_output=True
    )
    return r.returncode == 0


def ref_exists(ref: str) -> bool:
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref], capture_output=True
    )
    return r.returncode == 0


@dataclass
class WorktreeEntry:
    path: str
    branch: str | None
    sha: str
    detached: bool
    exists_on_disk: bool
    merged: bool
    live: bool

    @property
    def status(self) -> str:
        if self.live:
            return "LIVE"
        if not self.exists_on_disk:
            return "PRUNABLE-REGISTRATION"
        return "MERGED" if self.merged else "UNMERGED"


@dataclass
class LocalBranchEntry:
    name: str
    sha: str
    merged: bool
    origin_sha: str | None
    checked_out: bool

    @property
    def status(self) -> str:
        if self.checked_out:
            return "CHECKED-OUT (worktree) — never proposed"
        if self.merged and self.origin_sha == self.sha:
            return "SAFE-LOCAL-DELETE"
        if self.merged:
            return "MERGED (no matching origin ref — not proposed)"
        if self.origin_sha is None:
            return "UNMERGED-UNPUSHED (only copy — KEEP)"
        return "UNMERGED (has origin copy — KEEP)"


@dataclass
class RemoteBranchEntry:
    name: str
    sha: str
    merged: bool


def parse_worktrees() -> list[dict]:
    out = git("worktree", "list", "--porcelain")
    entries: list[dict] = []
    cur: dict = {}
    for line in out.splitlines():
        if line == "":
            if cur:
                entries.append(cur)
                cur = {}
            continue
        if line.startswith("worktree "):
            cur["path"] = line[len("worktree ") :]
        elif line.startswith("HEAD "):
            cur["sha"] = line[len("HEAD ") :]
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch ") :].removeprefix("refs/heads/")
        elif line == "detached":
            cur["branch"] = None
            cur["detached"] = True
        elif line == "bare":
            cur["bare"] = True
    if cur:
        entries.append(cur)
    return entries


def build_live_matcher(
    main_checkout: str,
    live_runs: list[str],
    live_paths: list[str],
    live_globs: list[str],
):
    norm_paths = [p.rstrip("/") for p in live_paths]

    def is_live(path: str) -> bool:
        if path == main_checkout:
            return True
        for p in norm_paths:
            if path == p or path.startswith(p + "/"):
                return True
        for run_id in live_runs:
            if fnmatch.fnmatch(path, f"*.claude/worktrees/wf_{run_id}*"):
                return True
        for g in live_globs:
            if fnmatch.fnmatch(path, g):
                return True
        return False

    return is_live


def classify(args: argparse.Namespace) -> dict:
    import os

    base = args.base
    raw_worktrees = parse_worktrees()
    main_checkout = raw_worktrees[0]["path"] if raw_worktrees else ""
    is_live = build_live_matcher(
        main_checkout, args.live_run, args.live_path, args.live
    )

    worktrees: list[WorktreeEntry] = []
    checked_out_branches: set[str] = set()
    for w in raw_worktrees:
        if w.get("bare"):
            continue
        sha = w.get("sha", "")
        branch = w.get("branch")
        if branch:
            checked_out_branches.add(branch)
        worktrees.append(
            WorktreeEntry(
                path=w["path"],
                branch=branch,
                sha=sha,
                detached=bool(w.get("detached")),
                exists_on_disk=os.path.isdir(w["path"]),
                merged=is_ancestor(sha, base) if sha else False,
                live=is_live(w["path"]),
            )
        )

    protected_branches = {"main"}
    if raw_worktrees:
        main_branch = raw_worktrees[0].get("branch")
        if main_branch:
            protected_branches.add(main_branch)

    origin_shas = {}
    for line in git(
        "for-each-ref", "refs/remotes/origin", "--format=%(refname:short) %(objectname)"
    ).splitlines():
        name, _, sha = line.partition(" ")
        origin_shas[name.removeprefix("origin/")] = sha

    local_branches: list[LocalBranchEntry] = []
    for line in git(
        "for-each-ref", "refs/heads", "--format=%(refname:short) %(objectname)"
    ).splitlines():
        name, _, sha = line.partition(" ")
        checked_out = name in checked_out_branches or name in protected_branches
        local_branches.append(
            LocalBranchEntry(
                name=name,
                sha=sha,
                merged=is_ancestor(sha, base),
                origin_sha=origin_shas.get(name),
                checked_out=checked_out,
            )
        )

    remote_branches: list[RemoteBranchEntry] = []
    for line in git(
        "for-each-ref",
        "refs/remotes/origin/worktree-agent-*",
        "--format=%(refname:short) %(objectname)",
    ).splitlines():
        name, _, sha = line.partition(" ")
        remote_branches.append(
            RemoteBranchEntry(name=name, sha=sha, merged=is_ancestor(sha, base))
        )

    tag_info = None
    if args.tag:
        tag_ref = f"refs/tags/{args.tag}"
        if ref_exists(tag_ref):
            tag_sha = git("rev-parse", tag_ref)
            tag_info = {
                "tag": args.tag,
                "sha": tag_sha,
                "worktrees_in_tag": [
                    w.path for w in worktrees if w.sha and is_ancestor(w.sha, tag_ref)
                ],
                "local_branches_in_tag": [
                    b.name for b in local_branches if is_ancestor(b.sha, tag_ref)
                ],
            }
        else:
            tag_info = {"tag": args.tag, "sha": None, "note": "tag does not exist yet"}

    stale_refs = git("remote", "prune", "origin", "--dry-run")

    return {
        "base": base,
        "base_sha": git("rev-parse", base),
        "worktrees": worktrees,
        "local_branches": local_branches,
        "remote_branches": remote_branches,
        "stale_refs_dry_run": stale_refs,
        "tag": tag_info,
    }


def build_deletion_commands(
    worktrees: list[WorktreeEntry],
    local_branches: list[LocalBranchEntry],
) -> list[str]:
    cmds: list[str] = []
    for w in worktrees:
        if w.status == "MERGED" and not w.live:
            cmds.append(f"git worktree remove {w.path}")
    cmds.append("git worktree prune")
    for b in local_branches:
        if b.status == "SAFE-LOCAL-DELETE":
            cmds.append(f"git branch -d {b.name}")
    return cmds


def render_markdown(data: dict, args: argparse.Namespace) -> str:
    lines: list[str] = []
    wt = data["worktrees"]
    lb = data["local_branches"]
    rb = data["remote_branches"]

    lines.append("## 1. Registered worktrees\n")
    lines.append(
        f"Source: `git worktree list --porcelain`, base `{data['base']}` @ `{data['base_sha']}`.\n"
    )
    lines.append("| Path | Branch | Tip | Path exists? | Status |")
    lines.append("|---|---|---|---|---|")
    for w in wt:
        branch = w.branch or "*(detached)*"
        lines.append(
            f"| `{w.path}` | `{branch}` | `{w.sha[:8]}` | {'yes' if w.exists_on_disk else 'no'} | **{w.status}** |"
        )
    lines.append("")

    lines.append("## 2. Local branches\n")
    lines.append(
        f"Source: `git for-each-ref refs/heads` ({len(lb)} refs), cross-checked against `origin/<name>`.\n"
    )
    by_status: dict[str, list[LocalBranchEntry]] = {}
    for b in lb:
        by_status.setdefault(b.status, []).append(b)
    for status, entries in sorted(by_status.items(), key=lambda kv: kv[0]):
        lines.append(f"### {status} ({len(entries)})\n")
        for b in sorted(entries, key=lambda e: e.name):
            lines.append(f"- `{b.name}` `{b.sha[:8]}`")
        lines.append("")

    lines.append("## 3. Remote agent branches (`origin/worktree-agent-*`)\n")
    lines.append(
        f"Source: `git for-each-ref refs/remotes/origin/worktree-agent-*` ({len(rb)} refs). "
        "Remote deletion is never proposed by this script — local copies only.\n"
    )
    merged_rb = [b for b in rb if b.merged]
    unmerged_rb = [b for b in rb if not b.merged]
    lines.append(f"- Merged into base: {len(merged_rb)}")
    lines.append(f"- Unmerged: {len(unmerged_rb)}\n")
    if unmerged_rb:
        lines.append("Unmerged remote agent branches (kept, informational only):\n")
        for b in sorted(unmerged_rb, key=lambda e: e.name):
            lines.append(f"- `{b.name}` `{b.sha[:8]}`")
        lines.append("")

    lines.append("## 4. Stale tracking refs\n")
    lines.append(
        "Source: `git remote prune origin --dry-run` (read-only; no refs were pruned by this run):\n"
    )
    lines.append("```")
    lines.append(data["stale_refs_dry_run"] or "(no output — nothing stale)")
    lines.append("```\n")

    lines.append("## 5. Never touch (restated)\n")
    for item in NEVER_TOUCH:
        lines.append(f"- {item}")
    lines.append("")

    if data.get("tag"):
        t = data["tag"]
        lines.append(f"## Tag ancestry: `{t['tag']}`\n")
        if t.get("sha") is None:
            lines.append(
                f"`{t['tag']}` {t['note']} — skipping tag-ancestry cross-check.\n"
            )
        else:
            lines.append(f"`{t['tag']}` = `{t['sha']}`.\n")
            lines.append(
                f"- Worktrees whose tip is an ancestor of the tag: {len(t['worktrees_in_tag'])}"
            )
            lines.append(
                f"- Local branches that are an ancestor of the tag: {len(t['local_branches_in_tag'])}\n"
            )

    lines.append("## Summary counts\n")
    live_wt = [w for w in wt if w.status == "LIVE"]
    merged_wt = [w for w in wt if w.status == "MERGED"]
    unmerged_wt = [w for w in wt if w.status == "UNMERGED"]
    prunable_wt = [w for w in wt if w.status == "PRUNABLE-REGISTRATION"]
    safe_delete_lb = by_status.get("SAFE-LOCAL-DELETE", [])
    unmerged_unpushed_lb = by_status.get("UNMERGED-UNPUSHED (only copy — KEEP)", [])
    lines.append("| Category | Count |")
    lines.append("|---|---|")
    lines.append(f"| Worktrees: LIVE | {len(live_wt)} |")
    lines.append(f"| Worktrees: MERGED (prune candidate) | {len(merged_wt)} |")
    lines.append(f"| Worktrees: UNMERGED | {len(unmerged_wt)} |")
    lines.append(f"| Worktrees: PRUNABLE-REGISTRATION | {len(prunable_wt)} |")
    lines.append(f"| Local branches: total | {len(lb)} |")
    lines.append(f"| Local branches: SAFE-LOCAL-DELETE | {len(safe_delete_lb)} |")
    lines.append(
        f"| Local branches: UNMERGED-UNPUSHED (keep) | {len(unmerged_unpushed_lb)} |"
    )
    lines.append(f"| Remote agent branches: total | {len(rb)} |")
    lines.append(f"| Remote agent branches: merged | {len(merged_rb)} |")
    lines.append(f"| Remote agent branches: unmerged | {len(unmerged_rb)} |")
    lines.append("")

    lines.append("## Exact deletion commands (lead runs these)\n")
    cmds = build_deletion_commands(wt, lb)
    lines.append("```")
    lines.extend(cmds)
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="origin/004-r4-experience-rebuild")
    p.add_argument("--tag", default=None)
    p.add_argument(
        "--live-run",
        action="append",
        default=[],
        help="workflow run id; marks .claude/worktrees/wf_<id>* as LIVE",
    )
    p.add_argument(
        "--live-path",
        action="append",
        default=[],
        help="any worktree path under this prefix is LIVE",
    )
    p.add_argument(
        "--live", action="append", default=[], help="extra fnmatch glob for LIVE paths"
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--selftest", action="store_true")
    return p.parse_args(argv)


def selftest() -> None:
    live_wt = WorktreeEntry(
        path="/live/path",
        branch="live-branch",
        sha="a" * 40,
        detached=False,
        exists_on_disk=True,
        merged=True,
        live=True,
    )
    dead_wt = WorktreeEntry(
        path="/dead/path",
        branch="dead-branch",
        sha="b" * 40,
        detached=False,
        exists_on_disk=True,
        merged=True,
        live=False,
    )
    live_branch = LocalBranchEntry(
        name="live-branch",
        sha="a" * 40,
        merged=True,
        origin_sha="a" * 40,
        checked_out=True,
    )
    dead_branch = LocalBranchEntry(
        name="dead-branch",
        sha="c" * 40,
        merged=True,
        origin_sha="c" * 40,
        checked_out=False,
    )

    cmds = build_deletion_commands([live_wt, dead_wt], [live_branch, dead_branch])

    assert not any(live_wt.path in c for c in cmds), (
        "selftest failed: emitted a delete for a LIVE worktree"
    )
    assert any(dead_wt.path in c for c in cmds), (
        "selftest failed: did not propose the dead worktree"
    )
    assert not any(f" {live_branch.name}" in c for c in cmds), (
        "selftest failed: emitted a delete for a checked-out (live) branch"
    )
    assert any(f" {dead_branch.name}" in c for c in cmds), (
        "selftest failed: did not propose the dead branch"
    )
    print("selftest OK", file=sys.stderr)


def main() -> None:
    args = parse_args(sys.argv[1:])
    if args.selftest:
        selftest()
        return
    data = classify(args)
    if args.json:

        def encode(o):
            if hasattr(o, "__dict__"):
                d = dict(o.__dict__)
                d["status"] = o.status
                return d
            raise TypeError

        print(json.dumps(data, default=encode, indent=2))
    else:
        print(render_markdown(data, args))


if __name__ == "__main__":
    main()

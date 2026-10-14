#!/usr/bin/env python3
"""Build the R15 register from the census, with countable drops.

Inputs (docs/redesign/verification/r15/census/):
  raw/*.json     raw findings per sweep           [{raw_id, title, severity, area, ...}]
  refute/*.json  refuter verdicts                 [{raw_id, verdict, severity_final, reason}]
  merge/*.json   per-area merge decisions         {"entries": [{id, title, severity, area,
                 subsystem, repro, evidence, raw_ids: [...]}], "rejections": [{raw_id, reason}]}

Outputs: vysted-r15-register.json + vysted-r15-register.md next to the run report.
Exit 1 if any raw id is unaccounted for (neither in an entry nor rejected) — the merge is the
run's highest fan-in, so a dropped finding must be a countable error, never a matter of trust.

  register.py status   # raw / refuted / merged counts, no writes
  register.py bundle   # write merge-in/<cluster>.json (surviving raw findings + verdicts) for the mergers
  register.py build    # write the register; fails on unaccounted raw ids
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "docs/redesign/verification"
CENSUS = ROOT / "r15/census"
SEVERITIES = ["critical", "high", "medium", "low"]
OPERATOR_AREAS = {
    "ui": "UI / panels / layout",
    "agent": "Agent / chat",
    "research": "Research / web search",
    "data": "Data on small or obscure stocks",
}
# Verdict vocabulary the refuters actually used (PROMPT_refute.md): confirmed|refuted stays
# out of the register at bundle time; removed_with_feature is the 23 Sep trading-removal close.
AUTO_REJECT_VERDICTS = {"refuted", "removed_with_feature"}
REMOVED_WITH_FEATURE_REASON = (
    "removed with the feature (trading removal, operator decision 23 Sep 2026; "
    "evidence: the Stage C removal commit)"
)
BROKERS_ADAPTERS_FILE = "code-brokers-adapters.json"


def _rows(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        print(f"  ! unreadable {path.name}: {exc}", file=sys.stderr)
        return []
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [])
    return [r for r in data if isinstance(r, dict)]


def _new_findings(path: Path) -> list[dict]:
    # A refuter records a defect it stumbled onto that isn't the finding it was refuting as a
    # top-level "new_findings" array alongside its verdict list (a bare array has none).
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return [n for n in data.get("new_findings", []) if isinstance(n, dict)] if isinstance(data, dict) else []


def load() -> tuple[dict[str, dict], dict[str, dict], list[dict], dict[str, str]]:
    raw: dict[str, dict] = {}
    for f in sorted((CENSUS / "raw").glob("*.json")):
        for r in _rows(f):
            rid = str(r.get("raw_id") or "").strip()
            if not rid:
                continue
            if rid in raw:
                rid = f"{rid}@{f.stem}"  # two sweeps reused an id: keep both, disambiguated
            raw[rid] = {**r, "raw_id": rid, "_file": f.name}
    for f in sorted((CENSUS / "refute").glob("*.json")):
        for i, nf in enumerate(_new_findings(f), 1):
            rid = f"{f.stem}-N{i}"
            raw[rid] = {**nf, "raw_id": rid, "_file": f.name}
    verdicts = {
        str(v.get("raw_id")): v
        for f in sorted((CENSUS / "refute").glob("*.json"))
        for v in _rows(f)
    }
    # code-brokers-adapters.json is never refuted per-finding (PROMPT_refute.md) — it bulk-closes
    # as removed_with_feature for every raw id that has no explicit verdict of its own.
    for rid, r in raw.items():
        if r["_file"] == BROKERS_ADAPTERS_FILE and rid not in verdicts:
            verdicts[rid] = {
                "raw_id": rid,
                "verdict": "removed_with_feature",
                "severity_final": r.get("severity", "low"),
                "reason": REMOVED_WITH_FEATURE_REASON,
            }
    entries: list[dict] = []
    rejections: dict[str, str] = {}
    for f in sorted((CENSUS / "merge").glob("*.json")):
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError) as exc:
            print(f"  ! unreadable merge file {f.name}: {exc}", file=sys.stderr)
            continue
        entries += [e for e in doc.get("entries", []) if isinstance(e, dict)]
        rejections.update(
            {
                str(r["raw_id"]): str(r.get("reason", ""))
                for r in doc.get("rejections", [])
                if "raw_id" in r
            }
        )
    return raw, verdicts, entries, rejections


CODE_GROUPS = {
    "research": ("research-",),
    "agent": ("agent-", "llm-", "runs-", "mcp-"),
    "data": ("resolver", "fundamentals", "disclosures", "market-data", "screener"),
    "frontend": ("frontend-", "host-actions", "workspace-"),
}


def _cluster(r: dict) -> str:
    area = str(r.get("area") or "code").lower()
    if area != "code":
        return area
    stem = r["_file"].removeprefix("code-").removesuffix(".json")
    for group, prefixes in CODE_GROUPS.items():
        if stem.startswith(prefixes):
            return f"code-{group}"
    return "code-platform"


def bundle(raw: dict[str, dict], verdicts: dict[str, dict]) -> int:
    out_dir = CENSUS / "merge-in"
    out_dir.mkdir(exist_ok=True)
    clusters: dict[str, list[dict]] = {}
    for rid, r in raw.items():
        v = verdicts.get(rid) or verdicts.get(rid.split("@")[0])
        if v and v.get("verdict") in AUTO_REJECT_VERDICTS:
            continue
        row = {k: val for k, val in r.items() if k != "_file"}
        row["source_file"] = r["_file"]
        if v:
            row["refuter"] = {
                k: v.get(k) for k in ("verdict", "severity_final", "reason")
            }
        clusters.setdefault(_cluster(r), []).append(row)
    for name, rows in sorted(clusters.items()):
        (out_dir / f"{name}.json").write_text(
            json.dumps(rows, indent=1, ensure_ascii=False) + "\n"
        )
        print(f"  merge-in/{name}.json: {len(rows)}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    raw, verdicts, entries, rejections = load()
    if cmd == "bundle":
        return bundle(raw, verdicts)
    cited = {rid for e in entries for rid in e.get("raw_ids", [])}
    # A refuted or removed_with_feature finding is a rejection by construction; refuted carries
    # the refuter's own reason, removed_with_feature always carries the canonical scope-change one
    # (so every trading-removal rejection cites the same commit, regardless of what a refuter wrote).
    for rid, v in verdicts.items():
        verdict = v.get("verdict")
        if verdict not in AUTO_REJECT_VERDICTS or rid not in raw or rid in cited:
            continue
        reason = (
            REMOVED_WITH_FEATURE_REASON
            if verdict == "removed_with_feature"
            else f"refuted: {v.get('reason', '')}"[:300]
        )
        rejections.setdefault(rid, reason)
    unaccounted = sorted(set(raw) - cited - set(rejections))
    phantom = sorted(cited - set(raw))
    by_sev = {s: sum(1 for e in entries if e.get("severity") == s) for s in SEVERITIES}
    print(
        f"raw findings: {len(raw)} in {len(list((CENSUS / 'raw').glob('*.json')))} files"
    )
    print(
        f"refuter verdicts: {len(verdicts)} (no verdict yet: {len(set(raw) - set(verdicts))})"
    )
    no_verdict_files = sorted(
        {
            r["_file"]
            for r in raw.values()
            if r["_file"] != BROKERS_ADAPTERS_FILE
        }
        - {r["_file"] for rid, r in raw.items() if rid in verdicts}
    )
    if no_verdict_files:
        print(f"ERROR: {len(no_verdict_files)} raw file(s) have NO refute coverage at all:")
        for fname in no_verdict_files:
            print("   ", fname)
    print(f"register entries: {len(entries)} {by_sev} · rejections: {len(rejections)}")
    print(
        f"unaccounted raw ids: {len(unaccounted)} · entries citing unknown raw ids: {len(phantom)}"
    )
    if cmd != "build":
        for rid in unaccounted[:40]:
            print("   unaccounted:", rid)
        return 0
    if unaccounted or phantom:
        print(
            "REFUSING to build: every raw id must resolve to an entry or a one-line rejection.",
            file=sys.stderr,
        )
        for rid in unaccounted[:80]:
            print("   unaccounted:", rid, file=sys.stderr)
        for rid in phantom[:40]:
            print("   phantom:", rid, file=sys.stderr)
        return 1
    entries.sort(
        key=lambda e: (
            SEVERITIES.index(e.get("severity", "low"))
            if e.get("severity") in SEVERITIES
            else 9,
            str(e.get("id")),
        )
    )
    for e in entries:
        e.setdefault("status", "open")
    out = {
        "entries": entries,
        "rejections": [
            {"raw_id": k, "reason": v} for k, v in sorted(rejections.items())
        ],
        "counts": {
            "raw": len(raw),
            "entries": len(entries),
            "rejections": len(rejections),
            **by_sev,
        },
    }
    (ROOT / "vysted-r15-register.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    )
    md = [
        "# R15 register (readable view)",
        "",
        f"{len(raw)} raw findings → {len(entries)} entries + {len(rejections)} rejections. "
        + " · ".join(f"{s}: {by_sev[s]}" for s in SEVERITIES),
        "",
    ]
    md += ["## The operator's four areas", ""]
    for area, label in OPERATOR_AREAS.items():
        rows = [e for e in entries if e.get("area") == area]
        md += (
            [f"### {label} ({len(rows)})", ""]
            + [
                f"- **{e.get('id')}** [{e.get('severity')}] {e.get('title')} — _{e.get('status')}_"
                for e in rows
            ]
            + [""]
        )
    md += [
        "## All entries by severity",
        "",
        "| id | sev | area | subsystem | title | status | raw ids |",
        "|---|---|---|---|---|---|---|",
    ]
    md += [
        f"| {e.get('id')} | {e.get('severity')} | {e.get('area')} | {e.get('subsystem', '')} | {str(e.get('title', '')).replace('|', '/')} | {e.get('status')} | {', '.join(e.get('raw_ids', []))} |"
        for e in entries
    ]
    (ROOT / "vysted-r15-register.md").write_text("\n".join(md) + "\n")
    print("register written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

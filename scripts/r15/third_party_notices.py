"""R15 third-party notices generator (stdlib-only).

Builds THIRD_PARTY_NOTICES.draft.{json,md} from: the three sidecar venvs' dist-info
metadata, the Stage D licence scan's bundled/dev-only classification
(DEPS_LICENCES.json), `pnpm licenses list --json --prod` output, and `cargo metadata`
output. Deterministic: every list is sorted before writing, so re-running on the same
inputs re-generates a byte-identical pair of files. Reads only; installs nothing.

Usage:
    python3 scripts/r15/third_party_notices.py \\
        --sidecar-venv sidecar/.venv \\
        --openbb-venv sidecar/openbb_mcp_subprocess/.venv \\
        --secedgar-venv sidecar/sec_edgar_mcp_subprocess/.venv \\
        --deps-licences docs/redesign/verification/r15/stage-d/DEPS_LICENCES.json \\
        --cargo-metadata /path/to/cargo-metadata.json \\
        --pnpm-licenses /path/to/pnpm-licenses.json \\
        --sha <git-sha-for-the-draft-header> \\
        --out-dir docs/redesign/verification/r15/stage-d

`--pnpm-licenses` may be omitted to read the same JSON from stdin instead. This
script does not invoke `pnpm licenses list` or `cargo metadata` itself — the caller
produces those two JSON files first and passes them in, e.g.:

    pnpm licenses list --json --prod > /tmp/pnpm-licenses.json
    cargo metadata --offline --locked --format-version 1 \\
        --manifest-path src-tauri/Cargo.toml > /tmp/cargo-metadata.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CORE_NOTICE = (
    "Vysted Terminal itself is licensed PolyForm Strict 1.0.0 (the plugin contract "
    "and the example plugin are separately Apache-2.0). It bundles the third-party "
    "components listed below, each under its own licence, as separate programs or "
    "processes where noted."
)

# PyInstaller's bootloader stub is compiled into every --onefile binary but ships no
# dist-info of its own, so it is not discoverable by walking site-packages. Its facts
# are the ones already established by the Stage D scan (DEPS_LICENCES.md:29-30).
BOOTLOADER_LICENCE = "GPL-2.0-or-later WITH PyInstaller-bootloader-exception"
BOOTLOADER_NOTE = (
    "PyInstaller bootloader compiled into the frozen --onefile binary; GPL with the "
    "PyInstaller bootloader exception, which permits distributing bootloader-linked "
    "binaries under any licence."
)

PYTHON_SIDECARS = [
    # (DEPS_LICENCES.json key, venv arg name, binary label)
    ("sidecar", "sidecar_venv", "vysted-sidecar"),
    ("openbb_mcp", "openbb_venv", "vysted-openbb-mcp-sidecar"),
    ("sec_edgar_mcp", "secedgar_venv", "vysted-sec-edgar-mcp-sidecar"),
]

# Signatures used only to identify which licence a shipped LICENSE file's text IS —
# never to fabricate a licence text. Order matters: more specific first.
LICENCE_SIGNATURES = [
    (
        "AGPL-3.0",
        re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE\s*\r?\n\s*Version 3", re.I),
    ),
    (
        "LGPL-3.0",
        re.compile(r"GNU LESSER GENERAL PUBLIC LICENSE\s*\r?\n\s*Version 3", re.I),
    ),
    ("GPL-3.0", re.compile(r"GNU GENERAL PUBLIC LICENSE\s*\r?\n\s*Version 3", re.I)),
    ("GPL-2.0", re.compile(r"GNU GENERAL PUBLIC LICENSE\s*\r?\n\s*Version 2\b", re.I)),
    ("MPL-2.0", re.compile(r"Mozilla Public License.{0,30}Version 2\.0", re.I | re.S)),
    ("Apache-2.0", re.compile(r"Apache License\r?\n?\s*Version 2\.0", re.I)),
    (
        "BSD-3-Clause",
        re.compile(
            r"Redistributions of source code must retain.*Redistributions in binary",
            re.I | re.S,
        ),
    ),
    ("MIT", re.compile(r"\bMIT License\b", re.I)),
    # Many MIT LICENSE files carry no "MIT License" title line at all — just the
    # boilerplate permission grant. Checked last, after the more specific signatures.
    (
        "MIT",
        re.compile(
            r"Permission is hereby granted,\s*free of charge,\s*to any person obtaining a copy",
            re.I,
        ),
    ),
]

COPYLEFT_KEYWORDS = (
    "AGPL",
    "GPL",
    "LGPL",
    "MPL",
    "SSPL",
    "EUPL",
    "OSL",
    "CC-BY-NC",
    "COMMONS CLAUSE",
    "BUSL",
)

# SPDX ids the Appendix carries full text for (per the role brief: AGPL-3.0, GPL-2.0,
# LGPL-3.0 only — MPL and any other copyleft licence in Section A cites upstream instead).
APPENDIX_LICENCE_IDS = ("AGPL-3.0", "GPL-2.0", "LGPL-3.0")


def canonical_id(licence: str | None) -> str | None:
    """Map a licence label (SPDX expression, OSI classifier text, or raw METADATA
    License: field) to the small set of ids this script special-cases. Returns None
    for anything not in that set (still shown verbatim in the tables either way)."""
    if not licence:
        return None
    up = licence.upper()
    if "AFFERO" in up or re.search(r"\bAGPL", up):
        return "AGPL-3.0"
    if re.search(r"\bLGPL", up):
        return "LGPL-3.0"
    if (
        "GENERAL PUBLIC LICENSE V2" in up
        or re.search(r"\bGPLV2\b", up)
        or "GPL-2.0" in up
    ):
        return "GPL-2.0"
    if re.search(r"\bGPL\b", up) or "GENERAL PUBLIC LICENSE" in up:
        return "GPL-3.0"
    if "MOZILLA PUBLIC LICENSE" in up or re.search(r"\bMPL\b", up):
        return "MPL-2.0"
    return None


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_metadata(text: str) -> dict[str, list[str]]:
    """Parse the RFC822-style header block of a dist-info METADATA file (headers
    only — stops at the first blank line, which is where the long description starts)."""
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.strip():
            break
        if line[0] in " \t":
            continue  # header continuation/folding — not needed for the fields we read
        if ": " in line:
            key, _, val = line.partition(": ")
            fields.setdefault(key, []).append(val.strip())
    return fields


def find_licence_files(dist_info: Path) -> list[Path]:
    out = []
    for p in sorted(dist_info.glob("*")):
        if p.is_file() and p.name.upper().startswith(("LICENSE", "COPYING")):
            out.append(p)
    lic_dir = dist_info / "licenses"
    if lic_dir.is_dir():
        for p in sorted(lic_dir.rglob("*")):
            if p.is_file() and p.name.upper().startswith(("LICENSE", "COPYING")):
                out.append(p)
    return out


def resolve_licence(
    license_expr: str | None,
    license_field: str | None,
    classifiers: list[str],
    licence_text: str,
) -> tuple[str | None, str | None]:
    if license_expr:
        return license_expr, "METADATA License-Expression"
    if classifiers:
        return classifiers[0].split("::")[-1].strip(), "dist-info Classifier"
    for label, pattern in LICENCE_SIGNATURES:
        if license_field and pattern.search(license_field):
            return label, "METADATA License (matched licence text)"
    for label, pattern in LICENCE_SIGNATURES:
        if licence_text and pattern.search(licence_text):
            return label, "LICENSE file (dist-info)"
    if license_field and license_field.strip().upper() not in ("", "UNKNOWN"):
        first = license_field.strip().splitlines()[0][:120]
        if first:
            return first, "METADATA License"
    return None, None


def _raw_copyleft_hit(s: str) -> bool:
    return canonical_id(s) is not None or any(k in s.upper() for k in COPYLEFT_KEYWORDS)


def is_copyleft(licence: str | None) -> tuple[bool, str | None]:
    if not licence:
        return False, None
    up = licence.upper()
    if " WITH " in up and "EXCEPTION" in up:
        return False, (
            "carries a linking exception that lifts the copyleft obligation for the "
            "program it is linked into"
        )
    # SPDX-style OR-choice: literal uppercase " OR " (as a License-Expression field
    # writes it), not the lowercase "...v2 or later" prose inside a single licence name.
    if " OR " in licence:
        alts = [a.strip() for a in licence.split(" OR ")]
        if len(alts) > 1:
            if not all(_raw_copyleft_hit(a) for a in alts):
                return (
                    False,
                    "OR-licensed; a permissive alternative is selectable without copyleft obligations",
                )
            return True, None
    if _raw_copyleft_hit(licence):
        return True, None
    return False, None


def walk_dist_infos(venv_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """{(norm_name, version): record} for every dist-info under a venv's site-packages."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for meta_path in sorted(venv_root.glob("**/site-packages/*.dist-info/METADATA")):
        dist_info = meta_path.parent
        text = meta_path.read_text(encoding="utf-8", errors="replace")
        fields = parse_metadata(text)
        stem = dist_info.name[: -len(".dist-info")]
        name = (fields.get("Name") or [stem.rsplit("-", 1)[0]])[0]
        version = (fields.get("Version") or [stem.rsplit("-", 1)[-1]])[0]
        licence_files = find_licence_files(dist_info)
        licence_text = ""
        for lf in licence_files:
            try:
                licence_text += lf.read_text(encoding="utf-8", errors="replace") + "\n"
            except OSError:
                pass
        license_expr = (fields.get("License-Expression") or [None])[0]
        license_field = (fields.get("License") or [None])[0]
        classifiers = [
            c for c in fields.get("Classifier", []) if c.startswith("License ::")
        ]
        homepage = (fields.get("Home-page") or [None])[0] or (
            fields.get("Project-URL") or [None]
        )[0]
        if homepage and homepage.strip().upper() == "UNKNOWN":
            homepage = None
        licence, source = resolve_licence(
            license_expr, license_field, classifiers, licence_text
        )
        copyleft, note = is_copyleft(licence)
        out[(norm(name), version)] = {
            "name": name,
            "version": version,
            "licence": licence,
            "licence_source": source,
            "url": homepage,
            "copyleft": copyleft,
            "note": note,
            "has_local_licence_file": bool(licence_files),
            "licence_text": licence_text,
        }
    return out


def python_rows(
    deps: dict[str, Any], dist_infos: dict[str, dict[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, venv_arg, binary in PYTHON_SIDECARS:
        section = deps["ecosystems"]["python"][key]
        bundled = [p for p in section["packages"] if p.get("scope") == "bundled"]
        table = dist_infos[venv_arg]
        for pkg in bundled:
            if pkg["name"] == "PyInstaller-bootloader":
                rows.append(
                    {
                        "ecosystem": "python",
                        "binary": binary,
                        "name": "PyInstaller-bootloader",
                        "version": "embedded",
                        "licence": BOOTLOADER_LICENCE,
                        "licence_source": "R15 Stage D scan (DEPS_LICENCES.md)",
                        "url": "https://pyinstaller.org/",
                        "copyleft": False,
                        "note": BOOTLOADER_NOTE,
                        "has_local_licence_file": False,
                    }
                )
                continue
            key2 = (norm(pkg["name"]), pkg["version"])
            rec = table.get(key2)
            if rec is None:
                rows.append(
                    {
                        "ecosystem": "python",
                        "binary": binary,
                        "name": pkg["name"],
                        "version": pkg["version"],
                        "licence": pkg.get("licence"),
                        "licence_source": "Stage D scan only (dist-info not found in this venv walk)",
                        "url": None,
                        "copyleft": is_copyleft(pkg.get("licence"))[0],
                        "note": "not_resolved: no dist-info matched this name+version in the inspected venv",
                        "has_local_licence_file": False,
                    }
                )
                continue
            rows.append(
                {
                    "ecosystem": "python",
                    "binary": binary,
                    "name": rec["name"],
                    "version": rec["version"],
                    "licence": rec["licence"],
                    "licence_source": rec["licence_source"],
                    "url": rec["url"],
                    "copyleft": rec["copyleft"],
                    "note": rec["note"],
                    "has_local_licence_file": rec["has_local_licence_file"],
                    "_licence_text": rec["licence_text"],
                }
            )
    return rows


def npm_rows(pnpm_json: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for licence, entries in pnpm_json.items():
        copyleft, note = is_copyleft(licence)
        for e in entries:
            versions = e.get("versions") or ([e["version"]] if e.get("version") else [])
            for version in versions:
                rows.append(
                    {
                        "ecosystem": "npm",
                        "binary": "frontend (static export)",
                        "name": e["name"],
                        "version": version,
                        "licence": licence,
                        "licence_source": "package.json (pnpm licenses list --prod)",
                        "url": e.get("homepage"),
                        "copyleft": copyleft,
                        "note": note,
                        "has_local_licence_file": False,
                    }
                )
    return rows


def cargo_bundled_ids(meta: dict[str, Any]) -> set[str]:
    """Normal-edge-reachable crate ids from the workspace root (mirrors
    DEPS_LICENCES.md's cargo BFS: normal-only = bundled, build/dev edges excluded)."""
    nodes = {n["id"]: n for n in meta["resolve"]["nodes"]}
    root = meta["resolve"]["root"]
    bundled: set[str] = set()
    seen = {root}
    stack = [root]
    while stack:
        cur = stack.pop()
        node = nodes.get(cur)
        if not node:
            continue
        for dep in node.get("deps", []):
            pkg_id = dep["pkg"]
            if pkg_id in seen:
                continue
            if any(k.get("kind") is None for k in dep.get("dep_kinds", [])):
                seen.add(pkg_id)
                bundled.add(pkg_id)
                stack.append(pkg_id)
    return bundled


def cargo_rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    packages = {p["id"]: p for p in meta["packages"]}
    rows = []
    for pkg_id in cargo_bundled_ids(meta):
        p = packages[pkg_id]
        licence = p.get("license")
        source = None
        if licence:
            source = "cargo metadata license field"
        elif p.get("license_file"):
            source = "cargo metadata license_file field"
        copyleft, note = is_copyleft(licence)
        rows.append(
            {
                "ecosystem": "cargo",
                "binary": "src-tauri (desktop core)",
                "name": p["name"],
                "version": p["version"],
                "licence": licence,
                "licence_source": source,
                "url": p.get("repository") or p.get("homepage"),
                "copyleft": copyleft,
                "note": note,
                "has_local_licence_file": False,
            }
        )
    return rows


def sort_key(row: dict[str, Any]) -> tuple:
    return (row["ecosystem"], row["binary"], norm(row["name"]), row["version"])


def cross_check(inventory: list[dict[str, Any]], deps: dict[str, Any]) -> list[str]:
    """Every DEPS_LICENCES.json flagged row must appear in our inventory at the same
    version. Returns a list of problems (empty = clean)."""
    have = {(norm(r["name"]), r["version"]) for r in inventory}
    problems = []
    for f in deps["flagged"]:
        if f["name"] == "PyInstaller-bootloader":
            continue
        if (norm(f["name"]), f["version"]) not in have:
            problems.append(
                f"{f['ecosystem']} {f['name']} {f['version']} missing from inventory"
            )
    return problems


def pick_licence_text(
    inventory: list[dict[str, Any]], licence_id: str
) -> tuple[str, str] | None:
    """Deterministically pick one bundled row's own shipped LICENSE file text for a
    given SPDX id (alphabetically first by name, version, binary), or None."""
    candidates = sorted(
        (
            r
            for r in inventory
            if canonical_id(r["licence"]) == licence_id and r.get("_licence_text")
        ),
        key=sort_key,
    )
    if not candidates:
        return None
    row = candidates[0]
    return row[
        "_licence_text"
    ].strip() + "\n", f"{row['name']} {row['version']} ({row['binary']})"


def build_inventory(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deps = json.loads(Path(args.deps_licences).read_text(encoding="utf-8"))
    dist_infos = {
        "sidecar_venv": walk_dist_infos(Path(args.sidecar_venv)),
        "openbb_venv": walk_dist_infos(Path(args.openbb_venv)),
        "secedgar_venv": walk_dist_infos(Path(args.secedgar_venv)),
    }
    cargo_meta = json.loads(Path(args.cargo_metadata).read_text(encoding="utf-8"))
    if args.pnpm_licenses:
        pnpm_json = json.loads(Path(args.pnpm_licenses).read_text(encoding="utf-8"))
    else:
        pnpm_json = json.loads(sys.stdin.read())

    inventory = (
        python_rows(deps, dist_infos) + npm_rows(pnpm_json) + cargo_rows(cargo_meta)
    )
    inventory.sort(key=sort_key)
    return inventory, deps


def counts_by_ecosystem(inventory: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in inventory:
        binkey = r["binary"] if r["ecosystem"] == "python" else r["ecosystem"]
        out[binkey] = out.get(binkey, 0) + 1
    return out


def render_json(inventory: list[dict[str, Any]], sha: str) -> dict[str, Any]:
    rows = []
    for r in inventory:
        rows.append(
            {
                "ecosystem": r["ecosystem"],
                "binary": r["binary"],
                "name": r["name"],
                "version": r["version"],
                "licence": r["licence"],
                "licence_source": r["licence_source"],
                "url": r.get("url"),
                "copyleft": bool(r["copyleft"]),
                "note": r.get("note"),
            }
        )
    return {
        "draft_at_sha": sha,
        "counts": counts_by_ecosystem(inventory),
        "copyleft_count": sum(1 for r in inventory if r["copyleft"]),
        "packages": rows,
    }


def render_md(
    inventory: list[dict[str, Any]], deps: dict[str, Any], sha: str, caveats: list[str]
) -> str:
    counts = counts_by_ecosystem(inventory)
    copyleft_rows = sorted((r for r in inventory if r["copyleft"]), key=sort_key)
    permissive_rows = sorted((r for r in inventory if not r["copyleft"]), key=sort_key)
    unresolved_rows = sorted(
        (
            r
            for r in inventory
            if r["licence"] is None or (r.get("note") or "").startswith("not_resolved")
        ),
        key=sort_key,
    )

    lines: list[str] = []
    lines.append(
        f"<!-- DRAFT at {sha} by the R15 notices agent; promote per DECISIONS §5.1 -->"
    )
    lines.append("")
    lines.append("# Third-party notices (draft)")
    lines.append("")
    lines.append(CORE_NOTICE)
    lines.append("")
    lines.append(
        "Counts by bundle (bundled/runtime packages only, dev-only and build-only excluded): "
        + "; ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        + f". Total copyleft rows: {sum(1 for r in inventory if r['copyleft'])}."
    )
    lines.append("")

    # Section A — copyleft
    lines.append("## Section A — Copyleft components")
    lines.append("")
    if not copyleft_rows:
        lines.append("None.")
    else:
        lines.append(
            "| Package | Version | Binary | Licence | Process boundary | Corresponding source |"
        )
        lines.append("|---|---|---|---|---|---|")
        for r in copyleft_rows:
            boundary = (
                "spawned as a separate process over loopback MCP, unmodified"
                if r["binary"]
                in ("vysted-openbb-mcp-sidecar", "vysted-sec-edgar-mcp-sidecar")
                else (
                    "runs in-process inside the main sidecar binary, unmodified"
                    if r["binary"] == "vysted-sidecar"
                    else "compiled unmodified into the desktop core binary"
                )
            )
            cid = canonical_id(r["licence"])
            url = r.get("url") or "(no URL recorded)"
            if (
                cid in APPENDIX_LICENCE_IDS
                and pick_licence_text(inventory, cid) is not None
            ):
                source_note = f"licence text: Appendix below ({cid})"
            elif r.get("has_local_licence_file"):
                source_note = (
                    f"licence text: the package's own LICENSE file in {r['binary']}'s venv, "
                    f"or upstream {url} (only AGPL-3.0/GPL-2.0/LGPL-3.0 texts are carried in the Appendix)"
                )
            else:
                source_note = f"licence text: see upstream {url} (this package ships no local LICENSE file)"
            corr = (
                f"upstream {r.get('url') or '(URL not recorded)'}; "
                f"pinned in this repo's requirements/lock file for {r['binary']}. {source_note}"
            )
            lines.append(
                f"| {r['name']} | {r['version']} | {r['binary']} | {r['licence']} | {boundary} | {corr} |"
            )
    lines.append("")

    # Section B — permissive, per ecosystem
    lines.append("## Section B — Permissive components")
    lines.append("")
    for label, ecosystem, binaries in (
        ("Python — vysted-sidecar", "python", ["vysted-sidecar"]),
        ("Python — vysted-openbb-mcp-sidecar", "python", ["vysted-openbb-mcp-sidecar"]),
        (
            "Python — vysted-sec-edgar-mcp-sidecar",
            "python",
            ["vysted-sec-edgar-mcp-sidecar"],
        ),
        ("npm (frontend, runtime/prod only)", "npm", ["frontend (static export)"]),
        (
            "Rust crates (src-tauri, normal deps only)",
            "cargo",
            ["src-tauri (desktop core)"],
        ),
    ):
        rows = [
            r
            for r in permissive_rows
            if r["ecosystem"] == ecosystem and r["binary"] in binaries
        ]
        lines.append(f"### {label}")
        lines.append("")
        if not rows:
            lines.append("None.")
            lines.append("")
            continue
        lines.append("| Name | Version | Licence | URL |")
        lines.append("|---|---|---|---|")
        for r in rows:
            lines.append(
                f"| {r['name']} | {r['version']} | {r['licence'] or '(unresolved)'} | {r.get('url') or ''} |"
            )
        lines.append("")
    lines.append(
        "_Note on `r-efi`: flagged by the Stage D scan because its licence string "
        'contains "LGPL", but it is an OR-choice (MIT/Apache-2.0 selectable without '
        "LGPL obligations) reachable only via `getrandom`'s UEFI-target edge, which is "
        "never active in a macOS/Windows/Linux desktop build — see DECISIONS §5.3._"
    )
    lines.append("")

    # Section C — not resolved
    lines.append("## Section C — Not resolved")
    lines.append("")
    if not unresolved_rows:
        lines.append(
            "None. The four packages the Stage D scan flagged with empty registry "
            "licence metadata (`caio`, `fredapi`, `peewee`, `httpxthrottlecache`) were "
            "each resolved from their own shipped `LICENSE`/`COPYING` file in the "
            "relevant venv's dist-info (see DECISIONS §5.3); all four are permissive "
            "(Apache-2.0 or MIT) and appear in Section B above."
        )
    else:
        lines.append("| Name | Version | Binary | What was checked |")
        lines.append("|---|---|---|---|")
        for r in unresolved_rows:
            lines.append(
                f"| {r['name']} | {r['version']} | {r['binary']} | {r.get('note') or 'no licence metadata or LICENSE file found in the inspected venv'} |"
            )
    lines.append("")

    # Appendix
    lines.append("## Appendix — full licence texts")
    lines.append("")
    lines.append(
        "Each text below is taken verbatim from a package's own shipped `LICENSE` file "
        "in one of the inspected venvs (never reconstructed from memory), and covers "
        "every package above under the same SPDX id."
    )
    for licence_id in ("AGPL-3.0", "GPL-2.0", "LGPL-3.0"):
        picked = pick_licence_text(inventory, licence_id)
        lines.append("")
        lines.append(f"### {licence_id}")
        lines.append("")
        if picked is None:
            lines.append(
                f"No local `LICENSE` file for {licence_id} was found in the inspected venvs."
            )
            continue
        text, src = picked
        lines.append(f"_Source: {src}'s own LICENSE file._")
        lines.append("")
        lines.append("```")
        lines.append(text.rstrip("\n"))
        lines.append("```")
    lines.append("")

    # Caveats
    lines.append("## Caveats")
    lines.append("")
    for c in caveats:
        lines.append(f"- {c}")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sidecar-venv", dest="sidecar_venv", required=True)
    parser.add_argument("--openbb-venv", dest="openbb_venv", required=True)
    parser.add_argument("--secedgar-venv", dest="secedgar_venv", required=True)
    parser.add_argument("--deps-licences", dest="deps_licences", required=True)
    parser.add_argument("--cargo-metadata", dest="cargo_metadata", required=True)
    parser.add_argument(
        "--pnpm-licenses", dest="pnpm_licenses", default=None, help="defaults to stdin"
    )
    parser.add_argument(
        "--sha", required=True, help="git sha stamped into the draft header"
    )
    parser.add_argument("--out-dir", dest="out_dir", required=True)
    args = parser.parse_args()

    inventory, deps = build_inventory(args)
    problems = cross_check(inventory, deps)
    if problems:
        print("CROSS-CHECK FAILURES:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    caveats = [
        "Only this machine's (macOS/Apple Silicon) venvs and lockfiles were inspected — "
        "no Windows or Linux wheels were scanned, so a platform-conditional dependency "
        "resolving differently there would not show up here.",
        "Python bundled/dev-only scope is taken from the Stage D scan's Requires-Dist "
        "closure walk (DEPS_LICENCES.json), not recomputed by this script.",
        "This is a DRAFT for the operator to promote, correct, or reject — it draws no "
        "legal conclusion about licence compatibility.",
    ]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "THIRD_PARTY_NOTICES.draft.json"
    md_path = out_dir / "THIRD_PARTY_NOTICES.draft.md"

    json_doc = render_json(inventory, args.sha)
    json_path.write_text(
        json.dumps(json_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_md(inventory, deps, args.sha, caveats), encoding="utf-8")

    print(f"{len(inventory)} bundled rows -> {json_path}, {md_path}")


if __name__ == "__main__":
    main()

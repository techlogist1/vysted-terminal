"""R15 licence-audit: dump licence metadata for the RUNTIME closure of a venv.

Run with the venv's own interpreter:
    <venv>/bin/python scripts/r15/licence_scan.py <requirements.txt> <out.json>
Closure = requirements.txt roots -> Requires-Dist (markers evaluated for THIS platform,
extras followed). Dev-only tools (pyinstaller, ruff, pytest) fall outside it by construction.
"""

import json
import re
import sys
from importlib import metadata

try:
    from packaging.requirements import Requirement
except ImportError:  # pip always vendors it
    from pip._vendor.packaging.requirements import Requirement


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def roots(req_file: str) -> list[Requirement]:
    out = []
    for raw in open(req_file, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            out.append(Requirement(line))
    return out


def main(req_file: str, out_file: str) -> None:
    dists = {
        norm(d.metadata["Name"]): d
        for d in metadata.distributions()
        if d.metadata["Name"]
    }
    seen: dict[str, set[str]] = {}
    missing: list[str] = []
    stack = [(norm(r.name), set(r.extras)) for r in roots(req_file)]
    while stack:
        name, extras = stack.pop()
        if name in seen and extras <= seen[name]:
            continue
        seen.setdefault(name, set()).update(extras)
        dist = dists.get(name)
        if dist is None:
            missing.append(name)
            continue
        for spec in dist.requires or []:
            req = Requirement(spec)
            envs = [{"extra": e} for e in extras] or [{"extra": ""}]
            if req.marker is None or any(req.marker.evaluate(env) for env in envs):
                stack.append((norm(req.name), set(req.extras)))

    rows = []
    for name in sorted(seen):
        dist = dists.get(name)
        if dist is None:
            continue
        md = dist.metadata
        licence = (md.get("License") or "").strip()
        rows.append(
            {
                "name": md["Name"],
                "version": dist.version,
                "license_expression": md.get("License-Expression"),
                "license": licence.splitlines()[0][:120] if licence else None,
                "classifiers": [
                    c.split("::", 1)[1].strip()
                    for c in md.get_all("Classifier") or []
                    if c.startswith("License ::")
                ],
                "home": md.get("Home-page")
                or next(iter(md.get_all("Project-URL") or []), None),
            }
        )
    json.dump(
        {
            "requirements": req_file,
            "closure_size": len(rows),
            "not_installed": sorted(set(missing)),
            "packages": rows,
        },
        open(out_file, "w", encoding="utf-8"),
        indent=1,
    )
    print(
        f"{len(rows)} runtime dists -> {out_file}; not installed: {sorted(set(missing))}"
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

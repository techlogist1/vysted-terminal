// @vitest-environment node
import { platform } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { SIDECAR_SPECS, pyinstallerCommand } from "./sidecar-specs.mjs";

const ROOT = resolve(import.meta.dirname, "..");
const isWin = platform() === "win32";
const SEP = isWin ? ";" : ":";
const p = (...parts) => join(ROOT, "sidecar", ...parts);
const tool = (dir) =>
  `"${join(dir, ".venv", isWin ? "Scripts" : "bin", isWin ? "pyinstaller.exe" : "pyinstaller")}"`;
const tail = (dir) =>
  `--distpath "${join(dir, "dist")}" --workpath "${join(dir, "build")}" ` +
  `--specpath "${join(dir, "build")}" main.py`;
const UVICORN =
  "--hidden-import=uvicorn.loops.auto --hidden-import=uvicorn.loops.asyncio " +
  "--hidden-import=uvicorn.protocols.http.auto --hidden-import=uvicorn.protocols.http.h11_impl " +
  "--hidden-import=uvicorn.protocols.websockets.auto --hidden-import=uvicorn.lifespan.on " +
  "--hidden-import=uvicorn.lifespan.off";

// The PyInstaller command each pre-refactor ensure script ran (captured from
// base 30b6414f with child_process stubbed). --onefile drops whatever a flag
// does not name while the build still succeeds, so these must not drift.
const BASE = {
  "vysted-sidecar":
    `${tool(p())} --onefile --clean --noconfirm --name vysted-sidecar ${UVICORN} ` +
    "--copy-metadata=fastmcp --copy-metadata=mcp --copy-metadata=anyio --copy-metadata=httpx " +
    "--copy-metadata=starlette --copy-metadata=uvicorn --collect-all=curl_cffi " +
    `--add-data "${p("agents")}${SEP}agents" ` +
    `--add-data "${p("services", "screener_universes")}${SEP}services/screener_universes" ` +
    `--add-data "${p("services", "resolver_masters")}${SEP}services/resolver_masters" ` +
    `--add-data "${p("config")}${SEP}config" ` +
    `--add-data "${p("services", "research", "psl")}${SEP}services/research/psl" ${tail(p())}`,
  "vysted-openbb-mcp-sidecar":
    `${tool(p("openbb_mcp_subprocess"))} --onefile --clean --noconfirm ` +
    `--name vysted-openbb-mcp-sidecar ${UVICORN} --hidden-import=openbb_mcp_server.app.app ` +
    "--collect-all=openbb_mcp_server --collect-all=openbb_core --collect-all=openbb_equity " +
    "--collect-all=openbb_economy --collect-all=openbb_yfinance --collect-all=openbb_fred " +
    "--collect-all=openbb_fmp --collect-all=fastmcp --copy-metadata=fastmcp " +
    "--copy-metadata=fastmcp-slim --copy-metadata=mcp --copy-metadata=openbb-mcp-server " +
    "--copy-metadata=openbb-core --copy-metadata=anyio --copy-metadata=httpx " +
    "--copy-metadata=starlette --copy-metadata=uvicorn " +
    tail(p("openbb_mcp_subprocess")),
  "vysted-sec-edgar-mcp-sidecar":
    `${tool(p("sec_edgar_mcp_subprocess"))} --onefile --clean --noconfirm ` +
    `--name vysted-sec-edgar-mcp-sidecar ${UVICORN} --hidden-import=sec_edgar_mcp.server ` +
    "--collect-all=sec_edgar_mcp --collect-data=edgar --collect-submodules=edgar " +
    "--copy-metadata=mcp --copy-metadata=sec-edgar-mcp --copy-metadata=edgartools " +
    "--copy-metadata=anyio --copy-metadata=httpx --copy-metadata=starlette " +
    "--copy-metadata=uvicorn " +
    tail(p("sec_edgar_mcp_subprocess")),
};

describe("SIDECAR_SPECS", () => {
  it("lists exactly the three bundled sidecars", () => {
    expect(SIDECAR_SPECS.map((s) => s.name)).toEqual(Object.keys(BASE));
  });

  it.each(Object.keys(BASE))("%s PyInstaller command is byte-identical to base", (name) => {
    const spec = SIDECAR_SPECS.find((s) => s.name === name);
    expect(pyinstallerCommand(spec)).toBe(BASE[name]);
  });

  it.each(SIDECAR_SPECS.map((s) => [s.name, s]))(
    "%s staleness walks every --add-data source",
    (_name, spec) => {
      for (const [src] of spec.addData) expect(spec.stale.dirs).toContain(src);
      const added = spec.pyinstallerFlags.filter((f) => f.startsWith("--add-data"));
      expect(added).toHaveLength(spec.addData.length);
    },
  );

  // R15-CODE-PLATFORM-078: every spec, including "main", builds its frozen
  // venv from requirements.txt — never requirements-dev.txt, which also pulls
  // ruff/pytest/pytest-asyncio into the venv PyInstaller freezes the release
  // binary from. Build-only tooling (pyinstaller) rides as a pipExtra instead.
  it.each(SIDECAR_SPECS.map((s) => [s.name, s]))(
    "%s builds from requirements.txt, not requirements-dev.txt",
    (_name, spec) => {
      expect(spec.requirements).toBe("requirements.txt");
      expect(spec.pipExtras).toContain("pyinstaller==6.20.0");
    },
  );
});

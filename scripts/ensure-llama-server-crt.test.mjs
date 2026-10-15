// @vitest-environment node
//
// Covers the Windows VC++ CRT redist staging helpers in ensure-llama-server.mjs
// (findVsCrtRedistDir, latestVersionDir, and copyWindowsCrtRuntime's win32 branch)
// without running on an actual Windows machine: process.platform and
// node:child_process's execFileSync (the vswhere.exe invocation) are faked so
// every branch is reachable on any host, with real temp-directory fixtures for
// the filesystem checks (existsSync/readdirSync are never mocked).
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("node:child_process", async (importOriginal) => ({
  ...(await importOriginal()),
  execFileSync: vi.fn(),
}));

import {
  copyWindowsCrtRuntime,
  findVsCrtRedistDir,
  latestVersionDir,
} from "./ensure-llama-server.mjs";

describe("latestVersionDir", () => {
  it("compares dotted version segments numerically, not lexicographically", () => {
    // Lexicographically "1.9.0" > "1.10.0" (the '9' char sorts after '1'); the
    // numeric comparator must still pick "1.10.0" as the newer version.
    expect(latestVersionDir(["1.9.0", "1.10.0"])).toBe("1.10.0");
  });

  it("picks the highest of three well-formed versions", () => {
    expect(latestVersionDir(["1.2.3", "1.10.0", "2.0.0"])).toBe("2.0.0");
  });

  it("treats a missing trailing segment as 0", () => {
    expect(latestVersionDir(["14", "14.1"])).toBe("14.1");
  });

  it("returns the only entry for a single-element list", () => {
    expect(latestVersionDir(["14.44.35112"])).toBe("14.44.35112");
  });
});

describe("findVsCrtRedistDir / copyWindowsCrtRuntime (win32 branches)", () => {
  let root;
  const originalProgramFilesX86 = process.env["ProgramFiles(x86)"];
  const originalSystemRoot = process.env.SystemRoot;
  let platformSpy;

  beforeEach(() => {
    root = mkdtempSync(join(tmpdir(), "llama-crt-helpers-"));
    vi.mocked(execFileSync).mockReset();
  });

  afterEach(() => {
    rmSync(root, { recursive: true, force: true });
    if (originalProgramFilesX86 === undefined) delete process.env["ProgramFiles(x86)"];
    else process.env["ProgramFiles(x86)"] = originalProgramFilesX86;
    if (originalSystemRoot === undefined) delete process.env.SystemRoot;
    else process.env.SystemRoot = originalSystemRoot;
    platformSpy?.mockRestore();
    vi.restoreAllMocks();
  });

  function stubWin32() {
    platformSpy = vi.spyOn(process, "platform", "get").mockReturnValue("win32");
  }

  it("returns null without invoking vswhere when vswhere.exe does not exist", () => {
    process.env["ProgramFiles(x86)"] = join(root, "no-such-dir");
    expect(findVsCrtRedistDir()).toBeNull();
    expect(execFileSync).not.toHaveBeenCalled();
  });

  function putVswhere() {
    const installerDir = join(root, "Microsoft Visual Studio", "Installer");
    mkdirSync(installerDir, { recursive: true });
    writeFileSync(join(installerDir, "vswhere.exe"), "fake");
    process.env["ProgramFiles(x86)"] = root;
  }

  it("returns null when vswhere.exe itself fails", () => {
    putVswhere();
    vi.mocked(execFileSync).mockImplementation(() => {
      throw new Error("vswhere crashed");
    });
    expect(findVsCrtRedistDir()).toBeNull();
  });

  it("returns null when vswhere reports no matching VS install", () => {
    putVswhere();
    vi.mocked(execFileSync).mockReturnValue("   ");
    expect(findVsCrtRedistDir()).toBeNull();
  });

  it("returns null when the resolved install has no VC/Redist/MSVC tree", () => {
    putVswhere();
    const installPath = join(root, "vs-install-no-redist");
    mkdirSync(installPath, { recursive: true });
    vi.mocked(execFileSync).mockReturnValue(installPath);
    expect(findVsCrtRedistDir()).toBeNull();
  });

  it("returns null when no MSVC version dir carries an x64 subfolder", () => {
    putVswhere();
    const installPath = join(root, "vs-install-no-x64");
    mkdirSync(join(installPath, "VC", "Redist", "MSVC", "14.40.0"), { recursive: true });
    vi.mocked(execFileSync).mockReturnValue(installPath);
    expect(findVsCrtRedistDir()).toBeNull();
  });

  it("resolves the newest version's Microsoft.VCxxx.CRT dir via vswhere", () => {
    putVswhere();
    const installPath = join(root, "vs-install-ok");
    const older = join(installPath, "VC", "Redist", "MSVC", "14.40.0", "x64");
    const newer = join(installPath, "VC", "Redist", "MSVC", "14.44.35112", "x64");
    mkdirSync(older, { recursive: true });
    mkdirSync(join(newer, "Microsoft.VC143.CRT"), { recursive: true });
    vi.mocked(execFileSync).mockReturnValue(installPath);
    const found = findVsCrtRedistDir();
    expect(found).toBe(join(newer, "Microsoft.VC143.CRT"));
  });

  it("copies the CRT DLLs app-local from the VS redist dir on win32", () => {
    stubWin32();
    putVswhere();
    const installPath = join(root, "vs-install-full");
    const crtDir = join(
      installPath,
      "VC",
      "Redist",
      "MSVC",
      "14.44.35112",
      "x64",
      "Microsoft.VC143.CRT",
    );
    mkdirSync(crtDir, { recursive: true });
    for (const dll of ["msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"]) {
      writeFileSync(join(crtDir, dll), "bytes");
    }
    vi.mocked(execFileSync).mockReturnValue(installPath);

    const stageDir = join(root, "stage-from-vs");
    mkdirSync(stageDir, { recursive: true });
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => undefined);
    copyWindowsCrtRuntime(stageDir);
    expect(readdirSync(stageDir).sort()).toEqual([
      "msvcp140.dll",
      "vcruntime140.dll",
      "vcruntime140_1.dll",
    ]);
    expect(logSpy).toHaveBeenCalledWith(expect.stringContaining("staged VC++ runtime DLLs from"));
  });

  it("falls back to System32 with a warning when no VS redist tree is found", () => {
    stubWin32();
    process.env["ProgramFiles(x86)"] = join(root, "no-such-dir");
    // copyWindowsCrtRuntime reads <SystemRoot>/System32 for the fallback.
    process.env.SystemRoot = root;
    mkdirSync(join(root, "System32"), { recursive: true });
    for (const dll of ["msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"]) {
      writeFileSync(join(root, "System32", dll), "bytes");
    }

    const stageDir = join(root, "stage-from-system32");
    mkdirSync(stageDir, { recursive: true });
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const logSpy = vi.spyOn(console, "log").mockImplementation(() => undefined);
    copyWindowsCrtRuntime(stageDir);
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("falling back to the runtime"));
    expect(readdirSync(stageDir).sort()).toEqual([
      "msvcp140.dll",
      "vcruntime140.dll",
      "vcruntime140_1.dll",
    ]);
    expect(logSpy).toHaveBeenCalled();
  });

  it("throws when neither the VS redist tree nor System32 has the CRT DLLs", () => {
    stubWin32();
    process.env["ProgramFiles(x86)"] = join(root, "no-such-dir");
    process.env.SystemRoot = join(root, "empty-system-root");
    mkdirSync(join(root, "empty-system-root", "System32"), { recursive: true });
    const stageDir = join(root, "stage-fail");
    mkdirSync(stageDir, { recursive: true });
    expect(() => copyWindowsCrtRuntime(stageDir)).toThrow(
      /could not find msvcp140\.dll, vcruntime140\.dll and vcruntime140_1\.dll/,
    );
  });
});

// @vitest-environment node
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  assemble,
  locateArtifacts,
  parseArgs,
  sanitizeName,
  sha256File,
  versionFromTag,
  walkFiles,
} from "./assemble-release.mjs";

const SCRIPT_PATH = join(dirname(fileURLToPath(import.meta.url)), "assemble-release.mjs");

describe("versionFromTag", () => {
  it("strips a leading v<digit>", () => {
    expect(versionFromTag("v0.10.0")).toBe("0.10.0");
  });
  it("leaves a tag with no leading v alone", () => {
    expect(versionFromTag("0.10.0")).toBe("0.10.0");
  });
  it("leaves a non-version-looking vX tag alone", () => {
    expect(versionFromTag("vnext")).toBe("vnext");
  });
});

describe("parseArgs", () => {
  it("parses --tag and --artifacts-dir, defaulting repo", () => {
    const args = parseArgs(["--tag", "v0.10.0", "--artifacts-dir", "/tmp/artifacts"]);
    expect(args).toEqual({
      tag: "v0.10.0",
      artifactsDir: "/tmp/artifacts",
      repo: "techlogist1/vysted-terminal",
    });
  });

  it("converts multi-word kebab-case flags to camelCase keys", () => {
    const args = parseArgs([
      "--out-dir",
      "/tmp/out",
      "--notes-file",
      "/tmp/notes.md",
      "--tauri-conf",
      "/tmp/tauri.conf.json",
    ]);
    expect(args.outDir).toBe("/tmp/out");
    expect(args.notesFile).toBe("/tmp/notes.md");
    expect(args.tauriConf).toBe("/tmp/tauri.conf.json");
  });

  it("lets an explicit --repo override the default", () => {
    expect(parseArgs(["--repo", "someone/else"]).repo).toBe("someone/else");
  });

  it("ignores stray tokens that do not start with --", () => {
    const args = parseArgs(["positional-noise", "--tag", "v1.0.0"]);
    expect(args.tag).toBe("v1.0.0");
    expect(args.positionalNoise).toBeUndefined();
  });
});

describe("sanitizeName", () => {
  it("replaces whitespace runs with a hyphen", () => {
    expect(sanitizeName("Vysted Terminal_0.10.0_aarch64.dmg")).toBe(
      "Vysted-Terminal_0.10.0_aarch64.dmg",
    );
  });
  it("is a no-op on an already space-free name", () => {
    expect(sanitizeName("Vysted-Terminal.AppImage")).toBe("Vysted-Terminal.AppImage");
  });
});

let root;

beforeEach(() => {
  root = mkdtempSync(join(tmpdir(), "assemble-release-"));
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

function put(rel, contents = "x") {
  const p = join(root, rel);
  mkdirSync(join(p, ".."), { recursive: true });
  writeFileSync(p, contents);
  return p;
}

function putConf(version = "0.10.0") {
  return put("tauri.conf.json", JSON.stringify({ version }));
}

function putFullFixture() {
  put("macos/dmg/Vysted Terminal_0.10.0_aarch64.dmg", "dmg-bytes");
  put("macos/macos/Vysted Terminal.app.tar.gz", "mac-tar-bytes");
  put("macos/macos/Vysted Terminal.app.tar.gz.sig", "mac-signature");
  // A real .app bundle directory sits alongside the updater artifacts in the
  // macOS bundle output — walkFiles must not descend into it.
  put("macos/macos/Vysted Terminal.app/Contents/MacOS/vysted-terminal", "binary");
  put("windows/nsis/Vysted Terminal_0.10.0_x64-setup.exe", "exe-bytes");
  put("windows/nsis/Vysted Terminal_0.10.0_x64-setup.exe.sig", "win-signature");
  put("linux/appimage/vysted-terminal_0.10.0_amd64.AppImage", "appimage-bytes");
  put("linux/appimage/vysted-terminal_0.10.0_amd64.AppImage.sig", "linux-signature");
}

describe("walkFiles", () => {
  it("finds loose files but skips inside a .app bundle directory", () => {
    putFullFixture();
    const files = walkFiles(root);
    expect(files.some((f) => f.endsWith(".dmg"))).toBe(true);
    expect(files.some((f) => f.includes("Contents/MacOS"))).toBe(false);
  });
});

describe("locateArtifacts", () => {
  it("finds every platform's pair when all three are present", () => {
    putFullFixture();
    const found = locateArtifacts(walkFiles(root));
    expect(found.dmg).toMatch(/\.dmg$/);
    expect(found.macTarGz).toMatch(/\.app\.tar\.gz$/);
    expect(found.macSig).toMatch(/\.sig$/);
    expect(found.winExe).toMatch(/-setup\.exe$/);
    expect(found.appImage).toMatch(/\.AppImage$/i);
  });

  it("tolerates a missing AppImage pair (Linux build job is continue-on-error)", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.includes("AppImage"));
    const found = locateArtifacts(files);
    expect(found.appImage).toBeUndefined();
    expect(found.dmg).toBeDefined();
  });

  it("throws when the macOS dmg is missing (required)", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.endsWith(".dmg"));
    expect(() => locateArtifacts(files)).toThrow(/dmg/i);
  });

  it("throws when a required .sig is missing", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.endsWith("x64-setup.exe.sig"));
    expect(() => locateArtifacts(files)).toThrow(/setup\.exe\.sig/);
  });

  it("throws when the macOS updater .app.tar.gz is missing", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.endsWith(".app.tar.gz"));
    expect(() => locateArtifacts(files)).toThrow(/macOS updater \.app\.tar\.gz/);
  });

  it("throws when the mac signature is missing while the tar.gz itself is present", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.endsWith(".app.tar.gz.sig"));
    expect(() => locateArtifacts(files)).toThrow(/app\.tar\.gz\.sig/);
  });

  it("throws when the AppImage signature is missing while the AppImage itself is present", () => {
    putFullFixture();
    const files = walkFiles(root).filter((f) => !f.endsWith(".AppImage.sig"));
    expect(() => locateArtifacts(files)).toThrow(/AppImage\.sig/i);
  });
});

describe("sha256File", () => {
  it("matches a hand-computed digest of known content", () => {
    const p = put("known.txt", "hello\n");
    // sha256("hello\n")
    expect(sha256File(p)).toBe("5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03");
  });
});

describe("assemble", () => {
  it("writes versioned + stable copies, latest.json and SHA256SUMS.txt for a full fixture", async () => {
    putFullFixture();
    const outDir = join(root, "out");
    const result = await assemble({
      tag: "v0.10.0",
      artifactsDir: root,
      tauriConf: putConf(),
      outDir,
      notesFile: join(root, "nonexistent-notes.md"),
    });

    expect(result.files).toContain("Vysted-Terminal-macOS-AppleSilicon.dmg");
    expect(result.files).toContain("Vysted-Terminal-Windows-x64-Setup.exe");
    expect(result.files).toContain("Vysted-Terminal-Linux-x86_64.AppImage");
    expect(result.files).toContain("latest.json");
    expect(result.files).toContain("SHA256SUMS.txt");
    // Spaces must never survive into an uploadable asset name.
    for (const name of result.files) expect(name).not.toMatch(/\s/);

    const latest = JSON.parse(readFileSync(result.latestJsonPath, "utf8"));
    expect(latest.version).toBe("0.10.0");
    expect(latest.notes).toBe("See the GitHub release page for details.");
    expect(latest.platforms["darwin-aarch64"].signature).toBe("mac-signature");
    expect(latest.platforms["darwin-aarch64"].url).toBe(
      "https://github.com/techlogist1/vysted-terminal/releases/download/v0.10.0/Vysted-Terminal.app.tar.gz",
    );
    expect(latest.platforms["windows-x86_64"].signature).toBe("win-signature");
    expect(latest.platforms["linux-x86_64"].signature).toBe("linux-signature");

    const sums = readFileSync(result.sumsPath, "utf8").trim().split("\n");
    // Every assembled file except SHA256SUMS.txt itself gets one line.
    expect(sums.length).toBe(result.files.length - 1);
    const dmgLine = sums.find((l) => l.endsWith("Vysted-Terminal-macOS-AppleSilicon.dmg"));
    expect(dmgLine.split("  ")[0]).toBe(
      sha256File(join(outDir, "Vysted-Terminal-macOS-AppleSilicon.dmg")),
    );
  });

  it("omits the linux platform and its stable copy when no AppImage was built", async () => {
    putFullFixture();
    rmSync(join(root, "linux"), { recursive: true, force: true });
    const outDir = join(root, "out");
    const result = await assemble({
      tag: "v0.10.0",
      artifactsDir: root,
      tauriConf: putConf(),
      outDir,
      repo: "someone/else",
    });

    expect(result.files).not.toContain("Vysted-Terminal-Linux-x86_64.AppImage");
    const latest = JSON.parse(readFileSync(result.latestJsonPath, "utf8"));
    expect(latest.platforms["linux-x86_64"]).toBeUndefined();
    expect(latest.platforms["darwin-aarch64"].url).toContain("someone/else");
  });

  it("uses a provided notes file's contents verbatim", async () => {
    putFullFixture();
    const notesPath = put("notes.md", "# Vysted Terminal 0.10.0\n\nEasy Install.\n");
    const result = await assemble({
      tag: "v0.10.0",
      artifactsDir: root,
      tauriConf: putConf(),
      outDir: join(root, "out"),
      notesFile: notesPath,
    });
    const latest = JSON.parse(readFileSync(result.latestJsonPath, "utf8"));
    expect(latest.notes).toContain("Easy Install.");
  });

  it("rejects a missing required artifact with a clear error", async () => {
    putFullFixture();
    rmSync(join(root, "windows"), { recursive: true, force: true });
    await expect(
      assemble({
        tag: "v0.10.0",
        artifactsDir: root,
        tauriConf: putConf(),
        outDir: join(root, "out"),
      }),
    ).rejects.toThrow(/setup\.exe/);
  });

  it("rejects when --tag is not given", async () => {
    await expect(assemble({ artifactsDir: root })).rejects.toThrow(/--tag is required/);
  });

  it("rejects when --artifacts-dir is not given", async () => {
    await expect(assemble({ tag: "v0.10.0" })).rejects.toThrow(/--artifacts-dir is required/);
  });

  it("rejects a tag that disagrees with the tauri.conf.json version", async () => {
    putFullFixture();
    await expect(
      assemble({
        tag: "v0.10.0",
        artifactsDir: root,
        tauriConf: putConf("0.10.0-beta.3"),
        outDir: join(root, "out"),
      }),
    ).rejects.toThrow(/does not match tauri\.conf\.json version 0\.10\.0-beta\.3/);
  });

  it("rejects built assets whose names do not carry the tag's version", async () => {
    putFullFixture();
    await expect(
      assemble({
        tag: "v0.11.0",
        artifactsDir: root,
        tauriConf: putConf("0.11.0"),
        outDir: join(root, "out"),
      }),
    ).rejects.toThrow(/do not carry version 0\.11\.0/);
  });
});

describe("CLI entry point", () => {
  it("succeeds end-to-end and prints the assembled file list", () => {
    putFullFixture();
    const outDir = join(root, "out");
    const result = spawnSync(
      process.execPath,
      [
        SCRIPT_PATH,
        "--tag",
        "v0.10.0",
        "--artifacts-dir",
        root,
        "--tauri-conf",
        putConf(),
        "--out-dir",
        outDir,
        "--notes-file",
        join(root, "nonexistent-notes.md"),
      ],
      { encoding: "utf8" },
    );
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("[assemble-release] wrote");
    expect(readFileSync(join(outDir, "latest.json"), "utf8")).toContain("0.10.0");
  });

  it("exits non-zero and logs a clear failure when a required artifact is missing", () => {
    putFullFixture();
    rmSync(join(root, "windows"), { recursive: true, force: true });
    const result = spawnSync(
      process.execPath,
      [
        SCRIPT_PATH,
        "--tag",
        "v0.10.0",
        "--artifacts-dir",
        root,
        "--tauri-conf",
        putConf(),
        "--out-dir",
        join(root, "out"),
      ],
      { encoding: "utf8" },
    );
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("[assemble-release] failed:");
  });
});

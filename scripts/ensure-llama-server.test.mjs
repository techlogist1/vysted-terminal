// @vitest-environment node
import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import https from "node:https";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Readable } from "node:stream";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ASSET_MAP,
  LIB_STAGE_ROOT,
  binaryOutPath,
  copyWindowsCrtRuntime,
  needsStage,
  resolveAsset,
  sha256OfFile,
  stageTriple,
} from "./ensure-llama-server.mjs";

const TRIPLES = ["aarch64-apple-darwin", "x86_64-pc-windows-msvc", "x86_64-unknown-linux-gnu"];

describe("ASSET_MAP", () => {
  it("pins all three contract triples with a well-formed sha256 and asset name", () => {
    for (const triple of TRIPLES) {
      const asset = ASSET_MAP[triple];
      expect(asset, `missing ASSET_MAP row for ${triple}`).toBeTruthy();
      expect(asset.sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(asset.assetName.length).toBeGreaterThan(0);
      expect(asset.binaryName.length).toBeGreaterThan(0);
      expect(asset.libs.length).toBeGreaterThan(0);
      // No duplicate lib entries (would silently double-copy / mask a typo).
      expect(new Set(asset.libs).size).toBe(asset.libs.length);
    }
  });

  it("stages 14 dlopen'ed ggml-cpu microarchitecture variants on Windows and Linux", () => {
    for (const triple of ["x86_64-pc-windows-msvc", "x86_64-unknown-linux-gnu"]) {
      const cpuVariants = ASSET_MAP[triple].libs.filter((l) => l.includes("ggml-cpu-"));
      expect(cpuVariants).toHaveLength(14);
    }
  });

  it("only the Windows (vulkan) asset carries a GPU backend lib", () => {
    expect(ASSET_MAP["x86_64-pc-windows-msvc"].libs).toContain("ggml-vulkan.dll");
    expect(ASSET_MAP["x86_64-unknown-linux-gnu"].libs.some((l) => l.includes("vulkan"))).toBe(
      false,
    );
    expect(ASSET_MAP["aarch64-apple-darwin"].libs.some((l) => l.includes("vulkan"))).toBe(false);
  });
});

describe("resolveAsset", () => {
  it("returns the pinned asset for a known triple", () => {
    expect(resolveAsset("aarch64-apple-darwin").assetName).toBe(
      "llama-b11429-bin-macos-arm64.tar.gz",
    );
  });

  it("throws a clear, actionable error for an unsupported triple", () => {
    expect(() => resolveAsset("aarch64-unknown-linux-gnu")).toThrow(
      /no llama\.cpp b11429 release asset is pinned/,
    );
  });
});

describe("binaryOutPath", () => {
  it("appends .exe only for the Windows triple", () => {
    expect(binaryOutPath("x86_64-pc-windows-msvc")).toMatch(
      /llama-server-x86_64-pc-windows-msvc\.exe$/,
    );
    expect(binaryOutPath("aarch64-apple-darwin")).toMatch(/llama-server-aarch64-apple-darwin$/);
    expect(binaryOutPath("aarch64-apple-darwin")).not.toMatch(/\.exe$/);
  });
});

describe("sha256OfFile", () => {
  let dir;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "llama-sha-"));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("matches a known sha256 for known content", () => {
    const f = join(dir, "x.txt");
    writeFileSync(f, "hello\n");
    expect(sha256OfFile(f)).toBe(
      "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
    );
  });

  it("differs for different content (catches a corrupted/truncated download)", () => {
    const a = join(dir, "a.txt");
    const b = join(dir, "b.txt");
    writeFileSync(a, "hello\n");
    writeFileSync(b, "hello!\n");
    expect(sha256OfFile(a)).not.toBe(sha256OfFile(b));
  });
});

describe("needsStage", () => {
  it("--force always needs staging regardless of any existing marker", () => {
    expect(needsStage("aarch64-apple-darwin", { force: true })).toBe(true);
  });

  it("an unknown triple needs staging (no marker can exist for it) without throwing", () => {
    expect(needsStage("not-a-real-triple")).toBe(true);
  });
});

describe("copyWindowsCrtRuntime", () => {
  it("warns and skips without throwing when staging the Windows triple off Windows", () => {
    expect(process.platform).not.toBe("win32"); // this suite only runs on macOS/Linux CI
    const dir = mkdtempSync(join(tmpdir(), "llama-crt-"));
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(() => copyWindowsCrtRuntime(dir)).not.toThrow();
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("non-Windows host"));
    expect(readdirSync(dir)).toHaveLength(0);
    warnSpy.mockRestore();
    rmSync(dir, { recursive: true, force: true });
  });
});

describe("stageTriple", () => {
  const triple = `x-test-fake-${process.pid}`;
  let src;
  let archive;
  let archiveSha;

  beforeEach(() => {
    // A stand-in release archive: <root>/llama-server + two libs, tarred.
    src = mkdtempSync(join(tmpdir(), "llama-stage-"));
    const root = join(src, "llama-fake");
    mkdirSync(root);
    writeFileSync(join(root, "llama-server"), "#!/bin/sh\necho fake\n");
    writeFileSync(join(root, "libone.so"), "one");
    writeFileSync(join(root, "libtwo.so"), "two");
    writeFileSync(join(root, "libunused.so"), "never staged");
    archive = join(src, "fake.tar.gz");
    execFileSync("tar", ["-czf", archive, "-C", src, "llama-fake"]);
    archiveSha = sha256OfFile(archive);
    ASSET_MAP[triple] = {
      assetName: `fake-${process.pid}.tar.gz`,
      sha256: archiveSha,
      archiveRoot: "llama-fake",
      binaryName: "llama-server",
      libs: ["libone.so", "libtwo.so"],
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
    rmSync(join(LIB_STAGE_ROOT, triple), { recursive: true, force: true });
    rmSync(join(LIB_STAGE_ROOT, ".cache", ASSET_MAP[triple].assetName), { force: true });
    rmSync(binaryOutPath(triple), { force: true });
    delete ASSET_MAP[triple];
    rmSync(src, { recursive: true, force: true });
  });

  /** Serve `body` for the next https.get (then a 302 hop first when `redirect`). */
  function stubDownload(body, { redirect = false } = {}) {
    let calls = 0;
    vi.spyOn(https, "get").mockImplementation((_url, _opts, onResponse) => {
      calls += 1;
      const hop = redirect && calls === 1;
      const resp = Readable.from(hop ? [] : [body]);
      resp.statusCode = hop ? 302 : 200;
      resp.headers = hop ? { location: "https://cdn.example/fake" } : {};
      setImmediate(() => onResponse(resp));
      return { on: () => undefined };
    });
  }

  it("downloads, verifies, and stages the binary plus exactly the declared libs", async () => {
    stubDownload(readFileSync(archive), { redirect: true });
    expect(needsStage(triple)).toBe(true);
    await stageTriple(triple);
    const stageDir = join(LIB_STAGE_ROOT, triple);
    expect(readFileSync(binaryOutPath(triple), "utf8")).toContain("echo fake");
    expect(readdirSync(stageDir).sort()).toEqual([".staged.json", "libone.so", "libtwo.so"]);
    const marker = JSON.parse(readFileSync(join(stageDir, ".staged.json"), "utf8"));
    expect(marker.sha256).toBe(archiveSha);
    expect(needsStage(triple)).toBe(false);
    expect(https.get).toHaveBeenCalledTimes(2);
  });

  it("re-stages from a verified cache without touching the network", async () => {
    stubDownload(readFileSync(archive));
    await stageTriple(triple);
    await stageTriple(triple, { force: true });
    expect(https.get).toHaveBeenCalledTimes(1);
    expect(existsSync(binaryOutPath(triple))).toBe(true);
  });

  it("is a no-op when already staged and fresh", async () => {
    stubDownload(readFileSync(archive));
    await stageTriple(triple);
    await stageTriple(triple);
    expect(https.get).toHaveBeenCalledTimes(1);
  });

  it("refuses an archive whose sha256 does not match the pin and deletes it", async () => {
    stubDownload(Buffer.from("tampered bytes"));
    await expect(stageTriple(triple)).rejects.toThrow(/sha256 mismatch/);
    expect(existsSync(join(LIB_STAGE_ROOT, ".cache", ASSET_MAP[triple].assetName))).toBe(false);
    expect(existsSync(binaryOutPath(triple))).toBe(false);
  });

  it("surfaces a non-200 download as an error", async () => {
    vi.spyOn(https, "get").mockImplementation((_url, _opts, onResponse) => {
      const resp = Readable.from([]);
      resp.statusCode = 404;
      resp.headers = {};
      setImmediate(() => onResponse(resp));
      return { on: () => undefined };
    });
    await expect(stageTriple(triple)).rejects.toThrow(/HTTP 404/);
  });
});

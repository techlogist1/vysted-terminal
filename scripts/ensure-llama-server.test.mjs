// @vitest-environment node
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  ASSET_MAP,
  binaryOutPath,
  needsStage,
  resolveAsset,
  sha256OfFile,
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

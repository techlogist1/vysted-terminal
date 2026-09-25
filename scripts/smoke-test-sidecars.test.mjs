// @vitest-environment node
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

const { _httpGetOk, _STATE_DIR, _scopedOrphanPreflight, _shouldProbeExchanges } =
  await import("./smoke-test-sidecars.mjs");

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Spawn-then-wait-for-exit so the returned PID is real but guaranteed dead. */
function deadPid() {
  return new Promise((resolveP) => {
    const child = spawn(process.execPath, ["-e", ""]);
    child.on("exit", () => resolveP(child.pid));
  });
}

describe("_httpGetOk (R15-CODE-PLATFORM-062)", () => {
  it("a 404 and an offline host (ENOTFOUND-shaped failure) yield different shapes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: false, status: 404 })
        .mockRejectedValueOnce(
          Object.assign(new Error("fetch failed"), { cause: { code: "ENOTFOUND" } }),
        ),
    );

    const notFound = await _httpGetOk("https://example.invalid/a");
    expect(notFound).toEqual({ ok: false, status: 404, error: null });

    const offline = await _httpGetOk("https://example.invalid/b");
    expect(offline.ok).toBe(false);
    expect(offline.status).toBeNull();
    expect(offline.error).toMatch(/fetch failed/);

    // The two failures must be distinguishable, never the same collapsed shape.
    expect(notFound).not.toEqual(offline);
  });

  it("a 200 reports ok:true with its status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: true, status: 200 }));
    await expect(_httpGetOk("https://example.invalid/c")).resolves.toEqual({
      ok: true,
      status: 200,
      error: null,
    });
  });
});

describe("_scopedOrphanPreflight (R15-LIFECYCLE-039)", () => {
  it("two ledgers coexist; pre-flight reaps only the dead-owner one and leaves the live-owner ledger alone", async () => {
    mkdirSync(_STATE_DIR, { recursive: true });
    const dead = await deadPid();
    const live = process.pid; // this test process — guaranteed alive throughout
    const deadFile = join(_STATE_DIR, `live-children-${dead}.json`);
    const liveFile = join(_STATE_DIR, `live-children-${live}.json`);
    const liveContents = JSON.stringify([]);
    writeFileSync(deadFile, JSON.stringify([]));
    writeFileSync(liveFile, liveContents);

    try {
      expect(existsSync(deadFile)).toBe(true);
      expect(existsSync(liveFile)).toBe(true);

      await _scopedOrphanPreflight();

      // The dead run's ledger is resolved and removed.
      expect(existsSync(deadFile)).toBe(false);
      // A concurrently-running smoke-test's ledger is never inspected or touched.
      expect(existsSync(liveFile)).toBe(true);
      expect(readFileSync(liveFile, "utf8")).toBe(liveContents);
    } finally {
      rmSync(deadFile, { force: true });
      rmSync(liveFile, { force: true });
    }
  });
});

describe("_shouldProbeExchanges (R15-RELEASE-008)", () => {
  it("default run schedules no exchange probe", () => {
    expect(_shouldProbeExchanges(["node", "scripts/smoke-test-sidecars.mjs"])).toBe(false);
  });

  it("--require-network (pnpm probe:exchanges) schedules the exchange probes", () => {
    expect(
      _shouldProbeExchanges(["node", "scripts/smoke-test-sidecars.mjs", "--require-network"]),
    ).toBe(true);
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";

import type { DownloadState } from "../../types/data";
import {
  downloadPercent,
  formatBytes,
  isActiveDownload,
  LocalModelsError,
  timeLeft,
} from "./local-models";

describe("formatBytes", () => {
  it("renders gigabytes to one decimal once at least 1 GB", () => {
    expect(formatBytes(1.5 * 1024 ** 3)).toBe("1.5 GB");
  });

  it("renders sub-gigabyte sizes rounded to the nearest MB", () => {
    expect(formatBytes(820 * 1024 ** 2)).toBe("820 MB");
  });

  it("never renders a negative MB count", () => {
    expect(formatBytes(0)).toBe("0 MB");
  });
});

describe("downloadPercent", () => {
  it("is 0 when the total size isn't known yet", () => {
    expect(downloadPercent({ totalBytes: 0, receivedBytes: 0 } as DownloadState)).toBe(0);
  });

  it("floors the ratio of received to total", () => {
    expect(downloadPercent({ totalBytes: 200, receivedBytes: 50 } as DownloadState)).toBe(25);
  });

  it("caps at 100 even if receivedBytes overshoots totalBytes", () => {
    expect(downloadPercent({ totalBytes: 100, receivedBytes: 150 } as DownloadState)).toBe(100);
  });
});

describe("timeLeft", () => {
  it("is null when the speed is unknown", () => {
    expect(
      timeLeft({ bytesPerSec: null, totalBytes: 100, receivedBytes: 0 } as DownloadState),
    ).toBeNull();
  });

  it("is null when the speed is zero or negative", () => {
    expect(
      timeLeft({ bytesPerSec: 0, totalBytes: 100, receivedBytes: 0 } as DownloadState),
    ).toBeNull();
  });

  it("reads as under a minute for a near-finished download", () => {
    expect(
      timeLeft({ bytesPerSec: 1000, totalBytes: 1000, receivedBytes: 990 } as DownloadState),
    ).toBe("less than a minute left");
  });

  it("reads in minutes under an hour", () => {
    expect(timeLeft({ bytesPerSec: 1, totalBytes: 600, receivedBytes: 0 } as DownloadState)).toBe(
      "about 10 min left",
    );
  });

  it("reads in hours once the remaining time is an hour or more", () => {
    expect(timeLeft({ bytesPerSec: 1, totalBytes: 7200, receivedBytes: 0 } as DownloadState)).toBe(
      "about 2 h left",
    );
  });
});

describe("isActiveDownload", () => {
  it.each(["queued", "downloading", "verifying"] as const)("%s counts as active", (state) => {
    expect(isActiveDownload({ state } as DownloadState)).toBe(true);
  });

  it.each(["done", "paused", "cancelled", "failed"] as const)(
    "%s does not count as active",
    (state) => {
      expect(isActiveDownload({ state } as DownloadState)).toBe(false);
    },
  );
});

describe("localModelsApi (raw sidecar-client wiring)", () => {
  afterEach(() => {
    vi.doUnmock("@/lib/sidecar-client");
    vi.resetModules();
  });

  it("cancel forwards the discard flag as a string param", async () => {
    vi.resetModules();
    const sidecarRequest = vi.fn(async () => ({ id: "qwen" }));
    vi.doMock("@/lib/sidecar-client", async (importOriginal) => ({
      ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
      sidecarRequest,
    }));
    const { localModelsApi } = await import("./local-models");
    await localModelsApi.cancel("qwen", true);
    expect(sidecarRequest).toHaveBeenCalledWith("POST", "/local-models/qwen/cancel", {
      params: { discard: "true" },
    });
    await localModelsApi.cancel("qwen");
    expect(sidecarRequest).toHaveBeenCalledWith("POST", "/local-models/qwen/cancel", {
      params: { discard: undefined },
    });
  });

  it("remove issues a DELETE against the model's path", async () => {
    vi.resetModules();
    const sidecarRequest = vi.fn(async () => undefined);
    vi.doMock("@/lib/sidecar-client", async (importOriginal) => ({
      ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
      sidecarRequest,
    }));
    const { localModelsApi } = await import("./local-models");
    await localModelsApi.remove("qwen");
    expect(sidecarRequest).toHaveBeenCalledWith("DELETE", "/local-models/qwen");
  });

  function mockDownloadTransport({
    status,
    jsonBody,
    jsonThrows = false,
  }: {
    status: number;
    jsonBody?: unknown;
    jsonThrows?: boolean;
  }) {
    vi.resetModules();
    vi.doMock("@/lib/sidecar-client", async (importOriginal) => ({
      ...(await importOriginal<typeof import("@/lib/sidecar-client")>()),
      getSidecarBaseUrl: async () => "http://127.0.0.1:9",
      sidecarRequestInit: async () => ({ method: "POST" }),
      sidecarFetch: async () => ({
        ok: status >= 200 && status < 300,
        status,
        json: jsonThrows ? async () => Promise.reject(new Error("bad json")) : async () => jsonBody,
      }),
    }));
  }

  it("returns the parsed body on a successful download response", async () => {
    mockDownloadTransport({ status: 200, jsonBody: { id: "qwen", state: "downloading" } });
    const { localModelsApi } = await import("./local-models");
    const result = await localModelsApi.download("qwen");
    expect(result).toEqual({ id: "qwen", state: "downloading" });
  });

  it("tolerates an unparseable body on a successful response", async () => {
    mockDownloadTransport({ status: 200, jsonThrows: true });
    const { localModelsApi } = await import("./local-models");
    const result = await localModelsApi.download("qwen");
    expect(result).toBeNull();
  });

  it("surfaces a non-409 failure as a plain SidecarError", async () => {
    mockDownloadTransport({ status: 503, jsonBody: { detail: "sidecar overloaded" } });
    const { localModelsApi } = await import("./local-models");
    const { SidecarError } = await import("@/lib/sidecar-client");
    const err = await localModelsApi.download("qwen").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(SidecarError);
    expect((err as InstanceType<typeof SidecarError>).status).toBe(503);
    expect((err as Error).message).toBe("sidecar overloaded");
  });
});

describe("LocalModelsError", () => {
  it("defaults the byte counts to null for a non-disk error", () => {
    const err = new LocalModelsError("other", "boom");
    expect(err.neededBytes).toBeNull();
    expect(err.freeBytes).toBeNull();
    expect(err.name).toBe("LocalModelsError");
  });
});

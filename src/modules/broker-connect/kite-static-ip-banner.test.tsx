import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import { KiteStaticIpBanner, type KiteStaticIpStatus } from "./kite-static-ip-banner";

function status(overrides: Partial<KiteStaticIpStatus> = {}): KiteStaticIpStatus {
  return {
    detectedIp: "203.0.113.5",
    configuredIp: "203.0.113.5",
    matches: true,
    message: "ok",
    detectedAt: 1,
    ...overrides,
  };
}

describe("KiteStaticIpBanner", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders a loading state before the first fetch resolves", async () => {
    const fetcher = vi.fn(() => new Promise<KiteStaticIpStatus>(() => {}));
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
      />,
    );
    const banner = await screen.findByTestId("kite-static-ip-banner");
    expect(banner.getAttribute("data-variant")).toBe("loading");
  });

  it("renders the ok variant when matches=true", async () => {
    const fetcher = vi.fn(async () => status({ matches: true }));
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
      />,
    );
    await waitFor(() => {
      const banner = screen.getByTestId("kite-static-ip-banner");
      expect(banner.getAttribute("data-variant")).toBe("ok");
    });
    expect(screen.getByText(/Kite static IP matches/)).toBeInTheDocument();
  });

  it("renders the mismatch variant when matches=false", async () => {
    const fetcher = vi.fn(async () =>
      status({
        matches: false,
        detectedIp: "198.51.100.42",
        message: "Detected public IP differs from the configured static IP.",
      }),
    );
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
      />,
    );
    await waitFor(() => {
      const banner = screen.getByTestId("kite-static-ip-banner");
      expect(banner.getAttribute("data-variant")).toBe("mismatch");
    });
    expect(screen.getByText(/Kite static IP mismatch/)).toBeInTheDocument();
    expect(screen.getByText(/Detected public IP differs/)).toBeInTheDocument();
  });

  it("renders the error variant when fetcher rejects", async () => {
    const fetcher = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
      />,
    );
    await waitFor(() => {
      const banner = screen.getByTestId("kite-static-ip-banner");
      expect(banner.getAttribute("data-variant")).toBe("error");
    });
    expect(screen.getByText(/ECONNREFUSED/)).toBeInTheDocument();
  });

  it("calls fetcher with the configured static IP in the query string", async () => {
    const fetcher = vi.fn(async (url: string) => {
      void url;
      return status();
    });
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
      />,
    );
    await waitFor(() => {
      expect(fetcher).toHaveBeenCalled();
    });
    expect(fetcher.mock.calls[0][0]).toContain("/safety/static-ip-status");
    expect(fetcher.mock.calls[0][0]).toContain("configured=203.0.113.5");
  });

  it("does not append the configured query param when null", async () => {
    const fetcher = vi.fn(async (url: string) => {
      void url;
      return status({ configuredIp: null });
    });
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp={null}
        fetcher={fetcher}
      />,
    );
    await waitFor(() => {
      expect(fetcher).toHaveBeenCalled();
    });
    expect(fetcher.mock.calls[0][0]).not.toContain("configured=");
  });

  it("invokes onStatus when a result lands", async () => {
    const onStatus = vi.fn();
    const fetcher = vi.fn(async (url: string) => {
      void url;
      return status();
    });
    render(
      <KiteStaticIpBanner
        sidecarBaseUrl="http://127.0.0.1:0"
        configuredIp="203.0.113.5"
        fetcher={fetcher}
        onStatus={onStatus}
      />,
    );
    await waitFor(() => {
      expect(onStatus).toHaveBeenCalled();
    });
    expect(onStatus.mock.calls[0][0].matches).toBe(true);
  });
});

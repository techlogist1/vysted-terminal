import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceDialog } from "./WorkspaceDialog";
import { useWorkspaceDialog } from "./workspace-dialog-store";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

const written: { filename: string; text: string }[] = [];
vi.mock("@/lib/export-artifact", () => ({
  saveTextArtifact: vi.fn(async (subdir: string, filename: string, text: string) => {
    written.push({ filename, text });
    return { path: `/data/exports/${subdir}/${filename}`, fellBack: false };
  }),
}));

/** An in-memory sidecar `/workspace` store: list, get, save. */
function stubWorkspaceStore(saved: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = decodeURIComponent(new URL(url).pathname);
      const ok = (body: unknown) =>
        ({ ok: true, status: 200, json: async () => body }) as unknown as Response;
      if (init?.method === "POST") {
        const { name, workspace } = JSON.parse(String(init.body)) as {
          name: string;
          workspace: unknown;
        };
        saved[name] = workspace;
        return ok({});
      }
      if (path === "/workspace") {
        return ok(Object.keys(saved).sort());
      }
      return ok(saved[path.slice("/workspace/".length)]);
    }),
  );
}

describe("WorkspaceDialog export / import (R15-UI-070)", () => {
  beforeEach(() => {
    written.length = 0;
    useWorkspaceDialog.setState({ mode: "load" });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    useWorkspaceDialog.setState({ mode: null });
  });

  it("exports a saved workspace to a .vysted-workspace file and imports it back under a chosen name", async () => {
    const swing = { name: "swing", layout: { grid: {}, panels: {} }, enabledModules: {} };
    const saved: Record<string, unknown> = { swing };
    stubWorkspaceStore(saved);
    render(<WorkspaceDialog />);

    fireEvent.click(await screen.findByRole("button", { name: "Export workspace swing" }));
    await screen.findByText("Exported to /data/exports/workspaces/swing.vysted-workspace");
    expect(written).toHaveLength(1);
    expect(JSON.parse(written[0].text)).toEqual(swing);

    const file = new File([written[0].text], written[0].filename, { type: "application/json" });
    fireEvent.change(screen.getByLabelText("Import workspace file"), { target: { files: [file] } });
    const nameField = (await screen.findByLabelText("Imported workspace name")) as HTMLInputElement;
    expect(nameField.value).toBe("swing");
    fireEvent.change(nameField, { target: { value: "swing copy" } });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    await screen.findByText('Imported "swing copy".');
    expect(saved["swing copy"]).toEqual({ ...swing, name: "swing copy" });
    expect(screen.getByRole("button", { name: "swing copy" })).toBeInTheDocument();
  });
});

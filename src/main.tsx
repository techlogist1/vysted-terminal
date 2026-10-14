import React from "react";
import ReactDOM from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";

// JetBrains Mono — the SINGLE family across every text role (VYSTED_DESIGN.md).
// Hierarchy is built from size + weight alone (400 / 500 / 700); there is no
// second face anywhere in the chrome. Self-hosted via @fontsource (the next/font
// loader this replaces did the same Google-fonts self-hosting at build time);
// --font-jetbrains-mono is defined in globals.css for the token slots and the
// canvas components that read it via getComputedStyle.
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/700.css";
import "./app/globals.css";

import Page from "./app/page";

/** A release build has no console: React render errors (a panel's, caught by
 *  its boundary, or an uncaught one) also go to the diagnostics log
 *  (R15-LIFECYCLE-023). Outside the Tauri shell the invoke fails: console only. */
function logRenderError(kind: "caught" | "uncaught") {
  return (error: unknown, info: { componentStack?: string }) => {
    console.error(error);
    const text = error instanceof Error ? (error.stack ?? error.message) : String(error);
    void invoke("diag_log_line", {
      line: `[renderer] ${kind} render error: ${text}${info.componentStack ?? ""}`,
    }).catch(() => undefined);
  };
}

ReactDOM.createRoot(document.getElementById("root")!, {
  onCaughtError: logRenderError("caught"),
  onUncaughtError: logRenderError("uncaught"),
}).render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>,
);

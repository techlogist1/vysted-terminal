import React from "react";
import ReactDOM from "react-dom/client";

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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>,
);

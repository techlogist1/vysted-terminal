import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Tauri serves the frontend as static files — there is no Node server at runtime.
  output: "export",
  // The Next.js image optimizer requires a server; static export cannot use it.
  images: { unoptimized: true },
};

export default nextConfig;

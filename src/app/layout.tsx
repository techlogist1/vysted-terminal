import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vysted Terminal",
  description: "Open-source AI-native finance terminal.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}

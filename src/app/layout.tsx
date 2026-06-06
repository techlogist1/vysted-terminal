import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

// JetBrains Mono — the SINGLE family across every text role (VYSTED_DESIGN.md).
// Hierarchy is built from size + weight alone (400 / 500 / 700); there is no
// second face anywhere in the chrome. Exposed as --font-jetbrains-mono, which
// the --font-sans / --font-serif / --font-mono token slots all reference.
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vysted",
  description: "The AI-native, extensible finance workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

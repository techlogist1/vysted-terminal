import type { Metadata } from "next";
import { Hanken_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Hanken Grotesk — a precise, modern grotesque display face for the wordmark +
// headings: clean and confident at display sizes, the cold-instrument voice
// (supersedes the warm Fraunces serif). Exposed as --font-display, which the
// `--font-serif` token slot now references.
const display = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["500", "600", "700"],
});

// JetBrains Mono — the data/terminal workhorse: every price, label, and chrome
// element. Kept from the prior system; ideal for a finance instrument.
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vysted Terminal",
  description: "The AI-native, extensible finance workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${display.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

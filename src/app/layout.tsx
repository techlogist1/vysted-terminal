import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";

// Inter — the Geist-class UI sans for the wordmark, headings, and dense chrome:
// tall x-height, tabular figures, the reference data-terminal face. Exposed as
// --font-display, which the `--font-serif` token slot now references.
const display = Inter({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

// Geist Mono — the data/terminal workhorse: every price, label, and chrome
// element. Contemporary, compressed, and pairs with Inter's geometry.
const jetbrainsMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vysted",
  description: "The AI-native, extensible finance workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`dark ${display.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

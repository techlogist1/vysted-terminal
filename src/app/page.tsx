import { CommandPalette } from "@/components/CommandPalette";

export default function Page() {
  return (
    <>
      <CommandPalette />
      <main className="bg-charcoal-950 flex min-h-screen items-center justify-center p-8">
        <article
          className="border-charcoal-700 bg-charcoal-900 w-full max-w-2xl rounded-[var(--radius-panel)] border p-10 shadow-xl"
          aria-label="Welcome panel"
        >
          {/* Eyebrow */}
          <p className="mb-3 font-mono text-xs tracking-widest text-amber-500 uppercase">
            Phase 0 · Scaffold
          </p>

          {/* Primary heading — serif, establishes editorial hierarchy */}
          <h1 className="text-charcoal-100 mb-2 font-serif text-4xl leading-tight font-semibold">
            Welcome to Vysted Terminal
          </h1>

          {/* Sub-heading — sage counterpoint to amber accent */}
          <h2 className="text-sage-400 mb-6 font-serif text-lg font-normal">
            Open-source AI-native finance terminal
          </h2>

          {/* Divider */}
          <div className="bg-charcoal-700 mb-6 h-px" aria-hidden="true" />

          {/* Body copy — monospace, establishes data-display voice */}
          <p className="text-charcoal-200 mb-4 font-mono text-sm leading-relaxed">
            This is a placeholder panel for Phase 0. The terminal scaffold is live — the design
            language, color palette, and typography are in place. Real panels, data feeds, and
            commands arrive in Phase 1.
          </p>

          {/* Mock data row — demonstrates the amber/positive/negative signal colors */}
          <div className="border-charcoal-700 bg-charcoal-850 mb-6 rounded-[var(--radius-control)] border px-4 py-3">
            <p className="text-charcoal-400 mb-2 font-mono text-xs">
              {/* Mock data — placeholder only */}
              mock_data · placeholder
            </p>
            <div className="grid grid-cols-3 gap-4 font-mono text-sm">
              <div>
                <span className="text-charcoal-400 block text-xs">TICKER</span>
                <span className="text-charcoal-100">VYSD</span>
              </div>
              <div>
                <span className="text-charcoal-400 block text-xs">PRICE</span>
                <span className="text-amber-400">142.08</span>
              </div>
              <div>
                <span className="text-charcoal-400 block text-xs">CHANGE</span>
                <span className="text-positive">+2.34%</span>
              </div>
            </div>
          </div>

          {/* Palette swatch row — visual proof of the color system */}
          <div className="mb-6 flex gap-2" aria-label="Color palette swatches">
            <div
              className="bg-charcoal-800 h-6 w-6 rounded-sm"
              title="charcoal-800"
              aria-label="charcoal-800 swatch"
            />
            <div
              className="bg-charcoal-700 h-6 w-6 rounded-sm"
              title="charcoal-700"
              aria-label="charcoal-700 swatch"
            />
            <div
              className="h-6 w-6 rounded-sm bg-amber-400"
              title="amber-400"
              aria-label="amber-400 swatch"
            />
            <div
              className="h-6 w-6 rounded-sm bg-amber-500"
              title="amber-500"
              aria-label="amber-500 swatch"
            />
            <div
              className="bg-sage-400 h-6 w-6 rounded-sm"
              title="sage-400"
              aria-label="sage-400 swatch"
            />
            <div
              className="bg-sage-500 h-6 w-6 rounded-sm"
              title="sage-500"
              aria-label="sage-500 swatch"
            />
          </div>

          {/* Cmd+K hint */}
          <div className="text-charcoal-400 flex items-center gap-2 font-mono text-xs">
            <kbd className="border-charcoal-700 bg-charcoal-800 text-charcoal-200 rounded border px-1.5 py-0.5">
              ⌘K
            </kbd>
            <span>Open command palette</span>
          </div>
        </article>
      </main>
    </>
  );
}

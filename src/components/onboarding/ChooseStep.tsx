import type { ReactNode } from "react";
import { Check, Cpu, KeyRound, Compass } from "lucide-react";

import { cn } from "@/lib/utils";
import { useLocalModelsStore } from "@/store/local-models";

export type ThinkPath = "local" | "key" | "skip";

/** "How should Vysted think?" — the three paths, one click each. */
export function ChooseStep({ onPick }: { onPick: (path: ThinkPath) => void }) {
  // A machine too small for a good on-computer model is steered to a key.
  const tier = useLocalModelsStore((s) => s.catalog?.tier);
  const localRecommended = tier !== "under-8gb";

  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="bg-charcoal-400 size-2 rounded-none" />
          <span className="hud-label leading-none">Welcome</span>
        </div>
        <h2 className="text-lume text-overview">How should Vysted think?</h2>
        <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
          Vysted has an assistant you can ask about any company or market. Pick how it should think
          — you can change this any time in Settings.
        </p>
      </div>

      <div className="border-positive/25 bg-positive/5 flex items-start gap-3 rounded-none border px-4 py-3">
        <Check className="text-positive mt-1 size-4 shrink-0" aria-hidden="true" />
        <p className="text-charcoal-200 text-caption font-mono leading-relaxed">
          Prices, charts and news already work — no account needed. Your notes and portfolio stay on
          this computer; market data and web searches go to public providers.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Choice
          icon={<Cpu className="text-charcoal-300 size-4" aria-hidden="true" />}
          title="On this computer"
          tag={localRecommended ? "Recommended" : undefined}
          body="Download a model once and it runs here. No key, no cost. Answers are slower than online models."
          onClick={() => onPick("local")}
          primary={localRecommended}
        />
        <Choice
          icon={<KeyRound className="text-charcoal-300 size-4" aria-hidden="true" />}
          title="My own API key"
          tag={localRecommended ? undefined : "Recommended"}
          body="Paste a key from OpenRouter, OpenAI, Anthropic or another provider. Fastest answers; the provider charges you per use — usually cents per question."
          onClick={() => onPick("key")}
          primary={!localRecommended}
        />
        <Choice
          icon={<Compass className="text-charcoal-300 size-4" aria-hidden="true" />}
          title="Skip for now"
          body="Look around first. You can turn the assistant on later from Settings."
          onClick={() => onPick("skip")}
        />
      </div>
    </div>
  );
}

function Choice({
  icon,
  title,
  tag,
  body,
  onClick,
  primary = false,
}: {
  icon: ReactNode;
  title: string;
  tag?: string;
  body: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col gap-1 rounded-none border px-4 py-3 text-left transition-colors",
        primary
          ? "border-charcoal-500/50 bg-charcoal-700/[0.06] hover:border-charcoal-400/60"
          : "border-charcoal-700 bg-charcoal-900 hover:border-charcoal-500/40",
      )}
    >
      <span className="flex items-center gap-2">
        {icon}
        <span className="text-charcoal-100 text-body font-mono font-medium">{title}</span>
        {tag && (
          <span className="text-micro ml-auto border border-amber-500/40 px-2 py-0.5 font-mono text-amber-300">
            {tag}
          </span>
        )}
      </span>
      <span className="text-charcoal-400 text-caption font-mono leading-relaxed">{body}</span>
    </button>
  );
}

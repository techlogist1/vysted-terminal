import { useState } from "react";
import { BarChart3, Bot, Command, List, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadPercent, isActiveDownload } from "@/lib/local-models";
import { formatBinding, useKeybindingsStore } from "@/store/keybindings";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore } from "@/store/local-models";
import { useOnboardingStore } from "@/store/onboarding";
import type { ThinkPath } from "./ChooseStep";
import { EXAMPLE_QUESTION, askAgent, showChartExample } from "./example";
import { LinkButton } from "./shared";

/** A short tour of the four main surfaces, ending in one example that works on the chosen path. */
export function TourStep({
  path,
  localModelId,
  onFinish,
}: {
  path: ThinkPath;
  localModelId: string | null;
  onFinish: () => void;
}) {
  const palette = formatBinding(useKeybindingsStore((s) => s.bindingFor("palette.open")));
  const cards = [
    {
      icon: <Bot className="text-charcoal-300 size-5" aria-hidden="true" />,
      title: "The assistant",
      body: "On the left. Ask anything in plain words — it looks up prices, news and company numbers, and shows where each figure came from.",
    },
    {
      icon: <BarChart3 className="text-charcoal-300 size-5" aria-hidden="true" />,
      title: "The chart",
      body: "See how a price has moved over a day, a year or longer. Type a company name to switch.",
    },
    {
      icon: <List className="text-charcoal-300 size-5" aria-hidden="true" />,
      title: "The watchlist",
      body: "Keep the companies you follow in one list, with live prices.",
    },
    {
      icon: <Command className="text-charcoal-300 size-5" aria-hidden="true" />,
      title: "Find anything",
      body: `Press ${palette} to open a panel, jump to a company or change a setting.`,
    },
  ];
  const [index, setIndex] = useState(0);
  const last = index === cards.length;

  return (
    <div className="flex flex-col gap-4 px-6 py-6" data-testid="onboarding-tour">
      <div className="flex items-center gap-2">
        <span className="hud-label leading-none">
          {last ? "Try it" : `${index + 1} of ${cards.length}`}
        </span>
        <span className="ml-auto">
          <LinkButton onClick={onFinish}>{last ? "Close" : "Skip the tour"}</LinkButton>
        </span>
      </div>
      {last ? (
        <Example path={path} localModelId={localModelId} onFinish={onFinish} />
      ) : (
        <>
          <div className="flex items-start gap-3">
            {cards[index].icon}
            <div className="flex flex-col gap-1">
              <h2 className="text-charcoal-100 text-section">{cards[index].title}</h2>
              <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
                {cards[index].body}
              </p>
            </div>
          </div>
          <div className="flex items-center justify-between pt-1">
            <div className="flex gap-1" aria-hidden="true">
              {cards.map((c, i) => (
                <span
                  key={c.title}
                  className={i === index ? "size-2 bg-amber-500" : "bg-charcoal-700 size-2"}
                />
              ))}
            </div>
            <Button size="sm" onClick={() => setIndex(index + 1)}>
              Next →
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function Example({
  path,
  localModelId,
  onFinish,
}: {
  path: ThinkPath;
  localModelId: string | null;
  onFinish: () => void;
}) {
  const engine = useLocalEngineStore((s) => s.status);
  const dl = useLocalModelsStore((s) => (localModelId ? s.downloads[localModelId] : undefined));

  if (path === "skip") {
    return (
      <>
        <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
          See how Reliance Industries has done — no setup needed.
        </p>
        <Button
          size="sm"
          className="self-start"
          onClick={() => {
            showChartExample();
            onFinish();
          }}
        >
          <Sparkles aria-hidden="true" /> Show Reliance on the chart
        </Button>
      </>
    );
  }

  const ask = (
    <Button
      size="sm"
      className="self-start"
      onClick={() => {
        askAgent(EXAMPLE_QUESTION);
        onFinish();
      }}
    >
      <Sparkles aria-hidden="true" /> Ask: “{EXAMPLE_QUESTION}”
    </Button>
  );
  if (path === "key" || engine.state === "ready") {
    return (
      <>
        <p className="text-charcoal-300 text-caption font-mono leading-relaxed">
          Ask your first question. The answer appears in the assistant on the left.
        </p>
        {ask}
      </>
    );
  }

  // On this computer, not ready yet: park the question; the strip offers it when ready.
  const waiting =
    dl && isActiveDownload(dl)
      ? `Your model is still downloading (${downloadPercent(dl)}%) — we'll let you know when it's ready.`
      : engine.state === "starting" || engine.state === "crashed"
        ? "Your model is starting — we'll let you know when it's ready."
        : "Your model isn't ready yet. The bar at the top shows what's happening and what to do next — we'll let you know when it's ready.";
  return (
    <>
      <p className="text-charcoal-300 text-caption font-mono leading-relaxed" role="status">
        {waiting}
      </p>
      <p className="text-charcoal-400 text-caption font-mono leading-relaxed">
        Then try: “{EXAMPLE_QUESTION}”
      </p>
      <Button
        size="sm"
        className="self-start"
        onClick={() => {
          useOnboardingStore.getState().setWaitingQuestion(EXAMPLE_QUESTION);
          onFinish();
        }}
      >
        Got it
      </Button>
    </>
  );
}

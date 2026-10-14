import type { ReactNode } from "react";
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export async function openExternal(url: string): Promise<void> {
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(url);
  } catch {
    // Non-Tauri / blocked — the link text still names where to go.
  }
}

export function StepHeader({
  icon,
  title,
  onBack,
}: {
  icon: ReactNode;
  title: string;
  onBack?: () => void;
}) {
  return (
    <div className="flex items-center gap-2">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="text-charcoal-400 hover:text-charcoal-100 rounded-control -ml-1 p-1 transition-colors"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
        </button>
      )}
      {icon}
      <h2 className="text-charcoal-100 text-section">{title}</h2>
    </div>
  );
}

/** A boxed message with its next steps. `tone` picks the edge colour. */
export function Notice({
  tone = "info",
  children,
  actions,
  testId,
}: {
  tone?: "info" | "warn" | "error";
  children: ReactNode;
  actions?: ReactNode;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      role={tone === "info" ? "status" : "alert"}
      className={cn(
        "flex flex-col gap-2 rounded-none border px-4 py-3",
        tone === "info" && "border-charcoal-700 bg-charcoal-900",
        tone === "warn" && "border-caution/30 bg-caution/5",
        tone === "error" && "border-negative/30 bg-negative/5",
      )}
    >
      <div className="flex items-start gap-2">
        {tone !== "info" && (
          <AlertCircle
            className={cn(
              "mt-0.5 size-4 shrink-0",
              tone === "warn" ? "text-caution" : "text-negative",
            )}
            aria-hidden="true"
          />
        )}
        <div className="text-charcoal-200 text-caption font-mono leading-relaxed">{children}</div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Waiting({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="text-charcoal-400 text-caption flex items-center gap-2 py-6 font-mono"
    >
      <Loader2 size={14} className="animate-spin" aria-hidden="true" /> {children}
    </div>
  );
}

/** A quiet text button for secondary next steps. */
export function LinkButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-charcoal-400 hover:text-charcoal-200 text-caption font-mono transition-colors"
    >
      {children}
    </button>
  );
}

/** `navigator.onLine === false` is the one reliable "no internet" signal. */
export function offline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}

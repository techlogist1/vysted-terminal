"use client";

import { useEffect, useRef, useState } from "react";
import type { VariantProps } from "class-variance-authority";

import { Button, buttonVariants } from "@/components/ui/button";

const ARM_MS = 4000;

/**
 * A destructive action's confirmation, inline (R15-UI-018): first click arms
 * the button — it shows "Confirm delete?" for 4s — and a second click within
 * that window calls `onConfirm`. Clicking elsewhere, or letting the window
 * lapse, disarms with no action taken. One shared primitive for every
 * destructive click in the shell so none of them fire on a single stray click.
 */
export function ConfirmButton({
  onConfirm,
  armedLabel = "Confirm delete?",
  children,
  className,
  variant,
  size,
  "aria-label": ariaLabel,
  disabled,
  ...props
}: Omit<React.ComponentProps<"button">, "onClick"> &
  VariantProps<typeof buttonVariants> & {
    onConfirm: () => void;
    armedLabel?: React.ReactNode;
  }) {
  const [armed, setArmed] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  function handleClick() {
    if (!armed) {
      setArmed(true);
      timerRef.current = setTimeout(() => setArmed(false), ARM_MS);
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    setArmed(false);
    onConfirm();
  }

  return (
    <Button
      type="button"
      variant={armed ? "destructive" : variant}
      size={size}
      className={className}
      disabled={disabled}
      aria-label={armed ? "Confirm: this cannot be undone" : ariaLabel}
      onClick={handleClick}
      {...props}
    >
      {armed ? armedLabel : children}
    </Button>
  );
}

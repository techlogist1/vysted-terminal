import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";

// VYSTED_DESIGN.md: rounded-control (4px) on every button; text-body (13px);
// NO shadow; hovers are a neutral luminance step (monochrome — no amber); a 1px
// neutral focus ring, never a halo. Control-size ladder is exactly TWO heights:
// 32px standard (default / sm / lg / icon / icon-sm / icon-lg) and 24px compact
// (xs / icon-xs), so sibling controls never misalign.
// Icon ladder (R8 §2): 14px (size-3.5) inside the 32px tier, 12px (size-3)
// inside the 24px tier; 16px is reserved for explicit primary actions — the
// caller passes `size-4` itself and the :not([class*='size-']) guard yields.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-control text-body font-medium whitespace-nowrap transition-all outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-charcoal-600",
        destructive: "border border-destructive text-destructive hover:bg-destructive/10",
        outline: "border border-border bg-transparent text-foreground hover:bg-secondary",
        secondary: "bg-secondary text-secondary-foreground hover:bg-charcoal-700",
        ghost: "text-muted-foreground hover:bg-secondary hover:text-foreground",
        link: "text-charcoal-200 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-8 px-3 has-[>svg]:px-2",
        xs: "h-6 gap-1 px-2 text-caption has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-2 has-[>svg]:px-2",
        lg: "h-8 px-4 has-[>svg]:px-3",
        icon: "size-8",
        "icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };

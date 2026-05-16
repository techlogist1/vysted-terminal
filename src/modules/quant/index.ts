import type { VystedModule } from "@/lib/module-registry";

import { BondPricerPanel } from "./BondPricerPanel";
import { GreeksDashboard } from "./GreeksDashboard";
import { OptionPricerPanel } from "./OptionPricerPanel";
import { YieldCurvePanel } from "./YieldCurvePanel";

/**
 * Quant module — Phase 6 (Teammate Q v0.6.0) surface.
 *
 * Surfaces four pricing panels — option pricer (BS / Binomial / MC),
 * bond pricer, yield curve bootstrap, Greeks dashboard. All four hit
 * the in-process QuantLib pipeline rooted at ``sidecar/services/quant``
 * via the ``/quant/...`` router. None of the panels touch the BLUEPRINT
 * §6.5 broker-execution surface — they are pure pricing math.
 */
export const quantModule: VystedModule = {
  id: "quant",
  title: "Quant",
  panels: [
    {
      id: "option-pricer",
      title: "Option Pricer",
      icon: "calculator",
      component: "option-pricer-panel",
      singleton: true,
      defaultSize: { w: 9, h: 8 },
    },
    {
      id: "greeks-dashboard",
      title: "Greeks Dashboard",
      icon: "gauge",
      component: "greeks-dashboard-panel",
      singleton: true,
      defaultSize: { w: 9, h: 6 },
    },
    {
      id: "bond-pricer",
      title: "Bond Pricer",
      icon: "calculator",
      component: "bond-pricer-panel",
      singleton: true,
      defaultSize: { w: 9, h: 7 },
    },
    {
      id: "yield-curve",
      title: "Yield Curve",
      icon: "activity",
      component: "yield-curve-panel",
      singleton: true,
      defaultSize: { w: 9, h: 9 },
    },
  ],
  commands: [
    {
      id: "quant.open-option-pricer",
      trigger: "option pricer",
      title: "Open Option Pricer",
      description: "Black-Scholes / Binomial / Monte Carlo option pricing",
      icon: "calculator",
      opensPanel: "option-pricer",
    },
    {
      id: "quant.open-greeks-dashboard",
      trigger: "greeks dashboard",
      title: "Open Greeks Dashboard",
      description: "Black-Scholes Δ/Γ/ν/Θ/ρ for a vanilla option",
      icon: "gauge",
      opensPanel: "greeks-dashboard",
    },
    {
      id: "quant.open-bond-pricer",
      trigger: "bond pricer",
      title: "Open Bond Pricer",
      description: "Fixed-rate bond clean/dirty/duration/convexity",
      icon: "calculator",
      opensPanel: "bond-pricer",
    },
    {
      id: "quant.open-yield-curve",
      trigger: "yield curve",
      title: "Open Yield Curve",
      description: "Bootstrap a zero curve from depo + swap instruments",
      icon: "activity",
      opensPanel: "yield-curve",
    },
  ],
  panelComponents: {
    "option-pricer-panel": OptionPricerPanel,
    "greeks-dashboard-panel": GreeksDashboard,
    "bond-pricer-panel": BondPricerPanel,
    "yield-curve-panel": YieldCurvePanel,
  },
};

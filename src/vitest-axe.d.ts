// R15-UI-071: vitest-axe@0.1.0 augments the legacy global `Vi.Assertion`, which
// Vitest 4 no longer reads; declare its matcher on the `vitest` module instead.
import type { AxeMatchers } from "vitest-axe/matchers";

declare module "vitest" {
  // The type parameter must match Vitest's own `Matchers<T = any>` for the merge.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
  interface Matchers<T = any> {
    toHaveNoViolations: AxeMatchers["toHaveNoViolations"];
  }
}

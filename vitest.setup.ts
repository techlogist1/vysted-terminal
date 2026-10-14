import "@testing-library/jest-dom/vitest";

// jsdom does not implement ResizeObserver or Element.scrollIntoView, both of which
// cmdk (and Radix primitives) call on mount. Stub them so component tests that
// render those primitives don't throw. No-ops are fine — layout is not asserted.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView(): void {};
}

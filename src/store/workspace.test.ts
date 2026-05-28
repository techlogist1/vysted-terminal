import { describe, expect, it } from "vitest";

import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName } from "@/store/workspace";

describe("layout name helpers", () => {
  it("the autosave slot is a reserved name", () => {
    expect(isReservedLayoutName(AUTOSAVE_LAYOUT_NAME)).toBe(true);
  });

  it("user layout names are not reserved", () => {
    expect(isReservedLayoutName("My Cockpit")).toBe(false);
    expect(isReservedLayoutName("default")).toBe(false);
    expect(isReservedLayoutName("trading-2026")).toBe(false);
  });

  it("treats any double-underscore-prefixed name as reserved/internal", () => {
    expect(isReservedLayoutName("__last_session__")).toBe(true);
    expect(isReservedLayoutName("__anything")).toBe(true);
  });
});

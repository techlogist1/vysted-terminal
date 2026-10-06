# UI-5 — fitLayoutTemplate at 1920x1080 / 1280x800 / 1024x768 (final-adv-maintainer, d38b5d1a)

Headless Chrome seam not attempted to completion: `fitLayoutTemplate` is reachable in the built app only through the agent's `arrange_layout` host action (src/lib/host-actions.ts:1670), so a counted run needs the onboarding flow + a live model turn inside the seam page plus a proven Fetch-domain Origin/CORS rewrite. Not counted as a pass.

Supporting evidence only (logic, scratch jsdom, not counted; UI-5/fit-logic.json): with the dockview width equal to the viewport width, research-cockpit and macro-scan apply unchanged at 1920 and 1280 and downgrade at 1024 (essentials-research, single-focus) against the thresholds RESEARCH_COCKPIT_MIN_WIDTH 1180 / MACRO_SCAN_MIN_WIDTH 1080 (src/lib/layout-templates.ts:329-334). The open question for the rig is the real dockview width at 1280x800 with the agent dock open (it can fall below 1180, which would downgrade research-cockpit at 1280) and whether the downgraded layouts render with populated panels.

Entry added to NEEDS_GUI.md.

VERDICT UI-5: needs_gui

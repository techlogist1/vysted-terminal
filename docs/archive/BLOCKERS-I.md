# BLOCKERS-I.md — Teammate I (India brokers)

## Open items

### Screenshot deliverable deferred to integration

The brief calls for two populated screenshots saved under
`docs/screenshots/v0.5.0/teammate-i/`:

1. `BrokerConnectPanel` with Dhan + Angel One + Kite connected in paper
   mode (both 1920×1080 and 2560×1440).
2. The Kite static-IP banner in the mismatch state, mounted inside the
   broker-connect panel.

Both require Teammate S's `BrokerConnectPanel.tsx`, which lives in their
`agent-S` worktree and is not present on `origin/main` at the time Teammate
I's branch was pushed. The worktree builds cleanly without the panel
(typecheck + lint + vitest all green), but there is no UI surface to
mount the banner inside.

**Suggested integration step (lead, at merge time):**

1. Merge Teammate S's `agent-S` branch first so `BrokerConnectPanel.tsx`
   exists.
2. Merge Teammate I's `worktree-agent-ab5a99f08d8aa3da9` branch on top.
3. Verify the panel mounts the `<KiteStaticIpBanner />` component from
   `src/modules/broker-connect/kite-static-ip-banner.tsx`.
4. Bring up `pnpm dev`, connect all three India brokers in paper mode,
   and capture the screenshots at both resolutions.
5. For the mismatch screenshot, temporarily patch
   `services.static_ip_detector.detect_public_ip` to return a fake IP
   that does not match `203.0.113.5` (or whatever the demo configured IP
   is) — this avoids the need to spoof the user's actual public IP.

The banner component is unit-tested at the variant level (loading, ok,
mismatch, error) in
`src/modules/broker-connect/kite-static-ip-banner.test.tsx` so its
rendering behaviour is verified independently of the panel.

## Closed items

None.

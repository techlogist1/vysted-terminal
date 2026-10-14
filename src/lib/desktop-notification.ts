/**
 * Desktop-notification bridge — drains workflow notification intents
 * into the OS notification API.
 *
 * Sidecar workflow nodes (`action.notify_desktop` in
 * `services/workflow_nodes/builtin.py`) emit a `desktop-notification`
 * intent on the SSE stream. `useWorkflowStore.appendEvent` captures the
 * intent into `pendingNotifications`; this bridge subscribes to that
 * slice, calls `@tauri-apps/plugin-notification`'s `sendNotification`,
 * and drains the queue.
 *
 * The bridge unblocks BLUEPRINT §10 UC3 (Earnings Playbook) and UC5
 * (Macro Thesis Watcher) — both rely on workflow steps triggering OS
 * notifications.
 *
 * Permission handling: the plugin asks the OS for permission lazily on
 * first send. On platforms where the user denies, `sendNotification`
 * silently no-ops — we don't block the workflow run on permission
 * decisions.
 *
 * Outside Tauri (standalone `pnpm dev` for visual capture), the bridge
 * is a safe no-op: the Tauri plugin import would throw, so we guard on
 * `__TAURI_INTERNALS__` and skip activation when running in a regular
 * browser.
 */

import { useEffect } from "react";

import {
  selectPendingNotifications,
  useWorkflowStore,
  type DesktopNotificationIntent,
} from "@/store/workflow";

/** True when running inside the Tauri webview (so the plugin import resolves). */
function _isInTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Lazily-imported notification module — kept out of the bundle's
 * top-level so the `pnpm dev` standalone path does not blow up trying
 * to resolve a Tauri-only module.
 */
async function _sendOne(intent: DesktopNotificationIntent): Promise<void> {
  if (!_isInTauri()) return;
  try {
    const { sendNotification, isPermissionGranted, requestPermission } =
      await import("@tauri-apps/plugin-notification");
    let granted = await isPermissionGranted();
    if (!granted) {
      const decision = await requestPermission();
      granted = decision === "granted";
    }
    if (!granted) return;
    sendNotification({ title: intent.title, body: intent.message });
  } catch {
    // Plugin not registered, OS API unavailable, etc. — workflow runs
    // are higher priority than notification UX; never surface this as
    // a workflow failure.
  }
}

/**
 * React hook — wires the bridge for the lifetime of the host component.
 *
 * Mount once near the app root (e.g. in `src/app/page.tsx::Page`). The
 * subscription pulls every newly-captured intent off the store, sends
 * the notification. Intents are taken (returned + cleared) BEFORE the send,
 * so one appended while a send is awaited stays pending for the next pass,
 * and re-mounts or store-resets do not re-fire already-sent intents.
 */
export function useDesktopNotificationBridge(): void {
  useEffect(() => {
    let active = true;
    // Serialize flushes: the bridge is re-entrant (mount flush + every store
    // subscription fire). `isFlushing` guards re-entry; the in-flight pass
    // keeps taking until the queue is empty, so an intent appended mid-send
    // is picked up by the same pass.
    let isFlushing = false;
    const flush = async (): Promise<void> => {
      if (!active || isFlushing) return;
      isFlushing = true;
      try {
        for (;;) {
          const intents = useWorkflowStore.getState().takeNotifications();
          if (intents.length === 0) break;
          for (const intent of intents) {
            if (!active) return;
            await _sendOne(intent);
          }
        }
      } finally {
        isFlushing = false;
      }
    };
    // Flush whatever the store already has at mount.
    if (selectPendingNotifications(useWorkflowStore.getState()).length > 0) {
      void flush();
    }
    const unsubscribe = useWorkflowStore.subscribe((state, previous) => {
      if (state.pendingNotifications === previous.pendingNotifications) return;
      if (state.pendingNotifications.length > 0) {
        void flush();
      }
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);
}

"use client";

/**
 * Unattended runs for the saved workflow (R15-AGENT-023): the Schedule control
 * (interval / announcement-phrase triggers) and the `action.webhook` URL
 * editor. The sidecar fires schedules while the app is open; a webhook URL is
 * a BYOK secret kept in the OS keychain, handed to sidecar memory by header.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import {
  createSchedule,
  deleteSchedule,
  listSchedules,
  registerWebhookUrl,
  setScheduleEnabled,
} from "@/store/workflow";

import {
  MIN_SCHEDULE_INTERVAL_MINUTES,
  type ScheduleTrigger,
  type WorkflowSchedule,
} from "../../../types/workflow";
import { generateId } from "./graph-state";

const INPUT_CLASS =
  "bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-control text-caption h-7 border px-2 font-mono outline-none";

function describeTrigger(trigger: ScheduleTrigger): string {
  return trigger.kind === "interval"
    ? `Every ${trigger.everyMinutes} min`
    : `${trigger.symbol} announcement contains "${trigger.phrase}"`;
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function ScheduleControl({ workflowId }: { workflowId: string }) {
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);
  const [kind, setKind] = useState<ScheduleTrigger["kind"]>("interval");
  const [minutes, setMinutes] = useState(String(60));
  const [symbol, setSymbol] = useState("");
  const [phrase, setPhrase] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () => listSchedules().then((all) => all.filter((s) => s.workflowId === workflowId)),
    [workflowId],
  );
  const refresh = async () => {
    try {
      setSchedules(await load());
    } catch (e: unknown) {
      setError(errorText(e));
    }
  };

  useEffect(() => {
    let alive = true;
    load().then(
      (mine) => alive && setSchedules(mine),
      (e: unknown) => alive && setError(errorText(e)),
    );
    return () => {
      alive = false;
    };
  }, [load]);

  const act = async (op: () => Promise<unknown>) => {
    setError(null);
    try {
      await op();
    } catch (e: unknown) {
      setError(errorText(e));
    }
    await refresh();
  };

  const add = () => {
    const trigger: ScheduleTrigger =
      kind === "interval"
        ? { kind, everyMinutes: Number(minutes) }
        : { kind, symbol: symbol.trim().toUpperCase(), phrase: phrase.trim() };
    void act(() => createSchedule({ workflowId, trigger }));
  };

  const intervalOk = Number(minutes) >= MIN_SCHEDULE_INTERVAL_MINUTES;
  const canAdd = kind === "interval" ? intervalOk : symbol.trim() !== "" && phrase.trim() !== "";

  return (
    <section data-testid="schedule-control" className="flex flex-col gap-2">
      <p className="text-charcoal-400 text-micro font-mono">
        Runs the saved workflow while Vysted is open. Save changes before scheduling.
      </p>
      <div className="flex flex-wrap items-center gap-1">
        <select
          aria-label="Trigger"
          value={kind}
          onChange={(e) => setKind(e.target.value as ScheduleTrigger["kind"])}
          className={INPUT_CLASS}
        >
          <option value="interval">Every N minutes</option>
          <option value="announcement">On announcement</option>
        </select>
        {kind === "interval" ? (
          <input
            aria-label="Minutes"
            type="number"
            min={MIN_SCHEDULE_INTERVAL_MINUTES}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            className={`${INPUT_CLASS} w-20`}
          />
        ) : (
          <>
            <input
              aria-label="Symbol"
              placeholder="TCS"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className={`${INPUT_CLASS} w-20`}
            />
            <input
              aria-label="Phrase"
              placeholder="financial results"
              value={phrase}
              onChange={(e) => setPhrase(e.target.value)}
              className={`${INPUT_CLASS} w-40`}
            />
          </>
        )}
        <Button size="sm" variant="outline" onClick={add} disabled={!canAdd}>
          Add schedule
        </Button>
      </div>
      {!intervalOk && kind === "interval" && (
        <p className="text-charcoal-400 text-micro font-mono">
          Minimum interval is {MIN_SCHEDULE_INTERVAL_MINUTES} minutes.
        </p>
      )}
      {error !== null && (
        <p role="alert" className="text-micro font-mono text-red-400">
          {error}
        </p>
      )}
      <ul className="flex flex-col gap-1">
        {schedules.map((s) => (
          <li
            key={s.id}
            data-testid="schedule-row"
            className="border-charcoal-700 flex items-center gap-2 border-t pt-1"
          >
            <label className="text-charcoal-200 text-micro flex flex-1 items-center gap-1 font-mono">
              <input
                type="checkbox"
                aria-label={`Enabled: ${describeTrigger(s.trigger)}`}
                checked={s.enabled}
                onChange={(e) => void act(() => setScheduleEnabled(s.id, e.target.checked))}
              />
              {describeTrigger(s.trigger)}
            </label>
            <span className="text-charcoal-400 text-micro font-mono" title={s.lastDetail ?? ""}>
              {s.lastFiredAt === null
                ? "never fired"
                : `${new Date(s.lastFiredAt).toLocaleString()} · ${s.lastStatus ?? ""}`}
            </span>
            <Button size="sm" variant="ghost" onClick={() => void act(() => deleteSchedule(s.id))}>
              Delete
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * The `action.webhook` node's URL: validated by the sidecar, then kept in the
 * keychain. The node config only ever carries `secret_ref`.
 */
export function WebhookUrlEditor({
  secretRef,
  onPatch,
}: {
  secretRef: string | undefined;
  onPatch: (patch: Record<string, unknown>) => void;
}) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const save = async () => {
    const ref = secretRef || generateId("webhook");
    try {
      await registerWebhookUrl(ref, url.trim());
      await setSecret(KEYCHAIN_NAMESPACES.workflowWebhook(ref), url.trim());
      onPatch({ secret_ref: ref });
      setUrl("");
      setStatus("URL stored in the keychain.");
    } catch (e: unknown) {
      setStatus(errorText(e));
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <span className="text-charcoal-400 text-micro font-mono uppercase">Webhook URL</span>
      <input
        aria-label="Webhook URL"
        type="password"
        autoComplete="off"
        placeholder={secretRef ? "stored in keychain (replace)" : "https://…"}
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        className={INPUT_CLASS}
      />
      <Button size="sm" variant="outline" onClick={() => void save()} disabled={url.trim() === ""}>
        Set URL
      </Button>
      {status !== null && <p className="text-charcoal-400 text-micro font-mono">{status}</p>}
    </div>
  );
}

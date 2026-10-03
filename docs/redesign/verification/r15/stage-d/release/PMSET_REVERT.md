# Power and system settings: what this run changed, and how to revert

Sources read: `docs/redesign/verification/vysted-r15-run-state.md` (every `pmset` and `caffeinate` mention) and `r15/stage-d/OPERATOR_HANDOVER.draft.md` section 7. Nothing here was run by an agent.

## pmset

**No `pmset` setting change is recorded anywhere in the run-state, ledger or evidence.** The only `pmset` fact on disk is a read: at 04:01 IST Fri 25 Sep the run read `pmset -g log` to confirm that an isolated stack and a caffeinate process had died with no sleep event. If a `pmset` change was made by hand during the burst window (14:35 IST Sat 3 Oct onward) or at any other time, it is not recorded, so its prior value is unknown.

To see the current state and decide for yourself:

```sh
pmset -g
pmset -g custom
pmset -g assertions
```

If you find a setting you changed and want the macOS defaults back (macOS defaults for a MacBook; **verify with `pmset -g`** after each command, because defaults differ by model and macOS version):

```sh
sudo pmset -a disablesleep 0
sudo pmset -b sleep 1 displaysleep 2
sudo pmset -c sleep 0 displaysleep 10
sudo pmset -a powernap 1
```

**Operator to confirm:** the defaults above are generic macOS defaults, not values this run recorded — confirm with `pmset -g` before applying any of them.

## caffeinate (the only power control the run recorded)

`caffeinate` is not a persistent setting: it holds an assertion until its process exits (or its `-t` timeout ends). Recorded events:

- Approval pass, 03:00-03:13 IST: granted `caffeinate -dimsu`, pid 91760 (run-state header).
- Stage 0: armed as pid 52012, `caffeinate -dimsu -t 86400` (24 h); released in the operator-requested graceful pause (L8, "caffeinate 52012 released").
- After the Mac slept during batch 6 (L26): re-armed with `-dimsu -t 86400`.
- 04:01 IST Fri 25 Sep: caffeinate 47158 found dead; re-armed for 48 h as pid 22698 beside pid 34805 (about 11 h left on 34805).
- No later caffeinate event is recorded, so which processes are alive now is unverified.

Revert (safe to run at any time; ends only the caffeinate processes):

```sh
pgrep -fl caffeinate
pkill caffeinate
pmset -g assertions
```

`pkill caffeinate` ends every caffeinate on the machine, including ones you started yourself; to be selective, `kill <pid>` the pids `pgrep -fl caffeinate` shows. A caffeinate release is also planned as a run-ending stage of `r15/tooling/final-pass.js`. **Operator to confirm:** whether that stage actually ran at the end of this run — it is not recorded in the run-state or ledger either way.

## Other system settings this run touched

None recorded as a system setting. The run did write WebKit housekeeping files under the real `~/Library` during the bundle rehearsal (DECISIONS 5.9) and set the dev keystore described in `docs/redesign/KEYCHAIN_DEV_SIGNING.md`; those are described there, not here.

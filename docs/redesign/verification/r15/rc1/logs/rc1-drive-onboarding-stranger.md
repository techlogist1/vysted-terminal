# rc1-drive-onboarding-stranger — working log

26 Sep 2026. Found a completed prior attempt of this role's output already on disk
(`rc1/drives/onboarding-stranger.md`, `rc1/findings/onboarding-stranger.json`,
`surface/onboarding-stranger/rc1/*`), but it was written against
`4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`, an sha 297 commits behind this gate round's actual
candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. `git diff` between the two shas touches
`sidecar/services/llm/{tool_call_rescue.py,ollama.py,openai.py}` and
`src/components/OnboardingFlow.tsx` — directly relevant to this group's own prior finding
(`tool_call_rescue.py`'s new `_call_syntax`/`LeakHold` code literally cites
`rc1-drive-onboarding-stranger:1` in its docstring as the motivating case). Treated this as
requiring live re-verification rather than a blind carry-forward, per "continue, never restart"
not extending to a fundamentally different candidate sha.

Register statuses for all 8 onboarding-group ids unchanged between the two shas
(R15-UI-008/DATA-018/UI-052/UI-019/AGENT-028 fixed, UI-041 not_a_defect, UI-076 open, UI-044
blocked_tier4) — cheap, so re-verified all of them live/by-code-read on `4c6dfe8c` anyway (own
sidecar :52326, clean data dir, per ISO_STACK.md's source-boot recipe). All held.

Re-ran the one LLM-backed probe (keyless llama3.1:8b Zomato question, under the shared Ollama
lock) fresh against the new candidate rather than trusting the stale transcript, since the
implicated file changed substantially. Result: the SPECIFIC leaked-text shape from the prior
attempt (fenced fake "Tool call: price_data(...)" + hand-typed JSON) is gone — the
`tool_call_rescue.py` fix closed it. But the underlying class recurred in a new shape: two REAL
`get_terminal_state` tool calls (ok:true, a UI-state snapshot with no price fields) followed by
invented specific price figures in prose. Checked the register for this defect_class
("hallucinated-tool-result-citation") and found it is `R15-LEAD-030`, already `blocked_tier4`,
already operator-adjudicated at DECISIONS 4.9 in this exact gate round. Per the LEAD NOTE's
explicit instruction for this class, corrected the prior attempt's classification from an
actionable `new_defect` (medium) to a register **note** against the existing `R15-LEAD-030`
entry — no fix round, as instructed.

Sidecar boot/stop, all curl probes, and the Ollama-locked vy.py call are logged in
`rc1/drives/onboarding-stranger.md`. Evidence files under
`surface/onboarding-stranger/rc1/*-r2.*` (new files, existing r1 files never overwritten).

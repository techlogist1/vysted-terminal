# RC1 Gate Round 3 — Findings Index

Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Merged mechanically from every
`findings/*.json` on disk (9 files: 6 empty `[]`, 3 with content). Sorted by kind then
severity. Full record: `FINDINGS.json`.

| Key | Kind | Severity | Register id | Title | Evidence file |
|---|---|---|---|---|---|
| `rc1-drive-composer-chat:1` | new_defect | medium | — (not register-tracked) | Missing/invalid key on an eagerly-validating provider (OpenAI/Groq, and by shared-class construction OpenRouter/xAI/DeepSeek) surfaces the generic "internal error" frame instead of a humanized key-missing message, on `/agents/{id}/invoke` and `/llm/chat` | `docs/redesign/verification/r15/surface/composer-chat/rc1/round-3/cc-20-err-nokey-openai.jsonl` |
| `rc1-drive-research-briefs:1` | new_defect | medium | — (not register-tracked; third instance of a recurring class) | Citation-integrity net only recognises a bare `[n]` marker; a model-written non-numeric bracket token (a literal internal `vysted://` scheme URL) ships unprocessed in the published brief | `docs/redesign/verification/r15/surface/research-briefs/rc1/round-3/1-deep-cgpower-llama.jsonl` |
| `rc1-gate8:1` | new_defect | low | — (not register-tracked) | Proposed-change review card and applied label price a US-region lot in the session's local currency (Add 4 MSFT @ ₹480 for a $480 lot) | `docs/redesign/verification/r15/rc1/round-3/gate8/portfolio-07-gated-add.json` |

Zero `regression`, `chain`, `gate8`(-kind), or `environment` findings filed this round (all 3
findings above are filed with `kind: "new_defect"` by their originating role, including the
one raised inside the gate-8 role's own evidence directory).

Empty finding files (no content, confirmed on disk): `rc1-battery-0.json`,
`rc1-battery-index.json`, `rc1-datapack.json`, `rc1-drive-failure-inducer.json`,
`rc1-drive-onboarding-stranger.json`, `rc1-drive-panels-layouts.json`,
`rc1-drive-portfolio-notes.json`, `rc1-drive-screener.json`,
`rc1-drive-settings-plugins.json`, `rc1-heavy.json`, `rc1-scenarios.json`.

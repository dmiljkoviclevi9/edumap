# INDEX — Task → Files

Routing map for AI agents. Pick the row that matches your task.
Read **only** the listed files plus the source code you are about
to change. If your task does not fit a row, fall back to the full
[`AGENTS.md`](../../AGENTS.md) flow.

Cap: ≤80 lines. If this file grows past that, fix the taxonomy, not the file.

## Routing table

| Task | Read first |
| --- | --- |
| Modifying an API endpoint | [`ai/knowledge/architecture/api-contracts.md`](architecture/api-contracts.md), [`ai/knowledge/services/backend-patterns.md`](services/backend-patterns.md) |
| Changing Country or CountryTranslation model | [`ai/knowledge/architecture/data-model.md`](architecture/data-model.md), [`ai/knowledge/architecture/api-contracts.md`](architecture/api-contracts.md) |
| Adding/editing translations or audio | [`ai/knowledge/architecture/i18n-model.md`](architecture/i18n-model.md), [`.claude/skills/edumap-localization/SKILL.md`](../../.claude/skills/edumap-localization/SKILL.md) |
| Frontend modal, map, or UI change | [`ai/knowledge/services/frontend-patterns.md`](services/frontend-patterns.md), [`ai/knowledge/architecture/i18n-model.md`](architecture/i18n-model.md) |
| Writing or reviewing tests | [`ai/knowledge/services/testing-patterns.md`](services/testing-patterns.md) |
| Deploy / CI/CD / GitHub Actions | [`ai/knowledge/infrastructure/deployment-guide.md`](infrastructure/deployment-guide.md), [`.claude/skills/iterative-azure-deploy/SKILL.md`](../../.claude/skills/iterative-azure-deploy/SKILL.md) |
| Azure infrastructure / resources | [`ai/knowledge/infrastructure/azure-resources.md`](infrastructure/azure-resources.md) |
| Debugging an unfamiliar failure | [`ai/memory/debugging-discoveries.md`](../memory/debugging-discoveries.md), [`ai/memory/developer-pitfalls.md`](../memory/developer-pitfalls.md) |

## After Coding — Update These Files

| What changed in code | Which knowledge files to update |
|---|---|
| New or changed API endpoint | `ai/knowledge/architecture/api-contracts.md`, `ai/knowledge/services/backend-patterns.md` |
| Changed Country or CountryTranslation record | `ai/knowledge/architecture/data-model.md` |
| Changed translation fallback logic or locale keys | `ai/knowledge/architecture/i18n-model.md` |
| New frontend pattern, hook, or UI convention | `ai/knowledge/services/frontend-patterns.md` |
| Changed Azure resource, OIDC config, or deploy workflow | `ai/knowledge/infrastructure/azure-resources.md` or `deployment-guide.md` |
| Bug, gotcha, or debugging discovery | relevant `ai/memory/` file |

## Rules

- Read these files **before** opening source code. The knowledge layer
  encodes constraints (locked contract, Cyrillic encoding, audio-first
  requirement) that make the source code make sense.
- Cap pre-reads at three files for any single task. If you need more,
  ask for clarification or follow the full Behavior Contract in [`AGENTS.md`](../../AGENTS.md).
- Never guess the Country/CountryTranslation schema — read
  [`ai/knowledge/architecture/data-model.md`](architecture/data-model.md) every time.
- Cheap-model contributors: also read [`ai/CHEATSHEET.md`](../CHEATSHEET.md) first.

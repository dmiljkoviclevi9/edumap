---
name: update-repo-knowledge
description: Update the repository knowledge layer after non-trivial work. Use after implementing a feature, fix, refactor, or significant debugging session to decide whether ai/knowledge, ai/memory, and docs should be updated, and to make the smallest grounded writeback that preserves what was learned.
---

# Update Repo Knowledge

Use this skill after finishing meaningful work. The goal is to preserve durable project knowledge without adding noise.

## Workflow

1. Confirm whether writeback is needed.
   - Write back after non-trivial implementation, refactoring, or debugging.
   - Skip only when the task was trivial and produced no durable knowledge, no behavior change, and no new lesson worth preserving.

2. Re-read the finished source of truth.
   - Review the changed code, configuration, validation results, and any relevant behavior you confirmed.
   - Prefer code and verified behavior over notes or intent.

3. Choose the destination.
   - Update `ai/knowledge/` for stable facts: architecture, contracts, schemas, workflows, integrations, and conventions.
   - Update `ai/memory/` for lessons: root causes, pitfalls, quirks, debugging discoveries, and environment surprises.
   - Update `docs/` or top-level markdown when humans need the change outside the AI layer: setup, deployment, operations, or repository process.
   - Keep `ai/memory/` files under 200 lines. Archive to `ai/memory/archive/` if they grow past that.

4. Keep the update minimal and precise.
   - Touch the smallest relevant file.
   - Extend an existing file before creating a new one.
   - Avoid copying the same fact into multiple places unless the audiences are different.

5. Keep each writeback durable.
   - `ai/knowledge/`: concise, repository-specific facts that should remain useful across tasks.
   - `ai/memory/`: non-obvious discoveries that are likely to save time or prevent repeat mistakes.
   - Never write ephemeral state (in-progress tasks, current branch names) into these files.

6. State what was updated.
   - Mention which files were updated and why.
   - If no writeback was needed, say why explicitly.

## Output

Return:

```md
## Knowledge Writeback

### Updated
- [file]: [why it changed]

### Not Updated
- [file or area]: [why no writeback was needed]

### Rules Applied
- `ai/knowledge`: [yes/no and reason]
- `ai/memory`: [yes/no and reason]
- `docs`: [yes/no and reason]
```

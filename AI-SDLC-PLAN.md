# AI-Assisted SDLC Plan for EduMap

A roadmap for improving how Claude assists in developing, deploying, and maintaining this project — across the seven Claude Code primitives (skills, knowledge, memory, tools, subagents, hooks, plugins) plus two more (slash commands, permissions).

This file is a planning artifact, not an implementation checklist. Each recommendation is sized and prioritized so it can land independently. Pick the ones that match your time budget and current needs.

## Guiding principle

Every AI SDLC investment should **multiply the value of each interaction** — meaning each future Claude session should be slightly faster, more accurate, and more aligned with your style than the last, because the AI has accumulated context that doesn't need rediscovering.

The corollary: every addition has a context cost. Skill descriptions are always loaded. Memory files are always loaded. CLAUDE.md is always loaded. Don't add things that don't pull their weight. The sweet spot for a personal project is "enough scaffolding that recurring patterns are automatic, not so much that the first reply takes 30 seconds to start streaming."

## Current state

Inventory as of right now:

| Primitive | Status | Notes |
|---|---|---|
| **Skills** | 2 installed at `.claude/skills/` | `iterative-azure-deploy` (cycle + gotchas reference), `edumap-localization` (i18n schema + 3 scripts). Both bundled in-repo. |
| **Knowledge (repo docs)** | 4 markdown files at repo root | `PLAN.md` (architecture), `WALKTHROUGH.md` (Azure runbook), `FUTURE.md` (deferred work), `AI-SDLC-PLAN.md` (this file). |
| **Knowledge (`AGENTS.md` / `CLAUDE.md`)** | **Missing** | High-priority gap — no project-bundled context file that fresh AI sessions auto-load. |
| **Memory (user-scoped)** | 3 files at `~/.claude/projects/C--REPOS-EduMap/memory/` | `MEMORY.md` (index), `user_role.md`, `project_edumap.md`. Lean but useful. |
| **Settings (permissions)** | `~30 entries` in `.claude/settings.local.json` | Mostly read-only / dev-loop commands accumulated through use. |
| **MCPs** | Several available | Claude Preview (heavily used), Claude in Chrome, scheduled-tasks, etc. None custom to EduMap. |
| **Subagents** | Built-ins only | Plan, Explore, general-purpose, claude-code-guide. No custom EduMap subagents. |
| **Hooks** | **None configured** | Could catch repeated mistakes automatically. |
| **Plugins** | `anthropic-skills` installed (PDF, XLSX, etc.) | EduMap skills are NOT yet packaged as a plugin. |
| **Slash commands** | Standard set only | No `/deploy`, `/verify-live`, etc. |
| **Local CLI tools** | `az` 2.84.0, `dotnet` 10, `git`, `python`, `docker`, `curl` | **`gh` CLI not installed** — costs ~10 lines of Python per workflow check. |

## Coverage analysis: SDLC phases vs primitives

The classic SDLC has six phases. The matrix below shows which primitive covers each phase today (✅), what's partial (⚠️), and what's a gap (❌).

| Phase | Skills | Knowledge | Memory | Tools | Subagents | Hooks | Plugins |
|---|---|---|---|---|---|---|---|
| Design | ❌ | ✅ PLAN.md | ⚠️ project_edumap.md | — | ⚠️ Plan agent | ❌ | — |
| Develop | ⚠️ edumap-localization (locale work only) | ⚠️ PLAN scattered | ⚠️ project_edumap.md | ✅ az/dotnet/git | ❌ | ❌ | — |
| Test | ⚠️ via deploy skill's Step 3 | ❌ | ❌ | ✅ dotnet test, Claude Preview | ❌ | ❌ | — |
| Deploy | ✅ iterative-azure-deploy | ✅ WALKTHROUGH.md | ❌ | ✅ az + curl | ❌ | ❌ | — |
| Operate | ❌ | ⚠️ WALKTHROUGH §3.5 | ❌ | ⚠️ KQL via portal | ❌ | ❌ | — |
| Iterate | ⚠️ via deploy skill's recovery section | ✅ FUTURE.md | ❌ | — | — | ❌ | — |

**The two biggest holes:** Operate (Week 4 will need this) and Hooks (every primitive could benefit from automation).

## Recommendations by primitive

### Skills

**Current**: 2 (`iterative-azure-deploy`, `edumap-localization`).

**Add next** (in order):

1. **`azure-resource-bootstrap`** (~3 hours to write). Generalizes the OIDC + UAMI + role-assignment pattern from one-off (App Service) to repeatable (Translator, Speech, ACR, Container Apps, App Insights). Captures provisioning command templates per resource type, the `az rest` workaround, and the "extend the existing UAMI's role assignments rather than creating a new identity" rule. Pairs naturally with `iterative-azure-deploy`: bootstrap creates the resource, deploy ships the code that uses it.

2. **`app-insights-kql`** (~2 hours to write). Application Insights + Log Analytics queries. Captures the `TelemetryClient.TrackEvent` custom-event pattern, KQL templates for common questions (top-N by event, P95 latency, failed-requests trend), alert rule patterns, the `Microsoft.ApplicationInsights.AspNetCore 2.22.0` pin (already in gotchas — surface it here too). Will be used for Week 4 of training and for years after.

**Don't add** (low ROI for this repo, would just add context tokens):
- `d3-geo-interactive-map` — too niche; existing comments in `index.html` + gotchas already cover it.
- `commit-message-craft` — already absorbed into the deploy skill's Step 5.
- `contract-first-fullstack` — would trigger ~once per new project; ROI doesn't justify the description-token cost.

**Sweet-spot total: 4 skills.** Above 5 the description tokens start eating context budget and triggering competition gets noisy. Below 3, you're missing meaningful repeats.

### Knowledge (repo docs)

**Current**: PLAN.md, WALKTHROUGH.md, FUTURE.md, this file. Plus the SKILL.md files which double as project knowledge once skills are bundled.

**Add next**:

1. **`AGENTS.md` at the repo root** (highest-priority gap). This is the cross-tool emerging convention — Codex auto-reads it, Antigravity reads it, and you can make Claude Code pick it up either as ambient `*.md` context or via a one-line `CLAUDE.md` containing `See AGENTS.md.` for the special-case auto-load. (See the **Cross-tool portability** section below for the full rationale.) Should be **short** (under 100 lines) and capture the things every session needs up front — not duplicate the longer docs. Suggested contents:
   - Project one-liner ("Kids' interactive world map deployed to Azure App Service via OIDC GitHub Actions; Serbian Cyrillic primary locale")
   - Local-dev one-liners (`dotnet build && dotnet test && dotnet run`)
   - The 3 hard rules that bit you (no `gh` CLI yet, `python -X utf8` for any Cyrillic, `Microsoft.ApplicationInsights.AspNetCore` pinned to 2.22.0)
   - Pointers to the longer docs and skills: `PLAN.md` for architecture, `WALKTHROUGH.md` for Azure runbook, `FUTURE.md` for deferred work, **explicit links** to the skill files in `.claude/skills/` so non-Claude tools can find the workflows (they won't auto-discover the `.claude/` path)
   - Azure resource IDs that don't change (subscription, tenant, UAMI clientId, web app name) — saves 30 seconds of `az account show` every session.

2. **Optional: `DECISIONS.md`** (~50 lines, append-only). One paragraph per non-obvious architectural decision and why it was made. Examples we accumulated this session:
   - Why .NET 10 (not 8): course material's quickstart link is `tabs=net10`
   - Why d3-geo (not Leaflet): Equal Earth projection for accuracy; per-polygon rewind for the winding bug
   - Why OIDC + UAMI (not publish profile, not AD app): Levi9 tenant blocks AD app create
   - Why Natural Earth 50m self-hosted (not 10m via raw.githubusercontent.com): corporate proxy hang + repo bloat tradeoff
   - Why `Microsoft.ApplicationInsights.AspNetCore` 2.22.0 (not 3.x): tests don't throw without conn string

   Future-you in six months will not remember the reasoning. A 50-line decision log saves the next "why did past-me do this?" detour.

**Don't add**:
- A separate `CONTRIBUTING.md` — you're the only contributor. Solo-dev repos shouldn't pretend to be team repos.
- A `CHANGELOG.md` — `git log` is the changelog. You're not publishing this on npm.

### Memory (user-scoped, `~/.claude/projects/<proj>/memory/`)

**Current**: `MEMORY.md` (index), `user_role.md`, `project_edumap.md`.

**Add**:

1. **`environment.md`** — your durable local-setup facts that recur. Things like: Windows + Git Bash + PowerShell available, `az` CLI 2.84.0 has the `MissingSubscription` bug, no `gh` CLI installed, .NET 8 not installed (only 9 + 10), corporate proxy blocks `raw.githubusercontent.com`. These don't belong in the repo (they're about your machine, not the project) but they recur every session.

2. **`preferences.md`** — explicit working-style preferences. Things like: prefer multi-paragraph commits with the *why*, no emojis in code or commits, no `git add -A`, kid-friendly tone, security-conscious choices, ask before changing API contracts. Claude infers most of these from session context but writing them down makes them durable across new sessions.

3. **Update `project_edumap.md`** to reflect the current state — d3-geo not Leaflet, i18n schema with Translations dict, OIDC-deployed not publish-profile. The existing one is mid-conversation accurate but the project moved on.

**Don't add**:
- A `tools_used.md` — Claude already enumerates available tools.
- A `commit_history_summary.md` — `git log` exists.
- A "what we did last session" — the auto-summary handles this.

The `consolidate-memory` skill from the anthropic-skills plugin will periodically merge, deduplicate, and prune these — run it occasionally to keep memory lean (it's already installed).

### Tools (local CLIs)

**Current**: `az` 2.84.0, `dotnet` 8/9/10, `git`, `python` 3.12 + utf8 flag, `docker`, `curl`, `powershell`.

**Add**:

1. **Install `gh` CLI** (`winget install GitHub.cli`). Single highest-ROI tooling change you could make.
   - Replaces ~15 lines of curl + python in every CI/CD verification with `gh run watch` (single command).
   - Replaces the GitHub UI secrets/variables flow with `gh secret set`, `gh variable set` from terminal.
   - Eliminates the cp1252 encoding crash class entirely (Go-compiled binary, no Python in the loop).
   - Required `gh auth login` is one-time; everything else just works.
   - **Update the `iterative-azure-deploy` skill** after install — the GitHub REST API polling pattern can be replaced with `gh run watch --interval 8`.

2. **Optional: `jq`** (`winget install jqlang.jq`). Replaces `python -X utf8 -c "import sys,json; print(...)"` one-liners for parsing API responses. Lighter syntax, no encoding flags, ubiquitous in cloud-engineering blog posts. Marginal benefit — Python works, `jq` is just a bit faster to type.

3. **Optional: `azd`** (Azure Developer CLI). Bundles `az` + bicep + GitHub Actions templates. The course doesn't use it, but if you're building a *second* Azure project after EduMap, `azd init` saves hours of bootstrap.

**Don't install** (anti-pattern for this project):
- `kubectl` / `helm` — you're using Container Apps, not AKS. No K8s in this project.
- `terraform` — your IaC needs are tiny (a handful of resources); `az` commands suffice.
- `pulumi` — same as Terraform; overkill for the scale.

### Subagents

**Current**: built-ins only (Plan, Explore, general-purpose, claude-code-guide, statusline-setup). The Plan and Explore agents were used heavily this session and worked well.

**Add (optional, lower ROI than skills)**:

1. **`translation-quality-reviewer`** — reads through `countries.json` translations and flags entries that look auto-translated / robotic / kid-inappropriate. Useful when running Chunk C of FUTURE.md (Azure Translator outputs are ~20% awkward). Implementation: ~50-line agent prompt that loads `countries.json`, samples 20 random `sr-Cyrl.funFact` entries, judges each on natural-tone / kid-friendliness scales, returns a list with suggested rewrites. Spawn after each Translator run.

2. **`deploy-readiness-reviewer`** — runs before pushing: checks for staged secrets, checks that the workflow YAML matches the deploy job's expectations, confirms no pending Azure-side changes (e.g., a UAMI role assignment that hasn't propagated). ~80-line prompt. Useful as a hook trigger rather than a manual one.

**Don't add**:
- A "code reviewer" subagent — built-in Claude can review code well enough at this scale.
- A "test runner" subagent — `dotnet test` is one command; no subagent needed.

Subagents are best when (a) the work is parallelizable, (b) the work has its own context that shouldn't bloat the parent, or (c) the work needs independent judgment. Translation-quality-review fits (c). Most other things don't.

### Hooks

**Current**: **None.** This is the biggest configuration gap — hooks automate the failures we've each hit multiple times this session.

Hooks are configured in `settings.local.json` under a top-level `hooks` key. Each hook is a `PreToolUse` / `PostToolUse` / `Stop` event with a shell command. See https://docs.claude.com/en/docs/claude-code/hooks for the schema.

**Add** (in order of value):

1. **`PreToolUse` for `Bash(az ad app create*)` → block + suggest UAMI.** We hit this twice in one session. The Levi9 tenant blocks AD app creation; the fix is always to use a UAMI. A hook can catch this before the failed command runs and emit "your tenant blocks AD app creation — use `az identity create` instead, see `.claude/skills/iterative-azure-deploy/references/gotchas.md`".

2. **`PostToolUse` for `Edit(countries.json)` → auto-validate JSON.** Run `python -X utf8 -c "import json; json.load(open('countries.json'))"` after every edit. If it fails (invalid JSON, encoding issue), surface immediately rather than discovering at next `dotnet test`. Five lines of YAML, saves the "tests fail because of JSON syntax error" debug detour.

3. **`PostToolUse` for `Edit(*.cs)` or `Write(*.cs)` → run `dotnet build` in the background.** If a syntax error sneaks in, you see it the same minute, not three commits later. Sub-2-second feedback loop. Could fire too often during refactors; gate on file change size or path patterns.

4. **`PreToolUse` for `Bash(git push*)` → confirm preconditions.** Specifically: check that `dotnet test` was run in this session and passed; check that we're on `main`; check there are no uncommitted files. Surfaces "you forgot to test before pushing" before the commit lands.

5. **`Stop` hook → session summary.** When the conversation ends, run a script that summarizes "files touched, tests run, commits made" and writes to `~/.claude/projects/<proj>/sessions/<id>/summary.md`. Useful for picking up next session, especially if the gap is long.

**Don't add**:
- A hook that auto-formats files on every Edit — pre-commit hooks already do this if you have them; doubling up creates merge conflicts.
- A hook that auto-commits — committing decisions should stay human.
- A hook for `Read` — Reads are cheap and frequent; hooking them slows everything down for no value.

**Important caveat**: hook failures can silently break the session. Test each hook with `--debug` mode first. The `settings.local.json` format does NOT support comments, so document hooks in a sibling `.claude/hooks.md` if they get complex.

### Plugins

**Current**: `anthropic-skills` plugin installed (gives you the PDF, XLSX, PPTX, DOCX, skill-creator, consolidate-memory skills).

**Add (low-priority, future move)**:

1. **Package EduMap's skills as a plugin** for Levi9 colleagues. Run `python -m scripts.package_skill` (the skill-creator's bundled tool) against each of `.claude/skills/iterative-azure-deploy/` and `.claude/skills/edumap-localization/`, producing `.skill` files. Anyone in your team building similar projects can drop them in. ~30 minutes total.

   Worth doing if you want to share the corporate-tenant gotchas (`MissingSubscription`, AD-blocked, App Service zip backslash) with colleagues going through the same training. Skip if EduMap stays personal.

**Don't add**:
- Random marketplace plugins. Each one adds skill descriptions to your context budget; install only what you'll actually use.

### Slash commands

**Current**: standard set (`/help`, `/clear`, `/model`, etc.).

**Add**:

1. **`/deploy`** — shorthand for "run the iterative-azure-deploy skill on whatever I just changed". Saves the user having to phrase the trigger phrase that matches the skill's description. Implementation: a single-line custom slash command in `~/.claude/commands/deploy.md` containing `Use the iterative-azure-deploy skill for the current uncommitted changes`.

2. **`/verify-live`** — one-shot verification of the live site. Captures the curl-then-parse cycle from Step 8 of the deploy skill, plus a check that the JSON shape matches the locally-staged data.

3. **`/sr-status`** — show the current Serbian Cyrillic translation coverage (the verification snippet at the end of the `edumap-localization` SKILL.md). Useful to glance at while iterating on Chunks B/C/D from FUTURE.md.

Custom slash commands are cheap to add (one short markdown file each) and worth the friction reduction.

**Don't add**:
- A command that wraps every common operation. The standard chat already handles "run the tests" fine.
- Aliases for things that have one obvious phrasing.

### Permissions (`settings.local.json`)

**Current**: ~30 entries, mostly accumulated through use.

**Improvement**: run the `fewer-permission-prompts` skill (already installed from anthropic-skills). It scans recent transcripts and proposes a tightened allowlist that covers your actual read-only / dev-loop commands while excluding anything dangerous. Five minutes, removes friction from future sessions.

Beyond that: don't curate permissions by hand. Add them as Claude requests them; review periodically with the helper skill.

## Cross-tool portability

Worth asking up front: **will this AI SDLC investment survive a switch from Claude Code to Codex, Antigravity, or whatever comes next?** Mostly yes — but only if you steer the right way. The principle:

> **Invest in content portability, not feature portability.** The workflows, gotchas, and conventions you encode are the long-term IP — they generalize across tools, models, and years. The auto-trigger mechanics (skills, hooks, slash commands) are convenience layers any tool can replicate.

### What's portable as-is

- **All four markdown docs at the repo root** (`PLAN`, `WALKTHROUGH`, `FUTURE`, this file). Every LLM-powered tool reads markdown.
- **Skill scripts** (`scripts/translate-names-capitals.py`, etc.). Plain Python, no Claude dependency.
- **Skill SKILL.md content**. Other tools won't auto-trigger them but will read them on request if pointed at the path.
- **MCP servers** (if you build any). MCP is an open standard implemented by Claude Code, Codex, VS Code Copilot, Antigravity, and most newcomers. Custom MCP tooling works everywhere.

### What's tool-specific

- **Auto-trigger via skill descriptions** — Claude Code only
- **Hooks** in `settings.local.json` — different schemas in each tool
- **Slash commands** — different syntaxes in each tool
- **User-scoped memory** (`~/.claude/projects/...`) — Claude Code only
- **`CLAUDE.md` auto-load** — Claude Code only

### The cross-tool lingua franca: `AGENTS.md`

OpenAI started shipping `AGENTS.md` as Codex's convention. Other vendors have adopted it as the de facto "this is how to work on this repo" file — Antigravity reads it, many emerging tools honor it. Plain markdown, repo root, project conventions + pointers to longer docs.

**Practical move**: write `AGENTS.md` at the root with the content the Knowledge section recommends. Then either:
- **Skip `CLAUDE.md`** — Claude Code reads `*.md` files at the root as ambient context, just without the special-cased auto-load. Often good enough.
- **Or create a one-line `CLAUDE.md`** containing `See AGENTS.md.` — preserves Claude's special-case auto-load behaviour with no content duplication.

One source of truth for project conventions; three (and counting) tools served. Adopt this naming convention from the start of any new project unless you have a specific reason not to.

### Linking workflows from `AGENTS.md`

Skills' `SKILL.md` files are markdown — readable by anything. The catch is that non-Claude tools won't auto-discover the `.claude/skills/*/SKILL.md` paths. Fix by linking explicitly in `AGENTS.md`:

```markdown
## Repeatable workflows

When deploying or verifying changes, follow the cycle in
[.claude/skills/iterative-azure-deploy/SKILL.md](.claude/skills/iterative-azure-deploy/SKILL.md).
Known error fixes for this project are in
[.claude/skills/iterative-azure-deploy/references/gotchas.md](.claude/skills/iterative-azure-deploy/references/gotchas.md).

When adding translations or audio, see
[.claude/skills/edumap-localization/SKILL.md](.claude/skills/edumap-localization/SKILL.md)
plus the ready-to-run scripts in that skill's `scripts/` directory.
```

Claude Code still auto-triggers these via the SKILL.md frontmatter descriptions; other tools find them via the `AGENTS.md` links. Both audiences served from the same files.

### Switching costs

If you ever migrate from Claude Code to another tool:

| Re-do effort | What |
|---|---|
| 0 min | All markdown docs, all Python scripts, all MCP servers — work as-is |
| 5 min | Create the `AGENTS.md` ↔ `CLAUDE.md` redirect, if you'd only set up one |
| 30 min per skill | Convert skill auto-triggering to the new tool's equivalent (or accept manual invocation via `AGENTS.md` links) |
| 30 min per hook | Re-implement in the new tool's hook schema |
| 5 min per slash command | Re-implement in the new tool's syntax |
| Start over | User-scoped memory — each tool has its own store |

Total: ~1-2 hours for the current scaffolding. Cheaper than re-deriving the workflows from scratch, which is what the markdown content saves you.

### What this doesn't optimize for

Some folks try to maintain parallel `*.cursorrules`, `.cody.md`, `.aider.conf`, and similar files — one per AI tool they might use. **Don't.** The maintenance burden compounds and the files inevitably drift apart. Pick `AGENTS.md` as the single source of truth, use a one-line redirect for any tool that prefers a different filename, and stop. The marginal benefit of tool-specific tuning is dwarfed by the cost of keeping N files in sync.

## Prioritized recommendations

The full table above is exhaustive. If you can only do a few things, here's the ordering by value-per-hour:

### Tier 1 — Do this week (low cost, high return)

| Add | Cost | Why |
|---|---|---|
| **AGENTS.md at repo root** | 20 min | Cross-tool universal — Codex, Antigravity, and Claude Code (via ambient `*.md` or a one-line `CLAUDE.md` redirect) all read it. Captures your hard rules once and stops re-discovery. |
| **Install `gh` CLI** | 5 min + auth | Single biggest tooling improvement. Eliminates the cp1252 crash class. |
| **Memory: `environment.md` + `preferences.md`** | 30 min | Personal context that's durable across sessions. |
| **Slash command `/deploy`** | 5 min | Tiny but high-frequency win. |

Total: ~1 hour. Expected payoff: 5-10 minutes saved per Claude session, every session, forever.

### Tier 2 — Do in the next few weeks (medium investment, course-aligned)

| Add | Cost | Why |
|---|---|---|
| **Skill: `azure-resource-bootstrap`** | 3 h | Will be used immediately for Translator + Speech (FUTURE.md C/D) and ACR + Container Apps (Week 4). |
| **Skill: `app-insights-kql`** | 2 h | Week 4 monitoring exercise. KQL templates pay off long after the course ends. |
| **Hook: `PreToolUse` az ad app create** | 30 min | We hit this twice. Worth automating once. |
| **Hook: `PostToolUse` JSON validation on Edit(countries.json)** | 30 min | Cheap, prevents one specific class of failure. |
| **DECISIONS.md** | 1 h | Future-you will thank you when you revisit in 6 months. |

Total: ~7 hours, spread over Weeks 3-4 of training.

### Tier 3 — Longer-term (graduation-level, sharing-with-team-level)

| Add | Cost | Why |
|---|---|---|
| **Subagent: `translation-quality-reviewer`** | 2 h | Useful when running Chunk C of FUTURE.md against ~240 funFacts. |
| **Hook: build-on-edit for `*.cs`** | 1 h | Faster feedback loop; some debugging needed first. |
| **Hook: pre-push preconditions** | 1 h | Catches "forgot to test" before push. |
| **Package skills as plugin** | 30 min | Only if sharing with colleagues. |
| **`/verify-live` and `/sr-status`** | 30 min total | Convenience. |

Total: ~5 hours, do these post-training if you keep maintaining EduMap.

## Sequencing roadmap (aligned to training weeks)

The next ~3 weeks of the course are: Week 3 (CI/CD, mostly done — see WALKTHROUGH §2.2), Week 4 (Docker + ACR + Container Apps + App Insights), then training ends and EduMap becomes a long-term personal project.

| When | What | Effort |
|---|---|---|
| **This weekend** | Tier 1 (AGENTS.md + optional 1-line CLAUDE.md redirect + gh CLI + memory files + `/deploy`) | ~1 h |
| **Mid-week 3** | Build `azure-resource-bootstrap` skill before provisioning Translator/Speech for Chunks C/D | 3 h |
| **Late week 3 / early week 4** | Run Chunks B/C/D from FUTURE.md using the new skill | 3-4 h work + script run-time |
| **Week 4 monitoring exercise** | Build `app-insights-kql` skill while doing the actual KQL queries; capture as you go | 2 h |
| **Week 4 monitoring exercise** | Add the AD-block-detect hook (you'll be provisioning resources, perfect time) | 30 min |
| **End of training** | Run `consolidate-memory` skill; review Tier-3 list; decide on plugin-packaging | 1 h |
| **3 months post-training** | Whatever Tier-3 items still feel useful. The honest answer might be "none" — that's fine. | varies |

## Maintenance discipline

Every added piece of scaffolding decays unless maintained. Three rules:

1. **Update skills as the project evolves.** When the OIDC pattern changes, when the App Service plan moves to S1, when a new gotcha is found — fold it into the skill. The next session deserves accurate context, not a 6-month-stale snapshot.

2. **Prune memory periodically.** Run the `consolidate-memory` skill quarterly. Stale or contradicting memory is worse than no memory.

3. **Re-read `AGENTS.md` every 6 months** and ask: "Does this still describe what's hard about this project, or is it describing what *used to be* hard?" Edit accordingly.

When in doubt, prefer fewer + accurate over more + stale.

## What NOT to add (and why)

Tempting things that I think aren't worth their context cost or maintenance burden for this specific project:

- **A `tests/` README.** Tests should be self-documenting. If they aren't, that's a test-quality problem, not a docs problem.
- **A `db/` schema doc.** You're using a JSON file as the data store. The C# DTO and the JSON itself are the schema.
- **A "scripts" directory with helper bash commands.** The skills' scripts/ subdirectory handles this. Don't double up.
- **Per-feature `*-PLAN.md` files for every future thing.** FUTURE.md is the staging area; once a chunk lands, strike it from FUTURE.md rather than creating a new completed-PLAN.
- **Per-tool rules files** (`.github/copilot-instructions.md`, `.cursorrules`, `.cody.md`, `.aider.conf`, etc.) — one for each AI you might use. This sounds portable but actually creates a maintenance treadmill: the files drift out of sync, no single one is authoritative, and you spend more time keeping them aligned than working on the code. Pick `AGENTS.md` as the universal source of truth (see the **Cross-tool portability** section above), use a one-line redirect for any tool that prefers a different filename (Claude's `CLAUDE.md`), and stop. The marginal benefit of tool-specific tuning is dwarfed by the cost of N parallel files.
- **A `docs/` directory.** Four top-level markdown files is the limit before consolidation pressure kicks in (`PLAN`, `WALKTHROUGH`, `FUTURE`, this file). We're at four. Don't add a fifth without striking one — the next thing that wants to be a markdown file should either fold into an existing doc or, if it's truly orthogonal, *replace* one that's no longer earning its keep.

## Open questions for you to decide

1. **Solo vs sharing.** If EduMap stays personal forever, the plugin-packaging step is unnecessary. If you plan to share with Levi9 colleagues going through the same training, packaging adds value.

2. **Course depth vs project longevity.** The course ends in ~3 weeks. Most Tier 2/3 investments pay back over years, but assume the course-specific framing fades. The skills and `AGENTS.md` will outlast the `WALKTHROUGH.md`'s relevance.

3. **Hook tolerance.** Some users love automated hooks; others find them spooky. Try one (the AD-block detector) before committing to more. If it bites once with a false positive, you'll know your appetite.

4. **Maintenance budget.** All of this requires occasional upkeep. If you're not going to revisit AI SDLC for a year after the course ends, Tier 1 alone is the right answer. If you're willing to refresh every 3-6 months, Tier 2 makes sense.

## Recommended starter set

If you only do one thing from this document: **add `AGENTS.md` at the repo root.** Single highest-ROI 20-minute investment. Every AI tool that reads this repo — Claude Code, Codex, Antigravity, and whatever comes next — immediately gets your hard rules, Azure IDs, and pointers to the longer docs without having to discover them. If you want Claude Code's special-case auto-load, add a 1-line `CLAUDE.md` containing `See AGENTS.md.` (5 seconds extra).

If you have an hour: do all of Tier 1 (AGENTS.md + the optional CLAUDE.md redirect + gh CLI + two memory files + `/deploy` slash command).

If you have an afternoon: add the two course-aligned skills (`azure-resource-bootstrap` + `app-insights-kql`) and you'll be set for Week 4.

Everything else is a discretionary "I want to invest more in this project's AI scaffolding" call. The honest answer for most personal projects is "Tier 1 is enough; the rest is a hobby."

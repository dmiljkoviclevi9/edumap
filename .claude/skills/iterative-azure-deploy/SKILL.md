---
name: iterative-azure-deploy
description: Use whenever the user is iterating on a .NET ASP.NET Core project deployed to Azure App Service via GitHub Actions CI/CD — making code changes that then need to land on the live site. Triggers strongly on phrases like "deploy this", "ship the fix", "let's push", "verify the deploy", "update the live site", or any message where the user has just finished editing code on such a project. Also trigger proactively when you notice an in-progress change that has been tested locally but is not yet committed — that pattern is the entry point to the cycle. Bias toward triggering this skill rather than not; the deploy-verify loop has four verification points with specific gotchas at each, and improvising any one of them silently breaks production. Especially relevant for projects matching the EduMap shape (Minimal API + static frontend + xUnit + OIDC-federated GitHub Actions + Azure App Service Free F1 + Linux + Damir's Levi9 subscription tooling), but the workflow applies broadly to any GitHub-Actions-deployed ASP.NET Core app.
---

# Iterative Azure App Service deploy + verify cycle

A repeatable loop for landing changes on a live Azure App Service deployment without breaking it. The cycle is intentionally repetitive — every step catches a specific class of failure, and skipping any one of them eventually costs more than running it. The four verification points (local build, local smoke, CI/CD pipeline, live-site curl) are non-negotiable; the bookkeeping bits (TodoWrite at the start, summary at the end) can flex with the size of the change.

## When this skill applies

This skill targets a specific project shape. Don't run it on something that doesn't match — the recipes won't generalize cleanly.

- A .NET (8 or 10) ASP.NET Core project, Minimal API or controllers
- Hosted on **Azure App Service** (Linux, F1 Free or higher)
- CI/CD via **GitHub Actions** on `ubuntu-latest`
- Test project using **xUnit** + `WebApplicationFactory<Program>`
- Authenticated to Azure via **OIDC federation** to a UAMI or service principal (no publish profile, no client secret)
- The **GitHub MCP** (`github` server, `.mcp.json`) is configured — use MCP tools for GitHub API calls in interactive sessions. In CI or scripts, fall back to `curl` + `python -X utf8`.

If the user is building their first project of this shape, the project's own `WALKTHROUGH.md` covers bootstrap; this skill is purely for **iteration after the project is already deployed once**.

## Expected file layout

When you read into a project, you should see something like this. Knowing the layout makes navigation faster and helps you spot when something's missing.

```
<repo>/
├── .github/workflows/
│   └── ci-cd.yml                         # OIDC-authenticated build → test → deploy
├── .gitignore                             # excludes bin/obj, .claude/settings.local.json, secrets
├── .dockerignore                          # excludes the same, plus markdown/docs
├── Dockerfile                             # multi-stage, exists from Week 4 onward
├── NuGet.config                           # public nuget.org only (overrides corporate feeds)
├── <Repo>.slnx                            # newer XML-based solution format
├── PLAN.md                                # architecture doc
├── WALKTHROUGH.md                         # Azure provisioning runbook
├── FUTURE.md                              # deferred-work plan, prompt-ready
├── azure-pipelines.yml                    # ADO alternative path
├── src/<App>.Api/
│   ├── <App>.Api.csproj
│   ├── Program.cs                         # ends with `public partial class Program {}` for tests
│   ├── Models/                            # DTOs, often `sealed record`s
│   ├── Services/                          # repositories, singletons
│   ├── Data/                              # source-of-truth JSON, marked Content/CopyToOutput
│   ├── Properties/launchSettings.json
│   ├── appsettings.json
│   └── wwwroot/                           # static frontend, served via UseStaticFiles
│       ├── index.html
│       ├── data/                          # large GeoJSON / blob assets, self-hosted
│       ├── flags/ (or similar)            # vendored visual assets
│       └── audio/                         # later additions
└── tests/<App>.Api.Tests/
    ├── <App>.Api.Tests.csproj             # uses `<None Include="../../Data/..." Link="Data/..." />`
    └── EndpointTests.cs                   # WebApplicationFactory<Program> based
```

If a directory the user thinks fits this shape is missing, mention it before charging ahead.

## The cycle

### Step 1 — Track the work with `TodoWrite`

If the change is more than one trivial edit, set up a todo list at the start. The steps below map cleanly; mark each as `in_progress` when you reach it and `completed` immediately when done.

This isn't bureaucracy. The cycle has four verification points (local build, local smoke, CI/CD, live site) and any one can fail; the todo list gives the user a clear checkpoint and protects against silently dropping a step under pressure.

### Step 2 — Make the change

Edit files using the `Edit` / `Write` tools. For changes touching multiple files, group by layer (model + repo + tests + frontend) rather than doing one file at a time across layers. If the change touches the data contract (a DTO, JSON schema), the frontend must be updated in the same commit — the contract is the seam where things break silently.

If you're uncertain about a design call, **ask the user before editing**, not after. Specifically: anything that changes API shape, locale defaults, schema fields, or deploy gates deserves a clarifying question.

### Step 3 — Build + test locally (verification point 1)

Always start with a kill-orphan-processes step. A previous `dotnet run` that didn't terminate cleanly will hold a lock on the .dll and `dotnet build` will fail confusingly:

```bash
powershell -NoProfile -Command "Get-Process <App>.Api -ErrorAction SilentlyContinue | Stop-Process -Force"
dotnet build --configuration Debug
dotnet test --no-build --no-restore --configuration Debug
```

Success criteria: zero errors, all tests pass. If a test fails on something orthogonal to your change, fix the root cause — never disable a test to make the cycle green.

### Step 4 — Smoke-test via Claude Preview (verification point 2, when available)

If `mcp__Claude_Preview__preview_start` is in the available tools, use it. This catches client-side bugs that don't surface in unit tests — JS errors, missing CSS, broken DOM state, projection bugs.

The pattern:

1. **Start the server** (the project should have `.claude/launch.json`; create it if missing, pointing at `dotnet run --no-build --project src/<App>.Api`).
2. **Eval DOM state** to confirm rendering. Wait for a known marker before measuring — e.g. SVG paths populated, modal opens after click.
3. **Take a screenshot** for visual confirmation. Use sparingly — screenshots tell you about layout and obvious breakage but lie about colors, font sizes, and small details.
4. **Inspect computed styles** via `preview_eval` for anything color/size-related instead of trusting the screenshot.
5. **Check the console** with `preview_console_logs --level error` — silence is the signal you want; any error is real.
6. **Stop the preview** before committing. Don't leave it running into Step 5 — you'll get bin lock errors when CI tries to rebuild on a stale local server. Use the `powershell ... Stop-Process -Force` pattern from Step 3.

If Claude Preview isn't available (e.g. plain Claude.ai with no MCP), skip this step but verify more carefully at Step 8.

### Step 5 — Commit with care

Read the existing log first to match the project's tone:

```bash
git log --oneline -8
```

Then read 1-2 recent multi-line commits in full (`git show <sha>`) to see the structure. The convention in this project family:

- **Imperative subject line** under ~72 chars
- Blank line
- **1-3 short paragraphs explaining the why** — not just the what. "What problem prompted this, what would the user/kid see before vs after, what's the intent."
- File paths are fine to mention; they help future-you grep the history
- `Requires:` footer when a new external resource or env var is introduced
- **No emojis** unless the user explicitly requested them
- **No `Co-Authored-By` line** unless the user requested it

Use a `HEREDOC` for multi-line messages so Windows-style line endings don't break:

```bash
git add <specific files, not -A>
git commit -m "$(cat <<'EOF'
Imperative subject line

First paragraph: the why. What problem prompted this change, what was
the user-visible symptom, what's the intended outcome.

Second paragraph: what was actually changed and where. File paths help
future-you grep for the change. Mention scripts and where they live.

Requires: <new env var, Azure resource, etc., or omit this line>
EOF
)"
```

**Never `git add -A`** — list files explicitly. This protects against accidentally committing `.env`, `appsettings.Development.json`, publish profiles, or temp artifacts. **Never `git commit --amend`** without explicit user permission. **Never `--force` push** without explicit user permission.

Files that should never be staged:
- `appsettings.Development.json` (often contains local secrets)
- `*.pubxml`, `*.PublishSettings`
- `secrets.json`
- `.claude/settings.local.json` (Claude Code per-user permission allowlist — already gitignored, but double-check on first commit)
- Anything under `publish/` or `bin/`

### Step 6 — Push

```bash
git push 2>&1 | tail -5
```

If it fails on upstream divergence or a protection rule, **stop and ask** — don't try to recover by force-pushing. The most common cause is the user pushed a hotfix from another machine since your last fetch.

### Step 7 — Watch the CI/CD run (verification point 3)

The GitHub MCP (`github` server in `.mcp.json`) is available — use MCP tools to check run status interactively. For scripted polling, use `curl` against the public GitHub API (no auth needed for public repos; rate limit is generous for polling).

```bash
REPO="<owner>/<repo>"
SHA=$(git rev-parse HEAD | cut -c1-7)
sleep 6   # let the workflow register

for i in {1..30}; do
  status=$(curl -s "https://api.github.com/repos/$REPO/actions/runs?per_page=3" | python -X utf8 -c "
import sys, json
for r in json.load(sys.stdin).get('workflow_runs', []):
    if r['head_sha'].startswith('$SHA'):
        print(f\"id={r['id']} status={r['status']} conclusion={r['conclusion']}\")
        break
else:
    print('not yet')
")
  echo "  attempt $i: $status"
  case "$status" in *"status=completed"*) break ;; esac
  sleep 8
done
```

**Critical:** the `python -X utf8` flag matters on Windows — any Cyrillic / non-ASCII content in the API response (e.g. translated commit messages, branch names with diacritics) crashes a default-codec Python with `UnicodeEncodeError: 'charmap' codec can't encode characters`. This bug bit us twice in this project. Use `-X utf8` unconditionally for any script that touches data with translations or user-supplied text.

When the run completes, drill into per-job status:

```bash
RUN_ID=$(curl -s "https://api.github.com/repos/$REPO/actions/runs?per_page=3" | python -X utf8 -c "
import sys, json
for r in json.load(sys.stdin).get('workflow_runs', []):
    if r['head_sha'].startswith('$SHA'):
        print(r['id']); break
")
curl -s "https://api.github.com/repos/$REPO/actions/runs/$RUN_ID/jobs" | python -X utf8 -c "
import sys, json
for j in json.load(sys.stdin).get('jobs', []):
    print(f'JOB: {j[\"name\"]} -> {j[\"conclusion\"]}')
    for s in j.get('steps', []):
        m = {'success':'OK','skipped':'--','failure':'XX'}.get(s['conclusion'] or '', '..')
        print(f'    [{m}] {s[\"name\"]}')
"
```

If a job fails, read the workflow YAML to understand which step blew up. Most common failure points:

- `azure/login@v2` failed → check the five GitHub variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_WEBAPP_NAME`, `DEPLOY_ENABLED`) and the federated-credential subject in Azure (`az identity federated-credential list -g <rg> --identity-name <uami>` → subject must be `repo:<owner>/<repo>:environment:production` exactly)
- `azure/webapps-deploy@v3` failed → usually a malformed zip from a custom-built artifact; the v3 action from a Linux runner produces the correct layout, so most failures here mean the artifact wasn't downloaded properly in the previous step
- Tests failed → a real regression in the change you just pushed
- Restore failed with NU1301 / 401 → corporate NuGet feed is set globally; the project's `NuGet.config` should clear and re-add only `nuget.org`

### Step 8 — Verify the live site (verification point 4)

After CI/CD reports success, hit the live site to confirm the deploy actually landed:

```bash
APP_URL="https://<app>.azurewebsites.net"

# Health endpoint — always the first probe
curl -s -o /dev/null -w "HTTP %{http_code}, latency %{time_total}s\n" $APP_URL/health

# An endpoint that exercises the specific change you made
curl -s $APP_URL/api/<endpoint> | python -X utf8 -m json.tool | head -20
```

**Latency note:** the first request after a quiet period on F1 Free tier takes ~25-30 seconds because of cold start. This is normal; wait it out, then re-hit to confirm warm response (200-500 ms). Don't try to "fix" a 28-second first response — there is nothing to fix.

If the live response doesn't reflect your change, possible causes (in order of probability):
1. App Service hasn't yet picked up the new files (rare; 10-30 s lag after deploy step reports success — wait, retry)
2. The deploy step landed but the artifact was stale (you pushed before the previous run completed — check the SHA the deploy job actually deployed)
3. Browser cache, if the user is verifying from a browser (hard refresh)

### Step 9 — Update the todos and report

Mark all todos completed. Summarize concisely:
- What changed (1 sentence)
- Test results (X/X passed)
- CI/CD duration (you have it from the API response — extract `created_at` and `updated_at`)
- Live site verification result
- Anything the user should verify manually (e.g. "tap a country on your phone to confirm the modal opens")

## Conventions specific to this project family

**Tooling expectations:**
- GitHub MCP configured (`.mcp.json`) — use MCP tools for GitHub interactions; fall back to `curl` + `python -X utf8` in CI scripts
- `TodoWrite` for any multi-step work
- Claude Preview MCP for frontend smoke tests when available
- `az` CLI for Azure; **never** `az role assignment create` if it errors with `MissingSubscription` — see `references/gotchas.md` for the `az rest` workaround

**Writing style:**
- No emojis in code, comments, or commit messages unless the user requested them
- No purple prose in commit messages — short, declarative, explains the why
- TODO comments in code are fine when scoped to a known follow-up (e.g. "Week 5 swap to TopoJSON, see FUTURE.md")
- Match existing tone — always read `git log --oneline -8` and one or two full commits before composing a new one

**Tools to NOT use unless asked:**
- `git add -A` (use explicit file lists)
- `git commit --amend` (always make a new commit)
- `git push --force` (always coordinate with user)
- `--no-verify` to skip hooks (investigate the hook failure first)

**Things to verify on first run** in a new clone of the project:
- `.gitignore` excludes `.claude/settings.local.json` (Claude Code adds it automatically; it doesn't belong in the public repo)
- `Microsoft.ApplicationInsights.AspNetCore` is pinned to **2.22.0** (the classic SDK that silently no-ops without a connection string) — version 3.x throws on startup without a config

## When something goes wrong

Specific failure modes have specific known fixes. Load `references/gotchas.md` whenever you hit one of these symptoms:

- `MissingSubscription` from `az role assignment create/list/show`
- AD app creation blocked with `Insufficient privileges` (corporate tenant policy)
- `az webapp deploy --type zip` fails with `rsync … Invalid argument (22)` errors
- `dotnet build` fails with file-lock errors on `*.dll`
- `dotnet test` fails with `FileNotFoundException` for data files when run from the test project
- d3-geo polygons paint the whole sphere instead of their actual shapes
- An external GeoJSON fetch hangs forever on the user's corporate proxy
- Python script crashes with `UnicodeEncodeError: 'charmap' codec`
- Application Insights tests fail with `connection string was not found`

The gotchas file has the exact symptom → root cause → fix for each.

## Recovery if you skipped a step

If you realize mid-cycle you skipped a step:
- Skipped tests → run them now before continuing. If they fail, the next commit is `revert` + fix, not "push and pray"
- Skipped Claude Preview smoke → still time to run it before pushing, even if you've committed locally; uncommitted changes aren't the only thing that matters
- Skipped CI/CD watch → just go to Step 7 now and retroactively poll for the run
- Skipped live verification → do it now; if the deploy is broken, your next action is a rollback commit, not a "let me just fix it forward"

The cycle is forgiving as long as you don't lie to the user about what you actually verified. If you didn't run a step, say so when reporting.

# Project-specific Claude skills

Two skills bundled with this repository:

- **`iterative-azure-deploy/`** — the change-test-commit-push-verify cycle for shipping EduMap changes to Azure App Service via the GitHub Actions OIDC pipeline. Plus a `references/gotchas.md` catalogue of specific error fixes (the `MissingSubscription` workaround, the d3-geo CW winding bug, the App Service zip backslash issue, etc.).
- **`edumap-localization/`** — adding or extending translations and audio for EduMap. Schema conventions, frontend rendering machinery, and three ready-to-run scripts (`scripts/translate-names-capitals.py`, `scripts/translate-fun-facts.py`, `scripts/generate-audio.py`) that automate the bulk-translation chunks described in `FUTURE.md`.

Both skills are intended to be loaded by Claude Code when working on this repo. They live in the repo (rather than a user-global location) because they're specific to EduMap's architecture, conventions, and gotchas.

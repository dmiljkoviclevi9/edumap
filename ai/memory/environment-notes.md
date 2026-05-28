# Environment Notes

Persistent memory of setup issues, config surprises, and platform-specific notes.
Entries in reverse chronological order. Cap: 200 lines.

Format:
```
## [YYYY-MM-DD] Title
**Context**: What was happening
**Discovery**: What was learned
**Resolution**: What to do about it
```

---

## [2026-05-28] az role assignment create returns MissingSubscription on Azure CLI 2.84.0

**Context**: Trying to assign the Website Contributor role to the UAMI via `az role assignment create`.

**Discovery**: Azure CLI 2.84.0 returns a misleading `MissingSubscription` error when assigning roles, even with a fully-qualified scope. `az role assignment list/show` is also affected.

**Resolution**: Use `az rest --method put` against the ARM REST API directly. Example in `WALKTHROUGH.md` section 2.2. This is a CLI bug; the ARM API itself works correctly.

---

## [2026-05-28] DEPLOY_ENABLED variable gates the deploy job

**Context**: Pushing to main triggered a deploy before Azure resources were ready.

**Discovery**: The deploy job in `.github/workflows/ci-cd.yml` checks `vars.DEPLOY_ENABLED == 'true'`. When bootstrapping Azure infrastructure, set this to `false` so pushes run build-test only.

**Resolution**: Set `DEPLOY_ENABLED = false` in GitHub repo variables while provisioning Azure. Set it to `true` when App Service is ready. The build-test job always runs regardless.

---

## [2026-05-28] F1 Free tier cold start is ~28 seconds

**Context**: First request to the app after an idle period returned slowly.

**Discovery**: Azure App Service Free F1 scales to zero. The first request after idle wakes the process — ~28 s warm-up time. This is normal behavior, not a bug.

**Resolution**: Don't flag a slow first request as a performance regression. The deploy step warms the app. For demo purposes, open the site before the audience arrives.

---

## [2026-05-28] Python cp1252 crashes on Cyrillic output — Windows only

**Context**: Running `scripts/translate-names-capitals.py` on Windows without UTF-8 mode.

**Discovery**: Windows defaults Python's stdout/stderr to cp1252. Printing any Cyrillic character throws `UnicodeEncodeError: 'charmap' codec can't encode character`.

**Resolution**: Always run: `python -X utf8 script.py`. Or set environment variable `PYTHONUTF8=1` permanently. This affects all scripts in `scripts/` that handle Serbian Cyrillic data.

---

## [2026-05-28] Wikidata SPARQL returns Latin-script fallback for some sr-Cyrl queries

**Context**: Running Chunk B translation script against Wikidata.

**Discovery**: Wikidata's label service falls back through `sr-Cyrl → sr → en` chains. Some country capitals return their Serbian Latin (sr) transcription or even the English name when no Cyrillic label exists in Wikidata.

**Resolution**: After the Wikidata fetch, filter out any returned capital that doesn't contain Cyrillic characters. Countries that fail this filter stay with the English fallback. Maintain a small `scripts/capitals-overrides.json` for known problematic cases. Apply overrides AFTER the Wikidata pass.

---

## [2026-05-28] F0 Cognitive Services per-region uniqueness constraint

**Context**: Attempting to provision a second F0 TextTranslation account for testing.

**Discovery**: Azure allows only ONE F0 account per Cognitive Services kind per region per subscription. Trying to create a second one returns a quota error.

**Resolution**: Reuse `cs-edumap-translator` in `rg-edumap`. If Speech Services are needed later, they're a different kind and can coexist as F0 in the same region. Standard S1 tier can be used if a second account of the same kind is genuinely needed.

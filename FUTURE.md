# Edu-Map: Future Work — Translation & Audio

Three follow-up chunks for the kids' world map. Each is independently shippable, lands as one commit, and exercises the existing OIDC-authenticated GitHub Actions → Azure App Service pipeline.

This file is **prompt material**: paste the block below into a new Claude session and let it execute one chunk at a time.

---

## Bootstrap prompt — copy this into a new Sonnet session

```
You're continuing work on Edu-Map (https://edumap-miljkovici.azurewebsites.net),
my kids' interactive world map deployed to Azure App Service from
github.com/dmiljkoviclevi9/EduMap. It's also the project I use as the
practical track for a Levi9 Azure & .NET training.

Before you touch anything, read these in order to build context — they're
the authoritative source for the project's state and conventions:

  1. FUTURE.md         (this file — lists the chunks below)
  2. PLAN.md           (original architecture + Claude design prompt)
  3. WALKTHROUGH.md    (Azure-side runbook — what's provisioned, OIDC setup)
  4. src/EduMap.Api/Models/Country.cs               (the data contract)
  5. src/EduMap.Api/Services/CountryRepository.cs   (how data is loaded)
  6. src/EduMap.Api/wwwroot/index.html              (renderer + i18n)
  7. src/EduMap.Api/Data/countries.json             (the data itself —
     skim the first ~50 lines for shape, don't read all 250 entries)

Then ask me which chunk to start (B, C, or D from FUTURE.md). Do NOT
silently chain chunks — each one is its own commit + push + CI/CD round
trip + my approval before the next. After each chunk:

  - run `dotnet test` and confirm 4/4 pass
  - load the live site via curl /api/countries/RS and check the new
    translation/audio fields appear
  - write a commit message in the style of the existing git log (read
    `git log --oneline -8` for the tone — present tense, specific,
    mentions the "why" not just the "what")
  - push to main and confirm the deploy job goes green via the GitHub
    REST API (the gh CLI is NOT installed; use curl against
    api.github.com/repos/.../actions/runs)

If you hit a real corporate-tenant limitation (e.g. can't create a
Cognitive Services account because of policy), stop and ask — don't
silently fall back to a worse approach.
```

---

## Project context (so you don't have to re-read the whole conversation)

**What Edu-Map is.** A children's interactive world map. Tap a country, modal shows flag + name + capital + funFact, optionally plays an audio clip of the country name. Primary audience: my kids, who can't read Latin letters yet, so the default locale is Serbian Cyrillic (`sr-Cyrl`). English (`en`) is the canonical source data and the debug-mode fallback (`?lang=en`).

**Tech stack.** .NET 10 Minimal API on Azure App Service Free F1, static frontend (vanilla JS + d3-geo + Equal Earth projection) served from `wwwroot/`, country/UK/world GeoJSON self-hosted in `wwwroot/data/`. CI/CD via GitHub Actions with OIDC federated to a User-Assigned Managed Identity (`mi-edumap-github` in `rg-edumap`, clientId `fe9a3ff5-fbdb-431f-a5c8-3f0e1061f3f4`). No publish profile, no client secret — just five GitHub repo *variables* (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_WEBAPP_NAME`, `DEPLOY_ENABLED`).

**Azure context.**
| Resource | Name | Notes |
|---|---|---|
| Subscription | `Damir` | `706589ae-fa0c-46d3-957f-e12535bc3deb` |
| Tenant | Levi9 | `40758481-7365-442c-ae94-563ed1606218` |
| Resource group | `rg-edumap` | Damir is Owner — full RBAC |
| App Service plan | `plan-edumap` | F1 Free, Linux, westeurope |
| App Service | `edumap-miljkovici` | DOTNETCORE:10.0 |
| UAMI | `mi-edumap-github` | Website Contributor on the App Service only |

**Levi9 tenant caveat.** AD application creation is blocked for non-admins; that's why we use a UAMI rather than an AD app + service principal. Cognitive Services account creation has worked in this RG so far — provision under `rg-edumap` so the same OIDC identity can be expanded to access them (you'll need to grant the UAMI a Reader role on the new resource if the workflow needs to call it).

---

## What's been built (so you don't duplicate work)

**Schema** — `Country` DTO in `Models/Country.cs` has an optional `Translations` dictionary keyed by BCP-47 tag, with `Name / Capital / FunFact / AudioUrl` overrides per locale. The C# record is a `Dictionary<string, CountryTranslation>?`; System.Text.Json serializes it as a camelCase `translations` object.

**Data** — `Data/countries.json` is the canonical source. English at the top level, `translations.sr-Cyrl` filled in for **12 starter countries**: RS, MR, US, GB, DE, FR, IT, JP, AU, HR, HU, BG. The remaining ~240 have no translations block — the frontend falls back to English for those.

**Frontend** — `wwwroot/index.html` reads `?lang=` URL param (default `sr-Cyrl`), has a `UI_STRINGS` table for both locales (loader, toast, aria-labels, alt text), a `tr(country, field)` helper with English fallback, and an `applyUiStrings()` function that runs at script start to localize the chrome before the GeoJSON arrives.

**You can verify the current state in 10 seconds:**
```bash
curl -s https://edumap-miljkovici.azurewebsites.net/api/countries/RS | python -X utf8 -m json.tool
# Should show translations.sr-Cyrl with Cyrillic name/capital/funFact
```

---

## Chunk B — Bulk CLDR + Wikidata translations

**Goal.** Fill in `translations.sr-Cyrl.name` and `.capital` for all ~239 not-yet-translated countries. Leave `funFact` alone (that's Chunk C). Leave `audioUrl` alone (that's Chunk D). Never overwrite the 12 hand-curated entries.

**No new Azure resources required.** Local script run, commit, push.

**Files to read first:**
- `src/EduMap.Api/Data/countries.json` — the existing 12 translated entries (find one like `RS` to copy structure)
- `src/EduMap.Api/Models/Country.cs` — confirm shape

**Steps:**

1. Write `scripts/translate-names-capitals.py`. It must:
   - Fetch CLDR territories from
     `https://github.com/unicode-org/cldr-json/raw/main/cldr-json/cldr-localenames-modern/main/sr-Cyrl/territories.json`
     (path is the value at `main["sr-Cyrl"].localeDisplayNames.territories`, a dict of `"AD": "Андора"`).
   - Fetch capitals via Wikidata SPARQL — query below returns ISO-2 → Serbian Cyrillic capital label for all sovereign + territory entities that have an ISO code. Use endpoint `https://query.wikidata.org/sparql` with `Accept: application/sparql-results+json`. Always include a User-Agent header naming the project — Wikidata rate-limits anonymous requests.

     ```sparql
     SELECT ?iso ?capitalLabel WHERE {
       ?country wdt:P297 ?iso .
       ?country wdt:P36 ?capital .
       SERVICE wikibase:label {
         bd:serviceParam wikibase:language "sr-Cyrl,sr,en".
       }
     }
     ```

   - Load `Data/countries.json`, loop each country, **only add fields that are missing**. Existing translations.sr-Cyrl.name and .capital take precedence — never overwrite. Skip countries with no CLDR territory entry.
   - Write the JSON back with `ensure_ascii=False`, `indent=2`, trailing newline. Preserve key order.

2. Run the script. Verify the diff on `countries.json` looks sane (Serbian Cyrillic strings, no destruction of existing entries). Spot-check a few: Indonesia → "Индонезија" / "Џакарта", Egypt → "Египат" / "Каиро".

3. **Per-locale lang attribute on the SPARQL label**. Wikidata returns the best available label following the fallback chain `sr-Cyrl → sr → en`. Filter out any results where the returned label is still in Latin (i.e. didn't have a `sr-Cyrl` form). Those countries should fall through to your hand-curated list (or stay English-fallback).

4. Optional polish: small hand-curated JSON at `scripts/capitals-overrides.json` for ones Wikidata gets wrong or returns in Latin script. Have the script apply this AFTER Wikidata, before write.

**Verification:**
- `dotnet test` → 4/4
- `curl /api/countries | jq '[.[] | select(.translations."sr-Cyrl".name)] | length'` should return ~240, not 12
- Load the live site after deploy, click ~5 random countries — each should show Cyrillic name + capital, English funFact (unchanged)

**Commit message template:**
```
Bulk-translate country names + capitals to sr-Cyrl via CLDR + Wikidata

Adds translations.sr-Cyrl.{name,capital} for ~240 countries that the
i18n-scaffolding commit left untranslated. Source: CLDR for names
(authoritative for locale-aware display), Wikidata SPARQL for capitals.
Existing hand-curated entries (RS, MR, US, GB, DE, FR, IT, JP, AU, HR,
HU, BG) are left untouched.

funFacts remain English — Chunk C (Azure Translator) handles those.
audioUrls remain null — Chunk D (Azure Speech TTS) handles those.

Script: scripts/translate-names-capitals.py, re-runnable, idempotent.
```

**Estimated time:** 1 hour.

---

## Chunk C — Fun fact translations via Azure Translator

**Goal.** Auto-translate `funFact` from English to Serbian Cyrillic for every country. Quality won't be perfect — the kid-friendly phrasing often gets lost. The script must be re-runnable so I can edit individual entries by hand without re-translating the ones I've already polished.

**New Azure resource required.** Cognitive Services / Azure AI Services account.

**Prerequisites (Azure):**
```powershell
$RG = "rg-edumap"
$LOCATION = "westeurope"

# Free tier (F0) gives 2M chars/month — way more than we need
az cognitiveservices account create `
  -g $RG -n cs-edumap-translator `
  --kind TextTranslation --sku F0 -l $LOCATION --yes

# Capture key + endpoint
$KEY = az cognitiveservices account keys list -g $RG -n cs-edumap-translator --query key1 -o tsv
$REGION = (az cognitiveservices account show -g $RG -n cs-edumap-translator --query location -o tsv)
```

Don't commit the key. Pass via environment variable to the script: `TRANSLATOR_KEY`, `TRANSLATOR_REGION`.

**API contract:**
- Endpoint: `https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to=sr-Cyrl`
- Headers: `Ocp-Apim-Subscription-Key: $KEY`, `Ocp-Apim-Subscription-Region: $REGION`, `Content-Type: application/json`
- Body: `[{"Text": "Has trains 2 km long..."}, ...]` — up to 100 items per request, 50,000 chars total per request. Batch in chunks of 50.
- Response: array of `{"translations": [{"text": "...", "to": "sr-Cyrl"}]}` in input order.

**Files to read first:**
- `src/EduMap.Api/Data/countries.json` — confirm any existing `translations.sr-Cyrl.funFact` entries (the 12 hand-curated ones)

**Steps:**

1. Write `scripts/translate-fun-facts.py`. It must:
   - Read `TRANSLATOR_KEY` and `TRANSLATOR_REGION` from env, fail-fast if missing.
   - Load `Data/countries.json`. Collect a list of `(iso2, english_funFact)` tuples where the country has a `funFact` AND `translations.sr-Cyrl.funFact` is null/absent (idempotent — never re-translates an already-translated entry).
   - Batch 50 at a time, POST to Translator, parse responses.
   - Write `translations.sr-Cyrl.funFact` for each, preserving any existing field (so re-runs don't clobber hand-edits).
   - Write the JSON back identically to Chunk B.

2. Run it. Quickly scan 10 random outputs — if more than half read robotically, consider tuning. Translator has a `category` parameter you can use to nudge towards children's content, but Microsoft hasn't trained a child-specific model for `sr-Cyrl` so this is mostly cosmetic.

3. Land the script. Tag any obviously broken outputs in a follow-up TODO comment in `countries.json` — they're cheaper to fix manually than to try to coax Translator into better output.

**Verification:**
- `dotnet test` → 4/4
- `curl /api/countries | jq '[.[] | select(.translations."sr-Cyrl".funFact)] | length'` should return ~240
- Load the live site, click 5 untranslated-before countries — each should show a Cyrillic funFact (even if slightly awkward)

**Commit message template:**
```
Translate funFacts to sr-Cyrl via Azure AI Translator

Adds translations.sr-Cyrl.funFact for the ~240 countries left without
one after Chunk B. Source: Azure AI Translator F0 (free tier, 2M
chars/month, well under our 240 × ~15 word usage). Existing hand-curated
funFacts are not re-translated.

Quality is "understandable but not always idiomatic" — the
scripts/translate-fun-facts.py script is re-runnable so refining a
specific entry is just edit-and-commit. The 12 starter countries with
hand-written funFacts are unchanged.

Requires: az cognitiveservices account 'cs-edumap-translator' (F0),
TRANSLATOR_KEY + TRANSLATOR_REGION env vars at script-run time.
```

**Estimated time:** 1 hour after the Cognitive Services account is provisioned.

---

## Chunk D — Audio playback + Azure Speech TTS

**Goal.** When the modal opens, play an audio file of the country name in Serbian. Hybrid strategy: Azure AI Speech generates a TTS clip for every country first; any country where I drop a manually-recorded `.mp3` later overrides the TTS automatically.

**New Azure resource required.** Speech service.

**Prerequisites (Azure):**
```powershell
$RG = "rg-edumap"
$LOCATION = "westeurope"

az cognitiveservices account create `
  -g $RG -n cs-edumap-speech `
  --kind SpeechServices --sku F0 -l $LOCATION --yes

$KEY = az cognitiveservices account keys list -g $RG -n cs-edumap-speech --query key1 -o tsv
$REGION = (az cognitiveservices account show -g $RG -n cs-edumap-speech --query location -o tsv)
```

Don't commit the key. `SPEECH_KEY`, `SPEECH_REGION` env vars.

**API contract:**
- Endpoint: `https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1`
- Headers: `Ocp-Apim-Subscription-Key: $KEY`, `Content-Type: application/ssml+xml`, `X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3`, `User-Agent: edumap-tts`
- Body (SSML):
  ```xml
  <speak version='1.0' xml:lang='sr-RS'>
    <voice name='sr-RS-SophieNeural'>Србија</voice>
  </speak>
  ```
- Response: raw MP3 bytes.

**Voice choice.** `sr-RS-SophieNeural` (female) and `sr-RS-NicholasNeural` (male) are both available. Kids tend to respond better to friendly female voices for narration — default Sophie unless I object. Both are neural voices in the free tier.

**Files to read first:**
- `src/EduMap.Api/wwwroot/index.html` — find `openModal` (~line 680) to wire the audio playback
- `src/EduMap.Api/Data/countries.json` — confirm `audioUrl` field shape (`translations.sr-Cyrl.audioUrl`)
- `.dockerignore` — ensure `wwwroot/audio/` is included in the Docker build context

**Steps:**

1. **TTS script** — `scripts/generate-audio.py`. It must:
   - Read `SPEECH_KEY` + `SPEECH_REGION` from env, fail-fast.
   - Load `Data/countries.json`. For each country with `translations.sr-Cyrl.name`:
     - Target file path: `src/EduMap.Api/wwwroot/audio/sr-Cyrl/{iso2-lowercase}.mp3`
     - **Skip if file already exists** — protects manual recordings AND saves API quota on re-runs.
     - POST SSML to Speech endpoint, save response body to file.
   - Update each country's `translations.sr-Cyrl.audioUrl` to `/audio/sr-Cyrl/{iso2}.mp3` after the file is created (so the frontend knows it exists).
   - Print a summary: `N generated, M skipped (existing), K failed`.

2. **Frontend hook** in `openModal`:

   ```js
   // Right after setting flagImg.src:
   const localizedTrans = c.translations && c.translations[LANG];
   if (localizedTrans && localizedTrans.audioUrl) {
     // Use a singleton so a fast double-tap doesn't overlap audio.
     if (window._edumapAudio) { window._edumapAudio.pause(); }
     const audio = new Audio(localizedTrans.audioUrl);
     window._edumapAudio = audio;
     audio.play().catch(() => {/* autoplay blocked — ignore */});
   }
   ```

   The play attempt is wrapped in `.catch()` because some browsers block autoplay even after a user gesture; falling back silently is fine, the modal still works visually.

3. **Replay button** (optional but kid-friendly) — small `🔊` button in the modal, click → replay. Add to the modal HTML in `index.html`, hide via CSS when `audioUrl` is absent.

   ```html
   <button class="replay-btn" id="replay-btn" aria-label="..." hidden>🔊</button>
   ```

   Localize the aria-label in `UI_STRINGS`: `en: "Hear it again"`, `sr-Cyrl: "Чуј поново"`.

4. **CSS** — match the existing modal style. ~44×44 px touch target. Place near the flag.

5. **Static file middleware** — ASP.NET Core's `app.UseStaticFiles()` already serves `wwwroot/audio/` because it's under wwwroot. No backend change needed.

6. **Repo size sanity** — 240 × ~15 KB MP3s = ~3.5 MB total. Acceptable to commit. If it grows past 50 MB at any point, switch to Azure Blob Storage with public-read access and update `audioUrl` to point there.

**Verification:**
- `dotnet test` → 4/4
- `curl -I /audio/sr-Cyrl/rs.mp3` from the live site → 200, ~15 KB
- Open the live site, tap Serbia, hear "Србија" — confirm the audio actually plays in iOS Safari (the strictest browser for autoplay)
- Drop in a manual recording at the same path, re-run script, confirm script skips (existing file)

**Commit message template:**
```
Add Serbian audio playback for country names (Azure Speech TTS)

Modal now plays a TTS clip of the country's localized name when opened.
Generates one MP3 per translated country using Azure AI Speech's
sr-RS-SophieNeural voice and stores it at /audio/sr-Cyrl/{iso2}.mp3.
The frontend uses a singleton Audio element so rapid country-tapping
doesn't overlap clips.

The generator script (scripts/generate-audio.py) is idempotent and
skips any file that already exists — so I can swap in my own
recordings for any country by dropping a same-named MP3 in the folder
and the next regen will leave it alone.

Includes a small 🔊 replay button in the modal (hidden when no audio
is available) so kids can re-hear the country name on demand.

Requires: az cognitiveservices account 'cs-edumap-speech' (F0),
SPEECH_KEY + SPEECH_REGION env vars at script-run time.
```

**Estimated time:** 2 hours after the Speech account is provisioned.

---

## Conventions you should follow

**File layout for scripts.** Put one-off translation/generation scripts under `scripts/`. They aren't shipped with the app; the `.dockerignore` should already exclude them, but double-check.

**Commit style.** Read `git log --oneline -8` for the existing tone. Pattern: imperative subject line under ~72 chars, then a few short paragraphs explaining the **why** (not just the what), and a `Requires:` footer when a new external resource (Azure CS account, secret) is introduced.

**CI/CD verification (no `gh` CLI installed).** Use the GitHub REST API anonymously since the repo is public:

```bash
SHA=$(git rev-parse HEAD | cut -c1-7)
sleep 5
for i in {1..30}; do
  curl -s "https://api.github.com/repos/dmiljkoviclevi9/EduMap/actions/runs?per_page=3" \
    | python -X utf8 -c "
import sys, json
for r in json.load(sys.stdin).get('workflow_runs', []):
    if r['head_sha'].startswith('$SHA'):
        print(f\"{r['status']}/{r['conclusion']}\"); break
else: print('not yet')"
  sleep 8
done
```

When you see `completed/success`, hit `https://edumap-miljkovici.azurewebsites.net/health` to confirm the deploy landed.

**Don't commit secrets.** Cognitive Services keys via env vars only. Never log them. The `.gitignore` already excludes `appsettings.*.json` except `appsettings.json` and `appsettings.Development.json` — if you ever need a runtime config that mentions a key, put it in `appsettings.Development.json` (untracked) or App Service Configuration.

---

## Known gotchas (skim before coding)

- **d3-geo winding bug.** Polygons whose exterior ring is clockwise read as "everything except this shape" on the sphere — covering the whole world. We fix this with `rewindFeature` in `index.html` operating **per polygon** (not per feature — MultiPolygons can have mixed winding). If you ever swap GeoJSON datasets, verify the rewind catches anything wrong by checking `d3.geoPath(projection).bounds({type:"Sphere"})` against individual feature bounds.

- **`az role assignment create` MissingSubscription.** Azure CLI 2.84.0 returns the misleading "MissingSubscription" error when assigning roles, even on scopes with full ID. Workaround: use `az rest --method put` against the ARM REST API directly (example in `WALKTHROUGH.md` section 2.2). Plain `az role assignment list/show` is also affected.

- **Translation fallback chain.** Frontend's `tr(country, field)` returns `country.translations[LANG][field] || country[field]`. If a translation is present but empty string, it falls back to English — make sure your scripts write `null` or omit the field when no translation is available, not `""`.

- **F1 Free tier cold start.** ~28 s after idle. Don't be alarmed by a slow first request after a quiet hour. The CI/CD pipeline's deploy step warms it back up.

- **F0 Cognitive Services per-region uniqueness.** You can only have ONE F0 account per kind per region per subscription. If Translator F0 already exists in westeurope, create the Speech one there too (they're different kinds) — no collision. If you ever need two of the same kind, use Standard (S1) which costs pennies.

- **iOS Safari autoplay policy.** Audio playback inside the click handler of a user tap is allowed. Audio playback in setTimeout / setInterval / async-after-await is sometimes blocked. The `openModal` hook fires inside the same task as the click handler, so it works — but if you refactor that, watch out.

- **Cyrillic console encoding on Windows.** Python on Windows defaults to cp1252 which can't print Cyrillic; if your script does `print(some_cyrillic_string)` it'll explode. Run scripts with `python -X utf8 ...` or `PYTHONUTF8=1`.

---

## When you ship a chunk, also update these

- **WALKTHROUGH.md** — Week 4 already covers monitoring/Application Insights; Chunks C and D create real Cognitive Services accounts that are great course material. Add a brief "Translator + Speech" sub-section to Week 4 listing the provisioning commands.

- **PLAN.md** — has an i18n-shaped hole. Once all three chunks ship, update the project summary so future readers understand sr-Cyrl is the default locale, not English.

- **README.md** — doesn't exist yet. Optional follow-up: add a minimal one pointing at this file + PLAN.md + WALKTHROUGH.md.

- **This file** — delete or strike-through any chunk after it ships, so a future session doesn't redo work.

---

## Order of operations recommendation

**Do B first** — no Azure resource needed, immediate kid-visible win (every country gets a Serbian name + capital). C and D both need Cognitive Services accounts; provision them together in one Azure side-trip, then knock out C and D in a single session.

So a clean two-session plan:
- **Session A**: Chunk B alone. ~1 h.
- **Session B**: Provision Translator + Speech (~10 min). Chunk C (~1 h). Chunk D (~2 h). Total ~3 h.

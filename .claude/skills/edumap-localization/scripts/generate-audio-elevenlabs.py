#!/usr/bin/env python3
# generate-audio-elevenlabs.py
# Generates one MP3 per country name using ElevenLabs TTS.
# Only fills countries that have translations.<locale>.name but no audioUrl.
# Idempotent: existing MP3 files on disk are never overwritten.
#
# Usage:
#   export ELEVENLABS_API_KEY=sk_...
#   python -X utf8 generate-audio-elevenlabs.py --locale sr-Cyrl
#
# Optional env overrides:
#   ELEVENLABS_VOICE_ID  (default: Charlotte — warm multilingual female)
#   ELEVENLABS_MODEL     (default: eleven_multilingual_v2 — handles Serbian Cyrillic)
#
# Dry run (no API calls, no writes):
#   python -X utf8 generate-audio-elevenlabs.py --locale sr-Cyrl --dry-run
#
# Cap a run to N countries (useful for testing quota cost):
#   python -X utf8 generate-audio-elevenlabs.py --locale sr-Cyrl --limit 10

import os, sys, json, time, pathlib, argparse, random
import urllib.request, urllib.error

# ---------------------------------------------------------------------------
# Voice / model defaults — change ELEVENLABS_VOICE_ID env var to override.
# Charlotte (XB0fDUnXU5powFXDhCwa): warm multilingual female, clear Serbian.
# eleven_multilingual_v2: best ElevenLabs model for Slavic languages.
# ---------------------------------------------------------------------------
DEFAULT_VOICE_ID = "XB0fDUnXU5powFXDhCwa"
DEFAULT_MODEL    = "eleven_multilingual_v2"

VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
MODEL_ID = os.getenv("ELEVENLABS_MODEL",    DEFAULT_MODEL)
API_KEY  = os.getenv("ELEVENLABS_API_KEY",  "")

API_BASE      = "https://api.elevenlabs.io"
TTS_URL       = f"{API_BASE}/v1/text-to-speech/{VOICE_ID}"
QUOTA_URL     = f"{API_BASE}/v1/user/subscription"
RATE_DELAY    = 0.4   # seconds between requests (well under ElevenLabs rate limit)
MAX_RETRIES   = 3


def require_api_key() -> None:
    if not API_KEY:
        sys.exit("Error: ELEVENLABS_API_KEY environment variable is not set.\n"
                 "  export ELEVENLABS_API_KEY=sk_...")


def fetch_quota() -> tuple[int, int]:
    req = urllib.request.Request(
        QUOTA_URL,
        headers={"xi-api-key": API_KEY, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("character_count", 0), data.get("character_limit", 0)
    except Exception as e:
        print(f"  Warning: could not fetch quota — {e}")
        return 0, 0


def tts(text: str) -> bytes:
    """Call ElevenLabs TTS. Returns raw MP3 bytes. Raises RuntimeError on failure."""
    body = json.dumps({
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
    }).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(
            TTS_URL,
            data=body,
            headers={
                "xi-api-key":   API_KEY,
                "Content-Type": "application/json",
                "Accept":       "audio/mpeg",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 15 * attempt
                print(f"  Rate limited (429), waiting {wait}s…")
                time.sleep(wait)
            elif e.code in (500, 502, 503) and attempt < MAX_RETRIES:
                print(f"  Server error {e.code}, retry {attempt}/{MAX_RETRIES}…")
                time.sleep(3)
            else:
                raise RuntimeError(f"ElevenLabs {e.code}: {e.reason}") from e

    raise RuntimeError("ElevenLabs TTS failed after max retries")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ElevenLabs TTS audio for EduMap country names."
    )
    parser.add_argument("--locale",    default="sr-Cyrl",
                        help="BCP-47 locale key in countries.json (default: sr-Cyrl)")
    parser.add_argument("--data-file", default="src/EduMap.Api/Data/countries.json",
                        help="Path to countries.json (relative to repo root)")
    parser.add_argument("--audio-dir", default="src/EduMap.Api/wwwroot/audio",
                        help="Output root; files land at <audio-dir>/<locale>/<iso2>.mp3")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print what would be generated; don't call the API")
    parser.add_argument("--limit",     type=int, default=0,
                        help="Stop after N generations (0 = no limit; useful for quota tests)")
    args = parser.parse_args()

    if not args.dry_run:
        require_api_key()

    data_path  = pathlib.Path(args.data_file)
    audio_root = pathlib.Path(args.audio_dir) / args.locale
    audio_root.mkdir(parents=True, exist_ok=True)

    with open(data_path, encoding="utf-8") as f:
        countries = json.load(f)

    # Candidates: have a localized name, no audio file on disk yet.
    candidates = []
    for c in countries:
        t = (c.get("translations") or {}).get(args.locale)
        if not t:
            continue
        name = (t.get("name") or "").strip()
        if not name:
            continue
        mp3_path = audio_root / f"{c['iso2'].lower()}.mp3"
        if mp3_path.exists():
            continue  # already done — idempotent
        candidates.append((c, t, name, mp3_path))

    total = len(candidates)
    if args.limit:
        candidates = candidates[:args.limit]

    print(f"Locale    : {args.locale}")
    print(f"Voice     : {VOICE_ID}  model: {MODEL_ID}")
    print(f"Candidates: {total}  |  Generating: {len(candidates)}")

    if not args.dry_run and candidates:
        used, limit = fetch_quota()
        if limit:
            print(f"Quota     : {used:,} / {limit:,} chars used this month")
        char_est = sum(len(n) for _, _, n, _ in candidates)
        print(f"Char est  : ~{char_est} for this run")
        if limit and (used + char_est) > limit * 0.90:
            print("WARNING: this run may approach your monthly character limit!")

    ok = fail = 0
    for c, t, name, mp3_path in candidates:
        iso2 = c["iso2"].lower()
        if args.dry_run:
            print(f"  DRY  {iso2:5s}  \"{name}\"")
            ok += 1
            continue

        print(f"  {iso2:5s}  \"{name}\" … ", end="", flush=True)
        try:
            mp3_bytes = tts(name)
            mp3_path.write_bytes(mp3_bytes)
            t["audioUrl"] = f"/audio/{args.locale}/{iso2}.mp3"
            print(f"OK ({len(mp3_bytes):,} B)")
            ok += 1
        except Exception as e:
            print(f"FAIL — {e}")
            fail += 1

        time.sleep(RATE_DELAY)

    if ok and not args.dry_run:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {data_path}")

    print(f"\nResult: {ok} generated, {fail} failed  (of {len(candidates)} attempted)")


if __name__ == "__main__":
    main()

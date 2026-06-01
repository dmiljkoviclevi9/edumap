#!/usr/bin/env python3
"""
Generate MP3 clips of country names in the target locale using Azure AI
Speech (text-to-speech). Saves to wwwroot/audio/<locale>/<iso2>.mp3 and
updates `translations.<locale>.audioUrl` in countries.json.

Idempotent on two axes:
  - File-system: if the target .mp3 already exists, the script skips it.
    This protects any manual recording you've dropped in to override TTS.
    The audioUrl field is still set if it's not already pointing at the
    file, so the JSON catches up to reality.
  - Data: countries without `translations.<locale>.name` are skipped
    entirely — no point synthesizing audio for a name you don't have.

Hybrid TTS + manual recording workflow:
  1. Run this script to get a baseline TTS clip for every translated country.
  2. Replace any country's clip with your own voice by dropping a same-named
     .mp3 into wwwroot/audio/<locale>/. The next time this script runs,
     it'll see the file exists and leave it alone.

Usage:
    python -X utf8 generate-audio.py [--locale BCP-47] [--voice VOICE_NAME] [--countries-json PATH]

    --locale            BCP-47 locale tag. Default: sr-Cyrl.
    --voice             Azure Speech voice name. Inferred from locale if omitted.
                          sr-Cyrl -> sr-RS-SophieNeural
                          en      -> en-US-AriaNeural
                          es      -> es-ES-ElviraNeural
                        Catalog: https://learn.microsoft.com/azure/ai-services/speech-service/language-support#text-to-speech
    --speech-lang       The xml:lang value in the SSML. Default: inferred from voice.
    --countries-json    Path to countries.json. Default: auto-detect.
    --audio-root        Where to save .mp3 files. Default: <project>/wwwroot/audio/<locale>/.
    --dry-run           Print what would be generated without calling the API.

Environment variables (required unless --dry-run):
    SPEECH_KEY          Cognitive Services Speech account key
    SPEECH_REGION       The Azure region (e.g., 'westeurope')

Always run with `python -X utf8` on Windows.

Requires only Python stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import xml.sax.saxutils
from pathlib import Path


SPEECH_TTS_URL_TEMPLATE = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

# Voice + xml:lang defaults by locale family. Microsoft Neural voices, all
# in the free tier. Sophie / Elvira / Aria are friendly female voices —
# kid-appropriate. Override with --voice if you want different.
VOICE_DEFAULTS = {
    "sr-Cyrl": ("sr-RS-SophieNeural",   "sr-RS"),
    "sr-Latn": ("sr-RS-SophieNeural",   "sr-RS"),
    "en":      ("en-US-AriaNeural",     "en-US"),
    "es":      ("es-ES-ElviraNeural",   "es-ES"),
    "fr":      ("fr-FR-DeniseNeural",   "fr-FR"),
    "de":      ("de-DE-KatjaNeural",    "de-DE"),
    "it":      ("it-IT-ElsaNeural",     "it-IT"),
    "ja":      ("ja-JP-NanamiNeural",   "ja-JP"),
    "zh":      ("zh-CN-XiaoxiaoNeural", "zh-CN"),
    "ru":      ("ru-RU-SvetlanaNeural", "ru-RU"),
}


def auto_detect_countries_json():
    for parent in [Path.cwd(), *Path.cwd().parents]:
        src = parent / "src"
        if not src.is_dir():
            continue
        for project_dir in src.iterdir():
            candidate = project_dir / "Data" / "countries.json"
            if candidate.is_file():
                return candidate
    raise SystemExit("Could not auto-detect countries.json. Pass --countries-json.")


def derive_audio_root(countries_json, locale):
    """<project>/wwwroot/audio/<locale>/ — derived from countries.json path."""
    project_dir = countries_json.parent.parent
    return project_dir / "wwwroot" / "audio" / locale


def build_ssml(text, voice, speech_lang):
    """Build SSML body. XML-escape `text` for ampersands, apostrophes, etc."""
    safe = xml.sax.saxutils.escape(text)
    ssml = (
        f"<speak version='1.0' xml:lang='{speech_lang}'>"
        f"<voice name='{voice}'>{safe}</voice>"
        f"</speak>"
    )
    return ssml.encode("utf-8")


def synthesize_one(text, voice, speech_lang, key, region):
    """Call the TTS REST endpoint and return the MP3 bytes."""
    url = SPEECH_TTS_URL_TEMPLATE.format(region=region)
    req = urllib.request.Request(
        url,
        data=build_ssml(text, voice, speech_lang),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "edumap-tts/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Speech HTTP {e.code} for text '{text}': {body}\n"
            f"Check SPEECH_KEY and SPEECH_REGION env vars. "
            f"A 400 usually means malformed SSML or a voice name that doesn't exist."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--locale", default="sr-Cyrl")
    parser.add_argument("--voice", default=None)
    parser.add_argument("--speech-lang", default=None)
    parser.add_argument("--countries-json", type=Path, default=None)
    parser.add_argument("--audio-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    json_path = args.countries_json or auto_detect_countries_json()
    audio_root = args.audio_root or derive_audio_root(json_path, args.locale)

    if args.voice and args.speech_lang:
        voice, speech_lang = args.voice, args.speech_lang
    else:
        default_voice, default_lang = VOICE_DEFAULTS.get(args.locale, (None, None))
        voice = args.voice or default_voice
        speech_lang = args.speech_lang or default_lang
        if not voice or not speech_lang:
            raise SystemExit(
                f"No default voice known for '{args.locale}'. Pass --voice and --speech-lang. "
                f"Catalog: https://learn.microsoft.com/azure/ai-services/speech-service/language-support#text-to-speech"
            )

    print(f"target file: {json_path}")
    print(f"audio root:  {audio_root}")
    print(f"locale:      {args.locale}")
    print(f"voice:       {voice} (xml:lang={speech_lang})")
    print(f"dry-run:     {args.dry_run}")

    key = os.environ.get("SPEECH_KEY", "")
    region = os.environ.get("SPEECH_REGION", "")
    if not args.dry_run and (not key or not region):
        raise SystemExit(
            "SPEECH_KEY and SPEECH_REGION env vars are required (unless --dry-run).\n"
            "    az cognitiveservices account keys list -g rg-edumap -n cs-edumap-speech --query key1 -o tsv\n"
            "    az cognitiveservices account show     -g rg-edumap -n cs-edumap-speech --query location -o tsv"
        )

    with json_path.open(encoding="utf-8") as f:
        countries = json.load(f)
    print(f"loaded {len(countries)} countries")

    audio_root.mkdir(parents=True, exist_ok=True)

    stats = {"generated": 0, "skipped_file_exists": 0, "skipped_no_name": 0, "audio_url_updated": 0}
    locale = args.locale

    for c in countries:
        iso = c["iso2"]
        translations = c.get("translations") or {}
        loc_block = translations.get(locale) or {}
        localized_name = loc_block.get("name")

        if not localized_name:
            stats["skipped_no_name"] += 1
            continue

        target_file = audio_root / f"{iso.lower()}.mp3"
        expected_audio_url = f"/audio/{locale}/{iso.lower()}.mp3"

        if target_file.exists():
            stats["skipped_file_exists"] += 1
        else:
            if args.dry_run:
                print(f"  [dry] would synthesize: [{iso}] '{localized_name}' -> {target_file}")
                stats["generated"] += 1
            else:
                print(f"  synthesizing [{iso}] '{localized_name}' -> {target_file.name}")
                mp3 = synthesize_one(localized_name, voice, speech_lang, key, region)
                target_file.write_bytes(mp3)
                stats["generated"] += 1
                time.sleep(0.05)  # gentle pacing — avoid 429s

        if loc_block.get("audioUrl") != expected_audio_url:
            c.setdefault("translations", {}).setdefault(locale, {})["audioUrl"] = expected_audio_url
            stats["audio_url_updated"] += 1

    if not args.dry_run:
        with json_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print()
    print("=== summary ===")
    for k, v in stats.items():
        print(f"  {k:25s}: {v}")
    print()
    if args.dry_run:
        print("dry-run — no API calls made, no files written.")
    else:
        print(f"wrote audio files to: {audio_root}")
        print(f"updated audioUrl fields in: {json_path}")
    print()
    print("verification tip:")
    print(f"  curl -I https://<app>.azurewebsites.net/audio/{locale}/rs.mp3   # should return 200 after deploy")


if __name__ == "__main__":
    main()

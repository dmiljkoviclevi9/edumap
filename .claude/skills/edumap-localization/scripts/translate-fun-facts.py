#!/usr/bin/env python3
"""
Batch-translate `funFact` fields in EduMap's countries.json from English to
the target locale via Azure AI Translator. Idempotent — only translates
countries whose `translations.<locale>.funFact` is currently null/missing.

Translator's free tier (F0) allows 2 million characters/month, which is
several orders of magnitude more than we need (240 countries × ~100
chars ≈ 25K chars). Quality is "understandable but not always idiomatic"
for child-friendly tone — expect to review and rewrite ~20% by hand.
The script is re-runnable, so refining individual entries is just
edit-and-commit.

Usage:
    python -X utf8 translate-fun-facts.py [--locale BCP-47] [--countries-json PATH]

    --locale            BCP-47 target locale. Default: sr-Cyrl.
    --countries-json    Path to countries.json. Default: auto-detect.
    --dry-run           Print what would be translated, don't call the API
                        or modify the file.

Environment variables (both required unless --dry-run):
    TRANSLATOR_KEY      Cognitive Services / Translator account key
    TRANSLATOR_REGION   The Azure region the resource lives in
                        (e.g., 'westeurope'). MUST match exactly — wrong
                        region with the right key returns 401.

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
import urllib.parse
import urllib.request
from pathlib import Path


TRANSLATE_URL = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to={locale}"
BATCH_SIZE = 50


def auto_detect_countries_json():
    for parent in [Path.cwd(), *Path.cwd().parents]:
        src = parent / "src"
        if not src.is_dir():
            continue
        for project_dir in src.iterdir():
            candidate = project_dir / "Data" / "countries.json"
            if candidate.is_file():
                return candidate
    raise SystemExit(
        "Could not auto-detect countries.json. Pass --countries-json explicitly."
    )


def translate_batch(texts, locale, key, region):
    """POST one batch (up to BATCH_SIZE items) to Translator. Returns translated
    strings in input order. Raises on HTTP error."""
    url = TRANSLATE_URL.format(locale=urllib.parse.quote(locale))
    body = json.dumps([{"Text": t} for t in texts], ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Ocp-Apim-Subscription-Region": region,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Translator HTTP {e.code}: {body_text}\n"
            f"Check TRANSLATOR_KEY and TRANSLATOR_REGION env vars. "
            f"A 401 here usually means the region doesn't match the resource's actual region."
        )

    return [item["translations"][0]["text"] for item in data]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--locale", default="sr-Cyrl")
    parser.add_argument("--countries-json", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    json_path = args.countries_json or auto_detect_countries_json()
    print(f"target file: {json_path}")
    print(f"target locale: {args.locale}")
    print(f"dry-run: {args.dry_run}")

    key = os.environ.get("TRANSLATOR_KEY", "")
    region = os.environ.get("TRANSLATOR_REGION", "")
    if not args.dry_run:
        if not key or not region:
            raise SystemExit(
                "TRANSLATOR_KEY and TRANSLATOR_REGION env vars are required.\n"
                "    az cognitiveservices account keys list -g rg-edumap -n cs-edumap-translator --query key1 -o tsv\n"
                "    az cognitiveservices account show     -g rg-edumap -n cs-edumap-translator --query location -o tsv"
            )

    with json_path.open(encoding="utf-8") as f:
        countries = json.load(f)
    print(f"loaded {len(countries)} countries")

    locale = args.locale
    todo = []
    skipped_no_source = 0
    skipped_already_translated = 0

    for i, c in enumerate(countries):
        en = c.get("funFact")
        if not en:
            skipped_no_source += 1
            continue
        existing = c.get("translations", {}).get(locale, {}).get("funFact")
        if existing:
            skipped_already_translated += 1
            continue
        todo.append((i, en))

    print(f"to translate: {len(todo)} (skipped {skipped_already_translated} already-translated, "
          f"{skipped_no_source} with no English source)")

    if args.dry_run:
        print()
        print("dry-run — first 5 strings that would be translated:")
        for idx, (i, en) in enumerate(todo[:5], 1):
            iso = countries[i]["iso2"]
            print(f"  {idx}. [{iso}] {en}")
        return

    if not todo:
        print("nothing to do. exiting.")
        return

    translated_count = 0
    for batch_start in range(0, len(todo), BATCH_SIZE):
        batch = todo[batch_start:batch_start + BATCH_SIZE]
        texts = [item[1] for item in batch]
        print(f"  translating batch {batch_start // BATCH_SIZE + 1} "
              f"({len(texts)} items, {sum(len(t) for t in texts)} chars)...")
        translations = translate_batch(texts, locale, key, region)

        for (country_idx, _english), translated in zip(batch, translations):
            c = countries[country_idx]
            c.setdefault("translations", {}).setdefault(locale, {})["funFact"] = translated
            translated_count += 1

        if batch_start + BATCH_SIZE < len(todo):
            time.sleep(0.5)

    with json_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print()
    print("=== summary ===")
    print(f"  translated: {translated_count}")
    print(f"  wrote {json_path}")
    print()
    print("review tip: spot-check 5-10 random entries before committing. "
          "Translator's output is correct but sometimes awkward for kid-friendly tone.")


if __name__ == "__main__":
    main()

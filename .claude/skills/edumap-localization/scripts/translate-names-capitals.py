#!/usr/bin/env python3
"""
Fill `translations.<locale>.name` and `.capital` for every country in
EduMap's countries.json, using authoritative sources:

  - Country names    : CLDR (Unicode locale data) — official locale-aware
                       display names. Authoritative for sr-Cyrl, es, de,
                       fr, ja, zh, ... — every locale CLDR covers.
  - Capital names    : Wikidata SPARQL — the only public source with
                       capital names in arbitrary scripts. Quality is
                       generally good for major capitals; falls back to
                       the English label when a target-locale label is
                       missing (we filter those out — better to leave the
                       field null than show "Belgrade" in a Cyrillic
                       modal).

The script is **idempotent**: it only writes to fields that are currently
null/missing. Hand-curated entries (already populated) are never touched.
Re-run as many times as needed — only new countries get written.

Usage:
    python -X utf8 translate-names-capitals.py [--locale BCP-47-tag] [--countries-json PATH]

    --locale            BCP-47 locale to fill. Default: sr-Cyrl.
    --countries-json    Path to countries.json. Default: auto-detect from
                        cwd (looks for src/<App>.Api/Data/countries.json).
    --overrides         Optional path to a JSON file mapping iso2 -> {name, capital}
                        with hand-curated values. Applied AFTER Wikidata,
                        BEFORE write — so they override anything else.
    --no-script-filter  Don't drop Wikidata results that look like Latin
                        script (use for Latin-script target locales).

Always run with the `-X utf8` flag on Windows or the script will crash
on Cyrillic / non-ASCII output via the default cp1252 console codec.

Requires only Python stdlib (urllib) — no pip install needed.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path


CLDR_URL_TEMPLATE = (
    "https://github.com/unicode-org/cldr-json/raw/main/"
    "cldr-json/cldr-localenames-modern/main/{locale}/territories.json"
)

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_QUERY = """
SELECT ?iso ?capitalLabel WHERE {
  ?country wdt:P297 ?iso .
  ?country wdt:P36 ?capital .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "%(locale)s,en".
  }
}
"""


def fetch_cldr_names(locale):
    """Return dict iso2 -> localized country name from CLDR."""
    url = CLDR_URL_TEMPLATE.format(locale=locale)
    print(f"  fetching CLDR territories for '{locale}' ...")
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    territories = (
        data.get("main", {})
        .get(locale, {})
        .get("localeDisplayNames", {})
        .get("territories", {})
    )

    if not territories:
        raise SystemExit(
            f"  CLDR has no territories block for locale '{locale}'. "
            f"Try a different BCP-47 tag (e.g., 'sr_Cyrl' instead of 'sr-Cyrl'), "
            f"or check https://github.com/unicode-org/cldr-json/tree/main/cldr-json/cldr-localenames-modern/main"
        )

    # CLDR keys include UN region codes (001, 002, ...) — filter to ISO-2 only
    return {
        iso: name
        for iso, name in territories.items()
        if len(iso) == 2 and iso.isalpha()
    }


def fetch_wikidata_capitals(locale):
    """Return dict iso2 -> capital name in target locale."""
    print(f"  querying Wikidata SPARQL for capitals in '{locale}' ...")
    query = WIKIDATA_QUERY % {"locale": locale}
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        f"{WIKIDATA_SPARQL_URL}?{params}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "edumap-localization/1.0 (https://github.com/dmiljkoviclevi9/EduMap)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    capitals = {}
    for binding in data.get("results", {}).get("bindings", []):
        iso = binding.get("iso", {}).get("value", "").upper()
        capital = binding.get("capitalLabel", {}).get("value", "")
        if iso and capital:
            capitals[iso] = capital
    print(f"  Wikidata returned {len(capitals)} capitals before filtering")
    return capitals


def is_latin_script(s):
    """Heuristic: ASCII-only string is probably a Latin-script fallback label."""
    return all(ord(ch) < 128 for ch in s)


def auto_detect_countries_json():
    """Walk up from cwd for src/<anything>.Api/Data/countries.json."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        src = parent / "src"
        if not src.is_dir():
            continue
        for project_dir in src.iterdir():
            candidate = project_dir / "Data" / "countries.json"
            if candidate.is_file():
                return candidate
    raise SystemExit(
        "Could not auto-detect countries.json. Pass --countries-json explicitly. "
        "Expected at src/<App>.Api/Data/countries.json relative to the repo root."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--locale", default="sr-Cyrl",
                        help="BCP-47 locale tag (default: sr-Cyrl)")
    parser.add_argument("--countries-json", type=Path, default=None)
    parser.add_argument("--overrides", type=Path, default=None,
                        help="Optional JSON of iso2 -> {name, capital} hand-curated overrides")
    parser.add_argument("--no-script-filter", action="store_true",
                        help="Don't drop Latin-script Wikidata results (for Latin target locales)")
    args = parser.parse_args()

    json_path = args.countries_json or auto_detect_countries_json()
    print(f"target file: {json_path}")
    print(f"target locale: {args.locale}")

    with json_path.open(encoding="utf-8") as f:
        countries = json.load(f)
    print(f"loaded {len(countries)} countries")

    cldr_names = fetch_cldr_names(args.locale)
    wikidata_capitals = fetch_wikidata_capitals(args.locale)

    if not args.no_script_filter:
        before = len(wikidata_capitals)
        wikidata_capitals = {
            iso: cap for iso, cap in wikidata_capitals.items()
            if not is_latin_script(cap)
        }
        print(f"  dropped {before - len(wikidata_capitals)} Latin-script capitals "
              f"(Wikidata fallback to English); pass --no-script-filter if undesired")

    overrides = {}
    if args.overrides:
        with args.overrides.open(encoding="utf-8") as f:
            overrides = json.load(f)
        print(f"loaded {len(overrides)} overrides from {args.overrides}")

    locale = args.locale
    stats = {"new_name": 0, "new_capital": 0, "skipped_existing_name": 0,
             "skipped_existing_capital": 0, "no_data": 0}

    for country in countries:
        iso = country["iso2"]
        translations = country.setdefault("translations", {})
        loc_block = translations.setdefault(locale, {})

        # Name
        if loc_block.get("name"):
            stats["skipped_existing_name"] += 1
        else:
            name = None
            if iso in overrides and overrides[iso].get("name"):
                name = overrides[iso]["name"]
            elif iso in cldr_names:
                name = cldr_names[iso]
            if name:
                loc_block["name"] = name
                stats["new_name"] += 1
            else:
                stats["no_data"] += 1

        # Capital
        if loc_block.get("capital"):
            stats["skipped_existing_capital"] += 1
        else:
            cap = None
            if iso in overrides and overrides[iso].get("capital"):
                cap = overrides[iso]["capital"]
            elif iso in wikidata_capitals:
                cap = wikidata_capitals[iso]
            if cap:
                loc_block["capital"] = cap
                stats["new_capital"] += 1

        # Clean up empty translation blocks
        if not loc_block:
            del translations[locale]
            if not translations:
                del country["translations"]

    with json_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print()
    print("=== summary ===")
    for k, v in stats.items():
        print(f"  {k:25s}: {v}")
    print()
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()

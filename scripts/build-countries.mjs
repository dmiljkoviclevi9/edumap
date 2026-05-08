#!/usr/bin/env node
// Regenerate src/EduMap.Api/Data/countries.json by joining three sources:
//
//   1. Flag SVGs vendored at src/EduMap.Api/wwwroot/flags/<iso2>.svg.
//   2. Country names + capitals from REST Countries v3.1 (public, no auth).
//   3. Kid-friendly fun facts curated in scripts/funfacts.json.
//
// A country is included only if it has all three: a flag SVG, a non-empty
// capital from REST Countries, and a fun fact in funfacts.json.
//
// Run from the repo root:
//   node scripts/build-countries.mjs
//
// Override naming/capital for special cases via NAME_OVERRIDES below — by
// default REST Countries' common names are used (e.g. "United States" instead
// of "United States of America"). Test EndpointTests.cs only checks Iso2 and
// Capital, so name overrides are purely cosmetic.

import { readFile, writeFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..");
const FLAGS_DIR = join(REPO, "src/EduMap.Api/wwwroot/flags");
const FUNFACTS_PATH = join(HERE, "funfacts.json");
const OUTPUT_PATH = join(REPO, "src/EduMap.Api/Data/countries.json");
const REST_URL =
  "https://restcountries.com/v3.1/all?fields=cca2,name,capital";

// Cosmetic name overrides. Existing data used long forms in a few places; we
// honor that to avoid touching the EndpointTests.cs Capital assertion or
// surprising the kids who already saw "United States of America" in the modal.
const NAME_OVERRIDES = {
  US: "United States of America",
};

async function main() {
  const flagFiles = await readdir(FLAGS_DIR);
  const flagCodes = new Set(
    flagFiles
      .filter((f) => f.endsWith(".svg") && !f.includes("-"))
      .map((f) => f.replace(/\.svg$/i, "").toUpperCase())
      .filter((code) => /^[A-Z]{2}$/.test(code)),
  );

  const funFacts = JSON.parse(await readFile(FUNFACTS_PATH, "utf8"));

  const res = await fetch(REST_URL);
  if (!res.ok) {
    throw new Error(`REST Countries fetch failed: ${res.status}`);
  }
  const rest = await res.json();

  const countries = [];
  const skipped = { noFlag: [], noCapital: [], noFact: [] };

  for (const c of rest) {
    const iso2 = c.cca2?.toUpperCase();
    if (!iso2) continue;

    if (!flagCodes.has(iso2)) {
      skipped.noFlag.push(iso2);
      continue;
    }
    const capital = c.capital?.[0];
    if (!capital) {
      skipped.noCapital.push(iso2);
      continue;
    }
    const funFact = funFacts[iso2];
    if (!funFact) {
      skipped.noFact.push(iso2);
      continue;
    }

    countries.push({
      iso2,
      name: NAME_OVERRIDES[iso2] ?? c.name.common,
      capital,
      flagUrl: `/flags/${iso2.toLowerCase()}.svg`,
      funFact,
    });
  }

  countries.sort((a, b) => a.name.localeCompare(b.name, "en"));

  // One-line-per-country pretty format. Hand-rolled because JSON.stringify with
  // an indent puts every property on its own line, which would balloon the
  // file to ~1500 lines for 246 countries.
  const lines = countries.map(
    (c) =>
      `  ${JSON.stringify({
        iso2: c.iso2,
        name: c.name,
        capital: c.capital,
        flagUrl: c.flagUrl,
        funFact: c.funFact,
      })}`,
  );
  const body = `[\n${lines.join(",\n")}\n]\n`;

  await writeFile(OUTPUT_PATH, body, "utf8");

  console.log(`Wrote ${countries.length} countries to ${OUTPUT_PATH}`);
  if (skipped.noFlag.length) {
    console.log(
      `  Skipped (no flag SVG): ${skipped.noFlag.length} -> ${skipped.noFlag.join(", ")}`,
    );
  }
  if (skipped.noCapital.length) {
    console.log(
      `  Skipped (no capital):  ${skipped.noCapital.length} -> ${skipped.noCapital.join(", ")}`,
    );
  }
  if (skipped.noFact.length) {
    console.log(
      `  Skipped (no funFact):  ${skipped.noFact.length} -> ${skipped.noFact.join(", ")}`,
    );
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

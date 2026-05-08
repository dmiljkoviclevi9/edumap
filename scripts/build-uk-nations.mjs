#!/usr/bin/env node
// Fetch the ONS UK TopoJSON, extract the four home-nation polygons (England,
// Scotland, Wales, Northern Ireland), tag them with subdivision ISO codes, and
// vendor the result as src/EduMap.Api/wwwroot/data/uk-nations.geojson.
//
// The frontend overlays this on top of the world GeoJSON so each home nation
// becomes its own clickable feature instead of being lumped into the GB
// multipolygon. Coords are rounded to 3 decimals (~110 m) — the world map only
// ever shows the UK at zoom 1-6, so 6-decimal precision is wasted bandwidth.
//
// Run from the repo root:
//   node scripts/build-uk-nations.mjs

import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..");
const SOURCE_URL =
  "https://raw.githubusercontent.com/ONSdigital/uk-topojson/refs/heads/main/output/topo.json";
const OUTPUT_PATH = join(REPO, "src/EduMap.Api/wwwroot/data/uk-nations.geojson");

const PREFIX_TO_ISO = { E: "GB-ENG", N: "GB-NIR", S: "GB-SCT", W: "GB-WLS" };

const round3 = (n) => Math.round(n * 1000) / 1000;

// Inline TopoJSON-to-GeoJSON conversion. This is the standard algorithm from
// topojson-specification rev 1; we vendor it here to avoid a runtime dependency
// on topojson-client. Handles Polygon and MultiPolygon (the only types that
// appear in ONS country boundaries).
function decodeArcs(topo) {
  const transform = topo.transform;
  const apply = transform
    ? ([x, y]) => [x * transform.scale[0] + transform.translate[0], y * transform.scale[1] + transform.translate[1]]
    : ([x, y]) => [x, y];

  return topo.arcs.map((arc) => {
    let x = 0;
    let y = 0;
    return arc.map(([dx, dy]) => {
      x += dx;
      y += dy;
      return apply([x, y]);
    });
  });
}

function ringFromArcIndices(arcIndices, arcs) {
  const ring = [];
  for (let i = 0; i < arcIndices.length; i++) {
    const idx = arcIndices[i];
    const arc = idx < 0 ? arcs[~idx].slice().reverse() : arcs[idx].slice();
    if (i > 0) arc.shift();
    for (const p of arc) ring.push(p);
  }
  return ring;
}

function geometryToGeoJson(geom, arcs) {
  if (geom.type === "Polygon") {
    return {
      type: "Polygon",
      coordinates: geom.arcs.map((ring) => ringFromArcIndices(ring, arcs)),
    };
  }
  if (geom.type === "MultiPolygon") {
    return {
      type: "MultiPolygon",
      coordinates: geom.arcs.map((poly) =>
        poly.map((ring) => ringFromArcIndices(ring, arcs)),
      ),
    };
  }
  throw new Error(`Unsupported geometry type: ${geom.type}`);
}

function roundCoords(geom) {
  const r = ([x, y]) => [round3(x), round3(y)];
  if (geom.type === "Polygon") {
    geom.coordinates = geom.coordinates.map((ring) => ring.map(r));
  } else {
    geom.coordinates = geom.coordinates.map((poly) =>
      poly.map((ring) => ring.map(r)),
    );
  }
}

async function main() {
  console.log(`Fetching ${SOURCE_URL}`);
  const res = await fetch(SOURCE_URL);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const topo = await res.json();

  const layer = topo.objects.ctry;
  if (!layer) throw new Error("No 'ctry' layer in topojson");

  const arcs = decodeArcs(topo);
  const features = layer.geometries.map((g) => {
    const code = g.properties?.areacd ?? "";
    const iso = PREFIX_TO_ISO[code[0]] ?? "";
    const geometry = geometryToGeoJson(g, arcs);
    roundCoords(geometry);
    return {
      type: "Feature",
      properties: {
        "ISO3166-1-Alpha-2": iso,
        name: g.properties?.areanm ?? "",
        areacd: code,
      },
      geometry,
    };
  });

  features.sort((a, b) =>
    a.properties["ISO3166-1-Alpha-2"].localeCompare(
      b.properties["ISO3166-1-Alpha-2"],
    ),
  );

  const fc = { type: "FeatureCollection", features };
  await writeFile(OUTPUT_PATH, JSON.stringify(fc), "utf8");

  const sizeKb = (Buffer.byteLength(JSON.stringify(fc)) / 1024).toFixed(1);
  console.log(`Wrote ${features.length} features to ${OUTPUT_PATH} (${sizeKb} KB)`);
  console.log(
    "Codes:",
    features.map((f) => f.properties["ISO3166-1-Alpha-2"]).join(", "),
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

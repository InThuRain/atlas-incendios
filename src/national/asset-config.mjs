/** Configuración única de activos del runtime nacional.
 *
 * Los paths por defecto apuntan al árbol local existente para desarrollo. El
 * build de artifact sustituye únicamente esta configuración por paths de
 * artifact/versionados; los loaders no conocen el host ni staging.
 */

export const PMTILES_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe";
export const PMTILES_BYTES = 63052056;
export const PMTILES_PRODUCTION_PATH = `data/esfire30/v1/${PMTILES_SHA256}/esfire30-national-fidelity-territories.pmtiles`;

export const LOCAL_ASSET_CONFIG = Object.freeze({
  asset_base_url: "/",
  runtime_entry: "../../prototypes/es4c/app.js",
  maplibre_script: "/data/derived/spain/es3/tools/browser/maplibre-gl-5.16.0.js",
  pmtiles_protocol_module: "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs",
  assets: {
    esfire30: {
      pmtiles: {
        logical_id: "esfire30-national-fidelity-territories",
        path: "/data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles",
        production_path: `/${PMTILES_PRODUCTION_PATH}`,
        bytes: PMTILES_BYTES,
        sha256: PMTILES_SHA256,
        source: "ESFire30 v1",
        required: true,
      },
    },
    egif: { manifest: { logical_id: "egif-national-web-manifest-2026-08-27", path: "/data/web/spain/egif/2026-08-27/manifest.json", required: true } },
    territories: {
      ccaa: { path: "/data/derived/spain/es4c2a/ccaa.geojson", required: true },
      provinces: { path: "/data/derived/spain/es4c2a/provinces.geojson", required: true },
    },
    municipalities: {
      catalog: { path: "/data/territories/spain/municipality_catalog_2026-08-29.json", required: false },
      shards_root: { path: "/data/derived/spain/es4c2a3/municipalities", required: false },
    },
    esfire30_municipality_indexes: { root: { path: "/data/derived/spain/es4c2b/runtime/municipality-index", required: false } },
  },
});

function join(base, path) {
  if (/^https?:\/\//.test(path)) return path;
  const normalizedBase = String(base || "/").replace(/\/+$/, "");
  return `${normalizedBase}/${String(path).replace(/^\/+/, "")}`;
}

function resolveNode(node, base) {
  if (Array.isArray(node)) return node.map((entry) => resolveNode(entry, base));
  if (!node || typeof node !== "object") return node;
  const resolved = {};
  for (const [key, value] of Object.entries(node)) {
    resolved[key] = key === "path" && typeof value === "string" ? join(base, value) : resolveNode(value, base);
  }
  return resolved;
}

export function resolveAssetConfig(overrides = {}) {
  const base = Object.prototype.hasOwnProperty.call(overrides, "asset_base_url")
    ? overrides.asset_base_url
    : LOCAL_ASSET_CONFIG.asset_base_url;
  const merged = {
    ...LOCAL_ASSET_CONFIG,
    ...overrides,
    assets: {
      ...LOCAL_ASSET_CONFIG.assets,
      ...(overrides.assets || {}),
    },
  };
  const resolved = resolveNode(merged, base);
  return {
    ...resolved,
    asset_base_url: base,
    maplibre_script: join(base, merged.maplibre_script),
    pmtiles_protocol_module: join(base, merged.pmtiles_protocol_module),
    asset_url(path) { return join(base, path); },
  };
}

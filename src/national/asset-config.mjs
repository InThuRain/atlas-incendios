/** Configuración única de activos del runtime nacional.
 *
 * Los paths por defecto apuntan al árbol local existente para desarrollo. El
 * build de artifact sustituye únicamente esta configuración por paths de
 * artifact/versionados; los loaders no conocen el host ni staging.
 */

export const PMTILES_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe";
export const PMTILES_BYTES = 63052056;
export const PMTILES_PRODUCTION_PATH = `data/esfire30/v1/${PMTILES_SHA256}/esfire30-national-fidelity-territories.pmtiles`;
export const BASEMAP_SHA256 = "72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729";
export const BASEMAP_BYTES = 293324998;
export const BASEMAP_VERSION = "protomaps-20260902-z12";
export const BASEMAP_PRODUCTION_ROOT = `data/basemap/protomaps/20260902-z12/${BASEMAP_SHA256}`;

export const LOCAL_ASSET_CONFIG = Object.freeze({
  asset_base_url: "/",
  runtime_entry: "../../prototypes/es4c/app.js",
  maplibre_script: "/data/derived/spain/es3/tools/browser/maplibre-gl-5.16.0.js",
  pmtiles_protocol_module: "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs",
  assets: {
    basemap: {
      enabled: true,
      role: "cartographic_context",
      source_id: "protomaps-context",
      version: BASEMAP_VERSION,
      pmtiles: {
        logical_id: BASEMAP_VERSION,
        path: "/build/es4e3c2-basemap/protomaps-spain-z12.pmtiles",
        production_path: `/${BASEMAP_PRODUCTION_ROOT}/basemap.pmtiles`,
        bytes: BASEMAP_BYTES,
        sha256: BASEMAP_SHA256,
        required: false,
      },
      glyphs: {
        fontstack: "Noto Sans Regular",
        template: "/build/es4e3c2-basemap/fonts/{fontstack}/{range}.pbf",
        production_template: `/${BASEMAP_PRODUCTION_ROOT}/fonts/{fontstack}/{range}.pbf`,
        range: "0-255",
        bytes: 76044,
        sha256: "62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397",
        required: false,
      },
      manifest: {
        path: "/config/national-basemap-protomaps-20260902-z12.json",
        production_path: `/${BASEMAP_PRODUCTION_ROOT}/manifest.json`,
        required: false,
      },
      attribution: "Protomaps · © OpenStreetMap contributors · Obra derivada de BDLJE CC-BY 4.0 ign.es",
      runtime_external_domains: [],
      api_keys_required: false,
    },
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
    // ICV reutiliza exactamente el bundle público valenciano ya validado.
    // El loader resuelve desde su manifest los shards provincia × bloque × LOD.
    icv: {
      manifest: { logical_id: "gva-icv-public-manifest", path: "/data/web/gva/manifest.json", required: true },
      asset_base_url: { path: "/", required: true },
    },
    effis: {
      manifest: { logical_id: "gva-recent-effis-public-manifest", path: "/data/web/gva/manifest.json", required: true },
      asset_base_url: { path: "/", required: true },
    },
    territories: {
      ccaa: { path: "/data/derived/spain/es4c2a/ccaa.geojson", required: true },
      provinces: { path: "/data/derived/spain/es4c2a/provinces.geojson", required: true },
    },
    municipalities: {
      catalog: { path: "/data/territories/spain/municipality_catalog_2026-08-29.json", required: false },
      shards_root: { path: "/data/derived/spain/es4c2a3/municipalities", required: false },
    },
    esfire30_municipality_indexes: { root: { path: "/data/derived/spain/es4c2b/runtime/municipality-index", required: false } },
    ux_summary: {
      manifest: {
        logical_id: "national-ux-summary-v1",
        path: "/data/derived/spain/national-ux-summary-v1/manifest.json",
        required: true,
      },
    },
    highlights: {
      manifest: {
        logical_id: "national-highlights-v1",
        path: "/data/derived/spain/national-highlights-v1/manifest.json",
        required: true,
      },
    },
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
    resolved[key] = (key === "path" || key === "template") && typeof value === "string" ? join(base, value) : resolveNode(value, base);
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

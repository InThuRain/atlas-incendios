/** Carga perezosa de municipios BDLJE actuales para ES-4C2A3C.
 *
 * El catálogo nacional no se carga al abrir España. Cada GeoJSON conserva la
 * geometría 0 m ya auditada y se solicita exclusivamente por `asset_id`.
 */

export const MUNICIPALITY_CATALOG_URL = "/data/territories/spain/municipality_catalog_2026-08-29.json";
export const MUNICIPALITY_SHARDS_ROOT = "/data/derived/spain/es4c2a3/municipalities";

export function shardPathForAsset(assetId, root = MUNICIPALITY_SHARDS_ROOT) {
  if (typeof assetId !== "string" || !/^municipalities:ES:(PROV|CCAA):\d{2}$/.test(assetId)) {
    throw new Error(`asset_id municipal inválido: ${assetId}`);
  }
  return `${root || MUNICIPALITY_SHARDS_ROOT}/${assetId.slice("municipalities:".length).replace(/:/g, "-")}.geojson`;
}

export function buildMunicipalityCatalog(payload) {
  const rows = payload && payload.municipalities;
  if (!Array.isArray(rows) || rows.length !== 8132) throw new Error("Catálogo municipal BDLJE inválido");
  const byId = new Map();
  const byProvince = new Map();
  const byCity = new Map();
  for (const row of rows) {
    if (!/^ES:MUN:\d{5}$/.test((row && row.municipality_id) || "") || byId.has(row.municipality_id)
      || !/^ES:CCAA:\d{2}$/.test(row.autonomous_community_id || "")
      || !/^municipalities:ES:(PROV|CCAA):\d{2}$/.test(row.asset_id || "")
      || !Array.isArray(row.bounds) || row.bounds.length !== 4 || !row.bounds.every(Number.isFinite)) {
      throw new Error("Fila municipal BDLJE inválida");
    }
    if (row.province_id != null && !/^ES:PROV:\d{2}$/.test(row.province_id)) throw new Error("Provincia municipal inválida");
    byId.set(row.municipality_id, row);
    const parent = row.province_id || row.autonomous_community_id;
    const bucket = row.province_id ? byProvince : byCity;
    const values = bucket.get(parent) || [];
    values.push(row); bucket.set(parent, values);
  }
  for (const values of [...byProvince.values(), ...byCity.values()]) {
    values.sort((left, right) => left.official_name.localeCompare(right.official_name, "es") || left.municipality_id.localeCompare(right.municipality_id));
  }
  return { rows, byId, byProvince, byCity };
}

function abortError() {
  const error = new Error("Carga municipal sustituida por un ámbito más reciente");
  error.name = "AbortError";
  return error;
}

export class MunicipalityLoader {
  constructor({ catalogUrl = MUNICIPALITY_CATALOG_URL, shardsRoot = MUNICIPALITY_SHARDS_ROOT, fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias para cargar municipios");
    this.catalogUrl = catalogUrl || MUNICIPALITY_CATALOG_URL; this.shardsRoot = shardsRoot || MUNICIPALITY_SHARDS_ROOT; this.fetchImpl = fetchImpl; this.AbortControllerImpl = AbortControllerImpl;
    this.catalog = null; this.catalogPromise = null; this.assetCache = new Map();
    this.generation = 0; this.activeController = null;
  }
  async fetchJson(url, signal) {
    const started = performance.now();
    const response = await this.fetchImpl(url, { signal });
    if (!response.ok) throw new Error(`Asset municipal no disponible (${response.status}): ${url}`);
    const text = await response.text(); const parsed = performance.now();
    return { data: JSON.parse(text), metrics: { raw_bytes: new TextEncoder().encode(text).byteLength, fetch_ms: parsed - started, parse_ms: performance.now() - parsed } };
  }
  async loadCatalog() {
    if (this.catalog) return this.catalog;
    if (!this.catalogPromise) this.catalogPromise = this.fetchJson(this.catalogUrl).then(({ data }) => {
      this.catalog = buildMunicipalityCatalog(data); return this.catalog;
    });
    return this.catalogPromise;
  }
  async loadAsset(assetId, signal) {
    const cached = this.assetCache.get(assetId); if (cached) return { ...cached, metrics: { ...cached.metrics, cached: true } };
    const { data, metrics } = await this.fetchJson(shardPathForAsset(assetId, this.shardsRoot), signal);
    if (signal && signal.aborted) throw abortError();
    if (!Array.isArray(data && data.features) || data.features.some((feature) => !feature || !feature.properties || !feature.properties.municipality_id || !feature.geometry)) {
      throw new Error(`Shard municipal inválido: ${assetId}`);
    }
    const loaded = { asset_id: assetId, data, metrics: { ...metrics, cached: false } };
    this.assetCache.set(assetId, loaded); return loaded;
  }
  cancel() { this.generation += 1; if (this.activeController) this.activeController.abort(); this.activeController = null; }
  async loadForParent({ provinceId = null, autonomousCommunityId = null }) {
    const catalog = await this.loadCatalog();
    const rows = provinceId ? (catalog.byProvince.get(provinceId) || []) : (catalog.byCity.get(autonomousCommunityId) || []);
    if (!rows.length) return { status: "complete", catalog, rows: [], shard: null };
    const assetId = rows[0].asset_id;
    if (rows.some((row) => row.asset_id !== assetId)) throw new Error("Padre municipal con shards incompatibles");
    const generation = ++this.generation; if (this.activeController) this.activeController.abort();
    const controller = new this.AbortControllerImpl(); this.activeController = controller;
    try {
      const shard = await this.loadAsset(assetId, controller.signal);
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      return { status: "complete", catalog, rows, shard };
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted || error.name === "AbortError") return { status: "stale" };
      throw error;
    } finally { if (generation === this.generation) this.activeController = null; }
  }
}

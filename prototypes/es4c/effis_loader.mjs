/** Loader del snapshot EFFIS valenciano ya publicado.
 *
 * No consulta EFFIS ni transforma geometrías: consume los dos GeoJSON anuales
 * declarados en el manifest GVA. `province_key` y `municipality_id` son
 * atributos del snapshot; los filtros no son intersecciones BDLJE nuevas.
 */

export const EFFIS_COVERAGE = { from: 2025, to: 2026 };
export const EFFIS_EXPECTED = Object.freeze({ 2025: 9, 2026: 16 });
export const EFFIS_PROVINCE_BY_ID = Object.freeze({
  "ES:PROV:03": "alicante", "ES:PROV:12": "castellon", "ES:PROV:46": "valencia",
});

function rootUrl(base) {
  if (/^https?:\/\//.test(base || "")) return base;
  return new URL(String(base || "/"), globalThis.location?.href || "http://invalid.invalid/").href;
}

export class EffisLoader {
  constructor({ manifestUrl, assetBaseUrl = "/", fetchImpl = globalThis.fetch?.bind(globalThis), AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!manifestUrl || !fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias para cargar EFFIS");
    Object.assign(this, { manifestUrl, assetBaseUrl, fetchImpl, AbortControllerImpl, manifest: null, assetCache: new Map(), generation: 0, activeController: null });
  }

  resolveUrl(path) { return /^https?:\/\//.test(path) ? path : new URL(String(path).replace(/^\/+/, ""), rootUrl(this.assetBaseUrl)).href; }
  cancel() { this.generation += 1; this.activeController?.abort(); this.activeController = null; }
  async fetchJson(path, signal) {
    const response = await this.fetchImpl(this.resolveUrl(path), { signal });
    if (!response.ok) throw new Error(`EFFIS HTTP ${response.status} al cargar ${path}`);
    return response.json();
  }
  async ensureManifest(signal) {
    if (this.manifest) return this.manifest;
    const manifest = await this.fetchJson(this.manifestUrl, signal);
    if (!Array.isArray(manifest?.recent?.assets) || !Array.isArray(manifest?.recent?.coverage)) throw new Error("Manifest EFFIS inválido");
    this.manifest = manifest; return manifest;
  }
  assetsFor(manifest, fromYear, toYear) {
    return manifest.recent.assets.filter((asset) => asset.kind === "effis_perimeters" && asset.year >= fromYear && asset.year <= toYear);
  }
  async loadAsset(asset, signal) {
    const cached = this.assetCache.get(asset.url);
    if (cached) return { ...cached, metrics: { ...cached.metrics, cached: true } };
    const started = performance.now();
    const payload = await this.fetchJson(asset.url, signal);
    if (!Array.isArray(payload?.features) || payload.features.length !== asset.feature_count) throw new Error(`Recuento EFFIS inesperado en ${asset.url}`);
    const ids = new Set();
    for (const feature of payload.features) {
      const properties = feature?.properties || {};
      if (!feature.geometry || !/^effis:rda:/.test(String(properties.geometry_id)) || ids.has(properties.geometry_id)) throw new Error(`Geometría EFFIS inválida en ${asset.url}`);
      if (properties.year !== asset.year || properties.source_id !== "effis") throw new Error(`Atributos EFFIS inesperados en ${asset.url}`);
      ids.add(properties.geometry_id);
    }
    const loaded = { asset, features: payload.features, metrics: { cached: false, load_ms: performance.now() - started } };
    this.assetCache.set(asset.url, loaded); return loaded;
  }
  async loadScope({ fromYear, toYear, provinceId = null, municipalityId = null }) {
    const generation = ++this.generation; this.activeController?.abort();
    const controller = new this.AbortControllerImpl(); this.activeController = controller;
    try {
      const manifest = await this.ensureManifest(controller.signal);
      const assets = this.assetsFor(manifest, fromYear, toYear);
      const loaded = await Promise.all(assets.map((asset) => this.loadAsset(asset, controller.signal)));
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      const provinceKey = provinceId ? EFFIS_PROVINCE_BY_ID[provinceId] : null;
      let features = loaded.flatMap((item) => item.features);
      // Ambos filtros son atributos documentados en el GeoJSON publicado.
      if (provinceKey) features = features.filter((feature) => feature.properties.province_key === provinceKey);
      if (municipalityId) features = features.filter((feature) => `ES:MUN:${feature.properties.municipality_id}` === municipalityId);
      return { status: "complete", manifest, assets, loaded, features,
        metrics: { assets: assets.length, cached_assets: loaded.filter((item) => item.metrics.cached).length, geometries: features.length, source_geometries: loaded.reduce((sum, item) => sum + item.features.length, 0) } };
    } catch (error) {
      if (error?.name === "AbortError" || generation !== this.generation) return { status: "stale" };
      throw error;
    } finally { if (generation === this.generation) this.activeController = null; }
  }
}

export function effisIntegratedTerritory(state) { return state.autonomous_community_id === "ES:CCAA:10"; }

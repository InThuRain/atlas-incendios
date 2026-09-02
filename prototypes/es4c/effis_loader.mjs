import { canonicalFilters, filterStateKey, recordMatchesSourceFilters } from "./source_filters.mjs";

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
  async loadScope({ fromYear, toYear, provinceId = null, municipalityId = null, filters = [] }) {
    const generation = ++this.generation; this.activeController?.abort();
    const controller = new this.AbortControllerImpl(); this.activeController = controller;
    try {
      const manifest = await this.ensureManifest(controller.signal);
      const normalizedFilters = canonicalFilters(filters);
      // Con filtro el snapshot completo son solo 25 features y permite una
      // serie anual exacta 2025–2026 sin crear un derivado adicional.
      const assets = this.assetsFor(manifest, normalizedFilters.length ? EFFIS_COVERAGE.from : fromYear, normalizedFilters.length ? EFFIS_COVERAGE.to : toYear);
      const loaded = await Promise.all(assets.map((asset) => this.loadAsset(asset, controller.signal)));
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      const provinceKey = provinceId ? EFFIS_PROVINCE_BY_ID[provinceId] : null;
      let territoryFeatures = loaded.flatMap((item) => item.features);
      // Ambos filtros son atributos documentados en el GeoJSON publicado.
      if (provinceKey) territoryFeatures = territoryFeatures.filter((feature) => feature.properties.province_key === provinceKey);
      if (municipalityId) territoryFeatures = territoryFeatures.filter((feature) => `ES:MUN:${feature.properties.municipality_id}` === municipalityId);
      const filteredAllYears = territoryFeatures.filter((feature) => recordMatchesSourceFilters("effis", feature.properties, normalizedFilters));
      const features = filteredAllYears.filter((feature) => feature.properties.year >= fromYear && feature.properties.year <= toYear);
      const annual = {};
      for (const feature of filteredAllYears) {
        const row = feature.properties;
        const slot = annual[row.year] || { geometries: 0, mapped_area_sum: 0, known_area: 0, unknown_area: 0 };
        slot.geometries += 1;
        if (typeof row.mapped_area_ha === "number" && Number.isFinite(row.mapped_area_ha)) { slot.mapped_area_sum += row.mapped_area_ha; slot.known_area += 1; }
        else slot.unknown_area += 1;
        annual[row.year] = slot;
      }
      const known = features.filter((feature) => typeof feature.properties.mapped_area_ha === "number" && Number.isFinite(feature.properties.mapped_area_ha));
      return { status: "complete", manifest, assets, loaded, features, annual,
        filters: normalizedFilters, filter_key: filterStateKey(normalizedFilters), filtered_summary_mode: "EXACT_RUNTIME",
        metrics: { assets: assets.length, cached_assets: loaded.filter((item) => item.metrics.cached).length, geometries: features.length, mapped_area_sum: known.reduce((sum, feature) => sum + feature.properties.mapped_area_ha, 0), known_area: known.length, unknown_area: features.length - known.length, source_geometries: loaded.reduce((sum, item) => sum + item.features.length, 0) } };
    } catch (error) {
      if (error?.name === "AbortError" || generation !== this.generation) return { status: "stale" };
      throw error;
    } finally { if (generation === this.generation) this.activeController = null; }
  }
}

export function effisIntegratedTerritory(state) { return state.autonomous_community_id === "ES:CCAA:10"; }

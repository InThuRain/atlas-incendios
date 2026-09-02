import { canonicalFilters, documentedIcvGif, filterStateKey, recordMatchesSourceFilters } from "./source_filters.mjs";

/** Loader ICV para el runtime nacional.
 *
 * Reutiliza el manifest público GVA v5: registros separados de perímetros,
 * GeoJSON por provincia × bloque temporal × LOD y una relación 1:N explícita
 * entre fire_id y geometry_id. No infiere episodios ni relaciones con EGIF o
 * ESFire30.
 */

export const ICV_EXPECTED_RECORDS = 13738;
export const ICV_EXPECTED_GEOMETRIES = 13739;
export const ICV_COVERAGE = { from: 1993, to: 2024 };
export const ICV_PROVINCE_BY_ID = Object.freeze({
  "ES:PROV:03": "alicante",
  "ES:PROV:12": "castellon",
  "ES:PROV:46": "valencia",
});
const ICV_KEY_BY_PROVINCE = Object.freeze({ "Alicante/Alacant": "alicante", "Castellón/Castelló": "castellon", "Valencia/València": "valencia" });

function abortError() {
  return new DOMException("Carga ICV sustituida por un estado posterior", "AbortError");
}

function normalizeMunicipalityId(value) {
  return /^\d{5}$/.test(String(value || "")) ? `ES:MUN:${value}` : null;
}

function rootUrl(base) {
  if (/^https?:\/\//.test(base || "")) return base;
  return new URL(String(base || "/"), globalThis.location?.href || "http://invalid.invalid/").href;
}

export class IcvLoader {
  constructor({ manifestUrl, assetBaseUrl = "/", fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!manifestUrl || !fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias para cargar ICV");
    this.manifestUrl = manifestUrl;
    this.assetBaseUrl = assetBaseUrl;
    this.fetchImpl = fetchImpl;
    this.AbortControllerImpl = AbortControllerImpl;
    this.manifest = null;
    this.firesById = null;
    this.assetCache = new Map();
    this.generation = 0;
    this.activeController = null;
  }

  cancel() {
    this.generation += 1;
    this.activeController?.abort();
    this.activeController = null;
  }

  resolveUrl(path) {
    return /^https?:\/\//.test(path) ? path : new URL(String(path).replace(/^\/+/, ""), rootUrl(this.assetBaseUrl)).href;
  }

  async fetchJson(path, signal) {
    const response = await this.fetchImpl(this.resolveUrl(path), { signal });
    if (!response.ok) throw new Error(`ICV HTTP ${response.status} al cargar ${path}`);
    return response.json();
  }

  async ensureManifest(signal) {
    if (this.manifest) return this.manifest;
    const manifest = await this.fetchJson(this.manifestUrl, signal);
    if (!manifest?.icv?.attributes?.fires || !Array.isArray(manifest.icv.geometry_assets)) throw new Error("Manifest ICV inválido");
    this.manifest = manifest;
    return manifest;
  }

  async ensureFires(manifest, signal) {
    if (this.firesById) return this.firesById;
    const payload = await this.fetchJson(manifest.icv.attributes.fires.url, signal);
    if (!Array.isArray(payload?.fires) || payload.fires.length !== ICV_EXPECTED_RECORDS) throw new Error("Recuento de source records ICV inesperado");
    const firesById = new Map(payload.fires.map((fire) => [fire.fire_id, fire]));
    if (firesById.size !== ICV_EXPECTED_RECORDS || !firesById.has("gva:pif-cv:2024AL0005")) throw new Error("Identidades ICV inesperadas");
    this.firesById = firesById;
    return firesById;
  }

  assetsFor(manifest, { provinces, fromYear, toYear, level }) {
    const blocks = new Set(manifest.icv.temporal_blocks
      .filter((block) => block.max_year >= fromYear && block.min_year <= toYear)
      .map((block) => block.id));
    return manifest.icv.geometry_assets.filter((asset) => asset.level === level && provinces.includes(asset.province) && blocks.has(asset.temporal_block));
  }

  async loadAsset(asset, firesById, signal) {
    const cached = this.assetCache.get(asset.url);
    if (cached) return { ...cached, metrics: { ...cached.metrics, cached: true } };
    const started = performance.now();
    const payload = await this.fetchJson(asset.url, signal);
    if (!Array.isArray(payload?.features) || payload.features.length !== asset.feature_count) throw new Error(`Recuento ICV inesperado en ${asset.url}`);
    const features = payload.features.map((feature) => {
      const fire = firesById.get(feature?.properties?.fire_id);
      if (!fire || !feature?.properties?.geometry_id || !feature.geometry) throw new Error(`Feature ICV sin identidad o fire asociado en ${asset.url}`);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          source_id: "icv",
          geometry_quality: "A_official_vector",
          municipality_id: normalizeMunicipalityId(fire.municipality_id),
          source_record_id: fire.num_pif_cv,
          year: fire.year,
        },
      };
    });
    const loaded = { asset, features, metrics: { cached: false, load_ms: performance.now() - started } };
    this.assetCache.set(asset.url, loaded);
    return loaded;
  }

  async loadScope({ provinces, fromYear, toYear, level, municipalityId = null, filters = [] }) {
    const generation = ++this.generation;
    this.activeController?.abort();
    const controller = new this.AbortControllerImpl();
    this.activeController = controller;
    try {
      const manifest = await this.ensureManifest(controller.signal);
      const firesById = await this.ensureFires(manifest, controller.signal);
      const normalizedFilters = canonicalFilters(filters);
      const assets = this.assetsFor(manifest, { provinces, fromYear, toYear, level });
      const loaded = await Promise.all(assets.map((asset) => this.loadAsset(asset, firesById, controller.signal)));
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      const territoryFires = [...firesById.values()].filter((fire) => provinces.includes(ICV_KEY_BY_PROVINCE[fire.province])
        && (!municipalityId || normalizeMunicipalityId(fire.municipality_id) === municipalityId));
      const filteredAllYears = territoryFires.filter((fire) => recordMatchesSourceFilters("icv", fire, normalizedFilters));
      const activeFires = filteredAllYears.filter((fire) => fire.year >= fromYear && fire.year <= toYear);
      const activeFireIds = new Set(activeFires.map((fire) => fire.fire_id));
      let features = loaded.flatMap((item) => item.features).filter((feature) => activeFireIds.has(feature.properties.fire_id));
      const annual = {};
      for (const fire of filteredAllYears) {
        const slot = annual[fire.year] || { records: 0, geometries: 0, declared_forest_area_sum: 0, known_area: 0, unknown_area: 0, gif: 0 };
        slot.records += 1;
        slot.geometries += Array.isArray(fire.geometry_ids) ? fire.geometry_ids.length : 0;
        if (typeof fire.reported_forest_area_ha === "number" && Number.isFinite(fire.reported_forest_area_ha)) { slot.declared_forest_area_sum += fire.reported_forest_area_ha; slot.known_area += 1; }
        else slot.unknown_area += 1;
        if (documentedIcvGif(fire) === true) slot.gif += 1;
        annual[fire.year] = slot;
      }
      const areaKnown = activeFires.filter((fire) => typeof fire.reported_forest_area_ha === "number" && Number.isFinite(fire.reported_forest_area_ha));
      const targetFire = features.filter((feature) => feature.properties.fire_id === "gva:pif-cv:2024AL0005");
      return {
        status: "complete", manifest, assets, loaded, features,
        fires_by_id: firesById, active_fire_ids: activeFireIds,
        filters: normalizedFilters, filter_key: filterStateKey(normalizedFilters), filtered_summary_mode: "EXACT_RUNTIME",
        annual,
        metrics: {
          assets: assets.length, cached_assets: loaded.filter((item) => item.metrics.cached).length,
          records: activeFires.length,
          geometries: activeFires.reduce((sum, fire) => sum + (Array.isArray(fire.geometry_ids) ? fire.geometry_ids.length : 0), 0),
          declared_forest_area_sum: areaKnown.reduce((sum, fire) => sum + fire.reported_forest_area_ha, 0),
          known_area: areaKnown.length, unknown_area: activeFires.length - areaKnown.length,
          gif: activeFires.filter((fire) => documentedIcvGif(fire) === true).length,
          target_2024AL0005_geometries: targetFire.length,
        },
      };
    } catch (error) {
      if (error?.name === "AbortError" || generation !== this.generation) return { status: "stale" };
      throw error;
    } finally {
      if (generation === this.generation) this.activeController = null;
    }
  }
}

export function icvProvincesForScope(state) {
  if (state.autonomous_community_id !== "ES:CCAA:10") return [];
  const selected = state.province_id ? ICV_PROVINCE_BY_ID[state.province_id] : null;
  return selected ? [selected] : Object.values(ICV_PROVINCE_BY_ID);
}

export function icvLevelForZoom(zoom, zoomLevels) {
  for (const level of ["overview", "regional", "local"]) {
    const limits = zoomLevels?.[level];
    if (limits && zoom >= limits.min_zoom && zoom <= limits.max_zoom) return level;
  }
  return Number(zoom) < 9 ? "overview" : Number(zoom) < 11 ? "regional" : "local";
}

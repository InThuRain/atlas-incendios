/**
 * Cargador columnar INITIAL para el laboratorio ES-4C.
 *
 * EGIF son partes administrativos sin geometría: este módulo no conoce ni
 * solicita DETAIL, CCINIF, ESFire30 ni relaciones entre fuentes.
 */

export function blocksIntersecting(blocks, fromYear, toYear) {
  return blocks.filter(([from, to]) => from <= toYear && to >= fromYear);
}

export function assetsForScope(manifest, territoryId, fromYear, toYear) {
  if (!territoryId || territoryId === "ES") return [];
  return manifest.assets
    .filter((asset) => asset.source_id === "egif" && asset.status === "complete"
      && asset.territory_id === territoryId
      && asset.from_year <= toYear && asset.to_year >= fromYear)
    .sort((left, right) => left.from_year - right.from_year || left.asset_id.localeCompare(right.asset_id));
}

export function manifestSummary(manifest, fromYear, toYear) {
  const assets = manifest.assets.filter((asset) => asset.source_id === "egif" && asset.status === "complete"
    && asset.from_year <= toYear && asset.to_year >= fromYear);
  let records = 0;
  for (const asset of assets) {
    for (const [year, spool] of Object.entries(asset.year_spools || {})) {
      const numericYear = Number(year);
      if (numericYear >= fromYear && numericYear <= toYear) records += spool.record_count;
    }
  }
  return {
    scope: "ES",
    source_id: "egif",
    records,
    asset_count: assets.length,
    blocks: blocksIntersecting(manifest.temporal_blocks, fromYear, toYear),
    note: "Resumen de manifest: España no materializa INITIAL en esta fase.",
  };
}

export function summarizeInitialAssets(loadedAssets, fromYear, toYear, provinceId = null, municipalityId = null) {
  const summary = {
    source_id: "egif",
    entity_label: "partes EGIF",
    records: 0,
    administrative_gif: 0,
    known_forest_area_sum: 0,
    records_with_known_forest_area: 0,
    records_with_unknown_forest_area: 0,
    municipality_resolved: 0,
    municipality_unresolved: 0,
    annual: {},
    asset_count: loadedAssets.length,
    lookup_entries: 0,
    raw_bytes: 0,
    manifest_gzip_bytes: 0,
    fetch_ms: 0,
    parse_ms: 0,
  };
  for (const loaded of loadedAssets) {
    const columns = loaded.data.columns;
    const years = columns.year;
    for (let ordinal = 0; ordinal < years.length; ordinal += 1) {
      const year = years[ordinal];
      if (year < fromYear || year > toYear) continue;
      if (provinceId && columns.province_id[ordinal] !== provinceId) continue;
      if (municipalityId && columns.municipality_id[ordinal] !== municipalityId) continue;
      summary.records += 1;
      summary.annual[year] = (summary.annual[year] || 0) + 1;
      if (columns.is_gif_forest_ge_500_ha[ordinal] === true) summary.administrative_gif += 1;
      if (columns.municipality_id[ordinal] == null) summary.municipality_unresolved += 1;
      else summary.municipality_resolved += 1;
      const forestArea = columns.reported_forest_area_ha[ordinal];
      if (typeof forestArea === "number" && Number.isFinite(forestArea)) {
        // Cero es una observación conocida; null/unknown no se convierte en 0.
        summary.known_forest_area_sum += forestArea;
        summary.records_with_known_forest_area += 1;
      } else summary.records_with_unknown_forest_area += 1;
    }
    summary.lookup_entries += loaded.lookup.size;
    summary.raw_bytes += loaded.metrics.raw_bytes;
    summary.manifest_gzip_bytes += loaded.asset.initial.gzip_size;
    summary.fetch_ms += loaded.metrics.fetch_ms;
    summary.parse_ms += loaded.metrics.parse_ms;
  }
  return summary;
}

function abortError() {
  const error = new Error("Carga EGIF sustituida por un estado más reciente");
  error.name = "AbortError";
  return error;
}

export class EGIFInitialLoader {
  constructor({ manifestUrl, fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!manifestUrl || !fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias de carga EGIF");
    this.manifestUrl = manifestUrl;
    this.fetchImpl = fetchImpl;
    this.AbortControllerImpl = AbortControllerImpl;
    this.manifest = null;
    this.manifestPromise = null;
    this.assetCache = new Map();
    this.generation = 0;
    this.activeController = null;
  }

  async fetchJson(url, signal) {
    const fetchStarted = performance.now();
    const response = await this.fetchImpl(url, { signal });
    if (!response.ok) throw new Error(`EGIF asset no disponible (${response.status}): ${url}`);
    const text = await response.text();
    const parsedStarted = performance.now();
    const data = JSON.parse(text);
    return {
      data,
      metrics: {
        raw_bytes: new TextEncoder().encode(text).byteLength,
        fetch_ms: parsedStarted - fetchStarted,
        parse_ms: performance.now() - parsedStarted,
      },
    };
  }

  async loadManifest() {
    if (this.manifest) return this.manifest;
    if (!this.manifestPromise) {
      this.manifestPromise = this.fetchJson(this.manifestUrl).then(({ data }) => {
        if (!Array.isArray(data.assets) || !Array.isArray(data.temporal_blocks)) throw new Error("Manifest EGIF inválido");
        this.manifest = data;
        return data;
      });
    }
    return this.manifestPromise;
  }

  async loadAsset(asset, signal) {
    const cached = this.assetCache.get(asset.asset_id);
    if (cached) return cached;
    const manifestUrl = this.manifestUrl.includes("://")
      ? this.manifestUrl
      : new URL(this.manifestUrl, globalThis.location.origin).toString();
    const url = new URL(asset.initial.path, manifestUrl).toString();
    const result = await this.fetchJson(url, signal);
    if (signal && signal.aborted) throw abortError();
    const { data } = result;
    if (data.asset_id !== asset.asset_id || !data.columns || !data.columns.record_id || !data.columns.year) {
      throw new Error(`Contrato INITIAL inválido: ${asset.asset_id}`);
    }
    const lookup = new Map();
    data.columns.record_id.forEach((recordId, ordinal) => lookup.set(recordId, ordinal));
    if (lookup.size !== data.columns.record_id.length) throw new Error(`record_id duplicado: ${asset.asset_id}`);
    const loaded = { asset, data, lookup, metrics: result.metrics };
    this.assetCache.set(asset.asset_id, loaded);
    return loaded;
  }

  cancel() {
    this.generation += 1;
    if (this.activeController) this.activeController.abort();
    this.activeController = null;
  }

  async loadScope({ territoryId = "ES", fromYear, toYear, provinceId = null, municipalityId = null }) {
    const manifest = await this.loadManifest();
    const generation = ++this.generation;
    if (this.activeController) this.activeController.abort();
    if (territoryId === "ES") return { status: "complete", kind: "manifest_summary", summary: manifestSummary(manifest, fromYear, toYear) };
    const controller = new this.AbortControllerImpl();
    this.activeController = controller;
    const assets = assetsForScope(manifest, territoryId, fromYear, toYear);
    try {
      const loadedAssets = await Promise.all(assets.map((asset) => this.loadAsset(asset, controller.signal)));
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      return {
        status: "complete",
        kind: "initial_assets",
        assets: assets.map((asset) => ({ asset_id: asset.asset_id, path: asset.initial.path, record_count: asset.record_count })),
        // Solo para el runtime aislado. No se serializa ni se expone como
        // resultado de depuración: conserva las columnas y lookups cargados.
        loaded_assets: loadedAssets,
        summary: summarizeInitialAssets(loadedAssets, fromYear, toYear, provinceId, municipalityId),
      };
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted || error.name === "AbortError") return { status: "stale" };
      throw error;
    } finally {
      if (generation === this.generation) this.activeController = null;
    }
  }
}

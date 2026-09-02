import { recordMatchesSourceFilters } from "./source_filters.mjs";

/**
 * Resolución perezosa de DETAIL para un único parte EGIF del prototipo ES-4C.
 *
 * INITIAL contiene la lista y los filtros; DETAIL nunca se solicita hasta una
 * selección explícita. No conoce geometrías, CCINIF ni candidate links.
 */

function abortError() {
  const error = new Error("Selección EGIF sustituida por otra más reciente");
  error.name = "AbortError";
  return error;
}

function valueAt(columns, field, ordinal) {
  return columns[field] ? columns[field][ordinal] : null;
}

function assetUrl(manifestUrl, path) {
  const base = manifestUrl.includes("://")
    ? manifestUrl
    : new URL(manifestUrl, globalThis.location.origin).toString();
  return new URL(path, base).toString();
}

export function locateRecord(loadedAssets, recordId) {
  for (const loaded of loadedAssets || []) {
    const ordinal = loaded.lookup.get(recordId);
    if (ordinal !== undefined) return { loaded, ordinal };
  }
  return null;
}

export function selectedInitialRow(loaded, ordinal) {
  const columns = loaded.data.columns;
  return {
    record_id: valueAt(columns, "record_id", ordinal),
    year: valueAt(columns, "year", ordinal),
    autonomous_community_id: valueAt(columns, "autonomous_community_id", ordinal),
    province_id: valueAt(columns, "province_id", ordinal),
    municipality_id: valueAt(columns, "municipality_id", ordinal),
    reported_forest_area_ha: valueAt(columns, "reported_forest_area_ha", ordinal),
    is_gif_forest_ge_500_ha: valueAt(columns, "is_gif_forest_ge_500_ha", ordinal),
    cause_source_code: valueAt(columns, "cause_source_code", ordinal),
    canonical_cause: valueAt(columns, "canonical_cause", ordinal),
    cause_mapping_status: valueAt(columns, "cause_mapping_status", ordinal),
    coverage_status: valueAt(columns, "coverage_status", ordinal),
    identity_status: valueAt(columns, "identity_status", ordinal),
    episode_identity_status: valueAt(columns, "episode_identity_status", ordinal),
  };
}

export function selectedDetailRow(data, ordinal) {
  const columns = data.columns;
  const row = {};
  for (const field of data.fields || Object.keys(columns)) row[field] = valueAt(columns, field, ordinal);
  return row;
}

export function rowMatchesInitialScope(columns, ordinal, fromYear, toYear, provinceId = null, municipalityId = null, filters = []) {
  const year = columns.year[ordinal];
  const row = { reported_forest_area_ha: valueAt(columns, "reported_forest_area_ha", ordinal), is_gif_forest_ge_500_ha: valueAt(columns, "is_gif_forest_ge_500_ha", ordinal) };
  return year >= fromYear && year <= toYear && (!provinceId || columns.province_id[ordinal] === provinceId)
    && (!municipalityId || columns.municipality_id[ordinal] === municipalityId)
    && recordMatchesSourceFilters("egif", row, filters);
}

export function recordMatchesInitialScope(loadedAssets, recordId, fromYear, toYear, provinceId = null, municipalityId = null, filters = []) {
  const location = locateRecord(loadedAssets, recordId);
  return Boolean(location && rowMatchesInitialScope(location.loaded.data.columns, location.ordinal, fromYear, toYear, provinceId, municipalityId, filters));
}

export function pageOfInitialRows(loadedAssets, fromYear, toYear, page, pageSize, provinceId = null, municipalityId = null, filters = []) {
  const start = Math.max(0, page) * pageSize;
  const rows = [];
  let total = 0;
  for (const loaded of loadedAssets || []) {
    const columns = loaded.data.columns;
    for (let ordinal = 0; ordinal < columns.record_id.length; ordinal += 1) {
      if (!rowMatchesInitialScope(columns, ordinal, fromYear, toYear, provinceId, municipalityId, filters)) continue;
      if (total >= start && rows.length < pageSize) {
        rows.push({ asset_id: loaded.asset.asset_id, ordinal, ...selectedInitialRow(loaded, ordinal) });
      }
      total += 1;
    }
  }
  return { page: Math.max(0, page), page_size: pageSize, total, rows };
}

export function topInitialRows(loadedAssets, fromYear, toYear, limit = 10, provinceId = null, municipalityId = null, filters = []) {
  const rows = [];
  for (const loaded of loadedAssets || []) {
    const columns = loaded.data.columns;
    for (let ordinal = 0; ordinal < columns.record_id.length; ordinal += 1) {
      if (!rowMatchesInitialScope(columns, ordinal, fromYear, toYear, provinceId, municipalityId, filters)) continue;
      const area = valueAt(columns, "reported_forest_area_ha", ordinal);
      // Desconocido no participa en un ranking de superficie y jamás se
      // convierte en cero. Cero conocido sí es un valor documentado.
      if (typeof area !== "number" || !Number.isFinite(area)) continue;
      rows.push({ asset_id: loaded.asset.asset_id, ordinal, ...selectedInitialRow(loaded, ordinal) });
    }
  }
  return rows.sort((left, right) => right.reported_forest_area_ha - left.reported_forest_area_ha || left.record_id.localeCompare(right.record_id))
    .slice(0, Math.min(10, Math.max(1, Number(limit) || 10)));
}

export class EGIFDetailLoader {
  constructor({ manifestUrl, fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!manifestUrl || !fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias DETAIL EGIF");
    this.manifestUrl = manifestUrl;
    this.fetchImpl = fetchImpl;
    this.AbortControllerImpl = AbortControllerImpl;
    this.assetCache = new Map();
    this.generation = 0;
    this.activeController = null;
  }

  async fetchDetail(asset, signal) {
    const cached = this.assetCache.get(asset.asset_id);
    if (cached) return { data: cached.data, metrics: { ...cached.metrics, cached: true } };
    const fetchStarted = performance.now();
    const response = await this.fetchImpl(assetUrl(this.manifestUrl, asset.detail.path), { signal });
    if (!response.ok) throw new Error(`DETAIL EGIF no disponible (${response.status}): ${asset.asset_id}`);
    const text = await response.text();
    const parsedStarted = performance.now();
    const data = JSON.parse(text);
    const metrics = {
      raw_bytes: new TextEncoder().encode(text).byteLength,
      fetch_ms: parsedStarted - fetchStarted,
      parse_ms: performance.now() - parsedStarted,
      manifest_gzip_bytes: asset.detail.gzip_size,
      cached: false,
    };
    if (signal && signal.aborted) throw abortError();
    if (data.asset_id !== asset.asset_id || data.role !== "detail_on_selection" || !data.columns
      || data.initial_record_id_order_sha256 !== asset.initial.record_id_order_sha256
      || data.ordinal_alignment !== "same_sorted_record_id_order_as_initial") {
      throw new Error(`Contrato DETAIL inválido: ${asset.asset_id}`);
    }
    const sourceIds = data.columns.source_record_id;
    if (!Array.isArray(sourceIds) || sourceIds.length !== asset.record_count) {
      throw new Error(`Longitud DETAIL inválida: ${asset.asset_id}`);
    }
    this.assetCache.set(asset.asset_id, { data, metrics });
    return { data, metrics };
  }

  async select({ recordId, loadedAssets }) {
    const location = locateRecord(loadedAssets, recordId);
    if (!location) throw new Error(`Parte EGIF fuera del ámbito cargado: ${recordId}`);
    const generation = ++this.generation;
    if (this.activeController) this.activeController.abort();
    const controller = new this.AbortControllerImpl();
    this.activeController = controller;
    try {
      const detail = await this.fetchDetail(location.loaded.asset, controller.signal);
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      return {
        status: "complete",
        record: { ...selectedInitialRow(location.loaded, location.ordinal), ...selectedDetailRow(detail.data, location.ordinal) },
        asset_id: location.loaded.asset.asset_id,
        ordinal: location.ordinal,
        metrics: detail.metrics,
      };
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted || error.name === "AbortError") return { status: "stale" };
      throw error;
    } finally {
      if (generation === this.generation) this.activeController = null;
    }
  }

  clearSelection() {
    this.generation += 1;
    if (this.activeController) this.activeController.abort();
    this.activeController = null;
  }
}

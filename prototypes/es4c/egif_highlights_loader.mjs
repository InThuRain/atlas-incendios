import { recordMatchesSourceFilters } from "./source_filters.mjs";

/** Índice anual mínimo para destacados EGIF cuando scope=España.
 *
 * No sustituye INITIAL ni DETAIL: sólo evita materializar 646.887 registros
 * para calcular el top-N nacional. La ficha sigue resolviendo INITIAL y carga
 * DETAIL únicamente después de una selección explícita.
 */
export class EgifHighlightsLoader {
  constructor({ manifestUrl, fetchImpl = globalThis.fetch?.bind(globalThis) } = {}) {
    if (!manifestUrl || !fetchImpl) throw new Error("Faltan dependencias del índice de destacados EGIF");
    this.manifestUrl = manifestUrl;
    this.fetchImpl = fetchImpl;
    this.manifest = null;
    this.data = null;
    this.loadPromise = null;
    this.telemetry = { requests: 0, bytes: 0, load_ms: 0 };
  }

  async load() {
    if (this.data) return this.data;
    if (this.loadPromise) return this.loadPromise;
    this.loadPromise = this.loadOnce();
    try {
      return await this.loadPromise;
    } catch (error) {
      this.loadPromise = null;
      throw error;
    }
  }

  async loadOnce() {
    const started = performance.now();
    const manifestResponse = await this.fetchImpl(this.manifestUrl);
    if (!manifestResponse.ok) throw new Error(`Manifest de destacados EGIF no disponible (${manifestResponse.status})`);
    const manifestText = await manifestResponse.text();
    this.manifest = JSON.parse(manifestText);
    const descriptor = this.manifest.assets?.find((row) => row.source_id === "egif");
    if (this.manifest.schema_version !== "national-highlights-v1" || !descriptor?.path) throw new Error("Manifest de destacados EGIF inválido");
    const assetUrl = new URL(descriptor.path, this.manifestUrl).toString();
    const response = await this.fetchImpl(assetUrl);
    if (!response.ok) throw new Error(`Destacados EGIF no disponibles (${response.status})`);
    const text = await response.text();
    this.data = JSON.parse(text);
    if (this.data.schema_version !== "national-highlights-v1" || this.data.metric_id !== "egif_declared_forest_area_ha") throw new Error("Contrato de destacados EGIF inválido");
    this.telemetry = { requests: 2, bytes: new TextEncoder().encode(manifestText).byteLength + new TextEncoder().encode(text).byteLength, load_ms: performance.now() - started };
    return this.data;
  }

  async top({ fromYear, toYear, filters = [], limit = 10 } = {}) {
    const data = await this.load();
    const gifOnly = filters.some((row) => row.source === "egif" && row.filter_id === "egif_gif" && row.value === true);
    const candidates = [];
    for (let year = Number(fromYear); year <= Number(toYear); year += 1) {
      const rows = data.years?.[String(year)]?.[gifOnly ? "gif_true" : "all"] || [];
      candidates.push(...rows.filter((row) => recordMatchesSourceFilters("egif", row, filters)));
    }
    return [...new Map(candidates.map((row) => [row.record_id, row])).values()]
      .sort((left, right) => right.reported_forest_area_ha - left.reported_forest_area_ha || left.record_id.localeCompare(right.record_id))
      .slice(0, Math.min(10, Math.max(1, Number(limit) || 10)));
  }

  async find(recordId) {
    const data = await this.load();
    for (const groups of Object.values(data.years || {})) {
      const row = groups.all?.find((candidate) => candidate.record_id === recordId);
      if (row) return row;
    }
    return null;
  }
}

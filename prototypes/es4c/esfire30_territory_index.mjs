export const INDEX_URL = "/data/derived/spain/es4c2b/runtime/territory-index.json";
export const ESFIRE30_OUT_OF_COVERAGE = new Set([
  "ES:CCAA:04", "ES:CCAA:05", "ES:CCAA:18", "ES:CCAA:19",
  "ES:PROV:07", "ES:PROV:35", "ES:PROV:38",
]);

export class ESFire30TerritoryIndex {
  constructor({ url = INDEX_URL, fetchImpl = globalThis.fetch.bind(globalThis) } = {}) {
    this.url = url; this.fetchImpl = fetchImpl; this.promise = null; this.data = null; this.metrics = null;
  }
  async load() {
    if (this.data) return { data: this.data, cached: true, metrics: { ...this.metrics, fetch_ms_cached: 0, parse_ms_cached: 0 } };
    if (!this.promise) this.promise = (async () => {
      const started = performance.now(); const response = await this.fetchImpl(this.url);
      if (!response.ok) throw new Error(`Índice territorial ESFire30 no disponible (${response.status})`);
      const text = await response.text(); const fetched = performance.now(); const data = JSON.parse(text); const parsed = performance.now();
      if (data.schema_version !== "es4c2b2a-external-territory-index-v1") throw new Error("Versión de índice territorial inesperada");
      this.data = data;
      this.metrics = { fetch_ms: fetched - started, parse_ms: parsed - fetched, prepare_ms: 0, raw_bytes: Number(response.headers.get("content-length")) || text.length };
      return { data, cached: false, metrics: this.metrics };
    })();
    return this.promise;
  }
  async idsFor(territoryId) {
    if (!territoryId || territoryId === "ES") return { ids: null, status: "national", metrics: { fetch_ms: 0, parse_ms: 0, prepare_ms: 0 } };
    const loaded = await this.load(); const started = performance.now();
    const ids = territoryId.startsWith("ES:PROV:") ? loaded.data.province_to_geometry_ids[territoryId] : loaded.data.ccaa_to_geometry_ids[territoryId];
    return { ids: ids || [], status: ids?.length ? "covered" : ESFIRE30_OUT_OF_COVERAGE.has(territoryId) ? "no_coverage" : "no_intersections", metrics: { ...loaded.metrics, prepare_ms: performance.now() - started } };
  }
}

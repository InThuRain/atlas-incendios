/** Índice experimental ESFire30 → municipio actual BDLJE para ES-4C2B3B1.
 *
 * Las listas contienen exclusivamente geometry_id con intersección positiva
 * documentada. No contienen geometrías, atributos EGIF ni una atribución de
 * municipio histórico. Un municipio ausente del mapa equivale a lista vacía.
 */

export const MUNICIPALITY_ESFIRE_INDEX_ROOT = "/data/derived/spain/es4c2b/runtime/municipality-index";
export const MUNICIPALITY_ESFIRE_INDEX_MANIFEST_URL = `${MUNICIPALITY_ESFIRE_INDEX_ROOT}/manifest.json`;
export const MUNICIPALITY_ESFIRE_INDEX_SCHEMA = "es4c2b3b1-municipality-runtime-index-v1";

export function buildMunicipalityIndex(payload) {
  if (!payload || payload.schema_version !== MUNICIPALITY_ESFIRE_INDEX_SCHEMA || !["national", "parent"].includes(payload.scope)
    || !payload.municipalities || typeof payload.municipalities !== "object" || Array.isArray(payload.municipalities)) {
    throw new Error("Índice municipal ESFire30 inválido");
  }
  const municipalityIds = new Map();
  for (const [municipalityId, geometryIds] of Object.entries(payload.municipalities)) {
    if (!/^ES:MUN:\d{5}$/.test(municipalityId) || !Array.isArray(geometryIds)
      || geometryIds.some((geometryId) => !/^esfire30:v1:\d{4}:\d+$/.test(geometryId))
      || geometryIds.some((geometryId, index) => index > 0 && geometryIds[index - 1] >= geometryId)) {
      throw new Error("Lista municipal ESFire30 inválida o no determinista");
    }
    municipalityIds.set(municipalityId, geometryIds);
  }
  return { scope: payload.scope, parent_id: payload.parent_id || null, municipalityIds };
}

function abortError() {
  const error = new Error("Carga del índice municipal sustituida por un ámbito más reciente");
  error.name = "AbortError";
  return error;
}

export class MunicipalityEsfireIndexLoader {
  constructor({ manifestUrl = MUNICIPALITY_ESFIRE_INDEX_MANIFEST_URL, root = MUNICIPALITY_ESFIRE_INDEX_ROOT, fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, AbortControllerImpl = globalThis.AbortController } = {}) {
    if (!fetchImpl || !AbortControllerImpl) throw new Error("Faltan dependencias para el índice municipal ESFire30");
    this.root = root || MUNICIPALITY_ESFIRE_INDEX_ROOT; this.manifestUrl = manifestUrl || `${this.root}/manifest.json`; this.fetchImpl = fetchImpl; this.AbortControllerImpl = AbortControllerImpl;
    this.manifest = null; this.manifestPromise = null; this.national = null; this.parentCache = new Map();
    this.generation = 0; this.activeController = null;
  }
  async fetchJson(url, signal) {
    const started = performance.now();
    const response = await this.fetchImpl(url, { signal });
    if (!response.ok) throw new Error(`Índice municipal ESFire30 no disponible (${response.status}): ${url}`);
    const text = await response.text(); const fetched = performance.now(); const data = JSON.parse(text);
    return { data, metrics: { raw_bytes: new TextEncoder().encode(text).byteLength, fetch_ms: fetched - started, parse_ms: performance.now() - fetched, cached: false } };
  }
  async loadManifest() {
    if (this.manifest) return this.manifest;
    if (!this.manifestPromise) this.manifestPromise = this.fetchJson(this.manifestUrl).then(({ data }) => {
      if (!data || data.schema_version !== MUNICIPALITY_ESFIRE_INDEX_SCHEMA || !data.national || !Array.isArray(data.by_parent)) throw new Error("Manifest municipal ESFire30 inválido");
      const parents = new Map();
      for (const row of data.by_parent) {
        if (!/^ES:(PROV|CCAA):\d{2}$/.test((row && row.parent_id) || "") || parents.has(row.parent_id) || typeof row.path !== "string") throw new Error("Shard municipal ESFire30 inválido");
        parents.set(row.parent_id, row);
      }
      this.manifest = { ...data, parents }; return this.manifest;
    });
    return this.manifestPromise;
  }
  async loadNational() {
    if (this.national) return { ...this.national, metrics: { ...this.national.metrics, cached: true } };
    const manifest = await this.loadManifest(); const loaded = await this.fetchJson(`/${manifest.national.path}`, undefined);
    const index = buildMunicipalityIndex(loaded.data);
    if (index.scope !== "national") throw new Error("Índice nacional municipal inesperado");
    this.national = { index, metrics: loaded.metrics, asset_id: "national" };
    return this.national;
  }
  async loadParent(parentId, signal) {
    const cached = this.parentCache.get(parentId);
    if (cached) return { ...cached, metrics: { ...cached.metrics, cached: true } };
    const manifest = await this.loadManifest(); const descriptor = manifest.parents.get(parentId);
    if (!descriptor) return { index: { scope: "parent", parent_id: parentId, municipalityIds: new Map() }, metrics: { raw_bytes: 0, fetch_ms: 0, parse_ms: 0, cached: true }, asset_id: parentId };
    const loaded = await this.fetchJson(`/${descriptor.path}`, signal);
    if (signal && signal.aborted) throw abortError();
    const index = buildMunicipalityIndex(loaded.data);
    if (index.scope !== "parent" || index.parent_id !== parentId) throw new Error("Índice provincial municipal inesperado");
    const value = { index, metrics: loaded.metrics, asset_id: parentId };
    this.parentCache.set(parentId, value); return value;
  }
  cancel() { this.generation += 1; if (this.activeController) this.activeController.abort(); this.activeController = null; }
  async resolve({ municipalityId, parentId, strategy = "national" }) {
    if (!/^ES:MUN:\d{5}$/.test(municipalityId) || !/^ES:(PROV|CCAA):\d{2}$/.test(parentId || "")) throw new Error("Ámbito municipal ESFire30 inválido");
    if (!["national", "parent"].includes(strategy)) throw new Error("Estrategia de índice municipal desconocida");
    const generation = ++this.generation; if (this.activeController) this.activeController.abort();
    const controller = new this.AbortControllerImpl(); this.activeController = controller;
    try {
      const loaded = strategy === "national" ? await this.loadNational() : await this.loadParent(parentId, controller.signal);
      if (generation !== this.generation || controller.signal.aborted) return { status: "stale" };
      return { status: "complete", strategy, parent_id: parentId, municipality_id: municipalityId, geometry_ids: loaded.index.municipalityIds.get(municipalityId) || [], asset_id: loaded.asset_id, metrics: loaded.metrics };
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted || error.name === "AbortError") return { status: "stale" };
      throw error;
    } finally { if (generation === this.generation) this.activeController = null; }
  }
}

export function municipalityFilterExpression(geometryIds) {
  if (!Array.isArray(geometryIds)) throw new Error("Lista geometry_id municipal inválida");
  // MapLibre interpreta el array como literal; no se construye una expresión
  // por ID ni se añade simultáneamente la lista de la provincia/CCAA.
  return geometryIds.length ? ["in", ["get", "geometry_id"], ["literal", geometryIds]] : ["==", ["get", "geometry_id"], "__municipality_without_esfire30_geometry__"];
}

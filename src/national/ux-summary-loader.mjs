const SCHEMA_VERSION = "national-ux-summary-v1";

function assetCode(territoryId) {
  return String(territoryId || "").replace(/:/g, "-");
}

function territoryRequest(state) {
  if (state.municipality_id) {
    const parentId = state.province_id || state.autonomous_community_id;
    return { kind: "municipality", territoryId: state.municipality_id, parentId };
  }
  if (state.province_id) return { kind: "province", territoryId: state.province_id };
  if (state.autonomous_community_id) return { kind: "ccaa", territoryId: state.autonomous_community_id };
  return { kind: "spain", territoryId: "ES" };
}

function parsePayload(text, path) {
  let payload;
  try {
    payload = JSON.parse(text);
  } catch (error) {
    throw new Error(`Respuesta de resumen no válida (${path})`);
  }
  if (!payload || payload.schema_version !== SCHEMA_VERSION || !Array.isArray(payload.territories)) {
    throw new Error(`Contrato de resumen incompatible (${path})`);
  }
  return payload;
}

function byteLength(text) {
  return unescape(encodeURIComponent(text)).length;
}

function controller() {
  if (typeof AbortController !== "undefined") return new AbortController();
  return { signal: {}, abort() {} };
}

function now() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

export class NationalUxSummaryLoader {
  constructor({ manifestUrl, fetchImpl } = {}) {
    if (!fetchImpl && typeof fetch === "function") fetchImpl = (url, options) => fetch(url, options);
    if (!manifestUrl) throw new Error("Falta la URL del manifest national-ux-summary-v1");
    if (typeof fetchImpl !== "function") throw new Error("No existe fetch para cargar el resumen nacional");
    const baseUrl = typeof document !== "undefined" ? document.baseURI : null;
    this.manifestUrl = baseUrl ? new URL(String(manifestUrl), baseUrl).toString() : String(manifestUrl);
    this.fetchImpl = fetchImpl;
    this.manifestPromise = null;
    this.assetCache = new Map();
    this.activeController = null;
    this.generation = 0;
    this.telemetry = { requests: 0, response_bytes: 0, cache_hits: 0, stale: 0 };
  }

  cancel() {
    this.generation += 1;
    if (this.activeController) this.activeController.abort();
    this.activeController = null;
  }

  async loadManifest() {
    if (!this.manifestPromise) {
      this.manifestPromise = (async () => {
        this.telemetry.requests += 1;
        const response = await this.fetchImpl(this.manifestUrl);
        if (!response.ok) throw new Error(`Manifest de resumen no disponible (${response.status})`);
        const text = await response.text();
        this.telemetry.response_bytes += byteLength(text);
        const manifest = JSON.parse(text);
        if (!manifest || manifest.schema_version !== SCHEMA_VERSION || !Array.isArray(manifest.files)) {
          throw new Error("Manifest national-ux-summary-v1 incompatible");
        }
        return manifest;
      })().catch((error) => {
        this.manifestPromise = null;
        throw error;
      });
    }
    return this.manifestPromise;
  }

  resolveEntry(manifest, request) {
    const files = manifest.files;
    let expected;
    if (request.kind === "spain") expected = "national.json";
    else if (request.kind === "ccaa") expected = `ccaa/${assetCode(request.territoryId)}.json`;
    else if (request.kind === "province") expected = `provinces/${assetCode(request.territoryId)}.json`;
    else expected = `municipalities/by-parent/${assetCode(request.parentId)}.json`;
    const entry = files.find((row) => row.path === expected);
    if (!entry) throw new Error(`No existe resumen para ${request.territoryId}`);
    return entry;
  }

  async loadAsset(entry, generation) {
    if (this.assetCache.has(entry.path)) {
      this.telemetry.cache_hits += 1;
      return { payload: this.assetCache.get(entry.path), cacheHit: true, bytes: 0 };
    }
    if (this.activeController) this.activeController.abort();
    const requestController = controller();
    this.activeController = requestController;
    const url = new URL(entry.path, new URL("./", this.manifestUrl)).toString();
    this.telemetry.requests += 1;
    try {
      const response = await this.fetchImpl(url, { signal: requestController.signal });
      if (!response.ok) throw new Error(`Resumen territorial no disponible (${response.status})`);
      const text = await response.text();
      const bytes = byteLength(text);
      this.telemetry.response_bytes += bytes;
      const payload = parsePayload(text, entry.path);
      this.assetCache.set(entry.path, payload);
      if (generation !== this.generation) return { stale: true };
      return { payload, cacheHit: false, bytes };
    } catch (error) {
      if ((error && error.name === "AbortError") || generation !== this.generation) return { stale: true };
      throw error;
    } finally {
      if (this.activeController === requestController) this.activeController = null;
    }
  }

  async loadTerritory(state) {
    const generation = ++this.generation;
    const started = now();
    const request = territoryRequest(state);
    try {
      const manifest = await this.loadManifest();
      if (generation !== this.generation) {
        this.telemetry.stale += 1;
        return { status: "stale" };
      }
      const entry = this.resolveEntry(manifest, request);
      const loaded = await this.loadAsset(entry, generation);
      if (loaded.stale || generation !== this.generation) {
        this.telemetry.stale += 1;
        return { status: "stale" };
      }
      const territory = loaded.payload.territories.find((row) => row && row.territory && row.territory.territory_id === request.territoryId);
      if (!territory) throw new Error(`El shard no contiene ${request.territoryId}`);
      return {
        status: "complete",
        territory,
        manifest,
        asset: {
          path: entry.path,
          declared_bytes: entry.bytes,
          declared_gzip_bytes: entry.gzip_bytes,
          response_bytes: loaded.bytes,
          cache_hit: loaded.cacheHit,
        },
        duration_ms: now() - started,
      };
    } catch (error) {
      if (generation !== this.generation) return { status: "stale" };
      return { status: "error", error: String((error && error.message) || error), request };
    }
  }
}

export { SCHEMA_VERSION, territoryRequest };

export class DatasetLoader {
  constructor(manifestUrl, {onMetric = () => {}} = {}) {
    this.manifestUrl = manifestUrl;
    this.onMetric = onMetric;
    this.manifest = null;
    this.fires = [];
    this.fireById = new Map();
    this.jsonCache = new Map();
    this.provenanceById = new Map();
    this.candidatesBySigif = new Map();
    this.candidatesByEffis = new Map();
    this.metrics = {requests: 0, blocksDownloaded: 0, responseBytes: 0, estimatedGzipBytes: 0, geometriesDownloaded: 0, events: []};
  }

  async init() {
    this.manifest = await this.fetchJson(this.manifestUrl, {kind: 'manifest', cache: 'no-cache'});
    return this.manifest;
  }

  async fetchJson(url, metadata = {}) {
    if (metadata.cache !== 'no-cache' && this.jsonCache.has(url)) return this.jsonCache.get(url);
    const promise = (async () => {
      const started = performance.now();
      const response = await fetch(new URL(url, document.baseURI), {cache: metadata.cache || 'default'});
      if (!response.ok) throw new Error(`HTTP ${response.status} al cargar ${url}`);
      const text = await response.text();
      const parsedAt = performance.now();
      let payload;
      try { payload = JSON.parse(text); } catch (error) { throw new Error(`JSON inválido en ${url}: ${error.message}`); }
      const event = {url, kind: metadata.kind || 'json', responseBytes: new TextEncoder().encode(text).length,
        estimatedGzipBytes: metadata.estimatedGzipBytes || 0, fetchMs: parsedAt - started,
        parseMs: performance.now() - parsedAt, totalMs: performance.now() - started};
      this.metrics.requests += 1;
      this.metrics.responseBytes += event.responseBytes;
      this.metrics.estimatedGzipBytes += event.estimatedGzipBytes;
      this.metrics.events.push(event);
      this.onMetric(event);
      return payload;
    })();
    if (metadata.cache !== 'no-cache') this.jsonCache.set(url, promise);
    try { return await promise; } catch (error) { this.jsonCache.delete(url); throw error; }
  }

  levelForZoom(zoom) {
    for (const level of ['overview', 'regional', 'local']) {
      const limits = this.manifest.zoom_levels[level];
      if (zoom >= limits.min_zoom && zoom <= limits.max_zoom) return level;
    }
    return zoom < this.manifest.zoom_levels.regional.min_zoom ? 'overview' : 'local';
  }

  async ensureIcvFires() {
    if (!this.manifest.icv || this.fires.length) return;
    const asset = this.manifest.icv.attributes.fires;
    const payload = await this.fetchJson(asset.url, {kind: 'icv_fires', estimatedGzipBytes: asset.gzip_bytes});
    this.fires = payload.fires;
    this.fireById = new Map(this.fires.map(fire => [fire.fire_id, fire]));
  }

  icvAssets(level, provinces, fromYear, toYear) {
    if (!this.manifest.icv) return [];
    const blocks = new Set(this.manifest.icv.temporal_blocks
      .filter(block => block.max_year >= fromYear && block.min_year <= toYear).map(block => block.id));
    return this.manifest.icv.geometry_assets.filter(asset =>
      asset.level === level && provinces.includes(asset.province) && blocks.has(asset.temporal_block));
  }

  recentAssets(kind, fromYear, toYear) {
    return (this.manifest.recent?.assets || []).filter(asset =>
      asset.kind === kind && asset.year >= fromYear && asset.year <= toYear);
  }

  async loadAsset(asset, sourceId) {
    const payload = await this.fetchJson(asset.url, {kind: asset.kind || `${sourceId}_geometry`, estimatedGzipBytes: asset.gzip_bytes});
    if (!Array.isArray(payload.features) || payload.features.length !== asset.feature_count) throw new Error(`Recuento inesperado en ${asset.url}`);
    this.metrics.blocksDownloaded += 1;
    this.metrics.geometriesDownloaded += payload.features.length;
    return payload.features.map(feature => ({...feature, properties: {...feature.properties,
      source_id: sourceId, entity_id: feature.properties.entity_id || feature.properties.geometry_id}}));
  }

  async ensureCandidates(debug = false) {
    if (!this.manifest.recent || this.candidatesBySigif.size) return;
    const kinds = new Set(['link_candidates_visible']);
    if (debug) kinds.add('link_candidates_debug');
    const assets = this.manifest.recent.assets.filter(asset => kinds.has(asset.kind));
    const groups = await Promise.all(assets.map(asset => this.fetchJson(asset.url, {kind: asset.kind, estimatedGzipBytes: asset.gzip_bytes})));
    for (const candidate of groups.flat()) {
      if (!this.candidatesBySigif.has(candidate.sigif_record_id)) this.candidatesBySigif.set(candidate.sigif_record_id, []);
      if (!this.candidatesByEffis.has(candidate.effis_id)) this.candidatesByEffis.set(candidate.effis_id, []);
      this.candidatesBySigif.get(candidate.sigif_record_id).push(candidate);
      this.candidatesByEffis.get(candidate.effis_id).push(candidate);
    }
  }

  async loadView({level, provinces, fromYear, toYear, sources, qualityDebug = false}) {
    const started = performance.now();
    const assets = [];
    const jobs = [];
    if (sources.has('icv') && fromYear <= 2024 && this.manifest.icv) {
      await this.ensureIcvFires();
      for (const asset of this.icvAssets(level, provinces, fromYear, toYear)) {
        assets.push(asset); jobs.push(this.loadAsset({...asset, kind: 'icv_geometry'}, 'icv'));
      }
    }
    for (const [source, kind] of [['sigif', 'sigif_points'], ['effis', 'effis_perimeters']]) {
      if (!sources.has(source)) continue;
      for (const asset of this.recentAssets(kind, fromYear, toYear)) {
        assets.push(asset); jobs.push(this.loadAsset(asset, source));
      }
    }
    if (toYear >= 2025 && sources.has('sigif') && sources.has('effis')) await this.ensureCandidates(qualityDebug);
    return {level, assets, features: (await Promise.all(jobs)).flat(), loadMs: performance.now() - started,
      rawBytes: assets.reduce((sum, asset) => sum + asset.bytes, 0),
      estimatedGzipBytes: assets.reduce((sum, asset) => sum + asset.gzip_bytes, 0)};
  }

  async provenanceFor(provenanceId) {
    if (!this.manifest.icv || !provenanceId) return null;
    if (!this.provenanceById.size) {
      const asset = this.manifest.icv.attributes.provenance;
      const payload = await this.fetchJson(asset.url, {kind: 'icv_provenance', estimatedGzipBytes: asset.gzip_bytes});
      this.provenanceById = new Map(payload.provenance.map(item => [item.provenance_id, item]));
    }
    return this.provenanceById.get(provenanceId) || null;
  }

  candidatesFor(feature) {
    if (feature.properties.source_id === 'sigif') return this.candidatesBySigif.get(feature.properties.sigif_record_id) || [];
    if (feature.properties.source_id === 'effis') return this.candidatesByEffis.get(String(feature.properties.effis_id)) || [];
    return [];
  }

  debugSnapshot() {
    return {...this.metrics, cachedUrls: [...this.jsonCache.keys()], candidateCount: [...this.candidatesBySigif.values()].flat().length};
  }
}

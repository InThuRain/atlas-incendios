export class DatasetLoader {
  constructor(manifestUrl, {onMetric = () => {}} = {}) {
    this.manifestUrl = manifestUrl;
    this.onMetric = onMetric;
    this.manifest = null;
    this.fires = [];
    this.fireById = new Map();
    this.geometryCache = new Map();
    this.provenancePromise = null;
    this.provenanceById = new Map();
    this.metrics = {
      requests: 0,
      blocksDownloaded: 0,
      responseBytes: 0,
      estimatedGzipBytes: 0,
      geometriesDownloaded: 0,
      events: []
    };
  }

  async init() {
    this.manifest = await this.fetchJson(this.manifestUrl, {
      kind: 'manifest',
      cache: 'no-cache'
    });
    const firesAsset = this.manifest.attributes.fires;
    const payload = await this.fetchJson(firesAsset.url, {
      kind: 'fires',
      expectedBytes: firesAsset.bytes,
      estimatedGzipBytes: firesAsset.gzip_bytes
    });
    this.fires = payload.fires;
    this.fireById = new Map(this.fires.map(fire => [fire.fire_id, fire]));
    return this.manifest;
  }

  async fetchJson(url, metadata = {}) {
    const started = performance.now();
    const response = await fetch(new URL(url, document.baseURI), {
      cache: metadata.cache || 'default'
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} al cargar ${url}`);
    }
    const text = await response.text();
    const parsedAt = performance.now();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch (error) {
      throw new Error(`JSON inválido en ${url}: ${error.message}`);
    }
    const finished = performance.now();
    const event = {
      url,
      kind: metadata.kind || 'json',
      responseBytes: new TextEncoder().encode(text).length,
      estimatedGzipBytes: metadata.estimatedGzipBytes || null,
      fetchMs: parsedAt - started,
      parseMs: finished - parsedAt,
      totalMs: finished - started
    };
    this.metrics.requests += 1;
    this.metrics.responseBytes += event.responseBytes;
    this.metrics.estimatedGzipBytes += event.estimatedGzipBytes || 0;
    this.metrics.events.push(event);
    this.onMetric(event);
    return payload;
  }

  levelForZoom(zoom) {
    for (const level of ['overview', 'regional', 'local']) {
      const limits = this.manifest.zoom_levels[level];
      if (zoom >= limits.min_zoom && zoom <= limits.max_zoom) return level;
    }
    return zoom < this.manifest.zoom_levels.regional.min_zoom
      ? 'overview'
      : 'local';
  }

  blocksForRange(fromYear, toYear) {
    return this.manifest.temporal_blocks
      .filter(block => block.max_year >= fromYear && block.min_year <= toYear)
      .map(block => block.id);
  }

  geometryAssets(level, provinces, fromYear, toYear) {
    const provinceSet = new Set(provinces);
    const blockSet = new Set(this.blocksForRange(fromYear, toYear));
    return this.manifest.geometry_assets.filter(asset =>
      asset.level === level &&
      provinceSet.has(asset.province) &&
      blockSet.has(asset.temporal_block)
    );
  }

  async loadGeometryAsset(asset) {
    if (!this.geometryCache.has(asset.url)) {
      const promise = this.fetchJson(asset.url, {
        kind: 'geometry',
        expectedBytes: asset.bytes,
        estimatedGzipBytes: asset.gzip_bytes
      }).then(collection => {
        if (!Array.isArray(collection.features)) {
          throw new Error(`GeoJSON sin features en ${asset.url}`);
        }
        if (collection.features.length !== asset.feature_count) {
          throw new Error(
            `Recuento inesperado en ${asset.url}: ` +
            `${collection.features.length}/${asset.feature_count}`
          );
        }
        this.metrics.blocksDownloaded += 1;
        this.metrics.geometriesDownloaded += collection.features.length;
        return {asset, collection};
      }).catch(error => {
        this.geometryCache.delete(asset.url);
        throw error;
      });
      this.geometryCache.set(asset.url, promise);
    }
    return this.geometryCache.get(asset.url);
  }

  async loadGeometrySet(level, provinces, fromYear, toYear) {
    const assets = this.geometryAssets(level, provinces, fromYear, toYear);
    const started = performance.now();
    const loaded = await Promise.all(assets.map(asset => this.loadGeometryAsset(asset)));
    const features = loaded.flatMap(item => item.collection.features);
    return {
      level,
      assets,
      features,
      loadMs: performance.now() - started,
      estimatedGzipBytes: assets.reduce((sum, asset) => sum + asset.gzip_bytes, 0),
      rawBytes: assets.reduce((sum, asset) => sum + asset.bytes, 0)
    };
  }

  async loadProvenance() {
    if (!this.provenancePromise) {
      const asset = this.manifest.attributes.provenance;
      this.provenancePromise = this.fetchJson(asset.url, {
        kind: 'provenance',
        expectedBytes: asset.bytes,
        estimatedGzipBytes: asset.gzip_bytes
      }).then(payload => {
        this.provenanceById = new Map(
          payload.provenance.map(item => [item.provenance_id, item])
        );
        return this.provenanceById;
      });
    }
    return this.provenancePromise;
  }

  async provenanceFor(provenanceId) {
    await this.loadProvenance();
    return this.provenanceById.get(provenanceId) || null;
  }

  debugSnapshot() {
    return {
      ...this.metrics,
      cachedBlocks: this.geometryCache.size,
      cachedUrls: [...this.geometryCache.keys()]
    };
  }
}

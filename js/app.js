import {DatasetLoader} from './data-loader.js';

const MANIFEST_URL = 'config/datasets-gva.json';
const REUSE_WARNING = 'Este perímetro es geométricamente idéntico a otros registros del conjunto de datos. Esto no implica por sí solo que se trate del mismo incendio ni confirma recurrencia.';
const APP_STARTED_AT = performance.now();

const $ = id => document.getElementById(id);
const elements = {
  status: $('status'),
  levelBadge: $('level-badge'),
  yearFrom: $('year-from'),
  yearTo: $('year-to'),
  yearFromValue: $('year-from-value'),
  yearToValue: $('year-to-value'),
  fullPeriod: $('full-period'),
  province: $('province-filter'),
  municipality: $('municipality-filter'),
  minimumArea: $('minimum-area'),
  cause: $('cause-filter'),
  gifOnly: $('gif-only'),
  metricFires: $('metric-fires'),
  metricPerimeters: $('metric-perimeters'),
  metricArea: $('metric-area'),
  metricGif: $('metric-gif'),
  histogram: $('histogram'),
  pointQuery: $('point-query'),
  pointHint: $('point-hint'),
  pointHistory: $('point-history'),
  details: $('details'),
  fireList: $('fire-list'),
  sourceLink: $('source-link'),
  activePeriod: $('active-period'),
  debugOutput: $('debug-output')
};

const state = {
  loader: null,
  map: null,
  geometryLayer: null,
  loadedFeatures: [],
  visibleRecords: [],
  individualLayers: new Map(),
  selectedFireId: null,
  selectedGeometryId: null,
  pointMode: false,
  pointMarker: null,
  historyResult: null,
  activeLevel: null,
  activeProvinces: [],
  activeAssets: [],
  activeTerritory: 'comunitat_valenciana',
  refreshSequence: 0,
  refreshPromise: Promise.resolve(),
  refreshTimer: null,
  lastRender: null,
  lastLoad: null
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function cleanText(value, fallback = '—') {
  const text = String(value ?? '').trim();
  return text || fallback;
}

function formatNumber(value, maximumFractionDigits = 2) {
  return Number(value || 0).toLocaleString('es-ES', {maximumFractionDigits});
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / 1024 ** 2).toFixed(2)} MiB`;
}

function formatDate(value) {
  if (!value) return '—';
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : cleanText(value);
}

function normalize(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function canonicalProvince(value) {
  const normalized = normalize(value);
  if (normalized.startsWith('castellon')) return 'castellon';
  if (normalized.startsWith('valencia')) return 'valencia';
  if (normalized.startsWith('alicante')) return 'alicante';
  return normalized;
}

function leafletBounds(bounds) {
  return L.latLngBounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]]);
}

function setStatus(message, mode = 'normal') {
  elements.status.textContent = message;
  elements.status.className = `status${mode === 'normal' ? '' : ` ${mode}`}`;
}

function selectedYears() {
  return {
    from: Number(elements.yearFrom.value),
    to: Number(elements.yearTo.value)
  };
}

function syncYearControls(changed = null) {
  let from = Number(elements.yearFrom.value);
  let to = Number(elements.yearTo.value);
  if (from > to) {
    if (changed === 'from') elements.yearTo.value = String(from);
    else elements.yearFrom.value = String(to);
    from = Number(elements.yearFrom.value);
    to = Number(elements.yearTo.value);
  }
  elements.yearFromValue.value = String(from);
  elements.yearToValue.value = String(to);
  elements.yearFromValue.textContent = String(from);
  elements.yearToValue.textContent = String(to);
  elements.activePeriod.textContent = from === to ? String(from) : `${from}–${to}`;
}

function visibleProvinces() {
  if (elements.province.value !== 'all') return [elements.province.value];
  const mapBounds = state.map.getBounds();
  const manifest = state.loader.manifest;
  return ['castellon', 'valencia', 'alicante'].filter(province =>
    mapBounds.intersects(leafletBounds(manifest.territories[province].bounds))
  );
}

function filterBaseFires() {
  const {from, to} = selectedYears();
  const province = elements.province.value;
  return state.loader.fires.filter(fire =>
    fire.year >= from && fire.year <= to &&
    (province === 'all' || canonicalProvince(fire.province) === province)
  );
}

function replaceSelectOptions(select, values, allLabel) {
  const previous = select.value;
  select.replaceChildren();
  const all = document.createElement('option');
  all.value = '';
  all.textContent = allLabel;
  select.appendChild(all);
  for (const value of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  }
  if (values.includes(previous)) select.value = previous;
}

function updateAttributeSelectors() {
  const fires = filterBaseFires();
  const municipalities = [...new Set(fires.map(fire => cleanText(fire.municipality, '')).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, 'es'));
  const causes = [...new Set(fires.map(fire => cleanText(fire.cause, '')).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, 'es'));
  replaceSelectOptions(elements.municipality, municipalities, 'Todos');
  replaceSelectOptions(elements.cause, causes, 'Todas');
}

function firePassesFilters(fire) {
  if (!fire) return false;
  const {from, to} = selectedYears();
  const area = Number(fire.reported_forest_area_ha || 0);
  const minimum = Number(elements.minimumArea.value || 0);
  if (fire.year < from || fire.year > to || area < minimum) return false;
  if (elements.gifOnly.checked && area < 500) return false;
  if (elements.cause.value && cleanText(fire.cause) !== elements.cause.value) return false;
  if (elements.municipality.value && cleanText(fire.municipality) !== elements.municipality.value) return false;
  if (elements.province.value !== 'all' && canonicalProvince(fire.province) !== elements.province.value) return false;
  return true;
}

function yearColor(year) {
  const {from, to} = selectedYears();
  const ratio = (year - from) / Math.max(1, to - from);
  const oldColor = [44, 123, 182];
  const newColor = [240, 82, 46];
  const values = oldColor.map((value, index) => Math.round(value + (newColor[index] - value) * ratio));
  return `rgb(${values.join(',')})`;
}

function featureStyle(feature) {
  const selected = feature.properties.fire_id === state.selectedFireId;
  const color = selected ? '#151a18' : yearColor(feature.properties.year);
  return {
    color,
    fillColor: selected ? '#f0a24a' : color,
    weight: selected ? 3 : 1.1,
    opacity: selected ? 1 : .88,
    fillOpacity: selected ? .52 : .28
  };
}

function reuseWarningHtml() {
  return `<div class="reuse-warning">${escapeHtml(REUSE_WARNING)}</div>`;
}

function popupHtml(fire, feature) {
  const reused = feature.properties.geometry_reused;
  return `
    <h3>${escapeHtml(fire.year)} · ${escapeHtml(cleanText(fire.municipality))}</h3>
    <p>${escapeHtml(cleanText(fire.place_name))}</p>
    <p><strong>Fecha:</strong> ${escapeHtml(formatDate(fire.start_date))}<br>
    <strong>Causa:</strong> ${escapeHtml(cleanText(fire.cause))}<br>
    <strong>Superficie declarada:</strong> ${formatNumber(fire.reported_forest_area_ha)} ha</p>
    <p><strong>Incendio:</strong> ${escapeHtml(fire.fire_id)}<br>
    <strong>Perímetro:</strong> ${escapeHtml(feature.properties.geometry_id)}</p>
    ${reused ? reuseWarningHtml() : ''}
  `;
}

function detailsHtml(fire, feature, provenance = null) {
  const geometryCount = Array.isArray(fire.geometry_ids) ? fire.geometry_ids.length : 0;
  const provenanceDetail = provenance ? `
    <dt>Capa de origen</dt><dd>${escapeHtml(provenance.source_year)} / layer ${escapeHtml(provenance.source_layer_id)}</dd>
    <dt>Recuperado</dt><dd>${escapeHtml(cleanText(provenance.retrieved_at))}</dd>
  ` : '<dt>Procedencia</dt><dd>Cargando detalle…</dd>';
  return `
    <dl>
      <dt>Año</dt><dd>${escapeHtml(fire.year)}</dd>
      <dt>Fecha</dt><dd>${escapeHtml(formatDate(fire.start_date))}</dd>
      <dt>Extinción</dt><dd>${escapeHtml(formatDate(fire.end_date))}</dd>
      <dt>Municipio</dt><dd>${escapeHtml(cleanText(fire.municipality))}</dd>
      <dt>Provincia</dt><dd>${escapeHtml(cleanText(fire.province))}</dd>
      <dt>Paraje</dt><dd>${escapeHtml(cleanText(fire.place_name))}</dd>
      <dt>Causa</dt><dd>${escapeHtml(cleanText(fire.cause))}</dd>
      <dt>Superficie</dt><dd>${formatNumber(fire.reported_forest_area_ha)} ha forestales declaradas</dd>
      <dt>NumPIF_CV</dt><dd>${escapeHtml(cleanText(fire.num_pif_cv))}</dd>
      <dt>Fuente</dt><dd>${escapeHtml(state.loader.manifest.source.label)}</dd>
      <dt>fire_id</dt><dd>${escapeHtml(fire.fire_id)}</dd>
      <dt>Geometrías</dt><dd>${formatNumber(geometryCount, 0)}</dd>
      <dt>geometry_id</dt><dd>${escapeHtml(feature.properties.geometry_id)}</dd>
      ${provenanceDetail}
    </dl>
    ${feature.properties.geometry_reused ? reuseWarningHtml() : ''}
    <div class="quality-note">Calidad geométrica: provisional/no asignada. Geometría derivada para web del perímetro ICV, sin reparación.</div>
  `;
}

async function showDetails(fire, feature) {
  elements.details.innerHTML = detailsHtml(fire, feature);
  const selectedGeometry = feature.properties.geometry_id;
  try {
    const provenance = await state.loader.provenanceFor(feature.properties.provenance_id);
    if (state.selectedGeometryId === selectedGeometry) {
      elements.details.innerHTML = detailsHtml(fire, feature, provenance);
    }
  } catch (error) {
    if (state.selectedGeometryId === selectedGeometry) {
      elements.details.insertAdjacentHTML('beforeend', `<p class="quality-note">No se pudo cargar el detalle de procedencia: ${escapeHtml(error.message)}</p>`);
    }
  }
}

function applySelectionStyles() {
  if (!state.geometryLayer) return;
  state.geometryLayer.eachLayer(layer => {
    if (layer.feature && layer.setStyle) layer.setStyle(featureStyle(layer.feature));
  });
}

function selectFire(fireId, geometryId = null, {fit = false, latlng = null} = {}) {
  const records = state.visibleRecords.filter(record => record.fire.fire_id === fireId);
  const fire = state.loader.fireById.get(fireId);
  if (!fire || !records.length) return false;
  const selected = records.find(record => record.feature.properties.geometry_id === geometryId) || records[0];
  state.selectedFireId = fireId;
  state.selectedGeometryId = selected.feature.properties.geometry_id;
  applySelectionStyles();
  showDetails(fire, selected.feature);
  if (fit) {
    const bounds = L.latLngBounds([]);
    records.forEach(record => bounds.extend(record.layer.getBounds()));
    if (bounds.isValid()) state.map.fitBounds(bounds, {padding: [30, 30], maxZoom: 14});
  }
  if (latlng) {
    L.popup({maxWidth: 360})
      .setLatLng(latlng)
      .setContent(popupHtml(fire, selected.feature))
      .openOn(state.map);
  }
  return true;
}

function handleFeatureClick(feature, event) {
  if (state.pointMode) return;
  if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
  selectFire(feature.properties.fire_id, feature.properties.geometry_id, {latlng: event.latlng});
}

function uniqueFires(records) {
  const result = new Map();
  for (const record of records) result.set(record.fire.fire_id, record.fire);
  return result;
}

function renderMetrics(records) {
  const fires = uniqueFires(records);
  const values = [...fires.values()];
  elements.metricFires.textContent = formatNumber(fires.size, 0);
  elements.metricPerimeters.textContent = formatNumber(records.length, 0);
  elements.metricArea.textContent = formatNumber(
    values.reduce((sum, fire) => sum + Number(fire.reported_forest_area_ha || 0), 0)
  );
  elements.metricGif.textContent = formatNumber(
    values.filter(fire => Number(fire.reported_forest_area_ha || 0) >= 500).length,
    0
  );
}

function renderHistogram(records) {
  const {from, to} = selectedYears();
  const counts = new Map();
  for (let year = from; year <= to; year += 1) counts.set(year, new Set());
  for (const record of records) counts.get(record.fire.year)?.add(record.fire.fire_id);
  const maximum = Math.max(1, ...[...counts.values()].map(values => values.size));
  elements.histogram.replaceChildren();
  for (const [year, fires] of counts) {
    const bar = document.createElement('button');
    bar.type = 'button';
    bar.style.height = `${Math.max(fires.size ? 5 : 1, fires.size / maximum * 100)}%`;
    bar.className = fires.size ? '' : 'empty';
    bar.title = `${year}: ${fires.size} incendio${fires.size === 1 ? '' : 's'}`;
    bar.setAttribute('aria-label', bar.title);
    bar.addEventListener('click', () => setYearRange(year, year));
    elements.histogram.appendChild(bar);
  }
}

function renderFireList(records) {
  const fires = [...uniqueFires(records).values()]
    .sort((left, right) => Number(right.reported_forest_area_ha || 0) - Number(left.reported_forest_area_ha || 0))
    .slice(0, 60);
  elements.fireList.replaceChildren();
  if (!fires.length) {
    elements.fireList.textContent = 'No hay incendios visibles con estos filtros.';
    elements.fireList.className = 'fire-list result-copy';
    return;
  }
  elements.fireList.className = 'fire-list';
  for (const fire of fires) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'fire-row';
    button.innerHTML = `<strong>${escapeHtml(fire.year)} · ${escapeHtml(cleanText(fire.municipality))} · ${formatNumber(fire.reported_forest_area_ha)} ha</strong><span>${escapeHtml(cleanText(fire.place_name))} · ${escapeHtml(cleanText(fire.cause))}</span>`;
    button.addEventListener('click', () => selectFire(fire.fire_id, null, {fit: true}));
    elements.fireList.appendChild(button);
  }
}

function renderGeometry(reason = 'filter') {
  const started = performance.now();
  const features = state.loadedFeatures.filter(feature =>
    firePassesFilters(state.loader.fireById.get(feature.properties.fire_id))
  );
  const records = [];
  const individualLayers = new Map();
  const nextLayer = L.geoJSON({type: 'FeatureCollection', features}, {
    style: featureStyle,
    onEachFeature(feature, layer) {
      const fire = state.loader.fireById.get(feature.properties.fire_id);
      if (!fire) return;
      const record = {feature, fire, layer};
      records.push(record);
      individualLayers.set(feature.properties.geometry_id, layer);
      layer.on('click', event => handleFeatureClick(feature, event));
    }
  });
  nextLayer.addTo(state.map);
  if (state.geometryLayer) state.geometryLayer.removeFrom(state.map);
  state.geometryLayer = nextLayer;
  state.visibleRecords = records;
  state.individualLayers = individualLayers;
  renderMetrics(records);
  renderHistogram(records);
  renderFireList(records);
  const renderMs = performance.now() - started;
  state.lastRender = {reason, geometryCount: records.length, renderMs};
  console.info('[atlas:render]', state.lastRender);
}

async function refreshData(reason = 'state') {
  if (!state.map || !state.loader?.manifest) return;
  const sequence = ++state.refreshSequence;
  const {from, to} = selectedYears();
  const level = state.loader.levelForZoom(state.map.getZoom());
  const provinces = visibleProvinces();
  const expectedAssets = state.loader.geometryAssets(level, provinces, from, to);
  elements.levelBadge.textContent = level;
  setStatus(
    expectedAssets.length
      ? `Cargando ${expectedAssets.length} bloque${expectedAssets.length === 1 ? '' : 's'} ${level}…`
      : 'La vista actual no intersecta ninguna provincia valenciana.',
    'loading'
  );
  const metricsBefore = state.loader.metrics.blocksDownloaded;
  const promise = state.loader.loadGeometrySet(level, provinces, from, to);
  state.refreshPromise = promise;
  try {
    const loaded = await promise;
    if (sequence !== state.refreshSequence) return;
    state.loadedFeatures = loaded.features;
    state.activeLevel = level;
    state.activeProvinces = provinces;
    state.activeAssets = loaded.assets;
    renderGeometry(reason);
    const downloadedNow = state.loader.metrics.blocksDownloaded - metricsBefore;
    state.lastLoad = {
      reason,
      level,
      provinces,
      assetCount: loaded.assets.length,
      loadedGeometryCount: loaded.features.length,
      downloadedNow,
      rawBytes: loaded.rawBytes,
      estimatedGzipBytes: loaded.estimatedGzipBytes,
      loadMs: loaded.loadMs
    };
    console.info('[atlas:load]', state.lastLoad, state.loader.debugSnapshot());
    setStatus(
      `${level} · ${loaded.assets.length} bloque${loaded.assets.length === 1 ? '' : 's'} · ` +
      `${formatNumber(loaded.features.length, 0)} geometrías disponibles · ` +
      `${downloadedNow ? `${downloadedNow} descargado${downloadedNow === 1 ? '' : 's'}` : 'caché de sesión'} · ` +
      `${formatBytes(loaded.estimatedGzipBytes)} gzip estimados`
    );
  } catch (error) {
    if (sequence !== state.refreshSequence) return;
    console.error(error);
    setStatus(
      `No se pudieron cargar los datos estáticos: ${error.message}. ` +
      'Los assets pueden seguir pendientes de publicación por licencia.',
      'error'
    );
  }
}

function scheduleRefresh(reason, delay = 120) {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => refreshData(reason), delay);
}

function setYearRange(from, to) {
  elements.yearFrom.value = String(from);
  elements.yearTo.value = String(to);
  syncYearControls();
  updateAttributeSelectors();
  refreshData('timeline');
}

function fitTerritory(territoryId, {updateFilter = true} = {}) {
  const territory = state.loader.manifest.territories[territoryId];
  if (!territory) return;
  state.activeTerritory = territoryId;
  if (updateFilter) {
    elements.province.value = territoryId === 'comunitat_valenciana'
      ? 'all'
      : territory.provinces[0];
    updateAttributeSelectors();
  }
  const bounds = leafletBounds(territory.bounds);
  state.map.fitBounds(bounds, {animate: false, padding: [18, 18]});
  if (territory.preferred_zoom && state.map.getZoom() < territory.preferred_zoom) {
    state.map.setZoom(territory.preferred_zoom, {animate: false});
  }
}

function setPointMode(enabled) {
  state.pointMode = enabled;
  elements.pointHint.hidden = !enabled;
  elements.pointQuery.classList.toggle('active', enabled);
  elements.pointQuery.textContent = enabled ? 'Cancelar consulta' : 'Consultar un punto del mapa';
  state.map.getContainer().style.cursor = enabled ? 'crosshair' : '';
  if (enabled) state.map.closePopup();
}

function queryPoint(latlng) {
  setPointMode(false);
  if (state.pointMarker) state.pointMarker.removeFrom(state.map);
  state.pointMarker = L.circleMarker(latlng, {
    radius: 6,
    color: '#172421',
    weight: 2,
    fillColor: '#fff',
    fillOpacity: 1
  }).addTo(state.map);
  const point = turf.point([latlng.lng, latlng.lat]);
  const grouped = new Map();
  for (const record of state.visibleRecords) {
    try {
      if (!record.layer.getBounds().contains(latlng)) continue;
      if (!turf.booleanPointInPolygon(point, record.feature)) continue;
      if (!grouped.has(record.fire.fire_id)) grouped.set(record.fire.fire_id, []);
      grouped.get(record.fire.fire_id).push(record);
    } catch (error) {
      console.warn('[atlas:point-query]', record.feature.properties.geometry_id, error);
    }
  }
  const results = [...grouped.entries()]
    .map(([fireId, records]) => ({fireId, fire: records[0].fire, records}))
    .sort((left, right) => left.fire.year - right.fire.year);
  const reused = results.some(result => result.records.some(record => record.feature.properties.geometry_reused));
  const years = [...new Set(results.map(result => result.fire.year))];
  state.historyResult = {
    fireCount: results.length,
    perimeterCount: results.reduce((sum, result) => sum + result.records.length, 0),
    years,
    reused
  };
  if (!results.length) {
    elements.pointHistory.innerHTML = '<strong>Incendios identificados cuyos perímetros contienen este punto: 0.</strong><br>No hay coincidencias con el periodo y los filtros activos.';
    return state.historyResult;
  }
  elements.pointHistory.innerHTML = `
    <strong>Incendios identificados cuyos perímetros contienen este punto: ${results.length}.</strong>
    <div>${years.map(year => `<span class="year-pill">${year}</span>`).join('')}</div>
    ${results.map(result => `<button type="button" class="fire-row history-fire" data-fire-id="${escapeHtml(result.fireId)}"><strong>${result.fire.year} · ${escapeHtml(cleanText(result.fire.municipality))} · ${formatNumber(result.fire.reported_forest_area_ha)} ha</strong><span>${result.records.length} perímetro${result.records.length === 1 ? '' : 's'} contiene${result.records.length === 1 ? '' : 'n'} el punto</span></button>`).join('')}
    ${reused ? reuseWarningHtml() : ''}
  `;
  elements.pointHistory.querySelectorAll('.history-fire').forEach(button => {
    button.addEventListener('click', () => selectFire(button.dataset.fireId, null, {fit: true}));
  });
  return state.historyResult;
}

function bindEvents() {
  document.querySelectorAll('[data-territory]').forEach(button => {
    button.addEventListener('click', () => fitTerritory(button.dataset.territory));
  });
  elements.yearFrom.addEventListener('input', () => syncYearControls('from'));
  elements.yearTo.addEventListener('input', () => syncYearControls('to'));
  elements.yearFrom.addEventListener('change', () => {
    updateAttributeSelectors();
    refreshData('timeline');
  });
  elements.yearTo.addEventListener('change', () => {
    updateAttributeSelectors();
    refreshData('timeline');
  });
  elements.fullPeriod.addEventListener('click', () => {
    const years = state.loader.manifest.years;
    setYearRange(years.min, years.max);
  });
  elements.province.addEventListener('change', () => {
    updateAttributeSelectors();
    refreshData('province-filter');
  });
  elements.municipality.addEventListener('change', () => renderGeometry('municipality-filter'));
  elements.minimumArea.addEventListener('change', () => renderGeometry('area-filter'));
  elements.cause.addEventListener('change', () => renderGeometry('cause-filter'));
  elements.gifOnly.addEventListener('change', () => renderGeometry('gif-filter'));
  elements.pointQuery.addEventListener('click', () => setPointMode(!state.pointMode));
  state.map.on('click', event => {
    if (state.pointMode) queryPoint(event.latlng);
  });
  state.map.on('moveend', () => scheduleRefresh('map-view'));
}

function applyUrlOptions(params) {
  const years = state.loader.manifest.years;
  const from = Math.max(years.min, Math.min(years.max, Number(params.get('from') || years.default)));
  const to = Math.max(years.min, Math.min(years.max, Number(params.get('to') || years.default)));
  elements.yearFrom.value = String(Math.min(from, to));
  elements.yearTo.value = String(Math.max(from, to));
  const province = params.get('province');
  if (['all', 'castellon', 'valencia', 'alicante'].includes(province)) elements.province.value = province;
  if (params.has('min_area')) elements.minimumArea.value = params.get('min_area');
  elements.gifOnly.checked = params.get('gif') === '1';
  syncYearControls();
  updateAttributeSelectors();
}

function debugSnapshot() {
  const fires = uniqueFires(state.visibleRecords);
  const selectedRecords = state.visibleRecords.filter(record => record.fire.fire_id === state.selectedFireId);
  return {
    ready: document.body.dataset.ready === 'true',
    territory: state.activeTerritory,
    zoom: state.map?.getZoom(),
    level: state.activeLevel,
    years: selectedYears(),
    provinceFilter: elements.province.value,
    activeProvinces: state.activeProvinces,
    activeAssetCount: state.activeAssets.length,
    activeAssetUrls: state.activeAssets.map(asset => asset.url),
    loadedGeometryCount: state.loadedFeatures.length,
    visiblePerimeterCount: state.visibleRecords.length,
    visibleFireCount: fires.size,
    visibleGifCount: [...fires.values()].filter(fire => Number(fire.reported_forest_area_ha || 0) >= 500).length,
    declaredAreaHa: [...fires.values()].reduce((sum, fire) => sum + Number(fire.reported_forest_area_ha || 0), 0),
    selectedFireId: state.selectedFireId,
    selectedGeometryId: state.selectedGeometryId,
    selectedVisibleGeometryCount: selectedRecords.length,
    selectedReused: selectedRecords.some(record => record.feature.properties.geometry_reused),
    history: state.historyResult,
    lastLoad: state.lastLoad,
    lastRender: state.lastRender,
    loader: state.loader.debugSnapshot(),
    appElapsedMs: performance.now() - APP_STARTED_AT,
    heapUsedBytes: performance.memory ? performance.memory.usedJSHeapSize : null,
    viewport: {width: innerWidth, height: innerHeight},
    mobileLayout: matchMedia('(max-width: 800px)').matches
  };
}

async function waitForIdle() {
  clearTimeout(state.refreshTimer);
  await state.refreshPromise;
  await new Promise(resolve => setTimeout(resolve, 0));
}

async function runDebugScenario(params) {
  const scenario = params.get('scenario');
  const result = {};
  if (scenario === 'zoom-transition') {
    result.levels = [];
    for (const zoom of [8, 9, 11]) {
      state.map.setZoom(zoom, {animate: false});
      clearTimeout(state.refreshTimer);
      await refreshData(`debug-zoom-${zoom}`);
      result.levels.push(debugSnapshot());
    }
  }
  const fireId = params.get('select_fire');
  if (fireId) {
    selectFire(fireId);
    result.selection = debugSnapshot();
  }
  const pointValue = params.get('point');
  if (pointValue) {
    const [longitude, latitude] = pointValue.split(',').map(Number);
    if (Number.isFinite(longitude) && Number.isFinite(latitude)) {
      queryPoint(L.latLng(latitude, longitude));
      result.point = debugSnapshot();
    }
  }
  const pointGeometryId = params.get('point_geometry');
  if (pointGeometryId) {
    const feature = state.loadedFeatures.find(
      item => item.properties.geometry_id === pointGeometryId
    );
    if (feature) {
      const point = turf.pointOnFeature(feature);
      queryPoint(L.latLng(point.geometry.coordinates[1], point.geometry.coordinates[0]));
      result.point = debugSnapshot();
    } else {
      result.pointError = `No se cargó ${pointGeometryId}`;
    }
  }
  result.final = debugSnapshot();
  elements.debugOutput.textContent = JSON.stringify(result);
  elements.debugOutput.dataset.complete = 'true';
}

async function initialize() {
  if (typeof L === 'undefined' || typeof turf === 'undefined') {
    setStatus('No se pudieron cargar Leaflet o Turf. Se necesita conexión a Internet.', 'error');
    return;
  }
  state.loader = new DatasetLoader(MANIFEST_URL, {
    onMetric: metric => console.debug('[atlas:request]', metric)
  });
  try {
    const manifest = await state.loader.init();
    const years = manifest.years;
    for (const input of [elements.yearFrom, elements.yearTo]) {
      input.min = String(years.min);
      input.max = String(years.max);
      input.value = String(years.default);
    }
    elements.fullPeriod.textContent = `${years.min}–${years.max}`;
    elements.sourceLink.href = manifest.source.catalog_url;
    const params = new URLSearchParams(location.search);
    applyUrlOptions(params);
    state.map = L.map('map', {preferCanvas: true, zoomControl: true});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(state.map);
    state.map.attributionControl.addAttribution(
      `<a href="${escapeHtml(manifest.source.catalog_url)}" target="_blank" rel="noopener">Datos ICV/GVA</a>`
    );
    bindEvents();
    const requestedView = params.get('view') || 'comunitat_valenciana';
    const initialTerritory = manifest.territories[requestedView]
      ? requestedView
      : 'comunitat_valenciana';
    if (!params.has('province') && initialTerritory !== 'comunitat_valenciana') {
      elements.province.value = manifest.territories[initialTerritory].provinces[0];
      updateAttributeSelectors();
    }
    fitTerritory(initialTerritory, {updateFilter: false});
    if (params.has('zoom')) state.map.setZoom(Number(params.get('zoom')), {animate: false});
    clearTimeout(state.refreshTimer);
    await refreshData('initial');
    document.body.dataset.ready = 'true';
    window.__atlasDebug = {
      state,
      loader: state.loader,
      snapshot: debugSnapshot,
      refresh: refreshData,
      waitForIdle,
      setYearRange,
      fitTerritory,
      queryPoint,
      selectFire
    };
    if (params.get('debug') === '1') await runDebugScenario(params);
  } catch (error) {
    console.error(error);
    setStatus(
      `No se pudo iniciar el visor: ${error.message}. ` +
      'Comprueba que el subconjunto estático de producción esté disponible.',
      'error'
    );
    elements.debugOutput.textContent = JSON.stringify({error: error.message});
    elements.debugOutput.dataset.complete = 'true';
  }
}

await initialize();

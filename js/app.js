import {DatasetLoader} from './data-loader.js';

const MANIFEST_URL = 'data/web/gva/manifest.json';
const REUSE_WARNING = 'Este perímetro es geométricamente idéntico a otros registros del conjunto de datos. Esto no implica por sí solo que se trate del mismo incendio ni confirma recurrencia.';
const APP_STARTED_AT = performance.now();
const $ = id => document.getElementById(id);
const elements = {
  status: $('status'), levelBadge: $('level-badge'), yearFrom: $('year-from'), yearTo: $('year-to'),
  yearFromValue: $('year-from-value'), yearToValue: $('year-to-value'), fullPeriod: $('full-period'),
  province: $('province-filter'), municipality: $('municipality-filter'), minimumArea: $('minimum-area'),
  cause: $('cause-filter'), gifOnly: $('gif-only'), metrics: $('metrics'), histogram: $('histogram'),
  sourceFilters: $('source-filters'), coverage: $('coverage-detail'), coverageEyebrow: $('coverage-eyebrow'),
  methodology: $('methodology-content'), pointQuery: $('point-query'), pointHint: $('point-hint'),
  pointHistory: $('point-history'), details: $('details'), fireList: $('fire-list'),
  activePeriod: $('active-period'), debugOutput: $('debug-output'),
  legendYearOld: $('legend-year-old'), legendYearNew: $('legend-year-new')
};

const state = {
  loader: null, map: null, geometryLayer: null, loadedFeatures: [], visibleRecords: [],
  selectedEntityId: null, selectedGeometryId: null, pointMode: false, pointMarker: null,
  historyResult: null, activeLevel: null, activeProvinces: [], activeAssets: [],
  activeTerritory: 'comunitat_valenciana', refreshSequence: 0, refreshPromise: Promise.resolve(),
  refreshTimer: null, lastRender: null, lastLoad: null, qualityDebug: false
};

function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char])); }
function cleanText(value, fallback = '—') { return String(value ?? '').trim() || fallback; }
function formatNumber(value, digits = 2) { return Number(value || 0).toLocaleString('es-ES', {maximumFractionDigits: digits}); }
function formatBytes(value) { return value < 1024 ? `${value} B` : value < 1024 ** 2 ? `${(value / 1024).toFixed(1)} KiB` : `${(value / 1024 ** 2).toFixed(2)} MiB`; }
function formatDate(value) { const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value || ''); return match ? `${match[3]}/${match[2]}/${match[1]}` : cleanText(value); }
function normalize(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
function canonicalProvince(value) { const text = normalize(value); if (text.includes('castell')) return 'castellon'; if (text.includes('val')) return 'valencia'; if (text.includes('alacant') || text.includes('alicante')) return 'alicante'; return text; }
function leafletBounds(bounds) { return L.latLngBounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]]); }
function setStatus(message, mode = 'normal') { elements.status.textContent = message; elements.status.className = `status${mode === 'normal' ? '' : ` ${mode}`}`; }
function selectedYears() { return {from: Number(elements.yearFrom.value), to: Number(elements.yearTo.value)}; }
function activeSources() { return new Set([...elements.sourceFilters.querySelectorAll('input:checked')].map(input => input.value)); }

function syncYearControls(changed = null) {
  let from = Number(elements.yearFrom.value), to = Number(elements.yearTo.value);
  if (from > to) { if (changed === 'from') elements.yearTo.value = String(from); else elements.yearFrom.value = String(to); }
  from = Number(elements.yearFrom.value); to = Number(elements.yearTo.value);
  elements.yearFromValue.textContent = String(from); elements.yearToValue.textContent = String(to);
  elements.activePeriod.textContent = from === to ? String(from) : `${from}–${to}`;
  renderCoverage();
}

function visibleProvinces() {
  if (elements.province.value !== 'all') return [elements.province.value];
  const bounds = state.map.getBounds();
  return ['castellon', 'valencia', 'alicante'].filter(key => bounds.intersects(leafletBounds(state.loader.manifest.territories[key].bounds)));
}

function recordFor(feature) {
  const p = feature.properties;
  if (p.source_id === 'icv') {
    const fire = state.loader.fireById.get(p.fire_id);
    if (!fire) return null;
    return {sourceId: 'icv', entityId: fire.fire_id, geometryId: p.geometry_id, year: fire.year,
      municipality: fire.municipality, province: fire.province, placeName: fire.place_name, cause: fire.cause,
      date: fire.start_date, endDate: fire.end_date, areaHa: Number(fire.reported_forest_area_ha || 0),
      fire, feature, isGif: Number(fire.reported_forest_area_ha || 0) >= 500};
  }
  if (p.source_id === 'sigif') return {sourceId: 'sigif', entityId: p.sigif_record_id, geometryId: p.sigif_record_id,
    year: p.year, municipality: p.municipality, province: p.province, placeName: p.place_name, cause: p.cause,
    date: p.date, areaHa: Number(p.reported_area_ha || 0), feature, isGif: Boolean(p.is_gif)};
  return {sourceId: 'effis', entityId: p.geometry_id, geometryId: p.geometry_id, year: p.year,
    municipality: p.municipality, province: p.province, placeName: null, cause: null, date: p.date,
    endDate: p.final_date, areaHa: Number(p.mapped_area_ha || 0), feature, isGif: false};
}

function replaceSelectOptions(select, values, label) {
  const previous = select.value; select.replaceChildren();
  const all = document.createElement('option'); all.value = ''; all.textContent = label; select.appendChild(all);
  for (const value of values) { const option = document.createElement('option'); option.value = value; option.textContent = value; select.appendChild(option); }
  if (values.includes(previous)) select.value = previous;
}

function updateAttributeSelectors() {
  const records = state.loadedFeatures.map(recordFor).filter(Boolean);
  replaceSelectOptions(elements.municipality, [...new Set(records.map(item => cleanText(item.municipality, '')).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es')), 'Todos');
  replaceSelectOptions(elements.cause, [...new Set(records.map(item => cleanText(item.cause, '')).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es')), 'Todas');
}

function passesFilters(record) {
  if (!record || !activeSources().has(record.sourceId)) return false;
  const {from, to} = selectedYears();
  if (record.year < from || record.year > to || record.areaHa < Number(elements.minimumArea.value || 0)) return false;
  if (!state.activeProvinces.includes(canonicalProvince(record.province))) return false;
  if (elements.gifOnly.checked && (!['icv', 'sigif'].includes(record.sourceId) || !record.isGif)) return false;
  if (elements.cause.value && cleanText(record.cause) !== elements.cause.value) return false;
  if (elements.municipality.value && cleanText(record.municipality) !== elements.municipality.value) return false;
  return true;
}

function yearColor(year) {
  const years = state.loader.manifest.years;
  const ratio = Math.max(0, Math.min(1, (Number(year) - years.min) / Math.max(1, years.max - years.min)));
  const oldColor = [44, 123, 182];
  const newColor = [240, 82, 46];
  const values = oldColor.map((value, index) => Math.round(value + (newColor[index] - value) * ratio));
  return `rgb(${values.join(',')})`;
}

function featureStyle(feature) {
  const p = feature.properties, selected = (p.entity_id || p.fire_id) === state.selectedEntityId;
  const temporalColor = yearColor(p.year);
  if (p.source_id === 'sigif') return {radius: selected ? 8 : 6, color: selected ? '#151a18' : '#8c3d20', weight: 2.5,
    fillColor: temporalColor, fillOpacity: .95};
  if (p.source_id === 'effis') return {color: selected ? '#211a2f' : temporalColor, fillColor: temporalColor, weight: selected ? 4 : 2, dashArray: '7 5', fillOpacity: selected ? .42 : .2};
  return {color: selected ? '#151a18' : temporalColor, fillColor: temporalColor, weight: selected ? 3 : 1.2, fillOpacity: selected ? .5 : .28};
}

function pointLayer(feature, latlng) {
  const selected = feature.properties.entity_id === state.selectedEntityId;
  return L.circleMarker(latlng, {radius: selected ? 8 : 6, color: selected ? '#151a18' : '#8c3d20', weight: 2.5,
    fillColor: yearColor(feature.properties.year), fillOpacity: .95});
}

function sourceLabel(sourceId) { return state.loader.manifest.sources[sourceId]?.short_label || sourceId; }
function candidateHtml(candidates, sourceId) {
  if (!candidates.length) return '';
  return candidates.map(item => `<div class="candidate-note"><strong>Posible correspondencia ${sourceId === 'effis' ? 'SIGIF' : 'EFFIS'} · ${escapeHtml(item.candidate_strength.replace('_candidate', ''))}</strong><br>Score ${item.score}/100 · diferencia temporal ${item.date_difference_days} días · distancia ${formatNumber(item.distance_to_effis_perimeter_m, 1)} m · ${sourceId === 'effis' ? `ID SIGIF ${escapeHtml(item.sigif_record_id)}` : `ID EFFIS ${escapeHtml(item.effis_id)}`}.<br><small>Enlace candidato, no confirmado.</small></div>`).join('');
}

function detailsHtml(record, provenance = null) {
  const p = record.feature.properties, candidates = state.loader.candidatesFor(record.feature);
  if (record.sourceId === 'icv') {
    return `<span class="source-chip">ICV · oficial consolidado</span><dl><dt>Año</dt><dd>${record.year}</dd><dt>Fecha</dt><dd>${formatDate(record.date)}</dd><dt>Extinción</dt><dd>${formatDate(record.endDate)}</dd><dt>Municipio</dt><dd>${escapeHtml(cleanText(record.municipality))}</dd><dt>Provincia</dt><dd>${escapeHtml(cleanText(record.province))}</dd><dt>Paraje</dt><dd>${escapeHtml(cleanText(record.placeName))}</dd><dt>Causa</dt><dd>${escapeHtml(cleanText(record.cause))}</dd><dt>Superficie</dt><dd>${formatNumber(record.areaHa)} ha forestales declaradas</dd><dt>NumPIF_CV</dt><dd>${escapeHtml(cleanText(record.fire.num_pif_cv))}</dd><dt>Fuente</dt><dd>${escapeHtml(state.loader.manifest.sources.icv.label)}</dd><dt>fire_id</dt><dd>${escapeHtml(record.entityId)}</dd><dt>Geometrías asociadas</dt><dd>${record.fire.geometry_ids.length}</dd><dt>geometry_id</dt><dd>${escapeHtml(record.geometryId)}</dd>${provenance ? `<dt>Capa de origen</dt><dd>${provenance.source_year} / layer ${provenance.source_layer_id}</dd>` : ''}</dl>${p.geometry_reused ? `<div class="reuse-warning">${escapeHtml(REUSE_WARNING)}</div>` : ''}<div class="quality-note">Geometría preferente A · perímetro oficial vectorial derivado para web sin reparación.</div>`;
  }
  if (record.sourceId === 'sigif') {
    return `<span class="source-chip">SIGIF · administrativo provisional</span><dl><dt>Fecha observada</dt><dd>${formatDate(record.date)}</dd><dt>Municipio</dt><dd>${escapeHtml(cleanText(record.municipality))}</dd><dt>Provincia</dt><dd>${escapeHtml(cleanText(record.province))}</dd><dt>Paraje</dt><dd>${escapeHtml(cleanText(record.placeName))}</dd><dt>Causa provisional</dt><dd>${escapeHtml(cleanText(record.cause))}</dd><dt>Superficie declarada</dt><dd>${formatNumber(record.areaHa, 4)} ha</dd><dt>Fuente</dt><dd>${escapeHtml(state.loader.manifest.sources.sigif.label)}</dd><dt>ID interno</dt><dd>${escapeHtml(record.entityId)}</dd><dt>Geometría</dt><dd>Punto de inicio; X/Y original EPSG:25830 transformado a EPSG:4326</dd><dt>Adquirido</dt><dd>${escapeHtml(cleanText(p.acquired_at))}</dd></dl>${candidateHtml(candidates, 'sigif')}`;
  }
  const postCutoff = record.year === 2026 && String(record.date) > '2026-06-30';
  return `<span class="source-chip">EFFIS · satelital provisional</span><dl><dt>Fecha EFFIS</dt><dd>${formatDate(record.date)}</dd><dt>Municipio/commune</dt><dd>${escapeHtml(cleanText(record.municipality))}</dd><dt>Provincia</dt><dd>${escapeHtml(cleanText(record.province))}</dd><dt>Superficie cartografiada</dt><dd>${formatNumber(record.areaHa)} ha</dd><dt>Fuente</dt><dd>${escapeHtml(state.loader.manifest.sources.effis.label)}</dd><dt>ID EFFIS</dt><dd>${escapeHtml(p.effis_id)}</dd><dt>geometry_id</dt><dd>${escapeHtml(record.geometryId)}</dd><dt>Calidad</dt><dd>B · teledetección provisional</dd><dt>Snapshot</dt><dd>${escapeHtml(cleanText(p.acquired_at))}</dd></dl>${postCutoff ? '<div class="candidate-note">No existe registro correspondiente en el snapshot SIGIF disponible, cuya cobertura termina el 30/06/2026. Esto no significa que SIGIF afirme que no hubo incendio.</div>' : ''}${candidateHtml(candidates, 'effis')}`;
}

async function showDetails(record) {
  elements.details.innerHTML = detailsHtml(record);
  if (record.sourceId !== 'icv') return;
  const provenance = await state.loader.provenanceFor(record.feature.properties.provenance_id);
  if (state.selectedGeometryId === record.geometryId) elements.details.innerHTML = detailsHtml(record, provenance);
}

function selectEntity(entityId, geometryId = null, {fit = false, latlng = null} = {}) {
  const records = state.visibleRecords.filter(item => item.record.entityId === entityId);
  if (!records.length) return false;
  const selected = records.find(item => item.record.geometryId === geometryId) || records[0];
  state.selectedEntityId = entityId; state.selectedGeometryId = selected.record.geometryId;
  state.geometryLayer.eachLayer(layer => { if (!layer.feature) return; if (layer.setStyle) layer.setStyle(featureStyle(layer.feature)); });
  showDetails(selected.record);
  if (fit) {
    const bounds = L.latLngBounds([]);
    for (const item of records) item.layer.getBounds ? bounds.extend(item.layer.getBounds()) : bounds.extend(item.layer.getLatLng());
    if (bounds.isValid()) state.map.fitBounds(bounds, {padding: [30, 30], maxZoom: 14});
  }
  if (latlng) L.popup({maxWidth: 380}).setLatLng(latlng).setContent(detailsHtml(selected.record)).openOn(state.map);
  return true;
}

function renderMetrics(records) {
  const grouped = {icv: new Map(), sigif: new Map(), effis: new Map()};
  for (const item of records) grouped[item.record.sourceId].set(item.record.entityId, item.record);
  const icv = [...grouped.icv.values()], sigif = [...grouped.sigif.values()], effis = [...grouped.effis.values()];
  const cards = [];
  if (state.loader.manifest.sources.icv) cards.push(['icv', icv.length, 'incendios ICV'], ['icv', records.filter(item => item.record.sourceId === 'icv').length, 'perímetros ICV'], ['icv', icv.reduce((s, x) => s + x.areaHa, 0), 'ha declaradas ICV'], ['icv', icv.filter(x => x.isGif).length, 'GIF ICV ≥ 500 ha']);
  if (state.loader.manifest.sources.sigif) cards.push(['sigif', sigif.length, 'registros SIGIF'], ['sigif', sigif.reduce((s, x) => s + x.areaHa, 0), 'ha declaradas SIGIF'], ['sigif', sigif.filter(x => x.isGif).length, 'GIF administrativos SIGIF']);
  if (state.loader.manifest.sources.effis) cards.push(['effis', effis.length, 'perímetros EFFIS'], ['effis', effis.reduce((s, x) => s + x.areaHa, 0), 'ha cartografiadas EFFIS']);
  elements.metrics.innerHTML = cards.map(([source, value, label]) => `<div class="metric ${source}"><strong>${formatNumber(value, label.startsWith('ha ') ? 2 : 0)}</strong><span>${label}</span></div>`).join('');
}

function renderHistogram(records) {
  const {from, to} = selectedYears(), counts = new Map();
  for (let year = from; year <= to; year += 1) counts.set(year, {icv: new Set(), sigif: new Set(), effis: new Set()});
  for (const item of records) counts.get(item.record.year)?.[item.record.sourceId].add(item.record.entityId);
  const maximum = Math.max(1, ...[...counts.values()].map(item => item.icv.size + item.sigif.size + item.effis.size));
  elements.histogram.replaceChildren();
  for (const [year, item] of counts) {
    const total = item.icv.size + item.sigif.size + item.effis.size, bar = document.createElement('button');
    bar.type = 'button'; bar.style.height = `${Math.max(total ? 5 : 1, total / maximum * 100)}%`; if (!total) bar.className = 'empty';
    bar.title = `${year}: ICV ${item.icv.size}, SIGIF ${item.sigif.size}, EFFIS ${item.effis.size}`;
    bar.addEventListener('click', () => setYearRange(year, year)); elements.histogram.appendChild(bar);
  }
}

function renderList(records) {
  const unique = new Map(); for (const item of records) unique.set(item.record.entityId, item.record);
  const values = [...unique.values()].sort((a, b) => b.areaHa - a.areaHa).slice(0, 60);
  elements.fireList.replaceChildren();
  if (!values.length) { elements.fireList.textContent = 'No hay elementos visibles con estos filtros.'; return; }
  for (const record of values) { const button = document.createElement('button'); button.type = 'button'; button.className = 'fire-row';
    button.innerHTML = `<strong>${record.year} · ${escapeHtml(sourceLabel(record.sourceId))} · ${escapeHtml(cleanText(record.municipality))} · ${formatNumber(record.areaHa)} ha</strong><span>${escapeHtml(cleanText(record.placeName))} · ${escapeHtml(cleanText(record.cause))}</span>`;
    button.addEventListener('click', () => selectEntity(record.entityId, null, {fit: true})); elements.fireList.appendChild(button); }
}

function renderGeometry(reason = 'filter') {
  const started = performance.now(), features = state.loadedFeatures.filter(feature => passesFilters(recordFor(feature))), records = [];
  const layer = L.geoJSON({type: 'FeatureCollection', features}, {
    style: featureStyle, pointToLayer: pointLayer,
    onEachFeature(feature, itemLayer) { const record = recordFor(feature); if (!record) return; records.push({feature, record, layer: itemLayer});
      itemLayer.on('click', event => { if (state.pointMode) return; if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent); selectEntity(record.entityId, record.geometryId, {latlng: event.latlng}); }); }
  }).addTo(state.map);
  if (state.geometryLayer) state.geometryLayer.removeFrom(state.map);
  state.geometryLayer = layer; state.visibleRecords = records;
  renderMetrics(records); renderHistogram(records); renderList(records);
  state.lastRender = {reason, geometryCount: records.length, renderMs: performance.now() - started};
  console.info('[atlas:render]', state.lastRender);
}

function renderCoverage() {
  if (!state.loader?.manifest) return;
  const {from, to} = selectedYears(), items = [];
  if (from <= 2024 && state.loader.manifest.sources.icv) items.push('<div class="coverage-item"><strong>ICV 1993–2024:</strong> histórico oficial consolidado de perímetros cartografiados; no es un inventario estadístico completo.</div>');
  for (const coverage of state.loader.manifest.recent?.coverage || []) {
    if (coverage.year < from || coverage.year > to) continue;
    const acquired = formatDate(state.loader.manifest.recent.acquired_at);
    items.push(`<div class="coverage-item"><strong>${coverage.year} · datos provisionales.</strong><br>SIGIF/GVA: datos administrativos ${coverage.coverage_complete ? `del ${formatDate(coverage.sigif_min_date)} al ${formatDate(coverage.sigif_max_date)} (año completo observado)` : `disponibles hasta ${formatDate(coverage.sigif_max_date)}; cobertura incompleta`}. EFFIS: perímetros satelitales según snapshot adquirido el ${acquired}. Las fuentes tienen cobertura y metodología diferentes.</div>`);
  }
  elements.coverage.innerHTML = items.join('') || 'No hay una fuente activa para este periodo en el perfil actual.';
}

async function refreshData(reason = 'state') {
  if (!state.map || !state.loader?.manifest) return;
  const sequence = ++state.refreshSequence, {from, to} = selectedYears(), level = state.loader.levelForZoom(state.map.getZoom()), provinces = visibleProvinces(), sources = activeSources();
  elements.levelBadge.textContent = level; setStatus('Cargando los bloques necesarios…', 'loading');
  const before = state.loader.metrics.requests;
  const promise = state.loader.loadView({level, provinces, fromYear: from, toYear: to, sources, qualityDebug: state.qualityDebug}); state.refreshPromise = promise;
  try {
    const loaded = await promise; if (sequence !== state.refreshSequence) return;
    state.loadedFeatures = loaded.features; state.activeLevel = level; state.activeProvinces = provinces; state.activeAssets = loaded.assets;
    updateAttributeSelectors(); renderGeometry(reason); renderCoverage();
    state.lastLoad = {reason, level, provinces, assetCount: loaded.assets.length, loadedGeometryCount: loaded.features.length,
      downloadedNow: state.loader.metrics.requests - before, rawBytes: loaded.rawBytes, estimatedGzipBytes: loaded.estimatedGzipBytes, loadMs: loaded.loadMs};
    setStatus(`${level} · ${loaded.assets.length} assets · ${formatNumber(loaded.features.length, 0)} geometrías/puntos · ${formatBytes(loaded.estimatedGzipBytes)} gzip estimados`);
    console.info('[atlas:load]', state.lastLoad, state.loader.debugSnapshot());
  } catch (error) { if (sequence !== state.refreshSequence) return; console.error(error); setStatus(`No se pudieron cargar los datos: ${error.message}`, 'error'); }
}

function scheduleRefresh(reason, delay = 120) { clearTimeout(state.refreshTimer); state.refreshTimer = setTimeout(() => refreshData(reason), delay); }
function setYearRange(from, to) { elements.yearFrom.value = String(from); elements.yearTo.value = String(to); syncYearControls(); refreshData('timeline'); }
function fitTerritory(id, {updateFilter = true} = {}) { const territory = state.loader.manifest.territories[id]; if (!territory) return; state.activeTerritory = id;
  if (updateFilter) elements.province.value = id === 'comunitat_valenciana' ? 'all' : territory.provinces[0];
  state.map.fitBounds(leafletBounds(territory.bounds), {animate: false, padding: [18, 18]}); if (territory.preferred_zoom && state.map.getZoom() < territory.preferred_zoom) state.map.setZoom(territory.preferred_zoom, {animate: false}); }
function setPointMode(enabled) { state.pointMode = enabled; elements.pointHint.hidden = !enabled; elements.pointQuery.classList.toggle('active', enabled); elements.pointQuery.textContent = enabled ? 'Cancelar consulta' : 'Consultar un punto del mapa'; state.map.getContainer().style.cursor = enabled ? 'crosshair' : ''; if (enabled) state.map.closePopup(); }

function queryPoint(latlng) {
  setPointMode(false); if (state.pointMarker) state.pointMarker.removeFrom(state.map);
  state.pointMarker = L.circleMarker(latlng, {radius: 6, color: '#172421', weight: 2, fillColor: '#fff', fillOpacity: 1}).addTo(state.map);
  const point = turf.point([latlng.lng, latlng.lat]), icv = new Map(), effis = [], nearby = [];
  for (const item of state.visibleRecords) {
    try {
      if (item.record.sourceId === 'sigif') { const distance = turf.distance(point, item.feature, {units: 'kilometers'}) * 1000; if (distance <= state.loader.manifest.query.sigif_proximity_m) nearby.push({...item, distance}); continue; }
      if (item.layer.getBounds && !item.layer.getBounds().contains(latlng)) continue;
      if (!turf.booleanPointInPolygon(point, item.feature)) continue;
      if (item.record.sourceId === 'icv') { if (!icv.has(item.record.entityId)) icv.set(item.record.entityId, []); icv.get(item.record.entityId).push(item); }
      else effis.push(item);
    } catch (error) { console.warn('[atlas:point-query]', item.record.geometryId, error); }
  }
  const reused = [...icv.values()].flat().some(item => item.feature.properties.geometry_reused);
  state.historyResult = {officialIcvFireCount: icv.size, officialIcvPerimeterCount: [...icv.values()].flat().length,
    effisPerimeterCount: effis.length, nearbySigifCount: nearby.length, sigifProximityM: state.loader.manifest.query.sigif_proximity_m, reused,
    fireCount: icv.size, perimeterCount: [...icv.values()].flat().length + effis.length};
  const icvRows = [...icv.values()].map(items => `<button class="fire-row history-result" data-entity="${escapeHtml(items[0].record.entityId)}"><strong>${items[0].record.year} · ${escapeHtml(cleanText(items[0].record.municipality))}</strong><span>${items.length} perímetro(s) ICV contienen el punto</span></button>`).join('');
  const effisRows = effis.map(item => `<button class="fire-row history-result" data-entity="${escapeHtml(item.record.entityId)}"><strong>${item.record.year} · EFFIS ${escapeHtml(item.feature.properties.effis_id)}</strong><span>Perímetro satelital contiene el punto</span></button>`).join('');
  const nearbyRows = nearby.sort((a, b) => a.distance - b.distance).map(item => `<button class="fire-row history-result" data-entity="${escapeHtml(item.record.entityId)}"><strong>${item.record.year} · ${escapeHtml(cleanText(item.record.municipality))}</strong><span>${formatNumber(item.distance, 0)} m del punto consultado</span></button>`).join('');
  elements.pointHistory.innerHTML = `<strong>Perímetros que contienen este punto</strong><p>Oficiales ICV: ${icv.size} incendios identificados / ${[...icv.values()].flat().length} perímetros.<br>Satelitales EFFIS: ${effis.length} perímetros.</p>${icvRows}${effisRows}<strong>Puntos de inicio SIGIF próximos</strong><p>Radio explícito: ${formatNumber(state.loader.manifest.query.sigif_proximity_m / 1000, 0)} km · ${nearby.length} resultados.</p>${nearbyRows}${reused ? `<div class="reuse-warning">${escapeHtml(REUSE_WARNING)}</div>` : ''}`;
  elements.pointHistory.querySelectorAll('.history-result').forEach(button => button.addEventListener('click', () => selectEntity(button.dataset.entity, null, {fit: true})));
  return state.historyResult;
}

function renderSourceControls() {
  elements.sourceFilters.replaceChildren();
  for (const [id, source] of Object.entries(state.loader.manifest.sources)) {
    const label = document.createElement('label'); label.className = 'source-toggle';
    label.innerHTML = `<input type="checkbox" value="${escapeHtml(id)}" checked><span>${escapeHtml(source.short_label)}</span><small>${source.source_status.replaceAll('_', ' ')}</small>`;
    label.querySelector('input').addEventListener('change', () => refreshData('source-filter')); elements.sourceFilters.appendChild(label);
  }
}

function renderMethodology() {
  elements.methodology.innerHTML = Object.values(state.loader.manifest.sources).map(source => `<p><strong>${escapeHtml(source.short_label)}:</strong> ${escapeHtml(source.source_status.replaceAll('_', ' '))}. <a href="${escapeHtml(source.methodology_url)}" target="_blank" rel="noopener">Fuente y metodología</a>.<br><small>${escapeHtml(source.attribution)}</small></p>`).join('') + '<p>Un registro SIGIF y un perímetro EFFIS pueden corresponder al mismo episodio, pero solo se enlazan como candidatos mientras no exista confirmación suficiente. Sus superficies nunca se suman entre sí.</p>';
}

function bindEvents() {
  document.querySelectorAll('[data-territory]').forEach(button => button.addEventListener('click', () => fitTerritory(button.dataset.territory)));
  elements.yearFrom.addEventListener('input', () => syncYearControls('from')); elements.yearTo.addEventListener('input', () => syncYearControls('to'));
  elements.yearFrom.addEventListener('change', () => refreshData('timeline')); elements.yearTo.addEventListener('change', () => refreshData('timeline'));
  elements.fullPeriod.addEventListener('click', () => setYearRange(state.loader.manifest.years.min, state.loader.manifest.years.max));
  elements.province.addEventListener('change', () => refreshData('province-filter'));
  for (const input of [elements.municipality, elements.minimumArea, elements.cause, elements.gifOnly]) input.addEventListener('change', () => renderGeometry('attribute-filter'));
  elements.pointQuery.addEventListener('click', () => setPointMode(!state.pointMode));
  state.map.on('click', event => { if (state.pointMode) queryPoint(event.latlng); }); state.map.on('moveend', () => scheduleRefresh('map-view'));
}

function applyUrlOptions(params) {
  const years = state.loader.manifest.years, from = Math.max(years.min, Math.min(years.max, Number(params.get('from') || years.default))), to = Math.max(years.min, Math.min(years.max, Number(params.get('to') || years.default)));
  elements.yearFrom.value = String(Math.min(from, to)); elements.yearTo.value = String(Math.max(from, to));
  if (['all', 'castellon', 'valencia', 'alicante'].includes(params.get('province'))) elements.province.value = params.get('province');
  if (params.has('min_area')) elements.minimumArea.value = params.get('min_area'); elements.gifOnly.checked = params.get('gif') === '1';
  if (params.has('sources')) {
    const requested = new Set(params.get('sources').split(','));
    elements.sourceFilters.querySelectorAll('input').forEach(input => { input.checked = requested.has(input.value); });
  }
  state.qualityDebug = params.get('quality_debug') === '1'; syncYearControls();
}

function debugSnapshot() {
  const counts = {icv: new Set(), sigif: new Set(), effis: new Set()}; for (const item of state.visibleRecords) counts[item.record.sourceId].add(item.record.entityId);
  const selected = state.visibleRecords.filter(item => item.record.entityId === state.selectedEntityId);
  return {ready: document.body.dataset.ready === 'true', profile: state.loader.manifest.profile, territory: state.activeTerritory,
    zoom: state.map?.getZoom(), level: state.activeLevel, years: selectedYears(), activeSources: [...activeSources()], provinceFilter: elements.province.value,
    activeProvinces: state.activeProvinces, activeAssetCount: state.activeAssets.length, activeAssetUrls: state.activeAssets.map(asset => asset.url),
    loadedGeometryCount: state.loadedFeatures.length, visiblePerimeterCount: state.visibleRecords.filter(item => item.record.sourceId !== 'sigif').length,
    visibleFireCount: counts.icv.size, visibleIcvFireCount: counts.icv.size, visibleSigifRecordCount: counts.sigif.size, visibleEffisPerimeterCount: counts.effis.size,
    visibleGifCount: [...new Map(state.visibleRecords.filter(item => ['icv', 'sigif'].includes(item.record.sourceId)).map(item => [item.record.entityId, item.record])).values()].filter(item => item.isGif).length,
    selectedEntityId: state.selectedEntityId, selectedFireId: state.selectedEntityId, selectedGeometryId: state.selectedGeometryId,
    selectedVisibleGeometryCount: selected.length, selectedCandidateStrengths: selected.flatMap(item => state.loader.candidatesFor(item.feature).map(candidate => candidate.candidate_strength)),
    coverageText: elements.coverage.textContent, detailsText: elements.details.textContent,
    history: state.historyResult, lastLoad: state.lastLoad, lastRender: state.lastRender, loader: state.loader.debugSnapshot(),
    appElapsedMs: performance.now() - APP_STARTED_AT, heapUsedBytes: performance.memory ? performance.memory.usedJSHeapSize : null,
    viewport: {width: innerWidth, height: innerHeight}, mobileLayout: matchMedia('(max-width: 800px)').matches};
}

async function runDebugScenario(params) {
  const result = {};
  if (params.get('scenario') === 'zoom-transition') { result.levels = []; for (const zoom of [8, 9, 11]) { state.map.setZoom(zoom, {animate: false}); clearTimeout(state.refreshTimer); await refreshData(`debug-${zoom}`); result.levels.push(debugSnapshot()); } }
  if (params.get('scenario') === 'year-transition') { result.years = []; for (const year of [2024, 2025, 2026]) { elements.yearFrom.value = String(year); elements.yearTo.value = String(year); syncYearControls(); clearTimeout(state.refreshTimer); await refreshData(`debug-year-${year}`); result.years.push(debugSnapshot()); } }
  if (params.get('select_entity') || params.get('select_fire')) { selectEntity(params.get('select_entity') || params.get('select_fire')); result.selection = debugSnapshot(); }
  if (params.get('point')) { const [lng, lat] = params.get('point').split(',').map(Number); queryPoint(L.latLng(lat, lng)); result.point = debugSnapshot(); }
  if (params.get('point_geometry')) { const feature = state.loadedFeatures.find(item => item.properties.geometry_id === params.get('point_geometry')); if (feature) { const point = turf.pointOnFeature(feature); queryPoint(L.latLng(point.geometry.coordinates[1], point.geometry.coordinates[0])); result.point = debugSnapshot(); } }
  result.final = debugSnapshot(); elements.debugOutput.textContent = JSON.stringify(result); elements.debugOutput.dataset.complete = 'true';
}

async function initialize() {
  if (typeof L === 'undefined' || typeof turf === 'undefined') { setStatus('No se pudieron cargar Leaflet o Turf.', 'error'); return; }
  state.loader = new DatasetLoader(MANIFEST_URL, {onMetric: metric => console.debug('[atlas:request]', metric)});
  try {
    const manifest = await state.loader.init(), years = manifest.years;
    for (const input of [elements.yearFrom, elements.yearTo]) { input.min = String(years.min); input.max = String(years.max); input.value = String(years.default); }
    elements.fullPeriod.textContent = `${years.min}–${years.max}`; elements.coverageEyebrow.textContent = `${years.min}–${years.max} · histórico y reciente provisional`;
    elements.legendYearOld.textContent = String(years.min); elements.legendYearNew.textContent = String(years.max);
    renderSourceControls(); renderMethodology(); const params = new URLSearchParams(location.search); applyUrlOptions(params);
    state.map = L.map('map', {preferCanvas: true, zoomControl: true});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'}).addTo(state.map);
    for (const source of Object.values(manifest.sources)) state.map.attributionControl.addAttribution(`<a href="${escapeHtml(source.methodology_url)}" target="_blank" rel="noopener">${escapeHtml(source.short_label)}</a>`);
    bindEvents(); const initial = manifest.territories[params.get('view')] ? params.get('view') : 'comunitat_valenciana';
    if (!params.has('province') && ['castellon', 'valencia', 'alicante'].includes(initial)) elements.province.value = initial;
    if (!params.has('province') && initial === 'mariola_font_roja') elements.province.value = 'alicante';
    fitTerritory(initial, {updateFilter: false});
    if (params.has('zoom')) state.map.setZoom(Number(params.get('zoom')), {animate: false}); clearTimeout(state.refreshTimer); await refreshData('initial');
    document.body.dataset.ready = 'true'; window.__atlasDebug = {state, loader: state.loader, snapshot: debugSnapshot, refresh: refreshData, setYearRange, fitTerritory, queryPoint, selectEntity};
    if (params.get('debug') === '1') await runDebugScenario(params);
  } catch (error) { console.error(error); setStatus(`No se pudo iniciar el visor: ${error.message}`, 'error'); elements.debugOutput.textContent = JSON.stringify({error: error.message}); elements.debugOutput.dataset.complete = 'true'; }
}

await initialize();

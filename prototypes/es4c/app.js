import { Protocol } from "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs";
import { EGIFInitialLoader } from "./egif_initial_loader.mjs";
import { EGIFDetailLoader, locateRecord, pageOfInitialRows } from "./egif_detail_loader.mjs";
import { canonicalTerritoryName, TERRITORY_OPTIONS } from "./territory_catalog.mjs";
import { createRuntimeState, effectiveCoverage, reduceRuntimeState, SOURCE_COVERAGE } from "./runtime_state.mjs";
import { parseStateHash, serializeState } from "./state_serialization.mjs";
import { addOfficialTerritoryLayer } from "./territory_layer.mjs";

const ARCHIVE_PATH = "/data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles";
const SOURCE_ID = "esfire30";
const SOURCE_LAYER = "esfire30";
const FILL_LAYER = "esfire30-perimeters";
const SELECTED_LAYER = "esfire30-selected";
const YEAR_MIN = 1968;
const YEAR_MAX = 2023;
const ESFIRE_YEAR_MIN = 1985;
const ESFIRE_YEAR_MAX = 2021;
const EGIF_MANIFEST_URL = "/data/web/spain/egif/2026-08-27/manifest.json";
const DEFAULT_VIEW = { center: [-3.7, 40.3], zoom: 4 };
const VIEWS = {
  spain: DEFAULT_VIEW,
  galicia: { center: [-8.1, 42.6], zoom: 6 },
  pais_valencia: { center: [-0.7, 39.3], zoom: 8 },
};

const output = document.querySelector("#debug-output");
const selectionSummary = document.querySelector("#selection-summary");
const fromInput = document.querySelector("#from-year");
const toInput = document.querySelector("#to-year");
const applyButton = document.querySelector("#apply-years");
const territoryScope = document.querySelector("#territory-scope");
const egifStatus = document.querySelector("#egif-status");
const egifMetrics = document.querySelector("#egif-metrics");
const egifRecordBrowser = document.querySelector("#egif-record-browser");
const egifRecordRows = document.querySelector("#egif-record-rows");
const egifRecordLookup = document.querySelector("#egif-record-lookup");
const egifRecordIdInput = document.querySelector("#egif-record-id");
const egifPagePrevious = document.querySelector("#egif-page-previous");
const egifPageNext = document.querySelector("#egif-page-next");
const egifPageStatus = document.querySelector("#egif-page-status");
const egifDetail = document.querySelector("#egif-detail");
const egifDetailStatus = document.querySelector("#egif-detail-status");
const egifDetailFields = document.querySelector("#egif-detail-fields");
const esfireVisibleInput = document.querySelector("#esfire30-visible");
const egifVisibleInput = document.querySelector("#egif-visible");
const sourceCoverage = document.querySelector("#source-coverage");
const runtimeStateSummary = document.querySelector("#runtime-state-summary");
const copyStateLink = document.querySelector("#copy-state-link");
const copyStateStatus = document.querySelector("#copy-state-status");
const territoryStatus = document.querySelector("#territory-status");
const params = new URLSearchParams(location.search);
const startedAt = performance.now();
const initialHeap = performance.memory?.usedJSHeapSize ?? null;
const errors = [];
let state = createRuntimeState({
  center: [...DEFAULT_VIEW.center],
  zoom: DEFAULT_VIEW.zoom,
});
const PROTOTYPE_DEFAULT_STATE = { ...state, center: [...state.center] };
const egifLoader = new EGIFInitialLoader({ manifestUrl: EGIF_MANIFEST_URL });
const egifDetailLoader = new EGIFDetailLoader({ manifestUrl: EGIF_MANIFEST_URL });
let egifReady = Promise.resolve();
let latestEgifResult = null;
let activeInitialAssets = [];
let egifPage = 0;
const EGIF_PAGE_SIZE = 50;
const territoryIds = new Set(TERRITORY_OPTIONS.map((territory) => territory.territory_id));
let stateHydrated = false;
let restoringFromUrl = false;
let territoryLayer = null;
let territoryLayerError = null;

for (const territory of TERRITORY_OPTIONS) {
  const option = document.createElement("option");
  option.value = territory.territory_id;
  option.textContent = territory.label;
  territoryScope.append(option);
}
state = reduceRuntimeState(state, { type: "set_range", from: clampYear(params.get("from"), ESFIRE_YEAR_MIN), to: clampYear(params.get("to"), ESFIRE_YEAR_MAX) });
fromInput.value = String(state.from);
toInput.value = String(state.to);
const requestedTerritory = params.get("egif_scope");
if (requestedTerritory && [...territoryScope.options].some((option) => option.value === requestedTerritory)) {
  territoryScope.value = requestedTerritory;
  state = reduceRuntimeState(state, { type: "set_scope", territory_id: requestedTerritory });
}
const restoredHash = parseStateHash(location.hash, PROTOTYPE_DEFAULT_STATE, territoryIds);
if (restoredHash.status !== "absent") state = restoredHash.state;
fromInput.value = String(state.from);
toInput.value = String(state.to);
territoryScope.value = state.autonomous_community_id || "ES";
esfireVisibleInput.checked = state.esfire30_visible;
egifVisibleInput.checked = state.egif_visible;

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const map = new maplibregl.Map({
  container: "map",
  center: state.center,
  zoom: state.zoom,
  minZoom: 3,
  maxZoom: 14,
  attributionControl: false,
  style: {
    version: 8,
    sources: {
      [SOURCE_ID]: {
        type: "vector",
        url: `pmtiles://${location.origin}${ARCHIVE_PATH}`,
      },
    },
    layers: [
      {
        id: FILL_LAYER,
        type: "fill",
        source: SOURCE_ID,
        "source-layer": SOURCE_LAYER,
        paint: { "fill-color": "#b54d2f", "fill-opacity": 0.42, "fill-outline-color": "#76321f" },
      },
      {
        id: SELECTED_LAYER,
        type: "line",
        source: SOURCE_ID,
        "source-layer": SOURCE_LAYER,
        filter: ["==", ["get", "geometry_id"], "__none__"],
        paint: { "line-color": "#112f72", "line-width": 3.5, "line-opacity": 1 },
      },
    ],
  },
});
map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "bottom-right");

const territoryLayerReady = new Promise((resolve) => {
  map.once("load", () => {
    addOfficialTerritoryLayer(map, {
      onSelect: (territoryId) => { setEgifScope(territoryId); },
    }).then((layer) => {
      territoryLayer = layer;
      syncTerritoryLayer();
      territoryStatus.textContent = "Límite oficial BDLJE cargado. Este ámbito controla EGIF; ESFire30 aún no se filtra territorialmente.";
      resolve(layer);
    }).catch((error) => {
      territoryLayerError = String(error);
      territoryStatus.textContent = `Límite oficial no disponible: ${error.message}. EGIF y ESFire30 continúan independientemente.`;
      resolve(null);
    });
  });
});

function clampYear(value, fallback) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= YEAR_MIN && parsed <= YEAR_MAX ? parsed : fallback;
}

function yearFilter() {
  const range = effectiveCoverage(state, "esfire30");
  // Tippecanoe conserva `year` como atributo de tesela; la conversión hace
  // explícita la comparación numérica sin depender de su serialización MVT.
  if (!range) return ["==", ["get", "year"], "__outside_esfire30_coverage__"];
  const { from, to } = range;
  return ["all", [">=", ["to-number", ["get", "year"]], from], ["<=", ["to-number", ["get", "year"]], to]];
}

function applyFilters() {
  map.setFilter(FILL_LAYER, yearFilter());
  map.setFilter(SELECTED_LAYER, state.selected_geometry_id
    ? ["all", yearFilter(), ["==", ["get", "geometry_id"], state.selected_geometry_id]]
    : ["==", ["get", "geometry_id"], "__none__"]);
}

async function applyYears() {
  const from = clampYear(fromInput.value, YEAR_MIN);
  const to = clampYear(toInput.value, YEAR_MAX);
  transition({ type: "set_range", from, to });
  fromInput.value = String(state.from);
  toInput.value = String(state.to);
  applyFilters();
  await refreshSources();
}

function formatNumber(value, maximumFractionDigits = 0) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(value);
}

function formatOptionalArea(value) {
  return typeof value === "number" && Number.isFinite(value) ? `${formatNumber(value, 2)} ha` : "No disponible";
}

function formatGif(value) {
  if (value === true) return "Sí (administrativo EGIF)";
  if (value === false) return "No (administrativo EGIF)";
  return "No determinable";
}

function clearEgifSelection(updateState = true) {
  if (updateState) state = reduceRuntimeState(state, { type: "clear_egif_selection" });
  egifDetailLoader.clearSelection();
  egifDetail.hidden = true;
  egifDetailStatus.textContent = "Selecciona una parte para cargar DETAIL.";
  egifDetailFields.replaceChildren();
}

function clearGeometrySelection(updateState = true) {
  if (updateState) state = reduceRuntimeState(state, { type: "clear_geometry_selection" });
  applyFilters();
  selectionSummary.textContent = "Pulsa o toca un perímetro para inspeccionarlo.";
}

function transition(event) {
  const previous = state;
  state = reduceRuntimeState(state, event);
  if (previous.selected_geometry_id && !state.selected_geometry_id) clearGeometrySelection(false);
  if (previous.selected_egif_record_id && !state.selected_egif_record_id) clearEgifSelection(false);
  replaceStateUrl();
  return state;
}

function syncTerritoryLayer({ fit = false } = {}) {
  if (!territoryLayer) return false;
  territoryLayer.setSelected(state.autonomous_community_id);
  return fit ? territoryLayer.fit(state.autonomous_community_id) : true;
}

function sourceCoverageDescription(sourceId) {
  const source = SOURCE_COVERAGE[sourceId];
  const range = effectiveCoverage(state, sourceId);
  const visible = state[`${sourceId}_visible`];
  if (!visible) return `${source.label}: desactivada`;
  if (!range) return `${source.label}: sin cobertura para ${state.from}–${state.to}`;
  const partial = range.from !== state.from || range.to !== state.to;
  return `${source.label}: ${partial ? `cobertura efectiva ${range.from}–${range.to}` : `cobertura ${range.from}–${range.to}`}`;
}

function renderRuntimeState() {
  sourceCoverage.replaceChildren();
  for (const sourceId of ["esfire30", "egif"]) {
    const item = document.createElement("li");
    item.textContent = sourceCoverageDescription(sourceId);
    sourceCoverage.append(item);
  }
  const egifSummary = latestEgifResult?.summary;
  const territory = territoryScope.selectedOptions[0]?.textContent || "España";
  const esfireVisible = state.esfire30_visible && effectiveCoverage(state, "esfire30")
    ? map.queryRenderedFeatures({ layers: [FILL_LAYER] }).length : 0;
  runtimeStateSummary.textContent = `Periodo solicitado: ${state.from}–${state.to} · ámbito: ${territory} · fuentes: ESFire30 ${state.esfire30_visible ? "activa" : "desactivada"}, EGIF ${state.egif_visible ? "activa" : "desactivada"} · EGIF INITIAL: ${activeInitialAssets.length} asset(s), ${egifSummary?.summary?.records ?? egifSummary?.records ?? 0} partes · ESFire30 visibles en viewport: ${formatNumber(esfireVisible)}.`;
}

function coverageStatePayload() {
  const describe = (sourceId) => {
    const range = effectiveCoverage(state, sourceId);
    return {
      visible: state[`${sourceId}_visible`],
      declared_coverage: SOURCE_COVERAGE[sourceId],
      effective_coverage: range,
      status: !state[`${sourceId}_visible`] ? "disabled" : range ? "covered" : "no_coverage",
    };
  };
  return { requested_range: { from: state.from, to: state.to }, territory_id: state.autonomous_community_id || "ES", esfire30: describe("esfire30"), egif: describe("egif") };
}

function stateUrl() {
  return `${location.origin}${location.pathname}${location.search}${serializeState(state)}`;
}

function replaceStateUrl() {
  if (!stateHydrated || restoringFromUrl) return;
  history.replaceState({ prototype: "es4c", version: 1 }, "", `${location.pathname}${location.search}${serializeState(state)}`);
}

async function copyCurrentStateLink() {
  const url = stateUrl();
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url);
    else {
      const fallback = document.createElement("textarea");
      fallback.value = url;
      fallback.setAttribute("readonly", "");
      fallback.style.position = "fixed";
      fallback.style.opacity = "0";
      document.body.append(fallback);
      fallback.select();
      document.execCommand("copy");
      fallback.remove();
    }
    copyStateStatus.textContent = "Enlace copiado.";
    return { status: "copied", url };
  } catch (error) {
    copyStateStatus.textContent = "No se pudo copiar automáticamente; copia esta URL: " + url;
    return { status: "fallback", url, error: String(error) };
  }
}

function renderEgifPage() {
  egifRecordRows.replaceChildren();
  if (!activeInitialAssets.length) {
    egifRecordBrowser.hidden = true;
    return;
  }
  const pageData = pageOfInitialRows(activeInitialAssets, state.from, state.to, egifPage, EGIF_PAGE_SIZE);
  const pages = Math.max(1, Math.ceil(pageData.total / EGIF_PAGE_SIZE));
  if (egifPage >= pages) {
    egifPage = pages - 1;
    return renderEgifPage();
  }
  for (const row of pageData.rows) {
    const tr = document.createElement("tr");
    const values = [
      String(row.year),
      row.record_id,
      row.province_id || "No disponible",
      row.municipality_id || "No resuelto",
      formatOptionalArea(row.reported_forest_area_ha),
      row.is_gif_forest_ge_500_ha === true ? "Sí" : row.is_gif_forest_ge_500_ha === false ? "No" : "No det.",
    ];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      if (index === 1) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = value;
        button.dataset.recordId = row.record_id;
        cell.append(button);
      } else cell.textContent = value;
      tr.append(cell);
    });
    egifRecordRows.append(tr);
  }
  egifPageStatus.textContent = `${formatNumber(pageData.total)} partes · página ${egifPage + 1}/${pages}`;
  egifPagePrevious.disabled = egifPage === 0;
  egifPageNext.disabled = egifPage + 1 >= pages;
  egifRecordBrowser.hidden = false;
}

function renderDetailFields(record, names) {
  egifDetailFields.replaceChildren();
  const municipality = record.municipality_id
    ? (names.municipality || record.municipality_id)
    : "Municipio no resuelto en la normalización";
  const rows = [
    ["Record ID", record.record_id],
    ["ID fuente / Número de parte", record.source_record_id || "No disponible"],
    ["Fuente", "EGIF · parte administrativo"],
    ["Año", record.year],
    ["Fecha de inicio", record.detection_date || "No disponible"],
    ["Fecha de extinción", record.extinction_date || "No disponible"],
    ["CCAA", names.autonomous_community || record.autonomous_community_id || "No disponible"],
    ["Provincia", names.province || record.province_id || "No disponible"],
    ["Municipio", municipality],
    ["Municipio declarado en la fuente", record.source_municipality_name || "No disponible"],
    ["Paraje declarado", record.source_paraje || "No disponible"],
    ["Superficie forestal declarada", formatOptionalArea(record.reported_forest_area_ha)],
    ["Superficie total declarada", formatOptionalArea(record.reported_total_area_ha)],
    ["Superficie arbolada declarada", formatOptionalArea(record.reported_wooded_area_ha)],
    ["Superficie no arbolada declarada", formatOptionalArea(record.reported_nonwooded_area_ha)],
    ["GIF", formatGif(record.is_gif_forest_ge_500_ha)],
    ["Causa", record.cause_source_code == null ? "Código EGIF no disponible" : `Código EGIF ${record.cause_source_code} (sin normalizar)`],
    ["Causa canónica", record.canonical_cause || "No mapeada"],
    ["Estado del mapeo", record.cause_mapping_status || "unmapped"],
    ["Modelo de parte", record.form_model || "No disponible"],
    ["ID de base fuente", record.source_database_id || "No disponible"],
    ["Identidad del episodio", record.episode_identity_status || "unresolved"],
  ];
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const definition = document.createElement("dd");
    definition.textContent = value == null ? "No disponible" : String(value);
    egifDetailFields.append(term, definition);
  }
}

async function selectEgifRecord(recordId) {
  if (!locateRecord(activeInitialAssets, recordId)) {
    egifDetail.hidden = false;
    egifDetailStatus.textContent = "El record_id no pertenece al ámbito EGIF cargado.";
    return { status: "missing" };
  }
  const initialLocation = locateRecord(activeInitialAssets, recordId);
  transition({ type: "select_egif_record", record_id: recordId, year: initialLocation.loaded.data.columns.year[initialLocation.ordinal] });
  egifDetail.hidden = false;
  egifDetailStatus.textContent = "Cargando DETAIL EGIF solo para la parte seleccionada…";
  egifDetailFields.replaceChildren();
  const heapBefore = performance.memory?.usedJSHeapSize ?? null;
  try {
    const result = await egifDetailLoader.select({ recordId, loadedAssets: activeInitialAssets });
    if (result.status === "stale" || state.selected_egif_record_id !== recordId) return result;
    const [autonomous_community, province, municipality] = await Promise.all([
      canonicalTerritoryName(result.record.autonomous_community_id),
      canonicalTerritoryName(result.record.province_id),
      canonicalTerritoryName(result.record.municipality_id),
    ]);
    if (state.selected_egif_record_id !== recordId) return { status: "stale" };
    renderDetailFields(result.record, { autonomous_community, province, municipality });
    const heapAfter = performance.memory?.usedJSHeapSize ?? null;
    egifDetailStatus.textContent = `DETAIL cargado para ${recordId}${result.metrics.cached ? " desde caché de sesión" : ""}.`;
    return { ...result, heap_delta_bytes: heapBefore === null || heapAfter === null ? null : heapAfter - heapBefore };
  } catch (error) {
    if (error.name === "AbortError") return { status: "stale" };
    if (state.selected_egif_record_id === recordId) {
      egifDetailStatus.textContent = `No se pudo cargar DETAIL EGIF: ${error.message}. INITIAL y ESFire30 continúan disponibles.`;
    }
    return { status: "error", error: String(error) };
  }
}

function renderEgifResult(result) {
  if (result.status === "stale") return;
  latestEgifResult = { ...result };
  delete latestEgifResult.loaded_assets;
  egifMetrics.hidden = true;
  egifMetrics.replaceChildren();
  const summary = result.summary;
  if (result.kind === "manifest_summary") {
    activeInitialAssets = [];
    egifRecordBrowser.hidden = true;
    egifStatus.textContent = `${formatNumber(summary.records)} partes EGIF disponibles en ${state.from}–${state.to}; España usa solo el manifest y no carga INITIAL.`;
    const rows = [["Bloques implicados", summary.blocks.map(([from, to]) => `${from}–${to}`).join(", ")], ["Assets INITIAL no cargados", "0"]];
    for (const [label, value] of rows) { const term = document.createElement("dt"); term.textContent = label; const definition = document.createElement("dd"); definition.textContent = value; egifMetrics.append(term, definition); }
    egifMetrics.hidden = false;
    renderRuntimeState();
    return;
  }
  activeInitialAssets = result.loaded_assets || [];
  egifPage = 0;
  egifStatus.textContent = `${formatNumber(summary.records)} partes EGIF cargados en ${result.assets.length} asset(s) INITIAL. No hay geometrías EGIF ni enlaces con ESFire30.`;
  const rows = [
    ["GIF administrativos", formatNumber(summary.administrative_gif)],
    ["Superficie forestal declarada (valores conocidos)", `${formatNumber(summary.known_forest_area_sum, 2)} ha`],
    ["Partes con superficie forestal conocida", formatNumber(summary.records_with_known_forest_area)],
    ["Partes con superficie forestal desconocida", formatNumber(summary.records_with_unknown_forest_area)],
    ["Partes con municipio resuelto", formatNumber(summary.municipality_resolved)],
    ["Partes sin municipio resuelto", formatNumber(summary.municipality_unresolved)],
    ["Años con partes", formatNumber(Object.keys(summary.annual).length)],
    ["Distribución anual", Object.entries(summary.annual).map(([year, count]) => `${year}: ${formatNumber(count)}`).join(" · ")],
  ];
  for (const [label, value] of rows) { const term = document.createElement("dt"); term.textContent = label; const definition = document.createElement("dd"); definition.textContent = value; egifMetrics.append(term, definition); }
  egifMetrics.hidden = false;
  renderEgifPage();
  renderRuntimeState();
}

async function refreshEgif() {
  const coverage = effectiveCoverage(state, "egif");
  if (!state.egif_visible || !coverage) {
    egifLoader.cancel();
    activeInitialAssets = [];
    egifMetrics.hidden = true;
    egifRecordBrowser.hidden = true;
    clearEgifSelection(false);
    egifStatus.textContent = state.egif_visible
      ? `EGIF: sin cobertura para ${state.from}–${state.to}.`
      : "EGIF desactivado; no se cargan assets INITIAL.";
    latestEgifResult = { status: "inactive", kind: "no_coverage", summary: { records: 0, asset_count: 0 } };
    renderRuntimeState();
    return latestEgifResult;
  }
  activeInitialAssets = [];
  egifRecordBrowser.hidden = true;
  const territoryId = state.autonomous_community_id || "ES";
  egifStatus.textContent = territoryId === "ES" ? "Calculando resumen EGIF desde el manifest…" : "Cargando assets INITIAL EGIF…";
  try {
    const result = await egifLoader.loadScope({ territoryId, fromYear: coverage.from, toYear: coverage.to });
    renderEgifResult(result);
    return result;
  } catch (error) {
    egifStatus.textContent = `EGIF no disponible: ${error.message}. ESFire30 continúa operativo.`;
    latestEgifResult = { status: "error", error: String(error) };
    renderRuntimeState();
    return latestEgifResult;
  }
}

async function setEgifScope(territoryId, { fit = true } = {}) {
  territoryScope.value = territoryId;
  transition({ type: "set_scope", territory_id: territoryId });
  await territoryLayerReady;
  syncTerritoryLayer({ fit });
  return refreshSources();
}

async function setSourceVisibility(sourceId, visible) {
  transition({ type: "set_visibility", source_id: sourceId, visible });
  if (sourceId === "esfire30") {
    applyFilters();
    renderRuntimeState();
    return null;
  }
  return refreshSources();
}

async function refreshSources() {
  applyFilters();
  const result = await refreshEgif();
  renderRuntimeState();
  return result;
}

function findLoadedGeometry(geometryId) {
  return map.querySourceFeatures(SOURCE_ID, { sourceLayer: SOURCE_LAYER })
    .find((feature) => String(feature.properties?.geometry_id) === geometryId) || null;
}

async function restoreSelectionsFromState() {
  if (state.selected_egif_record_id) {
    if (!state.egif_visible || !effectiveCoverage(state, "egif")) clearEgifSelection();
    else {
      const selected = await selectEgifRecord(state.selected_egif_record_id);
      if (selected.status !== "complete") clearEgifSelection();
    }
  }
  if (state.selected_geometry_id) {
    const geometry = state.esfire30_visible && effectiveCoverage(state, "esfire30")
      ? findLoadedGeometry(state.selected_geometry_id) : null;
    if (geometry) selectFeature(geometry);
    else clearGeometrySelection();
  }
}

async function restoreStateFromHash() {
  const parsed = parseStateHash(location.hash, PROTOTYPE_DEFAULT_STATE, territoryIds);
  if (parsed.status === "absent") return { status: "absent" };
  restoringFromUrl = true;
  state = parsed.state;
  fromInput.value = String(state.from);
  toInput.value = String(state.to);
  territoryScope.value = state.autonomous_community_id || "ES";
  esfireVisibleInput.checked = state.esfire30_visible;
  egifVisibleInput.checked = state.egif_visible;
  map.jumpTo({ center: state.center, zoom: state.zoom });
  await territoryLayerReady;
  // La URL contiene su propia vista. Solo se resalta el límite; no se hace
  // fitBounds durante restauración porque destruiría center/zoom compartidos.
  syncTerritoryLayer();
  applyFilters();
  await refreshSources();
  await waitForIdle();
  await restoreSelectionsFromState();
  restoringFromUrl = false;
  stateHydrated = true;
  renderRuntimeState();
  replaceStateUrl();
  return { status: parsed.status, state: { ...state } };
}

function selectFeature(feature) {
  const geometryId = feature?.properties?.geometry_id;
  if (!geometryId) return null;
  transition({ type: "select_geometry", geometry_id: String(geometryId), year: Number(feature.properties.year) });
  applyFilters();
  const year = feature.properties.year ?? "no disponible";
  selectionSummary.textContent = `geometry_id: ${state.selected_geometry_id} · año: ${year} · fuente: ESFire30 · superficie: no incluida en esta tesela diagnóstica.`;
  return state.selected_geometry_id;
}

function selectAtPoint(point) {
  const features = map.queryRenderedFeatures(point, { layers: [FILL_LAYER] });
  return features.length ? selectFeature(features[0]) : null;
}

function representativeCoordinate(geometry) {
  const visit = (value) => {
    if (!Array.isArray(value)) return null;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      return Math.abs(value[0]) <= 180 && Math.abs(value[1]) <= 90 ? [value[0], value[1]] : null;
    }
    for (const nested of value) {
      const found = visit(nested);
      if (found) return found;
    }
    return null;
  };
  return visit(geometry?.coordinates);
}

function selectFirstRenderedFeature() {
  // `queryRenderedFeatures` sin punto devuelve solo las features visibles. El
  // smoke pasa después por la misma función `selectFeature` que usa el clic.
  const feature = map.queryRenderedFeatures({ layers: [FILL_LAYER] })[0];
  const selected = selectFeature(feature);
  return selected ? { geometry_id: selected, representative_coordinate: representativeCoordinate(feature.geometry) } : null;
}

function waitForIdle(timeoutMs = 25000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("MapLibre no alcanzó idle")), timeoutMs);
    map.once("idle", () => { clearTimeout(timeout); resolve(); });
  });
}

async function rangeStats() {
  const response = await fetch("/__range_stats", { cache: "no-store" });
  return response.ok ? response.json() : { unavailable: true, status: response.status };
}

function resources() {
  const rows = performance.getEntriesByType("resource").filter((entry) => entry.name.includes(".pmtiles"));
  return {
    requests: rows.length,
    transfer_bytes: rows.reduce((sum, row) => sum + (row.transferSize || 0), 0),
    encoded_bytes: rows.reduce((sum, row) => sum + (row.encodedBodySize || 0), 0),
  };
}

function persistView() {
  const center = map.getCenter();
  state.center = [center.lng, center.lat];
  state.zoom = map.getZoom();
  replaceStateUrl();
}

map.on("moveend", persistView);
map.on("click", FILL_LAYER, (event) => selectFeature(event.features?.[0]));
map.on("mouseenter", FILL_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
map.on("mouseleave", FILL_LAYER, () => { map.getCanvas().style.cursor = ""; });
map.on("error", (event) => errors.push(String(event?.error || "MapLibre error")));
applyButton.addEventListener("click", () => { applyYears(); });
territoryScope.addEventListener("change", () => { setEgifScope(territoryScope.value); });
esfireVisibleInput.addEventListener("change", () => { setSourceVisibility("esfire30", esfireVisibleInput.checked); });
egifVisibleInput.addEventListener("change", () => { setSourceVisibility("egif", egifVisibleInput.checked); });
egifRecordRows.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-record-id]");
  if (button) selectEgifRecord(button.dataset.recordId);
});
egifRecordLookup.addEventListener("submit", (event) => {
  event.preventDefault();
  const recordId = egifRecordIdInput.value.trim();
  if (recordId) selectEgifRecord(recordId);
});
egifPagePrevious.addEventListener("click", () => { if (egifPage > 0) { egifPage -= 1; renderEgifPage(); } });
egifPageNext.addEventListener("click", () => { egifPage += 1; renderEgifPage(); });
copyStateLink.addEventListener("click", () => { copyCurrentStateLink(); });
window.addEventListener("hashchange", () => { restoreStateFromHash().catch((error) => errors.push(String(error))); });
window.addEventListener("popstate", () => { restoreStateFromHash().catch((error) => errors.push(String(error))); });

function activeRecordId(predicate = () => true, offset = 0) {
  let matches = 0;
  for (const loaded of activeInitialAssets) {
    const columns = loaded.data.columns;
    for (let ordinal = 0; ordinal < columns.record_id.length; ordinal += 1) {
      // El asset contiene todo el bloque: el smoke debe escoger una fila que
      // pertenezca al rango exacto activo, igual que la lista y la ficha.
      const year = columns.year[ordinal];
      if (year < state.from || year > state.to) continue;
      if (!predicate(columns, ordinal)) continue;
      if (matches === offset) return columns.record_id[ordinal];
      matches += 1;
    }
  }
  return null;
}

async function runDetailSmoke(mode) {
  const first = activeRecordId();
  if (!first) return { status: "missing_initial" };
  if (mode === "change_block") {
    fromInput.value = "2003";
    toInput.value = "2012";
    await applyYears();
    const recordId = activeRecordId();
    const result = await selectEgifRecord(recordId);
    return { mode, record_id: recordId, result };
  }
  if (mode === "null_municipality") {
    const recordId = activeRecordId((columns, ordinal) => columns.municipality_id[ordinal] == null);
    const result = await selectEgifRecord(recordId);
    return { mode, record_id: recordId, result };
  }
  if (mode === "same_asset") {
    const second = activeRecordId(() => true, 1);
    const firstResult = await selectEgifRecord(first);
    const secondResult = await selectEgifRecord(second);
    return { mode, first: { record_id: first, result: firstResult }, second: { record_id: second, result: secondResult } };
  }
  if (mode === "rapid") {
    const second = activeRecordId(() => true, 1);
    const firstPromise = selectEgifRecord(first);
    const secondPromise = selectEgifRecord(second);
    const [firstResult, secondResult] = await Promise.all([firstPromise, secondPromise]);
    return { mode, first: { record_id: first, result: firstResult }, second: { record_id: second, result: secondResult }, final_record_id: state.selected_egif_record_id };
  }
  const result = await selectEgifRecord(first);
  return { mode: mode || "single", record_id: first, result };
}

async function prepareStateRoundTrip(mode, name) {
  let egifSelection = null;
  if (mode === "egif" || mode === "both") egifSelection = await runDetailSmoke("single");
  if (mode === "geometry" || mode === "both") {
    const view = VIEWS[name] || VIEWS.pais_valencia;
    map.jumpTo({ center: view.center, zoom: view.zoom });
    await waitForIdle();
    selectFirstRenderedFeature();
  }
  const copied = await copyCurrentStateLink();
  return { copied, hash: serializeState(state), egif_selection: egifSelection, state: { ...state } };
}

async function runSmoke(name, initialReady = false) {
  if (!initialReady) await waitForIdle();
  const preparedRoundTrip = params.get("state_prepare")
    ? await prepareStateRoundTrip(params.get("state_prepare"), name) : null;
  let cancellation = null;
  let territoryInteraction = null;
  if (params.get("territory_select") || params.get("territory_click")) {
    const territoryId = params.get("territory_select") || params.get("territory_click");
    if (params.get("territory_click")) {
      // Reutiliza exactamente la misma ruta que el listener de clic de la
      // feature administrativa, no una deducción desde ESFire30.
      await territoryLayer.selectFromFeature(territoryLayer.byId.get(territoryId));
    } else await setEgifScope(territoryId);
    await waitForIdle();
    territoryInteraction = { mode: params.get("territory_click") ? "click_feature" : "selector", territory_id: state.autonomous_community_id, center: [...state.center], zoom: state.zoom };
  }
  if (params.get("egif_rapid") === "1") {
    const obsolete = setEgifScope("ES:CCAA:12");
    await Promise.resolve();
    const current = setEgifScope("ES:CCAA:17");
    const [obsoleteResult, currentResult] = await Promise.all([obsolete, current]);
    cancellation = { obsolete_status: obsoleteResult.status, current_status: currentResult.status, final_territory_id: state.autonomous_community_id };
  }
  let sourceToggle = null;
  if (params.get("source_toggle")) {
    const [sourceId, rawVisible] = params.get("source_toggle").split(":", 2);
    await setSourceVisibility(sourceId, rawVisible !== "off");
    sourceToggle = { source_id: sourceId, visible: state[`${sourceId}_visible`] };
  }
  let rangeCancellation = null;
  if (params.get("range_rapid") === "1") {
    fromInput.value = "1975";
    toInput.value = "1975";
    const obsolete = applyYears();
    fromInput.value = "1995";
    toInput.value = "1995";
    const current = applyYears();
    const [obsoleteResult, currentResult] = await Promise.all([obsolete, current]);
    rangeCancellation = { obsolete_status: obsoleteResult?.status, current_status: currentResult?.status, final_range: { from: state.from, to: state.to } };
  }
  let historyRoundTrip = null;
  if (params.get("history_test") === "1") {
    const original = serializeState(state);
    const alternate = serializeState({ ...state, from: 1975, to: 1975, selected_geometry_id: null, selected_egif_record_id: null });
    history.pushState({ prototype: "es4c", test: "alternate" }, "", `${location.pathname}${location.search}${alternate}`);
    await restoreStateFromHash();
    history.back();
    await new Promise((resolve) => setTimeout(resolve, 150));
    historyRoundTrip = { original, alternate, final_range: { from: state.from, to: state.to } };
  }
  const detail = params.get("egif_detail") ? await runDetailSmoke(params.get("egif_detail")) : null;
  const initial = {
    range: await rangeStats(), resources: resources(), usable_ms: performance.now() - startedAt,
    heap_delta_bytes: initialHeap === null || !performance.memory ? null : performance.memory.usedJSHeapSize - initialHeap,
    rendered_features: map.queryRenderedFeatures({ layers: [FILL_LAYER] }).length,
    source_feature_sample: map.querySourceFeatures(SOURCE_ID, { sourceLayer: SOURCE_LAYER })[0]?.properties ?? null,
  };
  const view = VIEWS[name] || VIEWS.spain;
  if (name !== "spain" && params.get("territory_restore") !== "1") {
    map.jumpTo({ center: view.center, zoom: view.zoom });
    await waitForIdle();
  }
  const afterNavigation = { range: await rangeStats(), resources: resources() };
  const selection = params.get("territory_restore") === "1" ? null : selectFirstRenderedFeature();
  let stableAtNextZoom = false;
  if (selection) {
    map.jumpTo({ center: selection.representative_coordinate || map.getCenter(), zoom: Math.min(map.getZoom() + 1, 14) });
    await waitForIdle();
    stableAtNextZoom = map.queryRenderedFeatures({ layers: [SELECTED_LAYER] })
      .some((feature) => String(feature.properties?.geometry_id) === selection.geometry_id);
  }
  const result = {
    prototype: "es4c1c2",
    scenario: name,
    archive: ARCHIVE_PATH,
    source: "ESFire30",
    geometry_semantics: "documented_remote_sensing_perimeter",
    state: { ...state },
    initial,
    after_navigation: afterNavigation,
    after_selection: { range: await rangeStats(), resources: resources() },
    selection: { ...selection, stable_at_next_zoom: stableAtNextZoom },
    egif: latestEgifResult,
    egif_detail: detail,
    egif_record_browser: {
      visible: !egifRecordBrowser.hidden,
      rows: egifRecordRows.children.length,
      detail_visible: !egifDetail.hidden,
    },
    cancellation,
    range_cancellation: rangeCancellation,
    history_round_trip: historyRoundTrip,
    serialized_hash: preparedRoundTrip?.hash || null,
    copy_result: preparedRoundTrip?.copied || null,
    prepared_round_trip: preparedRoundTrip,
    source_toggle: sourceToggle,
    territory_layer: territoryLayer ? {
      loaded: true,
      selected_territory_id: state.autonomous_community_id,
      selected_bounds: state.autonomous_community_id ? territoryLayer.byId.get(state.autonomous_community_id)?.properties?.bounds || null : null,
      national_bounds: territoryLayer.collection.metadata?.national_bounds || null,
      interaction: territoryInteraction,
      error: null,
    } : { loaded: false, error: territoryLayerError },
    coverage: coverageStatePayload(),
    heap_delta_bytes: initialHeap === null || !performance.memory ? null : performance.memory.usedJSHeapSize - initialHeap,
    errors,
  };
  output.textContent = JSON.stringify(result);
  output.dataset.complete = "true";
  return result;
}

map.once("idle", () => {
  territoryLayerReady.then(async () => {
    applyFilters();
    renderRuntimeState();
    egifReady = refreshSources().then(async () => {
    await restoreSelectionsFromState();
    stateHydrated = true;
    renderRuntimeState();
    replaceStateUrl();
    });
    const smoke = params.get("smoke");
    if (smoke) egifReady.then(() => runSmoke(smoke, true)).catch((error) => {
      output.textContent = JSON.stringify({ prototype: "es4c1c2", scenario: smoke, errors: [...errors, String(error)] });
      output.dataset.complete = "true";
    });
  });
});

window.__es4cRuntime = {
  map,
  getState: () => ({ ...state }),
  selectFirstRenderedFeature,
  applyYears,
  setEgifScope,
  refreshEgif,
  refreshSources,
  setSourceVisibility,
  selectEgifRecord,
  serializeState: () => serializeState(state),
  restoreStateFromHash,
  copyCurrentStateLink,
  territoryLayerReady,
  getEgifResult: () => latestEgifResult,
  runSmoke,
  ARCHIVE_PATH,
};

import { Protocol } from "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs";
import { EGIFInitialLoader } from "./egif_initial_loader.mjs";
import { TERRITORY_OPTIONS } from "./territory_catalog.mjs";

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
const params = new URLSearchParams(location.search);
const startedAt = performance.now();
const initialHeap = performance.memory?.usedJSHeapSize ?? null;
const errors = [];
const state = {
  center: [...DEFAULT_VIEW.center],
  zoom: DEFAULT_VIEW.zoom,
  from: YEAR_MIN,
  to: YEAR_MAX,
  territory_scope: "ES",
  autonomous_community_id: null,
  selected_geometry_id: null,
};
const egifLoader = new EGIFInitialLoader({ manifestUrl: EGIF_MANIFEST_URL });
let egifReady = Promise.resolve();
let latestEgifResult = null;

for (const territory of TERRITORY_OPTIONS) {
  const option = document.createElement("option");
  option.value = territory.territory_id;
  option.textContent = territory.label;
  territoryScope.append(option);
}
state.from = clampYear(params.get("from"), ESFIRE_YEAR_MIN);
state.to = clampYear(params.get("to"), ESFIRE_YEAR_MAX);
if (state.from > state.to) [state.from, state.to] = [state.to, state.from];
fromInput.value = String(state.from);
toInput.value = String(state.to);
const requestedTerritory = params.get("egif_scope");
if (requestedTerritory && [...territoryScope.options].some((option) => option.value === requestedTerritory)) {
  territoryScope.value = requestedTerritory;
  state.territory_scope = requestedTerritory === "ES" ? "ES" : "autonomous_community";
  state.autonomous_community_id = requestedTerritory === "ES" ? null : requestedTerritory;
}

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

function clampYear(value, fallback) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= YEAR_MIN && parsed <= YEAR_MAX ? parsed : fallback;
}

function yearFilter() {
  // Tippecanoe conserva `year` como atributo de tesela; la conversión hace
  // explícita la comparación numérica sin depender de su serialización MVT.
  const from = Math.max(state.from, ESFIRE_YEAR_MIN);
  const to = Math.min(state.to, ESFIRE_YEAR_MAX);
  if (from > to) return ["==", ["get", "year"], "__outside_esfire30_coverage__"];
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
  state.from = Math.min(from, to);
  state.to = Math.max(from, to);
  fromInput.value = String(state.from);
  toInput.value = String(state.to);
  applyFilters();
  await refreshEgif();
}

function formatNumber(value, maximumFractionDigits = 0) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(value);
}

function renderEgifResult(result) {
  latestEgifResult = result;
  egifMetrics.hidden = true;
  egifMetrics.replaceChildren();
  if (result.status === "stale") return;
  const summary = result.summary;
  if (result.kind === "manifest_summary") {
    egifStatus.textContent = `${formatNumber(summary.records)} partes EGIF disponibles en ${state.from}–${state.to}; España usa solo el manifest y no carga INITIAL.`;
    const rows = [["Bloques implicados", summary.blocks.map(([from, to]) => `${from}–${to}`).join(", ")], ["Assets INITIAL no cargados", "0"]];
    for (const [label, value] of rows) { const term = document.createElement("dt"); term.textContent = label; const definition = document.createElement("dd"); definition.textContent = value; egifMetrics.append(term, definition); }
    egifMetrics.hidden = false;
    return;
  }
  egifStatus.textContent = `${formatNumber(summary.records)} partes EGIF cargados en ${result.assets.length} asset(s) INITIAL. No hay geometrías EGIF ni enlaces con ESFire30.`;
  const rows = [
    ["GIF administrativos", formatNumber(summary.administrative_gif)],
    ["Superficie forestal declarada (valores conocidos)", `${formatNumber(summary.known_forest_area_sum, 2)} ha`],
    ["Partes con superficie forestal desconocida", formatNumber(summary.records_with_unknown_forest_area)],
    ["Partes con municipio resuelto", formatNumber(summary.municipality_resolved)],
    ["Partes sin municipio resuelto", formatNumber(summary.municipality_unresolved)],
    ["Años con partes", formatNumber(Object.keys(summary.annual).length)],
    ["Distribución anual", Object.entries(summary.annual).map(([year, count]) => `${year}: ${formatNumber(count)}`).join(" · ")],
  ];
  for (const [label, value] of rows) { const term = document.createElement("dt"); term.textContent = label; const definition = document.createElement("dd"); definition.textContent = value; egifMetrics.append(term, definition); }
  egifMetrics.hidden = false;
}

async function refreshEgif() {
  const territoryId = state.autonomous_community_id || "ES";
  egifStatus.textContent = territoryId === "ES" ? "Calculando resumen EGIF desde el manifest…" : "Cargando assets INITIAL EGIF…";
  try {
    const result = await egifLoader.loadScope({ territoryId, fromYear: state.from, toYear: state.to });
    renderEgifResult(result);
    return result;
  } catch (error) {
    egifStatus.textContent = `EGIF no disponible: ${error.message}. ESFire30 continúa operativo.`;
    latestEgifResult = { status: "error", error: String(error) };
    return latestEgifResult;
  }
}

async function setEgifScope(territoryId) {
  territoryScope.value = territoryId;
  state.territory_scope = territoryId === "ES" ? "ES" : "autonomous_community";
  state.autonomous_community_id = territoryId === "ES" ? null : territoryId;
  return refreshEgif();
}

function selectFeature(feature) {
  const geometryId = feature?.properties?.geometry_id;
  if (!geometryId) return null;
  state.selected_geometry_id = String(geometryId);
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
}

map.on("moveend", persistView);
map.on("click", FILL_LAYER, (event) => selectFeature(event.features?.[0]));
map.on("mouseenter", FILL_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
map.on("mouseleave", FILL_LAYER, () => { map.getCanvas().style.cursor = ""; });
map.on("error", (event) => errors.push(String(event?.error || "MapLibre error")));
applyButton.addEventListener("click", () => { applyYears(); });
territoryScope.addEventListener("change", () => { setEgifScope(territoryScope.value); });

async function runSmoke(name, initialReady = false) {
  if (!initialReady) await waitForIdle();
  let cancellation = null;
  if (params.get("egif_rapid") === "1") {
    const obsolete = setEgifScope("ES:CCAA:12");
    await Promise.resolve();
    const current = setEgifScope("ES:CCAA:17");
    const [obsoleteResult, currentResult] = await Promise.all([obsolete, current]);
    cancellation = { obsolete_status: obsoleteResult.status, current_status: currentResult.status, final_territory_id: state.autonomous_community_id };
  }
  const initial = {
    range: await rangeStats(), resources: resources(), usable_ms: performance.now() - startedAt,
    heap_delta_bytes: initialHeap === null || !performance.memory ? null : performance.memory.usedJSHeapSize - initialHeap,
    rendered_features: map.queryRenderedFeatures({ layers: [FILL_LAYER] }).length,
    source_feature_sample: map.querySourceFeatures(SOURCE_ID, { sourceLayer: SOURCE_LAYER })[0]?.properties ?? null,
  };
  const view = VIEWS[name] || VIEWS.spain;
  if (name !== "spain") {
    map.jumpTo({ center: view.center, zoom: view.zoom });
    await waitForIdle();
  }
  const afterNavigation = { range: await rangeStats(), resources: resources() };
  const selection = selectFirstRenderedFeature();
  let stableAtNextZoom = false;
  if (selection) {
    map.jumpTo({ center: selection.representative_coordinate || map.getCenter(), zoom: Math.min(map.getZoom() + 1, 14) });
    await waitForIdle();
    stableAtNextZoom = map.queryRenderedFeatures({ layers: [SELECTED_LAYER] })
      .some((feature) => String(feature.properties?.geometry_id) === selection.geometry_id);
  }
  const result = {
    prototype: "es4c1b1",
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
    cancellation,
    heap_delta_bytes: initialHeap === null || !performance.memory ? null : performance.memory.usedJSHeapSize - initialHeap,
    errors,
  };
  output.textContent = JSON.stringify(result);
  output.dataset.complete = "true";
  return result;
}

map.once("idle", () => {
  applyFilters();
  egifReady = refreshEgif();
  const smoke = params.get("smoke");
  if (smoke) egifReady.then(() => runSmoke(smoke, true)).catch((error) => {
      output.textContent = JSON.stringify({ prototype: "es4c1b1", scenario: smoke, errors: [...errors, String(error)] });
      output.dataset.complete = "true";
    });
});

window.__es4cRuntime = {
  map,
  getState: () => ({ ...state }),
  selectFirstRenderedFeature,
  applyYears,
  setEgifScope,
  refreshEgif,
  getEgifResult: () => latestEgifResult,
  runSmoke,
  ARCHIVE_PATH,
};

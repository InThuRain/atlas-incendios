import { Protocol } from "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs";

const ARCHIVE_PATH = "/data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles";
const SOURCE_ID = "esfire30";
const SOURCE_LAYER = "esfire30";
const FILL_LAYER = "esfire30-perimeters";
const SELECTED_LAYER = "esfire30-selected";
const YEAR_MIN = 1985;
const YEAR_MAX = 2021;
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
const params = new URLSearchParams(location.search);
const startedAt = performance.now();
const initialHeap = performance.memory?.usedJSHeapSize ?? null;
const errors = [];
const state = {
  center: [...DEFAULT_VIEW.center],
  zoom: DEFAULT_VIEW.zoom,
  from: YEAR_MIN,
  to: YEAR_MAX,
  selected_geometry_id: null,
};

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
  return ["all", [">=", ["to-number", ["get", "year"]], state.from], ["<=", ["to-number", ["get", "year"]], state.to]];
}

function applyFilters() {
  map.setFilter(FILL_LAYER, yearFilter());
  map.setFilter(SELECTED_LAYER, state.selected_geometry_id
    ? ["all", yearFilter(), ["==", ["get", "geometry_id"], state.selected_geometry_id]]
    : ["==", ["get", "geometry_id"], "__none__"]);
}

function applyYears() {
  const from = clampYear(fromInput.value, YEAR_MIN);
  const to = clampYear(toInput.value, YEAR_MAX);
  state.from = Math.min(from, to);
  state.to = Math.max(from, to);
  fromInput.value = String(state.from);
  toInput.value = String(state.to);
  applyFilters();
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
applyButton.addEventListener("click", applyYears);

async function runSmoke(name, initialReady = false) {
  if (!initialReady) await waitForIdle();
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
    prototype: "es4c1a",
    scenario: name,
    archive: ARCHIVE_PATH,
    source: "ESFire30",
    geometry_semantics: "documented_remote_sensing_perimeter",
    state: { ...state },
    initial,
    after_navigation: afterNavigation,
    after_selection: { range: await rangeStats(), resources: resources() },
    selection: { ...selection, stable_at_next_zoom: stableAtNextZoom },
    heap_delta_bytes: initialHeap === null || !performance.memory ? null : performance.memory.usedJSHeapSize - initialHeap,
    errors,
  };
  output.textContent = JSON.stringify(result);
  output.dataset.complete = "true";
  return result;
}

map.once("idle", () => {
  applyFilters();
  const smoke = params.get("smoke");
  if (smoke) runSmoke(smoke, true).catch((error) => {
    output.textContent = JSON.stringify({ prototype: "es4c1a", scenario: smoke, errors: [...errors, String(error)] });
    output.dataset.complete = "true";
  });
});

window.__es4cRuntime = {
  map,
  getState: () => ({ ...state }),
  selectFirstRenderedFeature,
  applyYears,
  runSmoke,
  ARCHIVE_PATH,
};

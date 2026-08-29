import { Protocol } from "/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs";

const params = new URLSearchParams(location.search);
const encoding = params.get("encoding") || "slots";
const ARCHIVE = encoding === "strings" ? "/data/derived/spain/es4c2b/pmtiles/esfire30-territories-sample-strings.pmtiles" : "/data/derived/spain/es4c2b/pmtiles/esfire30-territories-sample.pmtiles";
const errors = [];
const status = document.querySelector("#status");
const debug = document.querySelector("#debug-output");
const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const scope = params.get("scope") || "spain";
const code = Number(params.get("code"));
const from = Number(params.get("from") || 1985);
const to = Number(params.get("to") || 2021);
const selectedId = params.get("selected_geometry_id");
const views = { spain: {center: [-3.7, 40.3], zoom: 4}, valencian: {center: [-0.5,39.2],zoom:7}, galicia: {center: [-8.1,42.6],zoom:6}, ourense: {center: [-7.7,42.3],zoom:7} };
const view = views[params.get("view")] || views.spain;

function territoryExpression() {
  if (scope === "spain") return ["!=", ["get", "geometry_id"], "__no_geometry__"];
  if (encoding === "strings") {
    const property = scope === "ccaa" ? "ccaa_codes" : "prov_codes";
    // El delimitador evita colisiones 1/10. Sigue siendo una expresión
    // válida, pero duplica strings en MVT y no mejora los slots numéricos.
    return ["in", ["concat", "|", ["to-string", code], "|"], ["get", property]];
  }
  const prefix = scope === "ccaa" ? "ccaa" : "prov";
  return ["any", ...[1, 2, 3].map((slot) => ["==", ["get", `${prefix}_${slot}`], code])];
}
function combinedFilter() {
  return ["all", [">=", ["to-number", ["get", "year"]], from], ["<=", ["to-number", ["get", "year"]], to], territoryExpression()];
}

const map = new maplibregl.Map({
  container: "map", center: view.center, zoom: view.zoom, minZoom: 3, maxZoom: 14,
  style: {version: 8, sources: {esfire30: {type: "vector", url: `pmtiles://${location.origin}${ARCHIVE}`}}, layers: [
    {id: "perimeters", type: "fill", source: "esfire30", "source-layer": "esfire30", paint: {"fill-color": "#b54d2f", "fill-opacity": .45, "fill-outline-color": "#76321f"}},
    {id: "selected", type: "line", source: "esfire30", "source-layer": "esfire30", filter: ["==", ["get", "geometry_id"], "__none__"], paint: {"line-color": "#112f72", "line-width": 3}},
  ]},
});
map.on("error", (event) => errors.push(String(event.error?.message || event.error || "MapLibre error")));

function resourceMetrics() {
  const resources = performance.getEntriesByType("resource").filter((entry) => entry.name.includes(".pmtiles"));
  return {requests: resources.length, transfer_bytes: resources.reduce((sum, entry) => sum + (entry.transferSize || 0), 0), encoded_bytes: resources.reduce((sum, entry) => sum + (entry.encodedBodySize || 0), 0)};
}
async function settle() {
  await new Promise((resolve) => map.once("idle", resolve));
  await new Promise((resolve) => setTimeout(resolve, 120));
}
async function apply() {
  const started = performance.now();
  const filter = combinedFilter();
  map.setFilter("perimeters", filter);
  if (selectedId) map.setFilter("selected", ["all", filter, ["==", ["get", "geometry_id"], selectedId]]);
  await settle();
  const features = map.querySourceFeatures("esfire30", {sourceLayer: "esfire30"});
  const visible = map.queryRenderedFeatures({layers: ["perimeters"]});
  const prefix = scope === "ccaa" ? "ccaa" : "prov";
  const mismatches = scope === "spain" ? 0 : visible.filter((feature) => encoding === "strings" ? !String(feature.properties[scope === "ccaa" ? "ccaa_codes" : "prov_codes"]).includes(`|${code}|`) : ![1, 2, 3].some((slot) => Number(feature.properties[`${prefix}_${slot}`]) === code)).length;
  const selected = selectedId ? features.some((feature) => feature.properties.geometry_id === selectedId) : null;
  let selectedAtNextZoom = null;
  if (selectedId) {
    map.zoomTo(Math.min(map.getZoom() + 1, 14), {duration: 0});
    await settle();
    selectedAtNextZoom = map.querySourceFeatures("esfire30", {sourceLayer: "esfire30"}).some((feature) => feature.properties.geometry_id === selectedId);
  }
  const first = features.find((feature) => feature.properties.geometry_id) || null;
  const result = {encoding, scope, code: Number.isFinite(code) ? code : null, from, to, filter, filter_ms: performance.now() - started, source_features_loaded: features.length, rendered_features: visible.length, territory_filter_mismatches: mismatches, selected_geometry_id: selectedId, selected_geometry_available: selected, selected_geometry_at_next_zoom: selectedAtNextZoom, sample_properties: first ? first.properties : null, resources: resourceMetrics(), heap: performance.memory?.usedJSHeapSize ?? null, errors};
  status.textContent = `Filtro ${scope}; ${visible.length} features renderizadas`;
  debug.textContent = JSON.stringify(result);
  debug.dataset.complete = "true";
}
map.once("load", () => apply().catch((error) => { errors.push(String(error)); debug.textContent = JSON.stringify({errors}); debug.dataset.complete = "true"; }));

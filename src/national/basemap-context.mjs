/** Contexto cartográfico Protomaps aprobado para el producto nacional.
 *
 * Es deliberadamente una capa de orientación, no una fuente de incendios ni
 * la autoridad territorial. BDLJE conserva límites, jerarquía y selección.
 */

export const BASEMAP_SOURCE_ID = "protomaps-context";
export const FONTSTACK = "Noto Sans Regular";
export const BASEMAP_LAYER_IDS = Object.freeze([
  "atlas-context-earth",
  "atlas-context-landcover",
  "atlas-context-natural-landuse",
  "atlas-context-water",
  "atlas-context-rivers",
  "atlas-context-major-road-casing",
  "atlas-context-major-roads",
  "atlas-context-minor-roads",
  "atlas-context-regions",
  "atlas-context-localities",
  "atlas-context-road-labels",
]);

const BDLJE_FILL_OPACITY = Object.freeze({
  "official-ccaa-territories-fill": 0.1,
  "official-province-territories-fill": 0.04,
  "official-municipality-territories-fill": 0.025,
});
const BDLJE_FALLBACK_OPACITY = Object.freeze({
  "official-ccaa-territories-fill": 0.78,
  "official-province-territories-fill": 0.12,
  "official-municipality-territories-fill": 0.08,
});
const localName = ["coalesce", ["get", "name"], ["get", "name:es"], ["get", "name:en"]];

export function atlasContextLayers(source = BASEMAP_SOURCE_ID) {
  return [
    { id: BASEMAP_LAYER_IDS[0], type: "fill", source, "source-layer": "earth", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#f2f0e8" } },
    { id: BASEMAP_LAYER_IDS[1], type: "fill", source, "source-layer": "landcover", paint: {
      "fill-color": ["match", ["get", "kind"], "forest", "#dfe9dc", "scrub", "#e7ebdc", "grassland", "#e9eddf", "urban_area", "#eceae4", "#f2f0e8"],
      "fill-opacity": 0.58,
    } },
    { id: BASEMAP_LAYER_IDS[2], type: "fill", source, "source-layer": "landuse",
      filter: ["match", ["get", "kind"], ["forest", "wood", "nature_reserve", "protected_area", "national_park", "scrub", "grassland"], true, false],
      paint: { "fill-color": "#d9e5d5", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.12, 10, 0.38] } },
    { id: BASEMAP_LAYER_IDS[3], type: "fill", source, "source-layer": "water", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#c9e3eb" } },
    { id: BASEMAP_LAYER_IDS[4], type: "line", source, "source-layer": "water", minzoom: 7,
      filter: ["match", ["get", "kind"], ["river", "canal"], true, false],
      paint: { "line-color": "#9ccbd7", "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.35, 12, 1.2] } },
    { id: BASEMAP_LAYER_IDS[5], type: "line", source, "source-layer": "roads", minzoom: 5,
      filter: ["match", ["get", "kind"], ["highway", "major_road"], true, false],
      paint: { "line-color": "#f7f4ec", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 12, 4.2], "line-opacity": 0.92 } },
    { id: BASEMAP_LAYER_IDS[6], type: "line", source, "source-layer": "roads", minzoom: 5,
      filter: ["match", ["get", "kind"], ["highway", "major_road"], true, false],
      paint: { "line-color": ["match", ["get", "kind"], "highway", "#d3a878", "#c8bda8"], "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.55, 12, 2.15], "line-opacity": 0.9 } },
    { id: BASEMAP_LAYER_IDS[7], type: "line", source, "source-layer": "roads", minzoom: 9,
      filter: ["==", ["get", "kind"], "minor_road"],
      paint: { "line-color": "#d4cfc2", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.35, 12, 1.1], "line-opacity": 0.72 } },
    { id: BASEMAP_LAYER_IDS[8], type: "symbol", source, "source-layer": "places", maxzoom: 8,
      filter: ["==", ["get", "kind"], "region"],
      layout: { "text-field": localName, "text-font": [FONTSTACK], "text-size": ["interpolate", ["linear"], ["zoom"], 3, 10, 7, 14], "text-transform": "uppercase", "text-letter-spacing": 0.08 },
      paint: { "text-color": "#66736d", "text-halo-color": "rgba(247,246,241,0.92)", "text-halo-width": 1.2 } },
    { id: BASEMAP_LAYER_IDS[9], type: "symbol", source, "source-layer": "places", minzoom: 4,
      filter: ["==", ["get", "kind"], "locality"],
      layout: { "symbol-sort-key": ["coalesce", ["get", "sort_key"], ["get", "min_zoom"], 99], "text-field": localName, "text-font": [FONTSTACK], "text-size": ["interpolate", ["linear"], ["zoom"], 4, 10, 8, 12, 12, 14], "text-padding": 4, "text-max-width": 9 },
      paint: { "text-color": "#3f4c48", "text-halo-color": "rgba(247,246,241,0.96)", "text-halo-width": 1.4 } },
    { id: BASEMAP_LAYER_IDS[10], type: "symbol", source, "source-layer": "roads", minzoom: 9,
      filter: ["all", ["match", ["get", "kind"], ["highway", "major_road"], true, false], ["has", "name"]],
      layout: { "symbol-placement": "line", "text-field": localName, "text-font": [FONTSTACK], "text-size": 10.5, "text-max-angle": 35 },
      paint: { "text-color": "#776d5d", "text-halo-color": "rgba(247,246,241,0.95)", "text-halo-width": 1.3 } },
  ];
}

function setBoundaryOpacity(map, values) {
  for (const [layer, opacity] of Object.entries(values)) {
    if (map.getLayer(layer)) map.setPaintProperty(layer, "fill-opacity", opacity);
  }
}

function messageOf(event) {
  return event?.error?.message || String(event?.error || event?.message || "Error de contexto cartográfico");
}

function updatePublicContext(copy) {
  const context = document.querySelector(".map-context span");
  if (context) context.textContent = copy;
}

export function initNationalBasemap(runtime, config = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__) {
  const map = runtime?.map;
  const descriptor = config?.assets?.basemap || {};
  const state = {
    status: "idle",
    source_id: descriptor.source_id || BASEMAP_SOURCE_ID,
    layer_ids: [...BASEMAP_LAYER_IDS],
    errors: [],
    fallback: null,
    archive: null,
    glyphs: descriptor.glyphs?.template || null,
  };
  globalThis.__atlasBasemapContext = state;
  if (!map || descriptor.enabled === false || !descriptor.pmtiles?.path) {
    state.status = "fallback_bdlje_only";
    state.fallback = "not_configured";
    updatePublicContext("Costa y límites administrativos actuales · BDLJE/IGN");
    return state;
  }

  const archive = new URL(String(descriptor.pmtiles.path), new URL(".", location.href)).toString();
  const glyphHint = String(descriptor.glyphs?.template || "");
  state.archive = archive;

  const isOwnError = (event) => {
    if (event?.sourceId) return event.sourceId === state.source_id;
    const message = messageOf(event);
    return message.includes(archive) || message.includes("/data/basemap/protomaps/") || (glyphHint && message.includes(glyphHint.replace("{fontstack}", FONTSTACK).split("{range}")[0]));
  };

  const fallback = (reason) => {
    if (state.status === "fallback_bdlje_only") return;
    state.errors.push(String(reason));
    state.status = "fallback_bdlje_only";
    state.fallback = "bdlje_only";
    for (const layer of [...BASEMAP_LAYER_IDS].reverse()) {
      if (map.getLayer(layer)) map.removeLayer(layer);
    }
    if (map.getSource(state.source_id)) map.removeSource(state.source_id);
    setBoundaryOpacity(map, BDLJE_FALLBACK_OPACITY);
    updatePublicContext("Costa y límites administrativos actuales · BDLJE/IGN");
  };

  map.on("error", (event) => { if (isOwnError(event)) fallback(messageOf(event)); });
  const install = () => {
    if (state.status !== "idle") return;
    state.status = "loading";
    try {
      map.addSource(state.source_id, {
        type: "vector",
        url: `pmtiles://${archive}`,
        attribution: "Protomaps · © OpenStreetMap contributors",
      });
      const before = map.getLayer("official-ccaa-territories-fill") ? "official-ccaa-territories-fill" : map.getLayer("esfire30-perimeters") ? "esfire30-perimeters" : undefined;
      for (const layer of atlasContextLayers(state.source_id)) map.addLayer(layer, before);
      setBoundaryOpacity(map, BDLJE_FILL_OPACITY);
      updatePublicContext("Contexto Protomaps/OSM · límites administrativos BDLJE/IGN");
      state.status = "ready";
      Promise.resolve(runtime.territoryLayerReady).then(() => {
        if (state.status === "ready") setBoundaryOpacity(map, BDLJE_FILL_OPACITY);
      });
    } catch (error) {
      fallback(error);
    }
  };
  if (map.isStyleLoaded()) install(); else map.once("load", install);
  return state;
}

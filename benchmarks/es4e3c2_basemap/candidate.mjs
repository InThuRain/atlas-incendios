/** Estilo mínimo y reversible para la evaluación Protomaps ES-4E3C2.
 *
 * No forma parte del runtime nacional. El harness lo copia a un sitio temporal
 * y lo instala debajo de BDLJE y de todas las geometrías de incendio.
 */

export const BASEMAP_SOURCE_ID = "es4e3c2-protomaps";
export const BASEMAP_ARCHIVE_PATH = "data/basemap/protomaps-spain-z12.pmtiles";
export const GLYPH_TEMPLATE = "data/basemap/fonts/{fontstack}/{range}.pbf";
export const FONTSTACK = "Noto Sans Regular";

const localName = ["coalesce", ["get", "name"], ["get", "name:es"], ["get", "name:en"]];

export function atlasBasemapLayers(source = BASEMAP_SOURCE_ID) {
  return [
    {
      id: "es4e3c2-earth", type: "fill", source, "source-layer": "earth",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "fill-color": "#f2f0e8" },
    },
    {
      id: "es4e3c2-landcover", type: "fill", source, "source-layer": "landcover",
      paint: {
        "fill-color": ["match", ["get", "kind"], "forest", "#dfe9dc", "scrub", "#e7ebdc", "grassland", "#e9eddf", "urban_area", "#eceae4", "#f2f0e8"],
        "fill-opacity": 0.58,
      },
    },
    {
      id: "es4e3c2-natural-landuse", type: "fill", source, "source-layer": "landuse",
      filter: ["match", ["get", "kind"], ["forest", "wood", "nature_reserve", "protected_area", "national_park", "scrub", "grassland"], true, false],
      paint: { "fill-color": "#d9e5d5", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.12, 10, 0.38] },
    },
    {
      id: "es4e3c2-water", type: "fill", source, "source-layer": "water",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "fill-color": "#c9e3eb" },
    },
    {
      id: "es4e3c2-rivers", type: "line", source, "source-layer": "water", minzoom: 7,
      filter: ["match", ["get", "kind"], ["river", "canal"], true, false],
      paint: { "line-color": "#9ccbd7", "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.35, 12, 1.2] },
    },
    {
      id: "es4e3c2-major-road-casing", type: "line", source, "source-layer": "roads", minzoom: 5,
      filter: ["match", ["get", "kind"], ["highway", "major_road"], true, false],
      paint: { "line-color": "#f7f4ec", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 12, 4.2], "line-opacity": 0.92 },
    },
    {
      id: "es4e3c2-major-roads", type: "line", source, "source-layer": "roads", minzoom: 5,
      filter: ["match", ["get", "kind"], ["highway", "major_road"], true, false],
      paint: { "line-color": ["match", ["get", "kind"], "highway", "#d3a878", "#c8bda8"], "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.55, 12, 2.15], "line-opacity": 0.9 },
    },
    {
      id: "es4e3c2-minor-roads", type: "line", source, "source-layer": "roads", minzoom: 9,
      filter: ["==", ["get", "kind"], "minor_road"],
      paint: { "line-color": "#d4cfc2", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.35, 12, 1.1], "line-opacity": 0.72 },
    },
    {
      id: "es4e3c2-regions", type: "symbol", source, "source-layer": "places", maxzoom: 8,
      filter: ["==", ["get", "kind"], "region"],
      layout: { "text-field": localName, "text-font": [FONTSTACK], "text-size": ["interpolate", ["linear"], ["zoom"], 3, 10, 7, 14], "text-transform": "uppercase", "text-letter-spacing": 0.08 },
      paint: { "text-color": "#66736d", "text-halo-color": "rgba(247,246,241,0.92)", "text-halo-width": 1.2 },
    },
    {
      id: "es4e3c2-localities", type: "symbol", source, "source-layer": "places", minzoom: 4,
      filter: ["==", ["get", "kind"], "locality"],
      layout: {
        "symbol-sort-key": ["coalesce", ["get", "sort_key"], ["get", "min_zoom"], 99],
        "text-field": localName, "text-font": [FONTSTACK],
        "text-size": ["interpolate", ["linear"], ["zoom"], 4, 10, 8, 12, 12, 14],
        "text-padding": 4, "text-max-width": 9,
      },
      paint: { "text-color": "#3f4c48", "text-halo-color": "rgba(247,246,241,0.96)", "text-halo-width": 1.4 },
    },
    {
      id: "es4e3c2-road-labels", type: "symbol", source, "source-layer": "roads", minzoom: 9,
      filter: ["all", ["match", ["get", "kind"], ["highway", "major_road"], true, false], ["has", "name"]],
      layout: { "symbol-placement": "line", "text-field": localName, "text-font": [FONTSTACK], "text-size": 10.5, "text-max-angle": 35 },
      paint: { "text-color": "#776d5d", "text-halo-color": "rgba(247,246,241,0.95)", "text-halo-width": 1.3 },
    },
  ];
}

function waitForRuntime() {
  return new Promise((resolve) => {
    const poll = () => globalThis.__es4cRuntime ? resolve(globalThis.__es4cRuntime) : setTimeout(poll, 25);
    poll();
  });
}

export async function installEvaluationBasemap() {
  const runtime = await waitForRuntime();
  const map = runtime.map;
  await runtime.territoryLayerReady;
  const errors = [];
  map.on("error", (event) => {
    const message = event?.error?.message || String(event?.error || "MapLibre error");
    if (message.includes(BASEMAP_SOURCE_ID) || message.includes("glyph") || message.includes("pbf")) errors.push(message);
  });
  const archive = new URL(BASEMAP_ARCHIVE_PATH, new URL(".", location.href)).toString();
  map.addSource(BASEMAP_SOURCE_ID, { type: "vector", url: `pmtiles://${archive}` });
  const before = map.getLayer("official-ccaa-territories-fill") ? "official-ccaa-territories-fill" : "esfire30-perimeters";
  for (const layer of atlasBasemapLayers()) map.addLayer(layer, before);
  // Ajuste únicamente experimental: BDLJE sigue visible/seleccionable, pero su
  // relleno no debe tapar el contexto que se está evaluando.
  if (map.getLayer("official-ccaa-territories-fill")) map.setPaintProperty("official-ccaa-territories-fill", "fill-opacity", 0.1);
  if (map.getLayer("official-province-territories-fill")) map.setPaintProperty("official-province-territories-fill", "fill-opacity", 0.04);
  if (map.getLayer("official-municipality-territories-fill")) map.setPaintProperty("official-municipality-territories-fill", "fill-opacity", 0.025);
  const context = document.querySelector(".map-context span");
  if (context) context.textContent = "Contexto Protomaps/OSM · límites administrativos BDLJE/IGN";
  globalThis.__basemapEvaluation = { status: "installed", source: BASEMAP_SOURCE_ID, archive, errors, layer_ids: atlasBasemapLayers().map((row) => row.id) };
  return globalThis.__basemapEvaluation;
}

if (typeof document !== "undefined") {
  installEvaluationBasemap().catch((error) => {
    globalThis.__basemapEvaluation = { status: "error", errors: [String(error)] };
  });
}

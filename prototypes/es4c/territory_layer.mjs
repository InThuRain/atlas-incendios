/** Capa administrativa oficial exclusiva del prototipo ES-4C2A1.
 *
 * La geometría no se infiere desde ESFire30: se carga desde el derivado BDLJE
 * local. El controlador no filtra ninguna fuente de incendios; solo dibuja,
 * resalta y proporciona bounds administrativos para un ámbito seleccionado.
 */

export const CCAA_TERRITORIES_URL = "/data/derived/spain/es4c2a/ccaa.geojson";
export const CCAA_SOURCE_ID = "official-ccaa-territories";
export const CCAA_FILL_LAYER = "official-ccaa-territories-fill";
export const CCAA_LINE_LAYER = "official-ccaa-territories-line";
export const CCAA_SELECTED_LAYER = "official-ccaa-territories-selected";

function validBounds(bounds) {
  return Array.isArray(bounds) && bounds.length === 4 && bounds.every((value) => typeof value === "number" && Number.isFinite(value))
    && bounds[0] < bounds[2] && bounds[1] < bounds[3];
}

export function boundsForFeature(feature) {
  const bounds = feature && feature.properties ? feature.properties.bounds : null;
  return validBounds(bounds) ? [[bounds[0], bounds[1]], [bounds[2], bounds[3]]] : null;
}

export async function addOfficialTerritoryLayer(map, { fetchImpl = globalThis.fetch.bind(globalThis), onSelect = () => {}, url = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__?.assets?.territories?.ccaa?.path || CCAA_TERRITORIES_URL } = {}) {
  const response = await fetchImpl(url);
  if (!response.ok) throw new Error(`Límites BDLJE no disponibles (${response.status})`);
  const collection = await response.json();
  const features = collection.features || [];
  const byId = new Map(features.map((feature) => [feature.properties ? feature.properties.territory_id : null, feature]));
  if (byId.size !== 19) throw new Error(`Derivado BDLJE inválido: ${byId.size} territorios lógicos`);
  map.addSource(CCAA_SOURCE_ID, { type: "geojson", data: collection });
  map.addLayer({
    id: CCAA_FILL_LAYER,
    type: "fill",
    source: CCAA_SOURCE_ID,
    paint: { "fill-color": "#32735d", "fill-opacity": 0.035 },
  });
  map.addLayer({
    id: CCAA_LINE_LAYER,
    type: "line",
    source: CCAA_SOURCE_ID,
    paint: { "line-color": "#366052", "line-width": 1.15, "line-opacity": 0.78 },
  });
  map.addLayer({
    id: CCAA_SELECTED_LAYER,
    type: "line",
    source: CCAA_SOURCE_ID,
    filter: ["==", ["get", "territory_id"], "__none__"],
    paint: { "line-color": "#075e8e", "line-width": 3.4, "line-opacity": 1 },
  });
  map.on("mouseenter", CCAA_FILL_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
  map.on("mouseleave", CCAA_FILL_LAYER, () => { map.getCanvas().style.cursor = ""; });
  const selectFromFeature = (feature) => {
    const territoryId = feature && feature.properties ? feature.properties.territory_id : null;
    return territoryId ? onSelect(String(territoryId)) : null;
  };
  map.on("click", CCAA_FILL_LAYER, (event) => { selectFromFeature(event.features && event.features[0]); });
  const nationalBounds = boundsForFeature({ properties: { bounds: collection.metadata ? collection.metadata.national_bounds : null } });
  return {
    collection,
    byId,
    nationalBounds,
    setSelected(territoryId) {
      map.setFilter(CCAA_SELECTED_LAYER, territoryId
        ? ["==", ["get", "territory_id"], territoryId]
        : ["==", ["get", "territory_id"], "__none__"]);
    },
    selectFromFeature,
    fit(territoryId, options = {}) {
      const feature = territoryId ? byId.get(territoryId) : null;
      const bounds = feature ? boundsForFeature(feature) : nationalBounds;
      if (!bounds) return false;
      map.fitBounds(bounds, { padding: 48, maxZoom: territoryId ? 8 : 5.2, duration: 0, ...options });
      return true;
    },
  };
}

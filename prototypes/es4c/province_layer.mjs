/** Límites provinciales BDLJE, exclusivos del laboratorio ES-4C2A2.
 *
 * Esta capa solo representa territorio administrativo oficial. No calcula ni
 * consume relaciones ESFire30 → territorio, y sus bounds nunca proceden de
 * incendios. Ceuta y Melilla no se incluyen: son ciudades autónomas ES-2 y
 * no tienen un nivel provincial canónico inferior.
 */

export const PROVINCES_URL = "/data/derived/spain/es4c2a/provinces.geojson";
export const PROVINCE_SOURCE_ID = "official-province-territories";
export const PROVINCE_FILL_LAYER = "official-province-territories-fill";
export const PROVINCE_LINE_LAYER = "official-province-territories-line";
export const PROVINCE_SELECTED_LAYER = "official-province-territories-selected";

function boundsForFeature(feature) {
  const bounds = feature && feature.properties ? feature.properties.bounds : null;
  if (!Array.isArray(bounds) || bounds.length !== 4 || !bounds.every((value) => Number.isFinite(value))) return null;
  return [[bounds[0], bounds[1]], [bounds[2], bounds[3]]];
}

export async function addOfficialProvinceLayer(map, { fetchImpl = globalThis.fetch.bind(globalThis), onSelect = () => {}, url = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__?.assets?.territories?.provinces?.path || PROVINCES_URL } = {}) {
  const response = await fetchImpl(url);
  if (!response.ok) throw new Error(`Límites provinciales BDLJE no disponibles (${response.status})`);
  const collection = await response.json();
  const features = collection.features || [];
  const byId = new Map(features.map((feature) => [feature.properties ? feature.properties.territory_id : null, feature]));
  if (byId.size !== 50) throw new Error(`Derivado BDLJE provincial inválido: ${byId.size} provincias lógicas`);
  map.addSource(PROVINCE_SOURCE_ID, { type: "geojson", data: collection });
  const fireLayer = map.getLayer("esfire30-perimeters") ? "esfire30-perimeters" : undefined;
  map.addLayer({ id: PROVINCE_FILL_LAYER, type: "fill", source: PROVINCE_SOURCE_ID,
    filter: ["==", ["get", "parent_id"], "__none__"], paint: { "fill-color": "#e8e1cd", "fill-opacity": .12 } }, fireLayer);
  map.addLayer({ id: PROVINCE_LINE_LAYER, type: "line", source: PROVINCE_SOURCE_ID,
    filter: ["==", ["get", "parent_id"], "__none__"], paint: { "line-color": "#87775b", "line-width": ["interpolate", ["linear"], ["zoom"], 5, .55, 10, 1.1], "line-opacity": .65 } }, fireLayer);
  map.addLayer({ id: PROVINCE_SELECTED_LAYER, type: "line", source: PROVINCE_SOURCE_ID,
    filter: ["==", ["get", "territory_id"], "__none__"], paint: { "line-color": "#d15318", "line-width": 3.6, "line-opacity": 1 } });
  map.on("mouseenter", PROVINCE_FILL_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
  map.on("mouseleave", PROVINCE_FILL_LAYER, () => { map.getCanvas().style.cursor = ""; });
  const selectFromFeature = (feature) => {
    const properties = feature && feature.properties ? feature.properties : {};
    return properties.territory_id && properties.parent_id ? onSelect(String(properties.territory_id), String(properties.parent_id)) : null;
  };
  map.on("click", PROVINCE_FILL_LAYER, (event) => selectFromFeature(event.features && event.features[0]));
  return {
    byId,
    setScope(communityId, provinceId = null) {
      const visible = communityId ? ["==", ["get", "parent_id"], communityId] : ["==", ["get", "parent_id"], "__none__"];
      map.setFilter(PROVINCE_FILL_LAYER, visible);
      map.setFilter(PROVINCE_LINE_LAYER, visible);
      map.setFilter(PROVINCE_SELECTED_LAYER, provinceId ? ["==", ["get", "territory_id"], provinceId] : ["==", ["get", "territory_id"], "__none__"]);
    },
    selectFromFeature,
    fit(provinceId, options = {}) {
      const bounds = boundsForFeature(byId.get(provinceId));
      if (!bounds) return false;
      map.fitBounds(bounds, { padding: 48, maxZoom: 9, duration: 0, ...options });
      return true;
    },
  };
}

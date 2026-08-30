/** Capa GeoJSON 0 m de municipios BDLJE actuales, aislada de ESFire30. */
export const MUNICIPALITY_SOURCE_ID = "official-municipality-territories";
export const MUNICIPALITY_FILL_LAYER = "official-municipality-territories-fill";
export const MUNICIPALITY_LINE_LAYER = "official-municipality-territories-line";
export const MUNICIPALITY_SELECTED_LAYER = "official-municipality-territories-selected";
const EMPTY = { type: "FeatureCollection", features: [] };

export function addOfficialMunicipalityLayer(map, { onSelect = () => {} } = {}) {
  let byId = new Map();
  map.addSource(MUNICIPALITY_SOURCE_ID, { type: "geojson", data: EMPTY });
  map.addLayer({ id: MUNICIPALITY_FILL_LAYER, type: "fill", source: MUNICIPALITY_SOURCE_ID, paint: { "fill-color": "#58a6a6", "fill-opacity": 0.025 } });
  map.addLayer({ id: MUNICIPALITY_LINE_LAYER, type: "line", source: MUNICIPALITY_SOURCE_ID, paint: { "line-color": "#167276", "line-width": 1, "line-opacity": 0.9 } });
  map.addLayer({ id: MUNICIPALITY_SELECTED_LAYER, type: "line", source: MUNICIPALITY_SOURCE_ID, filter: ["==", ["get", "municipality_id"], "__none__"], paint: { "line-color": "#004d61", "line-width": 3.5, "line-opacity": 1 } });
  map.on("mouseenter", MUNICIPALITY_FILL_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
  map.on("mouseleave", MUNICIPALITY_FILL_LAYER, () => { map.getCanvas().style.cursor = ""; });
  map.on("click", MUNICIPALITY_FILL_LAYER, (event) => { const id = event.features?.[0]?.properties?.municipality_id; if (id) onSelect(String(id)); });
  return {
    setCollection(collection) {
      const effective = collection || EMPTY;
      byId = new Map((effective.features || []).map((feature) => [feature.properties?.municipality_id, feature]));
      map.getSource(MUNICIPALITY_SOURCE_ID).setData(effective);
    },
    setSelected(municipalityId) { map.setFilter(MUNICIPALITY_SELECTED_LAYER, municipalityId ? ["==", ["get", "municipality_id"], municipalityId] : ["==", ["get", "municipality_id"], "__none__"]); },
    clear() { this.setCollection(EMPTY); this.setSelected(null); },
    getFeature(municipalityId) { return byId.get(municipalityId) || null; },
    selectFromFeature(feature) {
      const id = feature?.properties?.municipality_id;
      return id ? onSelect(String(id)) : null;
    },
    fit(bounds, options = {}) { if (!Array.isArray(bounds) || bounds.length !== 4) return false; map.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]], { padding: 48, maxZoom: 12, duration: 0, ...options }); return true; },
  };
}

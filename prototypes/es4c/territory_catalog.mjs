// Derivado mínimo del snapshot oficial ES-2
// data/territories/spain/territories-2026-01-01.json. Solo se incluyen los
// ámbitos seleccionables de este prototipo, no provincias ni municipios.
export const TERRITORY_OPTIONS = [
  ["ES:CCAA:01", "Andalucía"], ["ES:CCAA:02", "Aragón"],
  ["ES:CCAA:03", "Asturias, Principado de"], ["ES:CCAA:04", "Balears, Illes"],
  ["ES:CCAA:05", "Canarias"], ["ES:CCAA:06", "Cantabria"],
  ["ES:CCAA:07", "Castilla y León"], ["ES:CCAA:08", "Castilla-La Mancha"],
  ["ES:CCAA:09", "Cataluña"], ["ES:CCAA:10", "Comunitat Valenciana"],
  ["ES:CCAA:11", "Extremadura"], ["ES:CCAA:12", "Galicia"],
  ["ES:CCAA:13", "Madrid, Comunidad de"], ["ES:CCAA:14", "Murcia, Región de"],
  ["ES:CCAA:15", "Navarra, Comunidad Foral de"], ["ES:CCAA:16", "País Vasco"],
  ["ES:CCAA:17", "Rioja, La"], ["ES:CCAA:18", "Ceuta (ciudad autónoma)"],
  ["ES:CCAA:19", "Melilla (ciudad autónoma)"],
].map(([territory_id, label]) => ({ territory_id, label }));

// La ficha pide el nombre canónico solamente tras una selección. Se lee el
// snapshot ES-2 bajo demanda y nunca forma parte de INITIAL EGIF.
const TERRITORY_SNAPSHOT_URL = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__?.assets?.territories?.catalog?.path
  || "/data/territories/spain/territories-2026-01-01.json";
let territoryLookupPromise = null;

export async function loadTerritoryLookup(fetchImpl = globalThis.fetch.bind(globalThis)) {
  if (!territoryLookupPromise) {
    territoryLookupPromise = fetchImpl(TERRITORY_SNAPSHOT_URL).then(async (response) => {
      if (!response.ok) throw new Error(`Catálogo territorial no disponible (${response.status})`);
      const snapshot = await response.json();
      const lookup = new Map();
      for (const territory of snapshot.territories || []) lookup.set(territory.territory_id, territory);
      return lookup;
    });
  }
  return territoryLookupPromise;
}

export async function canonicalTerritoryName(territoryId, fetchImpl) {
  if (!territoryId) return null;
  const lookup = await loadTerritoryLookup(fetchImpl);
  return lookup.get(territoryId)?.official_name || null;
}

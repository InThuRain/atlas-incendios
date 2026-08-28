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

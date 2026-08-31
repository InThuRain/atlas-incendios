/** Registro pequeño y extensible de las fuentes presentes en D2. */

export const NATIONAL_SOURCE_REGISTRY = Object.freeze({
  egif: {
    id: "egif", label: "EGIF / MITECO", coverage: { from: 1968, to: 2023 },
    entity_label: "partes administrativos", geometry_semantics: "sin geometría individual fiable",
    attribution: "Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico.",
    runtime_module: "sources/egif", default_visible: true,
  },
  esfire30: {
    id: "esfire30", label: "ESFire30", coverage: { from: 1985, to: 2021 },
    entity_label: "perímetros derivados de teledetección Landsat",
    geometry_semantics: "perímetros que intersectan el territorio seleccionado",
    attribution: "ESFire30 Causes, Ochoa, Chuvieco, Rodrigues y Franquesa (2026), versión v1, CC BY 4.0, DOI 10.5281/zenodo.18449006.",
    runtime_module: "sources/esfire30", default_visible: true,
  },
  bdlje: {
    id: "bdlje", label: "BDLJE / IGN-CNIG", coverage: null,
    entity_label: "límites administrativos actuales", geometry_semantics: "división administrativa actual",
    attribution: "Obra derivada de BDLJE CC-BY 4.0 ign.es.", runtime_module: "territories", default_visible: true,
  },
});

export function sourceFor(id) {
  const source = NATIONAL_SOURCE_REGISTRY[id];
  if (!source) throw new Error(`Fuente nacional desconocida: ${id}`);
  return source;
}

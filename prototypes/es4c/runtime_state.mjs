/** Estado y cobertura explícitos del prototipo nacional ES-4C.
 *
 * No serializa permalinks ni conoce datos: coordina fuentes con semánticas
 * distintas sin convertir ausencia de cobertura en cero registros.
 */

export const SOURCE_COVERAGE = {
  egif: { from: 1968, to: 2023, label: "EGIF · 1968–2023", entity_label: "partes administrativos" },
  esfire30: { from: 1985, to: 2021, label: "ESFire30 · 1985–2021", entity_label: "perímetros Landsat" },
};

export function intersectCoverage(range, coverage) {
  const from = Math.max(range.from, coverage.from);
  const to = Math.min(range.to, coverage.to);
  return from <= to ? { from, to } : null;
}

export function normalizeRange(from, to) {
  const numericFrom = Number(from);
  const numericTo = Number(to);
  if (!Number.isInteger(numericFrom) || !Number.isInteger(numericTo)) throw new Error("Periodo inválido");
  return numericFrom <= numericTo ? { from: numericFrom, to: numericTo } : { from: numericTo, to: numericFrom };
}

export function effectiveCoverage(state, sourceId) {
  const coverage = SOURCE_COVERAGE[sourceId];
  if (!coverage) throw new Error(`Fuente desconocida: ${sourceId}`);
  return state[`${sourceId}_visible`] ? intersectCoverage(state, coverage) : null;
}

export function createRuntimeState(overrides = {}) {
  return {
    from: 1985,
    to: 2021,
    territory_scope: "ES",
    autonomous_community_id: null,
    esfire30_visible: true,
    egif_visible: true,
    selected_geometry_id: null,
    selected_geometry_year: null,
    selected_egif_record_id: null,
    selected_egif_year: null,
    ...overrides,
  };
}

function geometryStillVisible(state) {
  if (!state.selected_geometry_id) return true;
  const range = effectiveCoverage(state, "esfire30");
  return Boolean(range && state.selected_geometry_year >= range.from && state.selected_geometry_year <= range.to);
}

function recordStillVisible(state) {
  if (!state.selected_egif_record_id) return true;
  const range = effectiveCoverage(state, "egif");
  return Boolean(range && state.selected_egif_year >= range.from && state.selected_egif_year <= range.to);
}

export function reduceRuntimeState(state, event) {
  let next = { ...state };
  if (event.type === "set_range") Object.assign(next, normalizeRange(event.from, event.to));
  else if (event.type === "set_scope") {
    next.territory_scope = event.territory_id === "ES" ? "ES" : "autonomous_community";
    next.autonomous_community_id = event.territory_id === "ES" ? null : event.territory_id;
  } else if (event.type === "set_visibility") next[`${event.source_id}_visible`] = Boolean(event.visible);
  else if (event.type === "select_geometry") Object.assign(next, { selected_geometry_id: event.geometry_id, selected_geometry_year: event.year });
  else if (event.type === "select_egif_record") Object.assign(next, { selected_egif_record_id: event.record_id, selected_egif_year: event.year });
  else if (event.type === "clear_egif_selection") Object.assign(next, { selected_egif_record_id: null, selected_egif_year: null });
  else if (event.type === "clear_geometry_selection") Object.assign(next, { selected_geometry_id: null, selected_geometry_year: null });
  else throw new Error(`Evento de estado desconocido: ${event.type}`);

  if (!geometryStillVisible(next)) Object.assign(next, { selected_geometry_id: null, selected_geometry_year: null });
  if (!recordStillVisible(next)) Object.assign(next, { selected_egif_record_id: null, selected_egif_year: null });
  if (event.type === "set_scope" && state.autonomous_community_id !== next.autonomous_community_id) {
    Object.assign(next, { selected_egif_record_id: null, selected_egif_year: null });
  }
  return next;
}

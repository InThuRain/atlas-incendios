/** Contratos source-aware de filtros humanos ES-4E3C1.
 *
 * Cada filtro conserva fuente, métrica, tipo, valor y unidad. Este módulo no
 * relaciona fuentes ni convierte ausencia de magnitud en cero.
 */

export const ICV_CAUSES = Object.freeze([
  { value: "lightning", label: "Rayo" },
  { value: "intentional", label: "Intencionado" },
  { value: "negligence", label: "Negligencia" },
  { value: "negligence_and_accidental", label: "Negligencias y causas accidentales" },
  { value: "rekindle", label: "Incendio reproducido" },
  { value: "other", label: "Otras causas" },
  { value: "under_investigation", label: "En investigación" },
  { value: "unknown", label: "Desconocida" },
]);

export const FILTER_CONTRACTS = Object.freeze([
  { filter_id: "egif_min_area", filter_type: "min_value", source: "egif", metric_id: "egif_declared_forest_area_ha", unit: "ha", label: "Superficie forestal declarada · EGIF" },
  { filter_id: "egif_gif", filter_type: "flag", source: "egif", metric_id: "egif_administrative_gif_count", unit: null, label: "Grandes incendios forestales (GIF) · EGIF" },
  { filter_id: "icv_min_area", filter_type: "min_value", source: "icv", metric_id: "icv_declared_forest_area_ha", unit: "ha", label: "Superficie forestal declarada · ICV" },
  { filter_id: "icv_gif", filter_type: "flag", source: "icv", metric_id: "icv_gif_count", unit: null, label: "Grandes incendios forestales (GIF) · ICV" },
  { filter_id: "icv_cause", filter_type: "enum", source: "icv", metric_id: "icv_cause_distribution", unit: null, label: "Causa documentada · ICV", values: ICV_CAUSES },
  { filter_id: "effis_min_area", filter_type: "min_value", source: "effis", metric_id: "effis_mapped_area_ha", unit: "ha", label: "Área del perímetro satelital · EFFIS" },
]);

const BY_ID = new Map(FILTER_CONTRACTS.map((row) => [row.filter_id, row]));
const CAUSE_CODES = new Set(ICV_CAUSES.map((row) => row.value));
const COVERAGE = Object.freeze({ egif: [1968, 2023], icv: [1993, 2024], effis: [2025, 2026] });

export function normalizeFilter(value) {
  if (!value || typeof value !== "object") return null;
  const contract = BY_ID.get(value.filter_id);
  if (!contract || value.filter_type !== contract.filter_type || value.source !== contract.source || value.metric_id !== contract.metric_id) return null;
  if (contract.filter_type === "min_value") {
    const number = Number(value.value);
    if (!Number.isFinite(number) || number <= 0 || number > 1000000) return null;
    return { filter_id: contract.filter_id, filter_type: contract.filter_type, source: contract.source, metric_id: contract.metric_id, value: number, unit: contract.unit };
  }
  if (contract.filter_type === "flag") {
    if (value.value !== true) return null;
    return { filter_id: contract.filter_id, filter_type: contract.filter_type, source: contract.source, metric_id: contract.metric_id, value: true, unit: null };
  }
  if (contract.filter_type === "enum") {
    if (typeof value.value !== "string" || !CAUSE_CODES.has(value.value)) return null;
    return { filter_id: contract.filter_id, filter_type: contract.filter_type, source: contract.source, metric_id: contract.metric_id, value: value.value, unit: null };
  }
  return null;
}

export function canonicalFilters(values = []) {
  const byId = new Map();
  for (const value of Array.isArray(values) ? values : []) {
    const normalized = normalizeFilter(value);
    if (normalized) byId.set(normalized.filter_id, normalized);
  }
  return [...byId.values()].sort((left, right) => left.filter_id.localeCompare(right.filter_id));
}

export function upsertFilter(values, value) {
  const normalized = normalizeFilter(value);
  if (!normalized) return canonicalFilters(values);
  return canonicalFilters([...(values || []).filter((row) => row.filter_id !== normalized.filter_id), normalized]);
}

export function removeFilter(values, filterId) {
  return canonicalFilters((values || []).filter((row) => row.filter_id !== filterId));
}

export function filtersForSource(values, source) {
  return canonicalFilters(values).filter((row) => row.source === source);
}

export function filterApplicable(state, filterOrContract) {
  const source = filterOrContract && filterOrContract.source;
  const coverage = COVERAGE[source];
  if (!coverage || state[`${source}_visible`] === false) return false;
  if (Math.max(Number(state.from), coverage[0]) > Math.min(Number(state.to), coverage[1])) return false;
  if ((source === "icv" || source === "effis") && state.autonomous_community_id !== "ES:CCAA:10") return false;
  return true;
}

export function applicableFilterContracts(state) {
  return FILTER_CONTRACTS.filter((row) => filterApplicable(state, row));
}

export function retainApplicableFilters(state) {
  return canonicalFilters(state.filters).filter((row) => filterApplicable(state, row));
}

export function documentedIcvGif(record) {
  const area = record && record.reported_forest_area_ha;
  return typeof area === "number" && Number.isFinite(area) ? area >= 500 : null;
}

export function recordMatchesSourceFilters(source, record, filters) {
  for (const filter of filtersForSource(filters, source)) {
    if (filter.filter_id === "egif_min_area" || filter.filter_id === "icv_min_area") {
      const area = record && record.reported_forest_area_ha;
      if (typeof area !== "number" || !Number.isFinite(area) || area < filter.value) return false;
    } else if (filter.filter_id === "effis_min_area") {
      const area = record && record.mapped_area_ha;
      if (typeof area !== "number" || !Number.isFinite(area) || area < filter.value) return false;
    } else if (filter.filter_id === "egif_gif") {
      if (record && record.is_gif_forest_ge_500_ha !== true) return false;
    } else if (filter.filter_id === "icv_gif") {
      if (documentedIcvGif(record) !== true) return false;
    } else if (filter.filter_id === "icv_cause" && (!record || record.cause_code !== filter.value)) return false;
  }
  return true;
}

export function filterStateKey(filters = []) {
  return JSON.stringify(canonicalFilters(filters));
}

/** Compatibilidad de entrada con el permalink público valenciano `#v=1`.
 *
 * Este módulo reproduce el contrato de `js/url-state.js` sin importar la UI
 * Leaflet. Sólo analiza/adapta estado; la aplicación nacional conserva su
 * propio serializer `es4c-state-v1` como formato de salida.
 */

export const GVA_V1 = "1";
export const GVA_V1_PROVINCES = Object.freeze({
  all: null,
  alicante: "ES:PROV:03",
  castellon: "ES:PROV:12",
  valencia: "ES:PROV:46",
});
export const GVA_V1_SOURCES = Object.freeze(["egif", "esfire30", "icv", "sigif", "effis"]);
const ICV_CAUSE_CODES = new Set(["lightning", "intentional", "negligence", "negligence_and_accidental", "rekindle", "other", "under_investigation", "unknown"]);

function finiteNumber(value) {
  if (value === null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function boundedInteger(value, minimum, maximum) {
  const number = finiteNumber(value);
  if (number === null) return null;
  const integer = Math.round(number);
  return integer >= minimum && integer <= maximum ? integer : null;
}

function boundedString(value) {
  return value && value.length <= 180 ? value : null;
}

/** Devuelve el estado legacy normalizado, sin aplicar defaults nacionales. */
export function parseLegacyGvaV1State(hash, { years = { min: 1968, max: 2026 } } = {}) {
  const source = String(hash || "").replace(/^#/, "");
  if (!source) return { status: "absent", state: null };
  const params = new URLSearchParams(source);
  if (params.get("v") !== GVA_V1) return { status: params.has("v") ? "unknown_version" : "invalid", state: null };
  const state = { version: 1 };
  const lat = finiteNumber(params.get("lat"));
  const lng = finiteNumber(params.get("lng"));
  const zoom = boundedInteger(params.get("z"), 2, 19);
  if (lat !== null && lng !== null && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) state.center = { lat, lng };
  if (zoom !== null) state.zoom = zoom;
  const from = boundedInteger(params.get("from"), years.min, years.max);
  const to = boundedInteger(params.get("to"), years.min, years.max);
  if (from !== null && to !== null) { state.from = Math.min(from, to); state.to = Math.max(from, to); }
  if (params.has("src")) {
    const raw = params.get("src");
    const requested = raw.split(",").filter((id) => GVA_V1_SOURCES.includes(id));
    if (requested.length || raw === "") state.sources = requested;
  }
  if (Object.prototype.hasOwnProperty.call(GVA_V1_PROVINCES, params.get("province"))) state.province = params.get("province");
  for (const key of ["municipality", "cause", "entity", "geometry"]) {
    const value = boundedString(params.get(key));
    if (value) state[key] = value;
  }
  const minimumArea = finiteNumber(params.get("min_area"));
  if (minimumArea !== null && minimumArea >= 0) state.minimumArea = minimumArea;
  if (params.get("gif") === "1" || params.get("gif") === "0") state.gifOnly = params.get("gif") === "1";
  return { status: "complete", state };
}

function selectionPatch(legacy) {
  const geometry = legacy.geometry;
  const entity = legacy.entity;
  if (/^gva:geometry:/.test(geometry || "")) return { selected_icv_geometry_id: geometry, selected_icv_record_id: /^gva:pif-cv:/.test(entity || "") ? entity : null };
  if (/^effis:rda:/.test(geometry || "")) return { selected_effis_geometry_id: geometry };
  if (/^effis:rda:/.test(entity || "")) return { selected_effis_geometry_id: entity };
  if (/^egif-record:\d+$/.test(entity || "")) return { selected_egif_record_id: entity };
  // Un source record ICV sin geometría se conserva como identidad de parte;
  // no se elige arbitrariamente una geometría, incluido 2024AL0005 (1:N).
  if (/^gva:pif-cv:/.test(entity || "")) return { selected_icv_record_id: entity };
  return {};
}

function exactLegacyFilters(legacy) {
  const filters = [];
  const sources = Array.isArray(legacy.sources) ? legacy.sources : [];
  const onlySource = sources.length === 1 ? sources[0] : null;
  const minimum = Number(legacy.minimumArea);
  if (Number.isFinite(minimum) && minimum > 0) {
    if (onlySource === "egif") filters.push({ filter_id: "egif_min_area", filter_type: "min_value", source: "egif", metric_id: "egif_declared_forest_area_ha", value: minimum, unit: "ha" });
    if (onlySource === "icv") filters.push({ filter_id: "icv_min_area", filter_type: "min_value", source: "icv", metric_id: "icv_declared_forest_area_ha", value: minimum, unit: "ha" });
    if (onlySource === "effis") filters.push({ filter_id: "effis_min_area", filter_type: "min_value", source: "effis", metric_id: "effis_mapped_area_ha", value: minimum, unit: "ha" });
  }
  if (legacy.gifOnly === true && onlySource === "egif") filters.push({ filter_id: "egif_gif", filter_type: "flag", source: "egif", metric_id: "egif_administrative_gif_count", value: true, unit: null });
  if (legacy.gifOnly === true && onlySource === "icv") filters.push({ filter_id: "icv_gif", filter_type: "flag", source: "icv", metric_id: "icv_gif_count", value: true, unit: null });
  if (legacy.cause && onlySource === "icv" && ICV_CAUSE_CODES.has(legacy.cause)) filters.push({ filter_id: "icv_cause", filter_type: "enum", source: "icv", metric_id: "icv_cause_distribution", value: legacy.cause, unit: null });
  return filters.sort((left, right) => left.filter_id.localeCompare(right.filter_id));
}

/** Adapta estado legacy a invariantes nacionales sin inferencias espaciales. */
export function adaptLegacyGvaV1State(legacy, defaults, {
  territoryIds = new Set(), provinceParents = new Map(), municipalityParents = new Map(),
} = {}) {
  if (!legacy || legacy.version !== 1) return { status: "invalid", state: { ...defaults }, mapping: {} };
  const state = { ...defaults, center: [...defaults.center] };
  const gvaId = "ES:CCAA:10";
  // El visor origen es valenciano incluso en su estado por defecto.
  if (territoryIds.has(gvaId)) Object.assign(state, { territory_scope: "autonomous_community", autonomous_community_id: gvaId, province_id: null, municipality_id: null });
  if (Number.isInteger(legacy.from) && Number.isInteger(legacy.to)) Object.assign(state, { from: legacy.from, to: legacy.to });
  if (legacy.center) state.center = [legacy.center.lng, legacy.center.lat];
  if (Number.isInteger(legacy.zoom)) state.zoom = legacy.zoom;

  const provinceId = GVA_V1_PROVINCES[legacy.province];
  if (provinceId && provinceParents.get(provinceId) === gvaId) Object.assign(state, { territory_scope: "province", autonomous_community_id: gvaId, province_id: provinceId, municipality_id: null });
  const municipalityId = /^\d{5}$/.test(legacy.municipality || "") ? `ES:MUN:${legacy.municipality}` : null;
  const municipalityParent = municipalityId ? municipalityParents.get(municipalityId) : null;
  if (municipalityParent && municipalityParent.autonomous_community_id === gvaId
    && (!provinceId || municipalityParent.province_id === provinceId)) {
    Object.assign(state, { territory_scope: "municipality", autonomous_community_id: gvaId, province_id: municipalityParent.province_id || null, municipality_id: municipalityId });
  }

  if (legacy.sources) {
    // `src` no conocía las fuentes nacionales posteriores: EGIF y ESFire30
    // quedan en los defaults nacionales. SIGIF no tiene equivalente nacional.
    state.icv_visible = legacy.sources.includes("icv");
    state.effis_visible = legacy.sources.includes("effis");
  }
  state.filters = exactLegacyFilters(legacy);
  Object.assign(state, selectionPatch(legacy));
  const mappedFilterIds = new Set(state.filters.map((row) => row.filter_id));
  const filterMapping = {
    minimumArea: legacy.minimumArea === undefined || Number(legacy.minimumArea) === 0 ? "NO_OP_EXACT"
      : mappedFilterIds.has("egif_min_area") || mappedFilterIds.has("icv_min_area") || mappedFilterIds.has("effis_min_area") ? "MAPPED_EXACTLY" : "IGNORED_SAFE",
    gifOnly: legacy.gifOnly !== true ? "NO_OP_EXACT" : mappedFilterIds.has("egif_gif") || mappedFilterIds.has("icv_gif") ? "MAPPED_EXACTLY" : "IGNORED_SAFE",
    cause: legacy.cause === undefined ? "ABSENT" : mappedFilterIds.has("icv_cause") ? "MAPPED_EXACTLY" : "IGNORED_SAFE",
  };
  return {
    status: "complete",
    state,
    mapping: {
      sources: legacy.sources ? { icv: legacy.sources.includes("icv"), effis: legacy.sources.includes("effis"), sigif: legacy.sources.includes("sigif") ? "ignored_safe" : null } : "national_defaults",
      filters: filterMapping,
      ignored: Object.entries(filterMapping).filter(([, value]) => value === "IGNORED_SAFE").map(([key]) => key),
      selection: state.selected_icv_geometry_id ? "icv_geometry_direct" : state.selected_icv_record_id ? "icv_record_preserved" : state.selected_effis_geometry_id ? "effis_geometry_direct" : state.selected_egif_record_id ? "egif_record_direct" : null,
    },
  };
}

export function dispatchStateHash(hash) {
  const text = String(hash || "");
  if (!text) return "absent";
  if (text.startsWith("#es4c-state-v1=")) return "national_v1";
  // Sólo el parámetro exacto v=1 pertenece al contrato legacy. Una versión
  // futura o ajena se clasifica aparte para que #v=10 nunca use reglas v1.
  const params = new URLSearchParams(text.replace(/^#/, ""));
  if (params.has("v")) return params.get("v") === GVA_V1 ? "gva_v1" : "legacy_unknown_version";
  return "unknown";
}

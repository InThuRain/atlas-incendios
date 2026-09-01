/** Hash versionado, exclusivo del prototipo ES-4C. */

export const STATE_VERSION = "es4c-state-v1";
const HASH_PREFIX = `#${STATE_VERSION}=`;

function rounded(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function base64UrlEncode(text) {
  if (typeof btoa === "function") return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  return Buffer.from(text, "utf8").toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlDecode(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4);
  if (typeof atob === "function") return atob(padded);
  return Buffer.from(padded, "base64").toString("utf8");
}

function validId(value, expression) {
  return typeof value === "string" && expression.test(value) ? value : null;
}

function validCoordinate(value, minimum, maximum, fallback) {
  return typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= maximum ? value : fallback;
}

export function canonicalPayload(state) {
  const [lon, lat] = Array.isArray(state.center) ? state.center : [null, null];
  return {
    v: STATE_VERSION,
    map: { lat: rounded(validCoordinate(lat, -90, 90, 40.3), 5), lon: rounded(validCoordinate(lon, -180, 180, -3.7), 5), z: rounded(validCoordinate(state.zoom, 3, 14, 4), 2) },
    time: { from: state.from, to: state.to },
    territory: {
      scope: state.territory_scope,
      autonomous_community_id: state.autonomous_community_id || null,
      // Campo aditivo v1: los enlaces C1C2 sin él siguen siendo válidos.
      province_id: state.province_id || null,
      municipality_id: state.municipality_id || null,
    },
    sources: { esfire30: Boolean(state.esfire30_visible), egif: Boolean(state.egif_visible), icv: Boolean(state.icv_visible), effis: Boolean(state.effis_visible) },
    selections: { geometry_id: state.selected_geometry_id || null, egif_record_id: state.selected_egif_record_id || null, icv_geometry_id: state.selected_icv_geometry_id || null, icv_record_id: state.selected_icv_record_id || null, effis_geometry_id: state.selected_effis_geometry_id || null },
  };
}

export function serializeState(state) {
  return `${HASH_PREFIX}${base64UrlEncode(JSON.stringify(canonicalPayload(state)))}`;
}

export function parseStateHash(hash, defaults, territoryIds, provinceParents = new Map(), municipalityParents = null) {
  if (!hash || !hash.startsWith("#es4c-state-")) return { status: "absent", state: { ...defaults } };
  if (!hash.startsWith(HASH_PREFIX)) return { status: "unknown_version", state: { ...defaults } };
  let payload;
  try { payload = JSON.parse(base64UrlDecode(hash.slice(HASH_PREFIX.length))); }
  catch (_error) { return { status: "invalid", state: { ...defaults } }; }
  if (!payload || payload.v !== STATE_VERSION) return { status: "unknown_version", state: { ...defaults } };
  const time = payload.time || {};
  const validYears = Number.isInteger(time.from) && Number.isInteger(time.to)
    && time.from >= 1968 && time.to <= 2026 && time.from <= time.to;
  const map = payload.map || {};
  const validMap = typeof map.lat === "number" && Number.isFinite(map.lat) && map.lat >= -90 && map.lat <= 90
    && typeof map.lon === "number" && Number.isFinite(map.lon) && map.lon >= -180 && map.lon <= 180
    && typeof map.z === "number" && Number.isFinite(map.z) && map.z >= 3 && map.z <= 14;
  const territory = payload.territory || {};
  const validScope = territory.scope === "ES" || territory.scope === "autonomous_community" || territory.scope === "province" || territory.scope === "municipality";
  const validCommunity = territory.autonomous_community_id == null || territoryIds.has(territory.autonomous_community_id);
  const provinceId = validId(territory.province_id, /^ES:PROV:\d{2}$/);
  const provinceParent = provinceId ? provinceParents.get(provinceId) : null;
  const municipalityId = validId(territory.municipality_id, /^ES:MUN:\d{5}$/);
  const municipalityParent = municipalityId && municipalityParents ? municipalityParents.get(municipalityId) : null;
  const municipalityScope = validScope && territory.scope === "municipality" && validCommunity && municipalityId
    && (!municipalityParents || (municipalityParent && municipalityParent.autonomous_community_id === territory.autonomous_community_id
      && municipalityParent.province_id === (provinceId || null)));
  const provinceScope = validScope && territory.scope === "province" && validCommunity
    && provinceId && provinceParent === territory.autonomous_community_id;
  const communityScope = validScope && validCommunity && territory.scope === "autonomous_community" && territory.autonomous_community_id;
  const scope = municipalityScope ? "municipality" : provinceScope ? "province" : communityScope ? "autonomous_community" : "ES";
  const sources = payload.sources || {};
  const selections = payload.selections || {};
  const state = {
    ...defaults,
    ...(validYears ? { from: time.from, to: time.to } : {}),
    center: validMap ? [map.lon, map.lat] : [...defaults.center],
    zoom: validMap ? map.z : defaults.zoom,
    territory_scope: scope,
    autonomous_community_id: scope === "ES" ? null : territory.autonomous_community_id,
    province_id: scope === "province" || scope === "municipality" ? provinceId : null,
    municipality_id: scope === "municipality" ? municipalityId : null,
    esfire30_visible: typeof sources.esfire30 === "boolean" ? sources.esfire30 : defaults.esfire30_visible,
    egif_visible: typeof sources.egif === "boolean" ? sources.egif : defaults.egif_visible,
    icv_visible: typeof sources.icv === "boolean" ? sources.icv : defaults.icv_visible,
    effis_visible: typeof sources.effis === "boolean" ? sources.effis : defaults.effis_visible,
    selected_geometry_id: validId(selections.geometry_id, /^esfire30:/),
    selected_egif_record_id: validId(selections.egif_record_id, /^egif-record:\d+$/),
    selected_icv_geometry_id: validId(selections.icv_geometry_id, /^gva:geometry:/),
    selected_icv_record_id: validId(selections.icv_record_id, /^gva:pif-cv:/),
    selected_effis_geometry_id: validId(selections.effis_geometry_id, /^effis:rda:/),
    selected_geometry_year: null,
    selected_egif_year: null,
    selected_icv_geometry_year: null,
    selected_effis_geometry_year: null,
  };
  return { status: "complete", state };
}

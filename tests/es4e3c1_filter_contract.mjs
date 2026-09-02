import assert from "assert";
import { FILTER_CONTRACTS, canonicalFilters, documentedIcvGif, recordMatchesSourceFilters } from "../prototypes/es4c/source_filters.mjs";
import { createRuntimeState, reduceRuntimeState } from "../prototypes/es4c/runtime_state.mjs";
import { parseStateHash, serializeState } from "../prototypes/es4c/state_serialization.mjs";
import { adaptLegacyGvaV1State } from "../src/national/compat/gva-v1.mjs";
import { applyRuntimeFiltersToTerritory, aggregateMetric } from "../src/national/metrics-histogram.mjs";
import { humanDate } from "../src/national/human-details.mjs";

const egifMinimum = { filter_id: "egif_min_area", filter_type: "min_value", source: "egif", metric_id: "egif_declared_forest_area_ha", value: 500, unit: "ha" };
const icvCause = { filter_id: "icv_cause", filter_type: "enum", source: "icv", metric_id: "icv_cause_distribution", value: "lightning", unit: null };

assert.strictEqual(FILTER_CONTRACTS.length, 6);
assert.deepStrictEqual(canonicalFilters([icvCause, egifMinimum]).map((row) => row.filter_id), ["egif_min_area", "icv_cause"]);
assert.strictEqual(recordMatchesSourceFilters("egif", { reported_forest_area_ha: null }, [egifMinimum]), false);
assert.strictEqual(recordMatchesSourceFilters("egif", { reported_forest_area_ha: 0 }, [egifMinimum]), false);
assert.strictEqual(recordMatchesSourceFilters("egif", { reported_forest_area_ha: 500 }, [egifMinimum]), true);
assert.strictEqual(documentedIcvGif({ reported_forest_area_ha: 500 }), true);
assert.strictEqual(documentedIcvGif({ reported_forest_area_ha: null }), null);
assert.strictEqual(recordMatchesSourceFilters("effis", { mapped_area_ha: 100 }, [egifMinimum]), true);

let state = createRuntimeState({ center: [-.5, 39.5], zoom: 7, from: 1995, to: 1995, territory_scope: "autonomous_community", autonomous_community_id: "ES:CCAA:10", icv_visible: true });
state = reduceRuntimeState(state, { type: "set_filter", filter: icvCause });
assert.strictEqual(state.filters.length, 1);
const hash = serializeState(state);
let parsed = parseStateHash(hash, createRuntimeState({ center: [-3.7, 40.3], zoom: 4 }), new Set(["ES:CCAA:10"]));
assert.deepStrictEqual(parsed.state.filters, [icvCause]);
parsed = parseStateHash("#es4c-state-v1=corrupt", createRuntimeState({ center: [-3.7, 40.3], zoom: 4 }), new Set());
assert.strictEqual(parsed.status, "invalid");
state = reduceRuntimeState(state, { type: "set_scope", territory_id: "ES:CCAA:12" });
assert.strictEqual(state.filters.length, 0);

const defaults = createRuntimeState({ center: [-.6, 39.4], zoom: 8 });
const context = { territoryIds: new Set(["ES:CCAA:10"]), provinceParents: new Map(), municipalityParents: new Map() };
let legacy = adaptLegacyGvaV1State({ version: 1, sources: ["icv"], minimumArea: 100, gifOnly: true, cause: "lightning" }, defaults, context);
assert.deepStrictEqual(legacy.state.filters.map((row) => row.filter_id), ["icv_cause", "icv_gif", "icv_min_area"]);
assert.strictEqual(legacy.mapping.filters.minimumArea, "MAPPED_EXACTLY");
legacy = adaptLegacyGvaV1State({ version: 1, sources: ["icv", "egif"], minimumArea: 100, gifOnly: true, cause: "lightning" }, defaults, context);
assert.deepStrictEqual(legacy.state.filters, []);
assert.deepStrictEqual(legacy.mapping.ignored.sort(), ["cause", "gifOnly", "minimumArea"]);

const territory = { territory: { territory_id: "ES:CCAA:10", official_name: "Comunitat Valenciana" }, source_summaries: [{ source_id: "icv", coverage: { status: "available", from: 1993, to: 2024 }, year_axis: { from: 1993, to: 1995 }, metrics: [
  { metric_id: "icv_fire_record_count", unit: "fire_records", values: [10, 11, 12] },
  { metric_id: "icv_declared_forest_area_ha", unit: "ha", values: [20, 30, 40], known_value_count: [1, 1, 1], unknown_value_count: [0, 0, 0] },
] }] };
const filteredState = { ...defaults, from: 1995, to: 1995, territory_scope: "autonomous_community", autonomous_community_id: "ES:CCAA:10", filters: [icvCause] };
const runtime = { getIcvResult: () => ({ status: "complete", filters: [icvCause], annual: { 1995: { records: 2, declared_forest_area_sum: 7, known_area: 1, unknown_area: 1 } } }) };
const filtered = applyRuntimeFiltersToTerritory(territory, filteredState, runtime);
assert.strictEqual(aggregateMetric(filtered, "icv_fire_record_count", 1995, 1995).value, 2);
assert.strictEqual(aggregateMetric(filtered, "icv_declared_forest_area_ha", 1995, 1995).unknown_value_count, 1);
assert.strictEqual(filtered.source_summaries[0].filtered_summary_mode, "EXACT_RUNTIME");
assert.strictEqual(humanDate("2024-07-03"), "03/07/2024");

console.log(JSON.stringify({ valid: true, contracts: FILTER_CONTRACTS.length, rules: 24 }));

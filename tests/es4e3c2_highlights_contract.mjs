import assert from "assert";
import { HIGHLIGHT_CONTRACTS, rankHighlightItems, sourceForMetric } from "../src/national/highlights.mjs";
import { topInitialRows } from "../prototypes/es4c/egif_detail_loader.mjs";

assert.strictEqual(HIGHLIGHT_CONTRACTS.egif.metric_id, "egif_declared_forest_area_ha");
assert.strictEqual(HIGHLIGHT_CONTRACTS.esfire30.status, "DEFERRED_NO_SAFE_RANKING_METRIC");
assert.strictEqual(sourceForMetric("icv_fire_record_count"), "icv");

const rows = [
  { record_id: "b", reported_forest_area_ha: 12 },
  { record_id: "a", reported_forest_area_ha: 12 },
  { record_id: "c", reported_forest_area_ha: null },
  { record_id: "d", reported_forest_area_ha: 0 },
];
assert.deepStrictEqual(rankHighlightItems("egif", rows).map((row) => row.record_id), ["a", "b", "d"]);

const columns = {
  record_id: ["egif-record:1", "egif-record:2", "egif-record:3"], year: [1995, 1995, 1995],
  autonomous_community_id: ["ES:CCAA:10", "ES:CCAA:10", "ES:CCAA:10"],
  province_id: ["ES:PROV:03", "ES:PROV:03", "ES:PROV:03"], municipality_id: [null, null, null],
  reported_forest_area_ha: [null, 0, 600], is_gif_forest_ge_500_ha: [false, false, true],
  cause_source_code: [null, null, null], canonical_cause: [null, null, null], cause_mapping_status: ["unmapped", "unmapped", "unmapped"],
  coverage_status: ["complete", "complete", "complete"], identity_status: ["source_record_only", "source_record_only", "source_record_only"], episode_identity_status: ["unresolved", "unresolved", "unresolved"],
};
const loaded = [{ asset: { asset_id: "egif:test" }, data: { columns }, lookup: new Map(columns.record_id.map((id, index) => [id, index])) }];
assert.deepStrictEqual(topInitialRows(loaded, 1995, 1995, 10).map((row) => [row.record_id, row.reported_forest_area_ha]), [["egif-record:3", 600], ["egif-record:2", 0]]);
assert.deepStrictEqual(topInitialRows(loaded, 1995, 1995, 10, null, null, [{ filter_id: "egif_gif", filter_type: "flag", source: "egif", metric_id: "egif_administrative_gif_count", value: true, unit: null }]).map((row) => row.record_id), ["egif-record:3"]);

console.log(JSON.stringify({ valid: true, assertions: 7 }));

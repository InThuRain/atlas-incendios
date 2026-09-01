import assert from "assert";
import fs from "fs";
import { adaptLegacyGvaV1State, dispatchStateHash, parseLegacyGvaV1State } from "../src/national/compat/gva-v1.mjs";

const fixtures = JSON.parse(fs.readFileSync(new URL("./fixtures/gva_permalink_v1.json", import.meta.url), "utf8")).fixtures;
const defaults = { from: 1985, to: 2021, center: [-3.7, 40.3], zoom: 4, territory_scope: "ES", autonomous_community_id: null, province_id: null, municipality_id: null, esfire30_visible: true, egif_visible: true, icv_visible: true, effis_visible: true, selected_geometry_id: null, selected_egif_record_id: null, selected_icv_geometry_id: null, selected_icv_record_id: null, selected_effis_geometry_id: null };
const territories = new Set(["ES:CCAA:10"]);
const provinces = new Map([["ES:PROV:03", "ES:CCAA:10"], ["ES:PROV:12", "ES:CCAA:10"], ["ES:PROV:46", "ES:CCAA:10"]]);
const municipalities = new Map([["ES:MUN:03065", { autonomous_community_id: "ES:CCAA:10", province_id: "ES:PROV:03" }]]);
for (const fixture of fixtures) {
  const parsed = parseLegacyGvaV1State(fixture.hash);
  assert.equal(parsed.status, "complete");
  const adapted = adaptLegacyGvaV1State(parsed.state, defaults, { territoryIds: territories, provinceParents: provinces, municipalityParents: municipalities });
  assert.equal(adapted.status, "complete");
  for (const [key, value] of Object.entries(fixture.expected)) if (key !== "safe_fallback") assert.deepEqual(adapted.state[key], value, `${fixture.id}:${key}`);
}
const multi = fixtures.find((item) => item.id === "icv_record_only_2024al0005");
const adapted = adaptLegacyGvaV1State(parseLegacyGvaV1State(multi.hash).state, defaults, { territoryIds: territories, provinceParents: provinces, municipalityParents: municipalities });
assert.equal(adapted.state.selected_icv_record_id, "gva:pif-cv:2024AL0005");
assert.equal(adapted.state.selected_icv_geometry_id, null);
assert.equal(dispatchStateHash("#es4c-state-v1=abc"), "national_v1");
assert.equal(dispatchStateHash("#v=1&from=2024"), "gva_v1");
assert.equal(dispatchStateHash("#v=2"), "legacy_unknown_version");
assert.equal(dispatchStateHash("#v=10"), "legacy_unknown_version");
assert.equal(dispatchStateHash("#garbage"), "unknown");

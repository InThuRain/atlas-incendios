import assert from "assert";
import fs from "fs";
import path from "path";
import { NationalUxSummaryLoader, territoryRequest } from "../src/national/ux-summary-loader.mjs";
import { aggregateMetric, annualSeries, availableSeries, defaultSeriesId, formatMetricValue, metricCards } from "../src/national/metrics-histogram.mjs";

async function main() {
const ROOT = process.cwd();
const SUMMARY = path.join(ROOT, "data/derived/spain/national-ux-summary-v1");
const read = (relative) => JSON.parse(fs.readFileSync(path.join(SUMMARY, relative), "utf8"));
const territory = (relative, id) => read(relative).territories.find((row) => row.territory.territory_id === id);
const fullState = (extra = {}) => Object.assign({
  from: 1968, to: 2026, autonomous_community_id: null, province_id: null, municipality_id: null,
  egif_visible: true, esfire30_visible: true, icv_visible: true, effis_visible: true,
}, extra);

const national = territory("national.json", "ES");
const gva = territory("ccaa/ES-CCAA-10.json", "ES:CCAA:10");
const canarias = territory("ccaa/ES-CCAA-05.json", "ES:CCAA:05");
const elx = territory("municipalities/by-parent/ES-PROV-03.json", "ES:MUN:03065");
const agost = territory("municipalities/by-parent/ES-PROV-03.json", "ES:MUN:03002");

assert.strictEqual(aggregateMetric(national, "egif_record_count", 1968, 2023).value, 646887);
assert.strictEqual(aggregateMetric(national, "esfire30_perimeter_count", 1985, 2021).value, 119498);
assert.strictEqual(aggregateMetric(gva, "icv_fire_record_count", 1993, 2024).value, 13738);
assert.strictEqual(aggregateMetric(gva, "icv_perimeter_count", 1993, 2024).value, 13739);
assert.strictEqual(aggregateMetric(gva, "effis_perimeter_count", 2025, 2025).value, 9);
assert.strictEqual(aggregateMetric(gva, "effis_perimeter_count", 2026, 2026).value, 16);
assert.strictEqual(aggregateMetric(canarias, "esfire30_perimeter_count", 1995, 1995).status, "no_source_coverage");
assert.strictEqual(aggregateMetric(agost, "esfire30_perimeter_count", 1985, 2021).value, 0);
assert.strictEqual(aggregateMetric(elx, "effis_perimeter_count", 2025, 2025).value, 1);
assert.strictEqual(formatMetricValue(646887, "records"), "646.887");
assert.strictEqual(formatMetricValue(12.25, "ha"), "12,3 ha");

let series = availableSeries(gva);
assert.strictEqual(defaultSeriesId(fullState({ from: 1995, to: 1995, autonomous_community_id: "ES:CCAA:10" }), series), "icv_fire_record_count");
assert.strictEqual(defaultSeriesId(fullState({ from: 2026, to: 2026, autonomous_community_id: "ES:CCAA:10" }), series), "effis_perimeter_count");
assert.strictEqual(defaultSeriesId(fullState({ from: 1980, to: 2026, autonomous_community_id: "ES:CCAA:10" }), series), "egif_record_count");
const histogram = annualSeries(national, "egif_record_count");
assert.strictEqual(histogram.find((row) => row.year === 1975).value, 4128);
assert.strictEqual(histogram.find((row) => row.year === 2026).status, "gap");
assert.strictEqual(annualSeries(agost, "esfire30_perimeter_count").find((row) => row.year === 1995).status, "zero");
assert.ok(metricCards(gva, fullState({ from: 1995, to: 1995, autonomous_community_id: "ES:CCAA:10" }), "icv").length <= 4);

assert.deepStrictEqual(territoryRequest(fullState()), { kind: "spain", territoryId: "ES" });
assert.deepStrictEqual(territoryRequest(fullState({ autonomous_community_id: "ES:CCAA:12" })), { kind: "ccaa", territoryId: "ES:CCAA:12" });
assert.deepStrictEqual(territoryRequest(fullState({ autonomous_community_id: "ES:CCAA:12", province_id: "ES:PROV:32" })), { kind: "province", territoryId: "ES:PROV:32" });
assert.deepStrictEqual(territoryRequest(fullState({ autonomous_community_id: "ES:CCAA:10", province_id: "ES:PROV:03", municipality_id: "ES:MUN:03065" })), { kind: "municipality", territoryId: "ES:MUN:03065", parentId: "ES:PROV:03" });

const manifest = fs.readFileSync(path.join(SUMMARY, "manifest.json"), "utf8");
const requested = [];
const fakeFetch = async (url) => {
  requested.push(String(url));
  const parsed = new URL(String(url));
  const marker = "/national-ux-summary-v1/";
  const relative = parsed.pathname.split(marker)[1];
  const target = path.join(SUMMARY, relative);
  if (!fs.existsSync(target)) return { ok: false, status: 404, text: async () => "" };
  return { ok: true, status: 200, text: async () => fs.readFileSync(target, "utf8") };
};
const loader = new NationalUxSummaryLoader({ manifestUrl: "https://atlas.test/data/summary/national-ux-summary-v1/manifest.json", fetchImpl: fakeFetch });
let loaded = await loader.loadTerritory(fullState());
assert.strictEqual(loaded.status, "complete"); assert.strictEqual(loaded.territory.territory.territory_id, "ES");
loaded = await loader.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:12" }));
assert.strictEqual(loaded.asset.path, "ccaa/ES-CCAA-12.json");
loaded = await loader.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:12", province_id: "ES:PROV:32" }));
assert.strictEqual(loaded.asset.path, "provinces/ES-PROV-32.json");
loaded = await loader.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:10", province_id: "ES:PROV:03", municipality_id: "ES:MUN:03065" }));
assert.strictEqual(loaded.territory.territory.official_name, "Elx/Elche");
const beforeCache = requested.length;
loaded = await loader.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:10", province_id: "ES:PROV:03", municipality_id: "ES:MUN:03065" }));
assert.strictEqual(loaded.asset.cache_hit, true); assert.strictEqual(requested.length, beforeCache);
assert.strictEqual((await loader.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:99" }))).status, "error");

let releaseSlow;
const delayedFetch = async (url) => {
  if (String(url).endsWith("manifest.json")) return { ok: true, status: 200, text: async () => manifest };
  if (String(url).includes("ES-CCAA-12")) await new Promise((resolve) => { releaseSlow = resolve; });
  const relative = new URL(String(url)).pathname.split("/national-ux-summary-v1/")[1];
  return { ok: true, status: 200, text: async () => fs.readFileSync(path.join(SUMMARY, relative), "utf8") };
};
const cancelling = new NationalUxSummaryLoader({ manifestUrl: "https://atlas.test/data/summary/national-ux-summary-v1/manifest.json", fetchImpl: delayedFetch });
const stalePromise = cancelling.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:12" }));
await new Promise((resolve) => setTimeout(resolve, 0));
const currentPromise = cancelling.loadTerritory(fullState({ autonomous_community_id: "ES:CCAA:10" }));
releaseSlow();
assert.strictEqual((await stalePromise).status, "stale");
assert.strictEqual((await currentPromise).status, "complete");

const malformed = new NationalUxSummaryLoader({
  manifestUrl: "https://atlas.test/data/summary/national-ux-summary-v1/manifest.json",
  fetchImpl: async (url) => String(url).endsWith("manifest.json")
    ? { ok: true, status: 200, text: async () => manifest }
    : { ok: true, status: 200, text: async () => "{}" },
});
assert.strictEqual((await malformed.loadTerritory(fullState())).status, "error");

const buildManifest = read("manifest.json");
assert.deepStrictEqual(buildManifest.source_reconciliation.icv.control_2024AL0005, { fire_record_count: 1, geometry_count: 2 });
console.log(JSON.stringify({ valid: true, rules: 34, loader_requests: requested.length }));
}

main().catch((error) => { console.error(error); process.exit(1); });

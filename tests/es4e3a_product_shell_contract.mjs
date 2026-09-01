import assert from "assert";
import { humanCoverageMessages, publicRuntimeMessage, recommendedView } from "../src/national/product-shell.mjs";

function state(from, to, autonomousCommunityId = null, extra = {}) {
  return { from, to, autonomous_community_id: autonomousCommunityId, province_id: null, municipality_id: null, ...extra };
}

let view = recommendedView(state(1995, 1995));
assert.strictEqual(view.primary, "esfire30");
assert.deepStrictEqual(view.geometry_sources, ["esfire30"]);
assert.deepStrictEqual(view.visibility, { esfire30: true, egif: true, icv: false, effis: false });

view = recommendedView(state(1990, 1990, "ES:CCAA:10"));
assert.strictEqual(view.primary, "esfire30");
view = recommendedView(state(1995, 1995, "ES:CCAA:10"));
assert.strictEqual(view.primary, "icv");
assert.deepStrictEqual(view.visibility, { esfire30: false, egif: true, icv: true, effis: false });
view = recommendedView(state(2026, 2026, "ES:CCAA:10"));
assert.strictEqual(view.primary, "effis");
assert.deepStrictEqual(view.visibility, { esfire30: false, egif: false, icv: false, effis: true });
view = recommendedView(state(1990, 2026, "ES:CCAA:10"));
assert.strictEqual(view.primary, "multi_regime");
assert.deepStrictEqual(view.geometry_sources, ["esfire30", "icv", "effis"]);
view = recommendedView(state(1995, 1995, "ES:CCAA:05"));
assert.strictEqual(view.primary, "egif");
assert.strictEqual(view.visibility.esfire30, false);

assert.ok(/registros administrativos.*no de perímetros/i.test(humanCoverageMessages(state(1975, 1975))));
assert.ok(/registros administrativos.*no de perímetros/i.test(humanCoverageMessages(state(1995, 1995, "ES:CCAA:05"))));
assert.ok(/No hay perímetros Landsat/i.test(humanCoverageMessages(state(1995, 1995, "ES:CCAA:10", { municipality_id: "ES:MUN:03002" }), { zeroRelations: true })));
assert.ok(/Periodo solicitado: 1980–1990.*1985–1990/i.test(humanCoverageMessages(state(1980, 1990))));
assert.strictEqual(humanCoverageMessages(state(2024, 2024, "ES:CCAA:10")), "");
assert.strictEqual(publicRuntimeMessage("source ready"), "");
assert.ok(/No disponemos/i.test(publicRuntimeMessage("sin cobertura")));
assert.ok(/No se han podido cargar/i.test(publicRuntimeMessage("error de carga")));

console.log(JSON.stringify({ valid: true, rules: 12 }));

const { Protocol } = window.pmtiles;

const params = new URLSearchParams(location.search);
const scenario = params.get("smoke") || "spain";
const assetUrl = new URL("../data/esfire30-national-fidelity-territories.pmtiles", location.href);
const output = document.querySelector("#debug-output");
const status = document.querySelector("#status");
const telemetry = [];
const runtimeErrors = [];
const baseFetch = window.fetch.bind(window);
const startedAt = performance.now();

window.addEventListener("error", (event) => runtimeErrors.push(String(event.error || event.message || "window error")));
window.addEventListener("unhandledrejection", (event) => runtimeErrors.push(String(event.reason || "unhandled rejection")));

function bytes(headers) {
  const range = headers.get("Content-Range")?.match(/^bytes\s+(\d+)-(\d+)\/(\d+)$/i);
  return range ? Number(range[2]) - Number(range[1]) + 1 : Number(headers.get("Content-Length")) || null;
}
window.fetch = async (input, init) => {
  const url = typeof input === "string" ? input : input?.url;
  const tracked = url === assetUrl.href;
  try {
    const response = await baseFetch(input, init);
    if (tracked) telemetry.push({ status: response.status, range: new Headers(init?.headers).get("Range"), content_range: response.headers.get("Content-Range"), bytes: bytes(response.headers) });
    return response;
  } catch (error) {
    if (tracked) telemetry.push({ status: null, error: String(error), aborted: error?.name === "AbortError" });
    throw error;
  }
};

const CASES = {
  spain: { center: [-3.7, 40.3], zoom: 4, year: [1993, 2002] },
  galicia: { center: [-8.1, 42.6], zoom: 6, year: [1993, 2002], slots: ["ccaa", 12] },
  ourense: { center: [-7.86, 42.34], zoom: 7, year: [1993, 2002], slots: ["prov", 32] },
  cangas: { center: [-6.55, 43.18], zoom: 8, year: [1985, 2021], municipal: ["ES-PROV-33.json", "ES:MUN:33011"] },
  elx: { center: [-0.7, 38.27], zoom: 10, year: [1993, 2002], municipal: ["ES-PROV-03.json", "ES:MUN:03065"], select: "esfire30:v1:1993:777" },
};
const selected = CASES[scenario] || CASES.spain;

async function territoryFilter() {
  if (selected.slots) {
    const [prefix, code] = selected.slots;
    return { expression: ["any", ...[1, 2, 3].map((slot) => ["==", ["get", `${prefix}_${slot}`], code])], membership_count: null };
  }
  if (selected.municipal) {
    const [path, municipalityId] = selected.municipal;
    const payload = await fetch(`./municipality-index/${path}`).then((response) => response.json());
    const ids = payload.municipalities[municipalityId] || [];
    return { expression: ["in", ["get", "geometry_id"], ["literal", ids]], membership_count: ids.length };
  }
  return { expression: ["!=", ["get", "geometry_id"], "__none__"], membership_count: null };
}

const directFetch = fetch(assetUrl, { headers: { Range: "bytes=0-0" }, cache: "no-store" })
  .then(async (response) => ({ status: response.status, content_range: response.headers.get("Content-Range"), bytes: (await response.arrayBuffer()).byteLength }))
  .catch((error) => ({ error: String(error) }));
const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
const map = new maplibregl.Map({ container: "map", center: selected.center, zoom: selected.zoom, style: { version: 8,
  sources: { fires: { type: "vector", url: `pmtiles://${assetUrl.href}` } },
  layers: [{ id: "fires", type: "fill", source: "fires", "source-layer": "esfire30", paint: { "fill-color": "#b54d2f", "fill-opacity": .45 } }],
} });
map.on("error", (event) => finish({ errors: [String(event.error || event.message || "MapLibre error")] }));
map.on("load", async () => {
  try {
    const territory = await territoryFilter();
    const filter = ["all", [">=", ["get", "year"], selected.year[0]], ["<=", ["get", "year"], selected.year[1]], territory.expression];
    map.setFilter("fires", filter);
    map.once("idle", () => {
      const features = map.queryRenderedFeatures({ layers: ["fires"] });
      const selection = selected.select ? features.find((feature) => feature.properties?.geometry_id === selected.select)?.properties?.geometry_id || null : features[0]?.properties?.geometry_id || null;
      finish({ source_status: "ready", filter, territory_membership_count: territory.membership_count, rendered_features: features.length, selected_geometry_id: selection });
    });
  } catch (error) { finish({ errors: [String(error)] }); }
});
function finish(extra) {
  const rows = telemetry.slice();
  const result = { scenario, asset_url: assetUrl.href, browser_range_fetch: null, pmtiles: {
    requests: rows.length, range_requests: rows.filter((row) => row.status === 206 && row.range).length,
    bytes: rows.reduce((sum, row) => sum + (row.bytes || 0), 0),
    full_download_observed: rows.some((row) => row.status === 200 && (row.bytes || 0) >= 63052056), rows,
  }, runtime_errors: runtimeErrors, map_ready_ms: Math.round((performance.now() - startedAt) * 1000) / 1000, ...extra };
  directFetch.then((value) => { result.browser_range_fetch = value; status.textContent = result.source_status || "error"; output.textContent = JSON.stringify(result); output.dataset.complete = "true"; });
}

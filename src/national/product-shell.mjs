import { NATIONAL_SOURCE_REGISTRY } from "./source-registry.mjs";
import { NationalUxSummaryLoader } from "./ux-summary-loader.mjs";
import { createMetricsHistogramUi } from "./metrics-histogram.mjs";
import { createSafeFiltersUi } from "./safe-filters.mjs";
import { createHumanDetailsUi } from "./human-details.mjs";
import { createHighlightsUi } from "./highlights.mjs";

const GVA_ID = "ES:CCAA:10";
const ESFIRE30_NO_TERRITORY_COVERAGE = new Set([
  "ES:CCAA:04", "ES:CCAA:05", "ES:CCAA:18", "ES:CCAA:19",
  "ES:PROV:07", "ES:PROV:35", "ES:PROV:38",
]);
const SOURCE_IDS = ["esfire30", "egif", "icv", "effis"];
const SOURCE_PRESENTATION = Object.freeze({
  esfire30: { legend: "Perímetros Landsat", swatch: "esfire30" },
  egif: { legend: null, swatch: null },
  icv: { legend: "Perímetros oficiales", swatch: "icv" },
  effis: { legend: "Perímetros satelitales provisionales", swatch: "effis" },
});

function overlaps(from, to, coverage) {
  return Math.max(Number(from), coverage.from) <= Math.min(Number(to), coverage.to);
}

export function recommendedView(state) {
  const from = Number(state.from);
  const to = Number(state.to);
  const isGva = state.autonomous_community_id === GVA_ID;
  const territoryId = state.province_id || state.autonomous_community_id;
  const esfireTerritoryCovered = !ESFIRE30_NO_TERRITORY_COVERAGE.has(territoryId)
    && !ESFIRE30_NO_TERRITORY_COVERAGE.has(state.autonomous_community_id);
  const egif = overlaps(from, to, NATIONAL_SOURCE_REGISTRY.egif.coverage);
  let geometrySources;
  if (!isGva) {
    geometrySources = esfireTerritoryCovered && overlaps(from, to, NATIONAL_SOURCE_REGISTRY.esfire30.coverage) ? ["esfire30"] : [];
  } else {
    geometrySources = [];
    if (Math.max(from, 1985) <= Math.min(to, 1992)) geometrySources.push("esfire30");
    if (Math.max(from, 1993) <= Math.min(to, 2024)) geometrySources.push("icv");
    if (Math.max(from, 2025) <= Math.min(to, 2026)) geometrySources.push("effis");
  }
  const primary = geometrySources.length === 1 ? geometrySources[0]
    : isGva && geometrySources.length > 1 ? "multi_regime"
    : geometrySources[0] || (egif ? "egif" : null);
  const visibility = {
    esfire30: geometrySources.includes("esfire30"),
    egif,
    icv: geometrySources.includes("icv"),
    effis: geometrySources.includes("effis"),
  };
  let copy;
  if (primary === "esfire30") copy = "Perímetros obtenidos mediante imágenes Landsat, junto a los registros administrativos disponibles.";
  else if (primary === "icv") copy = "Incendios y perímetros oficiales documentados por la Generalitat Valenciana; los registros EGIF permanecen como información independiente.";
  else if (primary === "effis") copy = "Perímetros satelitales provisionales EFFIS para el periodo reciente; no representan el cierre anual.";
  else if (primary === "multi_regime") copy = "El periodo atraviesa varias fuentes: cada tramo se presenta por separado y sin sumar ni enlazar sus elementos.";
  else if (primary === "egif") copy = "Registros administrativos disponibles; no disponemos de una capa de perímetros para este contexto.";
  else copy = "No disponemos de registros ni perímetros integrados para este contexto.";
  return { title: "Vista recomendada", copy, primary, geometry_sources: geometrySources, visibility };
}

export function humanCoverageMessages(state, { zeroRelations = false, sourceError = false } = {}) {
  const from = Number(state.from);
  const to = Number(state.to);
  const territoryId = state.municipality_id || state.province_id || state.autonomous_community_id || "ES";
  const egifAvailable = overlaps(from, to, NATIONAL_SOURCE_REGISTRY.egif.coverage);
  const esfireTime = overlaps(from, to, NATIONAL_SOURCE_REGISTRY.esfire30.coverage);
  const esfireTerritory = !ESFIRE30_NO_TERRITORY_COVERAGE.has(territoryId)
    && !ESFIRE30_NO_TERRITORY_COVERAGE.has(state.autonomous_community_id)
    && !ESFIRE30_NO_TERRITORY_COVERAGE.has(state.province_id);
  if (sourceError) return "No se han podido cargar algunos perímetros. El resto del Atlas sigue disponible.";
  if (zeroRelations && esfireTime && esfireTerritory) return "No hay perímetros Landsat que intersecten este territorio en el periodo seleccionado.";
  const gvaAlternativeGeometry = state.autonomous_community_id === GVA_ID
    && (overlaps(from, to, NATIONAL_SOURCE_REGISTRY.icv.coverage) || overlaps(from, to, NATIONAL_SOURCE_REGISTRY.effis.coverage));
  if (gvaAlternativeGeometry) return "";
  if (!esfireTime || !esfireTerritory) {
    if (egifAvailable) return "Disponemos de registros administrativos, pero no de perímetros cartografiados para este territorio y periodo.";
    return "No disponemos de registros ni perímetros integrados para este territorio y periodo.";
  }
  const effectiveFrom = Math.max(from, 1985);
  const effectiveTo = Math.min(to, 2021);
  if (effectiveFrom !== from || effectiveTo !== to) {
    return `Periodo solicitado: ${from === to ? from : `${from}–${to}`}. Perímetros Landsat disponibles: ${effectiveFrom}–${effectiveTo}.`;
  }
  return "";
}

export function publicRuntimeMessage(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("error") || text.includes("no disponible:")) return "No se han podido cargar estos datos. El resto del Atlas sigue disponible.";
  if (text.includes("sin perímetros") && text.includes("cobertura disponible")) return "No hay perímetros que intersecten este territorio en el periodo seleccionado.";
  if (text.includes("sin cobertura")) return "No disponemos de este tipo de dato para el territorio o periodo seleccionado.";
  if (text.includes("cargando") || text.includes("calculando")) return "Cargando datos…";
  return "";
}

function formatNumber(value, maximumFractionDigits = 0) {
  return new Intl.NumberFormat("es-ES", { maximumFractionDigits }).format(Number(value));
}

function appendMetric(list, label, value) {
  const term = document.createElement("dt"); term.textContent = label;
  const definition = document.createElement("dd"); definition.textContent = value;
  list.append(term, definition);
}

function currentTerritoryName() {
  const entries = [...document.querySelectorAll("#territory-breadcrumb button")].map((button) => button.textContent.trim()).filter(Boolean);
  return entries.length ? entries.join(" / ") : "España";
}

function sourceHasCoverage(state, sourceId) {
  if (!state[`${sourceId}_visible`]) return false;
  const source = NATIONAL_SOURCE_REGISTRY[sourceId];
  if (!source.coverage || !overlaps(state.from, state.to, source.coverage)) return false;
  if ((sourceId === "icv" || sourceId === "effis") && state.autonomous_community_id !== GVA_ID) return false;
  const territoryId = state.province_id || state.autonomous_community_id;
  if (sourceId === "esfire30" && (ESFIRE30_NO_TERRITORY_COVERAGE.has(territoryId) || ESFIRE30_NO_TERRITORY_COVERAGE.has(state.autonomous_community_id))) return false;
  return true;
}

function buildLegend(state, view) {
  const list = document.querySelector("#user-map-legend");
  if (!list) return;
  list.replaceChildren();
  const entries = [{ label: "Límite administrativo actual", swatch: "boundary" }];
  const preferred = view.primary === "multi_regime" ? view.geometry_sources : [view.primary, ...SOURCE_IDS];
  for (const id of [...new Set(preferred)]) {
    const presentation = SOURCE_PRESENTATION[id];
    if (!presentation || !presentation.legend || !sourceHasCoverage(state, id)) continue;
    entries.push({ label: presentation.legend, swatch: presentation.swatch });
  }
  for (const entry of entries) {
    const item = document.createElement("li");
    const swatch = document.createElement("span"); swatch.className = `legend-swatch legend-swatch--${entry.swatch}`; swatch.setAttribute("aria-hidden", "true");
    item.append(swatch, document.createTextNode(entry.label)); list.append(item);
  }
}

const HUMAN_FIELD_PATTERNS = [
  /^año$/i, /^fecha de inicio$/i, /^fecha de extinción$/i, /^fecha effis$/i, /^fecha final effis$/i,
  /^ccaa$/i, /^provincia/i, /^municipio$/i, /^municipio declarado/i, /^paraje/i,
  /^superficie forestal declarada$/i, /^superficie cartografiada$/i, /^gif$/i,
  /^geometrías de este/i, /^geometrías documentadas$/i,
];

function syncHumanFields(sourceId, targetId) {
  const source = document.querySelector(sourceId);
  const target = document.querySelector(targetId);
  if (!source || !target) return;
  target.replaceChildren();
  const children = [...source.children];
  for (let index = 0; index + 1 < children.length; index += 2) {
    const term = children[index]; const definition = children[index + 1];
    if (term.tagName !== "DT" || definition.tagName !== "DD") continue;
    const label = term.textContent.trim(); const value = definition.textContent.trim();
    if (!HUMAN_FIELD_PATTERNS.some((pattern) => pattern.test(label))) continue;
    if (!value || /^(no disponible|no det\.|no mapeada|unmapped)$/i.test(value)) continue;
    if (/^causa$/i.test(label) && /código|sin normalizar/i.test(value)) continue;
    appendMetric(target, label, value);
  }
}

function syncSelections() {
  const selectionSummary = document.querySelector("#selection-summary");
  const esfireRaw = selectionSummary ? selectionSummary.textContent : "";
  const esfireHuman = document.querySelector("#selection-human-summary");
  if (esfireHuman) {
    const match = esfireRaw.match(/año:\s*([^·]+)/i);
    const year = match && match[1] ? match[1].trim() : null;
    esfireHuman.textContent = esfireRaw.includes("geometry_id:")
      ? `Perímetro obtenido mediante imágenes Landsat${year ? ` · ${year}` : ""}. No constituye cartografía oficial.`
      : "Pulsa o toca un perímetro para conocer su año y procedencia.";
  }
  syncHumanFields("#egif-detail-fields", "#egif-human-detail-fields");
  syncHumanFields("#icv-detail-fields", "#icv-human-detail-fields");
  syncHumanFields("#effis-detail-fields", "#effis-human-detail-fields");
}

function syncDetailsAccessibility(runtime) {
  document.querySelectorAll("details").forEach((details) => {
    const summary = details.querySelector(":scope > summary");
    if (summary) summary.setAttribute("aria-expanded", String(details.open));
  });
  if (runtime.map && runtime.map.resize) runtime.map.resize();
}

function syncPublicUi(runtime, metricsUi = null, filtersUi = null, detailsUi = null, highlightsUi = null) {
  const state = runtime.getState();
  const territory = currentTerritoryName();
  const period = state.from === state.to ? String(state.from) : `${state.from}–${state.to}`;
  document.querySelector("#header-territory").textContent = territory;
  document.querySelector("#header-period").textContent = period;
  const mapContext = document.querySelector("#map-context-territory");
  if (mapContext) mapContext.textContent = territory;
  document.querySelector("#municipality-current-note").hidden = !state.municipality_id;
  const view = recommendedView(state);
  document.querySelector("#recommended-view-title").textContent = view.title;
  document.querySelector("#recommended-view-copy").textContent = view.copy;
  document.querySelector("#national-product-shell").dataset.recommendedSource = view.primary || "none";
  document.querySelectorAll("[data-source-card]").forEach((card) => { card.dataset.recommended = String(view.geometry_sources.includes(card.dataset.sourceCard)); });
  const sourceCoverage = document.querySelector("#source-coverage");
  const internal = sourceCoverage ? sourceCoverage.textContent : "";
  const zeroRelations = /sin perímetros ESFire30 que intersecten/i.test(internal);
  const sourceError = /error de carga|no disponible por error/i.test(internal);
  document.querySelector("#human-coverage-message").textContent = humanCoverageMessages(state, { zeroRelations, sourceError });
  const territoryStatus = document.querySelector("#territory-status");
  const territoryInternal = territoryStatus ? territoryStatus.textContent : "";
  document.querySelector("#territory-public-status").textContent = publicRuntimeMessage(territoryInternal);
  if (metricsUi) metricsUi.update(state, view);
  highlightsUi?.update();
  filtersUi?.render();
  buildLegend(state, view);
  if (detailsUi) detailsUi.sync(); else syncSelections();
}

async function applyRecommendedVisibility(runtime) {
  const view = recommendedView(runtime.getState());
  for (const sourceId of SOURCE_IDS) {
    const key = `${sourceId}_visible`;
    if (Boolean(runtime.getState()[key]) !== view.visibility[sourceId]) await runtime.setSourceVisibility(sourceId, view.visibility[sourceId]);
  }
}

function waitUntil(predicate, timeoutMs = 30000) {
  const started = performance.now();
  return new Promise((resolve) => {
    const check = () => {
      if (predicate() || performance.now() - started >= timeoutMs) resolve();
      else setTimeout(check, 50);
    };
    check();
  });
}

export function initNationalProductShell(runtime = globalThis.__es4cRuntime, config = globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__) {
  if (!runtime) throw new Error("El runtime nacional no está disponible");
  const summaryManifest = config && config.assets && config.assets.ux_summary && config.assets.ux_summary.manifest && config.assets.ux_summary.manifest.path;
  const summaryLoader = new NationalUxSummaryLoader({ manifestUrl: summaryManifest });
  let highlightsUi = null;
  const metricsUi = createMetricsHistogramUi({ runtime, loader: summaryLoader, onSeriesChange: () => highlightsUi?.update({ force: true }) });
  let detailsUi = null;
  let filtersUi = null;
  const syncAll = () => syncPublicUi(runtime, metricsUi, filtersUi, detailsUi, highlightsUi);
  detailsUi = createHumanDetailsUi({ runtime });
  filtersUi = createSafeFiltersUi({ runtime, onChange: async () => { await metricsUi.update(runtime.getState(), recommendedView(runtime.getState()), { force: true }); syncAll(); } });
  highlightsUi = createHighlightsUi({ runtime, getSelectedMetric: () => metricsUi.getState().selected_series_id });
  const initialUrlHadState = location.hash.length > 1;
  let sourceChoiceIsManual = initialUrlHadState;
  let recommendationGeneration = 0;
  const scheduleRecommendation = () => {
    if (sourceChoiceIsManual) return;
    const generation = ++recommendationGeneration;
    setTimeout(async () => {
      if (generation !== recommendationGeneration || sourceChoiceIsManual) return;
      await applyRecommendedVisibility(runtime);
      syncAll();
    }, 30);
  };

  document.querySelectorAll("#esfire30-visible, #egif-visible, #icv-visible, #effis-visible").forEach((input) => {
    input.addEventListener("change", (event) => { if (event.isTrusted) sourceChoiceIsManual = true; });
  });
  document.querySelectorAll("#territory-scope, #province-scope, #municipality-scope").forEach((input) => input.addEventListener("change", scheduleRecommendation));
  const applyYears = document.querySelector("#apply-years");
  if (applyYears) applyYears.addEventListener("click", scheduleRecommendation);
  document.querySelectorAll("details").forEach((details) => details.addEventListener("toggle", () => syncDetailsAccessibility(runtime)));
  window.addEventListener("resize", () => { if (runtime.map && runtime.map.resize) runtime.map.resize(); });
  window.addEventListener("hashchange", () => { sourceChoiceIsManual = true; setTimeout(syncAll, 50); });
  window.addEventListener("popstate", () => { sourceChoiceIsManual = true; setTimeout(syncAll, 50); });

  const watched = ["#source-coverage", "#runtime-state-summary", "#egif-status", "#egif-detail-fields", "#icv-detail-fields", "#effis-detail-fields", "#selection-summary"]
    .map((selector) => document.querySelector(selector)).filter(Boolean);
  const observer = new MutationObserver(syncAll);
  watched.forEach((node) => observer.observe(node, { childList: true, subtree: true, characterData: true }));
  syncDetailsAccessibility(runtime);
  syncAll();

  if (!initialUrlHadState) {
    waitUntil(() => location.hash.startsWith("#es4c-state-v1=")).then(() => {
      scheduleRecommendation();
      syncAll();
    });
  }
  globalThis.__nationalProductShell = {
    recommendedView: () => recommendedView(runtime.getState()),
    sync: syncAll,
    metrics: metricsUi,
    filters: filtersUi,
    details: detailsUi,
    highlights: highlightsUi,
    sourceChoiceIsManual: () => sourceChoiceIsManual,
    destroy: () => { observer.disconnect(); metricsUi.destroy(); highlightsUi.destroy(); },
  };
  return globalThis.__nationalProductShell;
}

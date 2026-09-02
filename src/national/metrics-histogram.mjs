const GLOBAL_FROM = 1968;
const GLOBAL_TO = 2026;
const GVA_ID = "ES:CCAA:10";

export const METRIC_PRESENTATION = Object.freeze({
  egif_record_count: { source: "egif", sourceLabel: "EGIF", card: "Registros administrativos de incendios", tab: "Registros EGIF", unit: "records", singular: "registro", plural: "registros" },
  egif_declared_forest_area_ha: { source: "egif", sourceLabel: "EGIF", card: "Superficie forestal declarada conocida", tab: "Superficie declarada · EGIF", unit: "ha", singular: "ha", plural: "ha" },
  egif_administrative_gif_count: { source: "egif", sourceLabel: "EGIF", card: "Grandes incendios forestales", unit: "records", singular: "GIF", plural: "GIF" },
  esfire30_perimeter_count: { source: "esfire30", sourceLabel: "ESFire30", card: "Perímetros derivados de imágenes Landsat", tab: "Perímetros Landsat", unit: "perimeters", singular: "perímetro Landsat", plural: "perímetros Landsat" },
  icv_fire_record_count: { source: "icv", sourceLabel: "ICV", card: "Incendios oficiales documentados", tab: "Incendios ICV", unit: "fire_records", singular: "incendio documentado", plural: "incendios documentados" },
  icv_perimeter_count: { source: "icv", sourceLabel: "ICV", card: "Perímetros oficiales", unit: "perimeters", singular: "perímetro oficial", plural: "perímetros oficiales" },
  icv_declared_forest_area_ha: { source: "icv", sourceLabel: "ICV", card: "Superficie forestal declarada conocida", tab: "Superficie declarada · ICV", unit: "ha", singular: "ha", plural: "ha" },
  icv_gif_count: { source: "icv", sourceLabel: "ICV", card: "Grandes incendios forestales", unit: "fire_records", singular: "GIF", plural: "GIF" },
  effis_perimeter_count: { source: "effis", sourceLabel: "EFFIS", card: "Perímetros satelitales provisionales", tab: "Perímetros provisionales", unit: "perimeters", singular: "perímetro provisional", plural: "perímetros provisionales" },
  effis_mapped_area_ha: { source: "effis", sourceLabel: "EFFIS", card: "Área del perímetro satelital provisional", tab: "Área cartografiada · EFFIS", unit: "ha", singular: "ha", plural: "ha" },
});

const HISTOGRAM_METRICS = new Set([
  "egif_record_count", "egif_declared_forest_area_ha", "esfire30_perimeter_count",
  "icv_fire_record_count", "icv_declared_forest_area_ha", "effis_perimeter_count", "effis_mapped_area_ha",
]);

function sourceSummary(territory, sourceId) {
  return territory && Array.isArray(territory.source_summaries) ? territory.source_summaries.find((row) => row.source_id === sourceId) || null : null;
}

function filterKey(filters = []) {
  return JSON.stringify([...filters].sort((left, right) => left.filter_id.localeCompare(right.filter_id)));
}

function replaceAnnualMetric(summary, metricId, annual, valueField, knownField = null, unknownField = null, exactRange = null) {
  const metric = (summary.metrics || []).find((row) => row.metric_id === metricId);
  if (!metric) return;
  metric.values = metric.values.map((_value, index) => {
    const year = summary.year_axis.from + index;
    if (exactRange && (year < exactRange.from || year > exactRange.to)) return null;
    return Number((annual[year] && annual[year][valueField]) || 0);
  });
  if (knownField && Array.isArray(metric.known_value_count)) metric.known_value_count = metric.known_value_count.map((_value, index) => {
    const year = summary.year_axis.from + index;
    return exactRange && (year < exactRange.from || year > exactRange.to) ? null : Number((annual[year] && annual[year][knownField]) || 0);
  });
  if (unknownField && Array.isArray(metric.unknown_value_count)) metric.unknown_value_count = metric.unknown_value_count.map((_value, index) => {
    const year = summary.year_axis.from + index;
    return exactRange && (year < exactRange.from || year > exactRange.to) ? null : Number((annual[year] && annual[year][unknownField]) || 0);
  });
}

/** Aplica sólo agregados exactos ya calculados por los loaders de cada fuente. */
export function applyRuntimeFiltersToTerritory(territory, state, runtime) {
  const clone = JSON.parse(JSON.stringify(territory));
  const filters = state.filters || [];
  for (const summary of clone.source_summaries || []) {
    const sourceFilters = filters.filter((row) => row.source === summary.source_id);
    summary.filtered_summary_mode = sourceFilters.length ? "HIDE_WHILE_FILTERED" : "NOT_FILTERED";
    if (!sourceFilters.length) continue;
    let result = null;
    if (summary.source_id === "egif") result = runtime.getEgifResult ? runtime.getEgifResult() : null;
    if (summary.source_id === "icv") result = runtime.getIcvResult ? runtime.getIcvResult() : null;
    if (summary.source_id === "effis") result = runtime.getEffisResult ? runtime.getEffisResult() : null;
    const sameFilters = result && filterKey(result.filters || (result.summary && result.summary.filters) || []) === filterKey(sourceFilters);
    if (summary.source_id === "egif" && state.territory_scope === "ES") {
      const ids = new Set(sourceFilters.map((row) => `${row.filter_id}:${row.value}`));
      const exactGifEquivalent = [...ids].every((id) => id === "egif_gif:true" || id === "egif_min_area:500");
      if (exactGifEquivalent) {
        const count = summary.metrics.find((row) => row.metric_id === "egif_record_count");
        const gif = summary.metrics.find((row) => row.metric_id === "egif_administrative_gif_count");
        if (count && gif) count.values = [...gif.values];
        summary.metrics = summary.metrics.filter((row) => row.metric_id !== "egif_declared_forest_area_ha");
        summary.filtered_summary_mode = "EXACT_DERIVED";
      }
      continue;
    }
    if (!sameFilters || result.status !== "complete") continue;
    if (summary.source_id === "egif" && result.kind === "initial_assets") {
      const annual = result.summary.annual_metrics || {};
      const range = { from: Number(state.from), to: Number(state.to) };
      replaceAnnualMetric(summary, "egif_record_count", annual, "records", null, null, range);
      replaceAnnualMetric(summary, "egif_administrative_gif_count", annual, "administrative_gif", null, null, range);
      replaceAnnualMetric(summary, "egif_declared_forest_area_ha", annual, "known_forest_area_sum", "known_forest_area", "unknown_forest_area", range);
      summary.filtered_summary_mode = "EXACT_RUNTIME";
    } else if (summary.source_id === "icv") {
      replaceAnnualMetric(summary, "icv_fire_record_count", result.annual || {}, "records");
      replaceAnnualMetric(summary, "icv_perimeter_count", result.annual || {}, "geometries");
      replaceAnnualMetric(summary, "icv_declared_forest_area_ha", result.annual || {}, "declared_forest_area_sum", "known_area", "unknown_area");
      replaceAnnualMetric(summary, "icv_gif_count", result.annual || {}, "gif");
      summary.filtered_summary_mode = "EXACT_RUNTIME";
    } else if (summary.source_id === "effis") {
      replaceAnnualMetric(summary, "effis_perimeter_count", result.annual || {}, "geometries");
      replaceAnnualMetric(summary, "effis_mapped_area_ha", result.annual || {}, "mapped_area_sum", "known_area", "unknown_area");
      summary.filtered_summary_mode = "EXACT_RUNTIME";
    }
  }
  return clone;
}

function metricRow(territory, metricId) {
  const presentation = METRIC_PRESENTATION[metricId];
  const summary = presentation ? sourceSummary(territory, presentation.source) : null;
  const metric = summary && Array.isArray(summary.metrics) ? summary.metrics.find((row) => row.metric_id === metricId) || null : null;
  return { presentation, summary, metric };
}

export function aggregateMetric(territory, metricId, from, to) {
  const { presentation, summary, metric } = metricRow(territory, metricId);
  if (!presentation || !summary) return { status: "missing", metric_id: metricId };
  if (!summary.coverage || summary.coverage.status !== "available") return { status: "no_source_coverage", metric_id: metricId, source_id: presentation.source };
  if (!metric) return { status: "missing", metric_id: metricId, source_id: presentation.source };
  const start = Math.max(Number(from), summary.year_axis.from);
  const end = Math.min(Number(to), summary.year_axis.to);
  if (start > end) return { status: "outside_coverage", metric_id: metricId, source_id: presentation.source };
  let value = 0;
  let numericValues = 0;
  let known = 0;
  let unknown = 0;
  for (let year = start; year <= end; year += 1) {
    const index = year - summary.year_axis.from;
    const current = metric.values[index];
    if (typeof current === "number" && Number.isFinite(current)) { value += current; numericValues += 1; }
    if (Array.isArray(metric.known_value_count)) known += Number(metric.known_value_count[index] || 0);
    if (Array.isArray(metric.unknown_value_count)) unknown += Number(metric.unknown_value_count[index] || 0);
  }
  return {
    status: numericValues ? "available" : "unknown",
    metric_id: metricId,
    source_id: presentation.source,
    unit: metric.unit,
    value: numericValues ? value : null,
    known_value_count: Array.isArray(metric.known_value_count) ? known : null,
    unknown_value_count: Array.isArray(metric.unknown_value_count) ? unknown : null,
    coverage: summary.coverage,
  };
}

export function availableSeries(territory) {
  const result = [];
  for (const summary of (territory && territory.source_summaries) || []) {
    if (!summary.coverage || summary.coverage.status !== "available") continue;
    for (const metric of summary.metrics || []) {
      if (!HISTOGRAM_METRICS.has(metric.metric_id)) continue;
      const presentation = METRIC_PRESENTATION[metric.metric_id];
      if (presentation) result.push({ id: metric.metric_id, ...presentation, coverage: summary.coverage });
    }
  }
  return result;
}

function seriesExists(series, id) {
  return series.some((row) => row.id === id);
}

function overlaps(state, coverage) {
  return Math.max(Number(state.from), coverage.from) <= Math.min(Number(state.to), coverage.to);
}

export function defaultSeriesId(state, series) {
  const isGva = state.autonomous_community_id === GVA_ID;
  if (isGva && Number(state.from) >= 1993 && Number(state.to) <= 2024 && seriesExists(series, "icv_fire_record_count")) return "icv_fire_record_count";
  if (isGva && Number(state.from) >= 2025 && Number(state.to) <= 2026 && seriesExists(series, "effis_perimeter_count")) return "effis_perimeter_count";
  const egif = series.find((row) => row.id === "egif_record_count");
  if (egif && overlaps(state, egif.coverage)) return egif.id;
  for (const id of ["esfire30_perimeter_count", "icv_fire_record_count", "effis_perimeter_count"]) {
    const row = series.find((entry) => entry.id === id);
    if (row && overlaps(state, row.coverage)) return id;
  }
  return series.length ? series[0].id : null;
}

export function annualSeries(territory, metricId, from = GLOBAL_FROM, to = GLOBAL_TO) {
  const { presentation, summary, metric } = metricRow(territory, metricId);
  const rows = [];
  for (let year = from; year <= to; year += 1) {
    if (!presentation || !summary || !summary.coverage || summary.coverage.status !== "available" || !metric || year < summary.year_axis.from || year > summary.year_axis.to) {
      rows.push({ year, status: "gap", value: null });
      continue;
    }
    const value = metric.values[year - summary.year_axis.from];
    rows.push({ year, status: value == null ? "unknown" : value === 0 ? "zero" : "value", value });
  }
  return rows;
}

export function formatMetricValue(value, unit, { tooltip = false } = {}) {
  if (value == null || !Number.isFinite(Number(value))) return "No disponible";
  const number = Number(value);
  const digits = unit === "ha" && Math.abs(number) < 100 ? 1 : 0;
  const formattedWithoutGrouping = new Intl.NumberFormat("es-ES", { useGrouping: false, maximumFractionDigits: tooltip ? Math.max(digits, 1) : digits }).format(number);
  const parts = formattedWithoutGrouping.split(",");
  const sign = parts[0].startsWith("-") ? "-" : "";
  const integer = (sign ? parts[0].slice(1) : parts[0]).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const formatted = `${sign}${integer}${parts.length > 1 ? `,${parts[1]}` : ""}`;
  return unit === "ha" ? `${formatted} ha` : formatted;
}

export function metricCards(territory, state, recommendedSource) {
  const sourceOrder = recommendedSource === "multi_regime"
    ? ["egif", "esfire30", "icv", "effis"]
    : [recommendedSource, "egif", "esfire30", "icv", "effis"].filter(Boolean);
  const countMetric = { egif: "egif_record_count", esfire30: "esfire30_perimeter_count", icv: "icv_fire_record_count", effis: "effis_perimeter_count" };
  const areaMetric = { egif: "egif_declared_forest_area_ha", icv: "icv_declared_forest_area_ha", effis: "effis_mapped_area_ha" };
  const cards = [];
  for (const source of [...new Set(sourceOrder)]) {
    const metricId = countMetric[source];
    const aggregate = aggregateMetric(territory, metricId, state.from, state.to);
    const summary = sourceSummary(territory, source);
    if (aggregate.status !== "available" || (summary && summary.filtered_summary_mode === "HIDE_WHILE_FILTERED")) continue;
    const presentation = METRIC_PRESENTATION[metricId];
    cards.push({ ...aggregate, label: presentation.card, source_label: presentation.sourceLabel });
    if (cards.length === 4) return cards;
  }
  for (const source of [...new Set(sourceOrder)]) {
    if (!areaMetric[source]) continue;
    const metricId = areaMetric[source];
    const aggregate = aggregateMetric(territory, metricId, state.from, state.to);
    const summary = sourceSummary(territory, source);
    if (aggregate.status !== "available" || (summary && summary.filtered_summary_mode === "HIDE_WHILE_FILTERED")) continue;
    const presentation = METRIC_PRESENTATION[metricId];
    cards.push({ ...aggregate, label: presentation.card, source_label: presentation.sourceLabel });
    if (cards.length === 4) return cards;
  }
  return cards;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function yearLabel(row, presentation, territoryName) {
  if (row.status === "gap" || row.status === "unknown") return `${row.year}: no disponemos de este tipo de dato para este año. ${presentation.sourceLabel}.`;
  const value = formatMetricValue(row.value, presentation.unit, { tooltip: true });
  const noun = row.value === 1 ? presentation.singular : presentation.plural;
  return `${row.year}: ${value}${presentation.unit === "ha" ? "" : ` ${noun}`}. Fuente: ${presentation.sourceLabel}. ${territoryName}.`;
}

export function createMetricsHistogramUi({ runtime, loader }) {
  const cardsNode = document.querySelector("#summary-cards");
  const statusNode = document.querySelector("#summary-loading-status");
  const secondary = document.querySelector("#summary-secondary-metrics");
  const secondaryDetails = document.querySelector("#summary-more-data");
  const tabsNode = document.querySelector("#histogram-series-tabs");
  const chartNode = document.querySelector("#histogram-chart");
  const ticksNode = document.querySelector("#histogram-ticks");
  const tooltipNode = document.querySelector("#histogram-tooltip");
  const tableBody = document.querySelector("#histogram-data-body");
  const histogramStatus = document.querySelector("#histogram-status");
  const timelineSlot = document.querySelector("#timeline-slot");
  let current = null;
  let selectedSeriesId = null;
  let explicitSeries = false;
  let updateGeneration = 0;
  let lastTerritoryId = null;
  let pendingKey = null;

  function renderSecondary(territory, state) {
    secondary.replaceChildren();
    const entries = [];
    for (const metricId of ["egif_administrative_gif_count", "icv_gif_count", "icv_perimeter_count"]) {
      const metric = aggregateMetric(territory, metricId, state.from, state.to);
      if (metric.status !== "available") continue;
      entries.push([`${METRIC_PRESENTATION[metricId].card} · ${METRIC_PRESENTATION[metricId].sourceLabel}`, formatMetricValue(metric.value, metric.unit)]);
    }
    for (const metricId of ["egif_declared_forest_area_ha", "icv_declared_forest_area_ha", "effis_mapped_area_ha"]) {
      const metric = aggregateMetric(territory, metricId, state.from, state.to);
      if (metric.status !== "available" || metric.known_value_count == null) continue;
      const total = metric.known_value_count + metric.unknown_value_count;
      entries.push([`Cobertura de superficie · ${METRIC_PRESENTATION[metricId].sourceLabel}`, `${formatMetricValue(metric.known_value_count, "records")} de ${formatMetricValue(total, "records")} registros con valor conocido`]);
    }
    for (const [label, value] of entries) {
      const dt = element("dt", null, label); const dd = element("dd", null, value); secondary.append(dt, dd);
    }
    secondaryDetails.hidden = entries.length === 0;
  }

  function renderCards(territory, state, view) {
    cardsNode.replaceChildren();
    const cards = metricCards(territory, state, view.primary);
    for (const card of cards) {
      const article = element("article", `summary-card summary-card--${card.source_id}`);
      const value = element("strong", null, formatMetricValue(card.value, card.unit));
      const label = element("span", "summary-card__label", card.label);
      const source = element("small", "summary-card__source", `Fuente: ${card.source_label}`);
      article.append(value, label, source); cardsNode.append(article);
    }
    const egifCount = aggregateMetric(territory, "egif_record_count", state.from, state.to);
    const egifStatus = document.querySelector("#egif-human-status");
    if (egifStatus) egifStatus.textContent = egifCount.status === "available"
      ? `${formatMetricValue(egifCount.value, egifCount.unit)} registros administrativos de incendios · EGIF.`
      : "Los registros EGIF no están disponibles para este territorio y periodo.";
    renderSecondary(territory, state);
    const includes2026Effis = cards.some((card) => card.source_id === "effis") && Number(state.to) >= 2026;
    const filteredModes = (territory.source_summaries || []).filter((row) => row.filtered_summary_mode && row.filtered_summary_mode !== "NOT_FILTERED");
    const filteredZero = cards.some((card) => card.value === 0 && filteredModes.some((row) => row.source_id === card.source_id && (row.filtered_summary_mode === "EXACT_RUNTIME" || row.filtered_summary_mode === "EXACT_DERIVED")));
    statusNode.textContent = filteredZero
      ? "No hay resultados que cumplan estos filtros en la fuente indicada. Las demás fuentes permanecen independientes."
      : filteredModes.some((row) => row.filtered_summary_mode === "HIDE_WHILE_FILTERED")
      ? "Una métrica filtrada se oculta porque el resumen no puede calcularla exactamente en este ámbito. Las demás fuentes no cambian."
      : filteredModes.length ? "Resultados filtrados únicamente en la fuente indicada; las fuentes no se suman ni se enlazan." : includes2026Effis
      ? "Datos EFFIS 2026 correspondientes al snapshot de 19/08/2026; no representan el cierre anual."
      : cards.length ? "Cada cifra corresponde a la fuente indicada; no se suman fuentes distintas." : "No hay métricas disponibles para este territorio y periodo.";
  }

  function showTooltip(text) { tooltipNode.textContent = text; }

  function renderHistogram(territory, state) {
    const series = availableSeries(territory);
    if (!seriesExists(series, selectedSeriesId)) {
      selectedSeriesId = defaultSeriesId(state, series);
      explicitSeries = false;
    }
    tabsNode.replaceChildren();
    for (const row of series) {
      const button = element("button", "histogram-tab", row.tab);
      button.type = "button"; button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(row.id === selectedSeriesId));
      button.dataset.metricId = row.id;
      button.addEventListener("click", () => { selectedSeriesId = row.id; explicitSeries = true; renderHistogram(territory, runtime.getState()); });
      tabsNode.append(button);
    }
    chartNode.replaceChildren(); ticksNode.replaceChildren(); tableBody.replaceChildren();
    if (!selectedSeriesId) {
      histogramStatus.textContent = "No disponemos de una serie anual para este territorio.";
      timelineSlot.dataset.status = "no-data";
      return;
    }
    const presentation = METRIC_PRESENTATION[selectedSeriesId];
    const rows = annualSeries(territory, selectedSeriesId);
    const maximum = Math.max(0, ...rows.filter((row) => typeof row.value === "number").map((row) => row.value));
    const territoryName = territory.territory.official_name;
    for (const row of rows) {
      const button = element("button", `histogram-bar histogram-bar--${row.status}`);
      button.type = "button";
      button.dataset.year = String(row.year);
      button.style.setProperty("--bar-size", `${maximum > 0 && row.value > 0 ? Math.max(2, (row.value / maximum) * 100) : 0}%`);
      if (row.year >= Number(state.from) && row.year <= Number(state.to)) button.classList.add("is-in-range");
      const label = yearLabel(row, presentation, territoryName);
      button.setAttribute("aria-label", label); button.title = label;
      button.addEventListener("mouseenter", () => showTooltip(label));
      button.addEventListener("focus", () => showTooltip(label));
      button.addEventListener("click", async () => {
        document.querySelector("#from-year").value = String(row.year);
        document.querySelector("#to-year").value = String(row.year);
        showTooltip(`Actualizando el periodo a ${row.year}…`);
        await runtime.applyYears();
        await update(runtime.getState(), null, { force: true });
      });
      chartNode.append(button);
      const tr = element("tr"); tr.append(element("th", null, String(row.year)), element("td", null, label)); tableBody.append(tr);
    }
    const tickYears = new Set([1968, 1980, 1990, 2000, 2010, 2020, 2026]);
    for (let year = GLOBAL_FROM; year <= GLOBAL_TO; year += 1) ticksNode.append(element("span", tickYears.has(year) ? "is-labelled" : null, tickYears.has(year) ? String(year) : ""));
    const selectedSourceSummary = sourceSummary(territory, presentation.source);
    const mode = selectedSourceSummary && selectedSourceSummary.filtered_summary_mode;
    histogramStatus.textContent = mode === "HIDE_WHILE_FILTERED"
      ? `${presentation.tab} · ${presentation.sourceLabel}. El filtro activo no se aplica a esta serie porque no puede calcularse exactamente.`
      : `${presentation.tab} · ${presentation.sourceLabel}${mode === "EXACT_RUNTIME" || mode === "EXACT_DERIVED" ? " · filtrado exacto" : ""}. Una barra por año; el sombreado indica ${state.from === state.to ? state.from : `${state.from}–${state.to}`}.`;
    timelineSlot.dataset.status = "ready";
  }

  async function update(state, view = null, { force = false } = {}) {
    const territoryId = state.municipality_id || state.province_id || state.autonomous_community_id || "ES";
    const key = `${territoryId}|${state.from}|${state.to}|${state.egif_visible}|${state.esfire30_visible}|${state.icv_visible}|${state.effis_visible}|${filterKey(state.filters || [])}`;
    if (!force && pendingKey === key) return;
    pendingKey = key;
    const generation = ++updateGeneration;
    statusNode.textContent = "Cargando el resumen de este territorio…";
    timelineSlot.dataset.status = "loading";
    const result = await loader.loadTerritory(state);
    if (generation !== updateGeneration || result.status === "stale") {
      if (generation === updateGeneration) pendingKey = null;
      return;
    }
    if (result.status === "error") {
      current = result; cardsNode.replaceChildren(); secondary.replaceChildren(); secondaryDetails.hidden = true;
      statusNode.textContent = "No se ha podido cargar el resumen de este territorio.";
      histogramStatus.textContent = "La evolución temporal no está disponible. El mapa sigue funcionando.";
      chartNode.replaceChildren(); tabsNode.replaceChildren(); timelineSlot.dataset.status = "error";
      pendingKey = null;
      return;
    }
    if (territoryId !== lastTerritoryId) {
      const nextSeries = availableSeries(result.territory);
      if (!explicitSeries || !seriesExists(nextSeries, selectedSeriesId)) {
        selectedSeriesId = defaultSeriesId(state, nextSeries);
        explicitSeries = false;
      }
      lastTerritoryId = territoryId;
    }
    const effectiveTerritory = applyRuntimeFiltersToTerritory(result.territory, state, runtime);
    current = { ...result, territory: effectiveTerritory };
    const defaultId = defaultSeriesId(state, availableSeries(effectiveTerritory));
    const fallbackView = { primary: defaultId ? defaultId.split("_")[0] : "egif" };
    renderCards(effectiveTerritory, state, view || fallbackView);
    renderHistogram(effectiveTerritory, state);
    pendingKey = null;
  }

  return {
    update,
    getState: () => ({ selected_series_id: selectedSeriesId, explicit_series: explicitSeries, result: current, telemetry: { ...loader.telemetry } }),
    selectSeries(metricId) { selectedSeriesId = metricId; explicitSeries = true; if (current && current.territory) renderHistogram(current.territory, runtime.getState()); },
    destroy() { loader.cancel(); updateGeneration += 1; },
  };
}

export { GLOBAL_FROM, GLOBAL_TO };

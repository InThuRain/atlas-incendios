const PRESETS = [10, 100, 500, 1000];

function node(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text != null) result.textContent = text;
  return result;
}

function valueLabel(contract, value) {
  if (contract.filter_type === "min_value") return `${contract.source.toUpperCase()} · ≥${new Intl.NumberFormat("es-ES").format(value)} ha`;
  if (contract.filter_type === "flag") return `${contract.source.toUpperCase()} · GIF`;
  const choice = (contract.values || []).find((row) => row.value === value);
  return `${contract.source.toUpperCase()} · Causa: ${(choice && choice.label) || value}`;
}

function filterFromControl(contract, control) {
  let value;
  if (contract.filter_type === "flag") {
    if (!control.checked) return null;
    value = true;
  } else if (contract.filter_type === "enum") {
    if (!control.value) return null;
    value = control.value;
  } else {
    value = Number(control.value);
    if (!Number.isFinite(value) || value <= 0) return null;
  }
  return {
    filter_id: contract.filter_id,
    filter_type: contract.filter_type,
    source: contract.source,
    metric_id: contract.metric_id,
    value,
    unit: contract.unit,
  };
}

function minAreaControl(contract, current) {
  const wrapper = node("div", "filter-control filter-control--area");
  const label = node("label", null, contract.label);
  const input = document.createElement("input");
  input.type = "number"; input.min = "0.01"; input.max = "1000000"; input.step = "0.01";
  input.inputMode = "decimal"; input.dataset.filterId = contract.filter_id;
  input.value = current ? String(current.value) : "";
  input.placeholder = "Sin mínimo";
  label.append(input);
  const presets = node("div", "filter-presets");
  for (const value of PRESETS) {
    const button = node("button", null, `${new Intl.NumberFormat("es-ES").format(value)} ha`);
    button.type = "button"; button.dataset.presetFor = contract.filter_id; button.dataset.value = String(value);
    button.setAttribute("aria-label", `${contract.label}: mínimo ${value} hectáreas`);
    presets.append(button);
  }
  wrapper.append(label, presets, node("small", null, "Los registros sin una magnitud conocida quedan fuera; desconocido no equivale a 0 ha."));
  return wrapper;
}

function simpleControl(contract, current) {
  const wrapper = node("div", "filter-control");
  const label = document.createElement("label");
  let input;
  if (contract.filter_type === "flag") {
    input = document.createElement("input"); input.type = "checkbox"; input.checked = Boolean(current);
    label.append(input, document.createTextNode(" Grandes incendios forestales (GIF)"));
    const help = contract.source === "icv"
      ? "ICV · criterio documentado de 500 ha de superficie forestal declarada."
      : "EGIF · clasificación administrativa registrada por la fuente.";
    wrapper.append(label, node("small", null, help));
  } else {
    label.textContent = contract.label;
    input = document.createElement("select");
    const none = document.createElement("option"); none.value = ""; none.textContent = "Todas las causas"; input.append(none);
    for (const choice of contract.values || []) {
      const option = document.createElement("option"); option.value = choice.value; option.textContent = choice.label; input.append(option);
    }
    input.value = (current && current.value) || ""; label.append(input); wrapper.append(label);
  }
  input.dataset.filterId = contract.filter_id;
  return wrapper;
}

export function createSafeFiltersUi({ runtime, onChange = () => {} }) {
  const openButton = document.querySelector("#open-filters");
  const panel = document.querySelector("#filter-panel");
  const closeButton = document.querySelector("#close-filters");
  const form = document.querySelector("#safe-filter-form");
  const groups = document.querySelector("#safe-filter-groups");
  const chips = document.querySelector("#active-filter-chips");
  const clear = document.querySelector("#clear-filters");
  const status = document.querySelector("#filter-status");
  if (!openButton || !panel || !form || !groups || !chips) throw new Error("Falta el contrato DOM de filtros seguros");
  let contracts = [];
  let busy = false;

  function setOpen(value) {
    panel.hidden = !value;
    openButton.setAttribute("aria-expanded", String(value));
    if (value) (panel.querySelector("input, select, button") || panel).focus();
  }

  function render() {
    const state = runtime.getState();
    contracts = runtime.getFilterContracts();
    const active = state.filters || [];
    const byId = new Map(active.map((row) => [row.filter_id, row]));
    groups.replaceChildren();
    const bySource = new Map();
    for (const contract of contracts) {
      if (!bySource.has(contract.source)) bySource.set(contract.source, []);
      bySource.get(contract.source).push(contract);
    }
    for (const [source, rows] of bySource) {
      const fieldset = document.createElement("fieldset");
      const legend = node("legend", null, source === "icv" ? "ICV · Generalitat Valenciana" : source.toUpperCase());
      fieldset.append(legend);
      for (const contract of rows) fieldset.append(contract.filter_type === "min_value"
        ? minAreaControl(contract, byId.get(contract.filter_id))
        : simpleControl(contract, byId.get(contract.filter_id)));
      groups.append(fieldset);
    }
    if (!contracts.length) groups.append(node("p", "filter-empty", "No hay filtros seguros disponibles para este territorio y periodo."));
    chips.replaceChildren();
    for (const filter of active) {
      const contract = contracts.find((row) => row.filter_id === filter.filter_id);
      if (!contract) continue;
      const button = node("button", "filter-chip", `${valueLabel(contract, filter.value)} ×`);
      button.type = "button"; button.dataset.removeFilter = filter.filter_id;
      button.setAttribute("aria-label", `Quitar filtro ${valueLabel(contract, filter.value)}`);
      chips.append(button);
    }
    clear.hidden = active.length === 0;
    openButton.textContent = active.length ? `Filtros · ${active.length}` : "Filtros";
    openButton.dataset.count = String(active.length);
    const notice = runtime.getFilterNotice ? runtime.getFilterNotice() : "";
    if (notice) status.textContent = notice;
  }

  async function apply() {
    if (busy) return;
    busy = true; status.textContent = "Aplicando filtros…";
    const state = runtime.getState();
    const values = [...form.querySelectorAll("[data-filter-id]")];
    const controls = new Map(values.map((control) => [control.dataset.filterId, control]));
    try {
      const desired = contracts.map((contract) => filterFromControl(contract, controls.get(contract.filter_id))).filter(Boolean);
      const desiredIds = new Set(desired.map((row) => row.filter_id));
      for (const active of state.filters || []) if (contracts.some((row) => row.filter_id === active.filter_id) && !desiredIds.has(active.filter_id)) await runtime.removeAnalysisFilter(active.filter_id);
      for (const filter of desired) await runtime.setAnalysisFilter(filter);
      const failed = desired.some((filter) => {
        const getter = filter.source === "egif" ? runtime.getEgifResult : filter.source === "icv" ? runtime.getIcvResult : runtime.getEffisResult;
        return getter && getter().status === "error";
      });
      if (failed) throw new Error("filter source unavailable");
      status.textContent = desired.length ? "Filtros aplicados únicamente a la fuente indicada." : "Filtros retirados.";
      render(); await onChange();
      if (matchMedia("(max-width: 760px)").matches) setOpen(false);
    } catch (_error) {
      status.textContent = "No se han podido aplicar estos filtros. El mapa y las demás fuentes siguen disponibles.";
    } finally { busy = false; }
  }

  form.addEventListener("submit", (event) => { event.preventDefault(); apply(); });
  groups.addEventListener("click", (event) => {
    const preset = event.target.closest("[data-preset-for]");
    if (!preset) return;
    const input = groups.querySelector(`[data-filter-id="${preset.dataset.presetFor}"]`);
    if (input) input.value = preset.dataset.value;
  });
  chips.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-remove-filter]");
    if (!button) return;
    await runtime.removeAnalysisFilter(button.dataset.removeFilter); render(); await onChange();
  });
  clear.addEventListener("click", async () => { await runtime.clearAnalysisFilters(); status.textContent = "Filtros retirados."; render(); await onChange(); });
  openButton.addEventListener("click", () => setOpen(panel.hidden));
  if (closeButton) closeButton.addEventListener("click", () => setOpen(false));
  render();
  return { render, open: () => setOpen(true), close: () => setOpen(false), getState: () => ({ open: !panel.hidden, contracts: contracts.map((row) => row.filter_id), filters: runtime.getState().filters || [] }) };
}

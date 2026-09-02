function valuesFrom(list) {
  const result = new Map();
  if (!list) return result;
  const children = [...list.children];
  for (let index = 0; index + 1 < children.length; index += 2) {
    if (children[index].tagName === "DT" && children[index + 1].tagName === "DD") {
      result.set(children[index].textContent.trim(), children[index + 1].textContent.trim());
    }
  }
  return result;
}

function useful(value) {
  return Boolean(value) && !/^(no disponible|no det\.|no mapeada|unmapped|null|undefined|unknown)$/i.test(value.trim());
}

function humanDate(value) {
  if (!useful(value)) return null;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
}

function addRows(target, rows) {
  target.replaceChildren();
  for (const [label, raw] of rows) {
    const value = label.startsWith("Fecha") ? humanDate(raw) : raw;
    if (!useful(value)) continue;
    const dt = document.createElement("dt"); dt.textContent = label;
    const dd = document.createElement("dd"); dd.textContent = value;
    target.append(dt, dd);
  }
}

function currentTerritory() {
  const values = [...document.querySelectorAll("#territory-breadcrumb button")].map((row) => row.textContent.trim()).filter(Boolean);
  return values.length ? values.join(" / ") : "España";
}

function syncEgif() {
  const raw = valuesFrom(document.querySelector("#egif-detail-fields"));
  const target = document.querySelector("#egif-human-detail-fields");
  if (!target) return;
  const municipality = raw.get("Municipio");
  const unresolved = municipality && /no resuelto/i.test(municipality);
  addRows(target, [
    ["Fecha de inicio", raw.get("Fecha de inicio")], ["Fecha de extinción", raw.get("Fecha de extinción")],
    ["Año", raw.get("Año")], ["Municipio", unresolved ? null : municipality], ["Provincia", raw.get("Provincia")],
    ["Paraje", raw.get("Paraje declarado")], ["Superficie forestal declarada", raw.get("Superficie forestal declarada")],
    ["Gran incendio forestal (GIF)", raw.get("GIF")],
  ]);
  const note = document.querySelector("#egif-human-note");
  if (note) note.textContent = unresolved ? "No se ha podido vincular este registro con un municipio actual." : "Registro administrativo EGIF; no dispone de un perímetro individual.";
}

function syncIcv() {
  const raw = valuesFrom(document.querySelector("#icv-detail-fields"));
  const target = document.querySelector("#icv-human-detail-fields");
  if (!target) return;
  addRows(target, [
    ["Fecha de inicio", raw.get("Fecha de inicio")], ["Fecha de extinción", raw.get("Fecha de extinción")], ["Año", raw.get("Año")],
    ["Municipio", raw.get("Municipio declarado")], ["Provincia", raw.get("Provincia declarada")], ["Paraje", raw.get("Paraje")],
    ["Superficie forestal declarada", raw.get("Superficie forestal declarada")], ["Causa", raw.get("Causa documentada")],
    ["Gran incendio forestal (GIF)", raw.get("GIF")], ["Perímetros documentados", raw.get("Geometrías de este registro") || raw.get("Geometrías documentadas")],
  ]);
  const count = Number(raw.get("Geometrías de este registro") || raw.get("Geometrías documentadas"));
  const note = document.querySelector("#icv-human-note");
  if (note) note.textContent = Number.isInteger(count) && count > 1
    ? `Un único incendio documentado por ICV dispone de ${count} perímetros; no se cuenta como ${count} incendios.`
    : "Incendio y perímetro oficial documentados por la Generalitat Valenciana / ICV.";
}

function syncEffis() {
  const raw = valuesFrom(document.querySelector("#effis-detail-fields"));
  addRows(document.querySelector("#effis-human-detail-fields"), [
    ["Fecha", raw.get("Fecha EFFIS")], ["Fecha final", raw.get("Fecha final EFFIS")], ["Año", raw.get("Año")],
    ["Municipio", raw.get("Municipio/commune declarado")], ["Provincia", raw.get("Provincia declarada")],
    ["Área cartografiada", raw.get("Superficie cartografiada")], ["Snapshot de datos", raw.get("Snapshot")],
  ]);
}

function syncEsfire(runtime) {
  const selection = document.querySelector("#selection-summary");
  const raw = selection ? selection.textContent : "";
  const target = document.querySelector("#selection-human-detail-fields");
  const summary = document.querySelector("#selection-human-summary");
  const selected = raw.includes("geometry_id:");
  const yearMatch = raw.match(/año:\s*([^·]+)/i);
  const year = yearMatch && yearMatch[1] ? yearMatch[1].trim() : null;
  if (target) addRows(target, [["Año", year], ["Territorio consultado", selected ? currentTerritory() : null], ["Fuente", selected ? "ESFire30" : null]]);
  if (summary) summary.textContent = selected
    ? "Perímetro obtenido mediante imágenes Landsat. No constituye cartografía oficial."
    : "Pulsa o toca un perímetro para conocer su año y procedencia.";
  const card = document.querySelector('[data-detail-card="esfire30"]');
  if (card) card.dataset.hasSelection = String(Boolean(runtime.getState().selected_geometry_id));
}

export function createHumanDetailsUi({ runtime }) {
  let keyboardPending = false;
  let previousSelections = "";
  const recordBrowser = document.querySelector("#egif-record-browser");
  const map = document.querySelector("#map");
  if (recordBrowser) recordBrowser.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") keyboardPending = true; });
  if (map) map.addEventListener("pointerdown", () => { keyboardPending = false; });
  document.querySelectorAll("[data-detail-close]").forEach((button) => button.addEventListener("click", () => runtime.clearSourceSelection(button.dataset.detailClose)));
  document.querySelectorAll("[data-detail-minimize]").forEach((button) => button.addEventListener("click", () => {
    const card = button.closest(".human-detail");
    const minimized = !card.classList.contains("is-minimized");
    card.classList.toggle("is-minimized", minimized); button.setAttribute("aria-expanded", String(!minimized));
  }));

  function sync() {
    syncEgif(); syncIcv(); syncEffis(); syncEsfire(runtime);
    const state = runtime.getState();
    const signature = [state.selected_egif_record_id, state.selected_geometry_id, state.selected_icv_geometry_id || state.selected_icv_record_id, state.selected_effis_geometry_id].join("|");
    if (keyboardPending && signature !== previousSelections) {
      const source = state.selected_egif_record_id ? "egif" : state.selected_icv_geometry_id || state.selected_icv_record_id ? "icv" : state.selected_effis_geometry_id ? "effis" : state.selected_geometry_id ? "esfire30" : null;
      const heading = document.querySelector(`[data-detail-card="${source}"] h3`);
      if (heading) heading.focus({ preventScroll: false });
      keyboardPending = false;
    }
    previousSelections = signature;
  }
  sync();
  return { sync, getState: () => ({ selections: previousSelections, mobile_sheet: matchMedia("(max-width: 760px)").matches }) };
}

export { humanDate };

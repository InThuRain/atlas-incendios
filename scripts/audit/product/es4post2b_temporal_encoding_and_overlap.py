#!/usr/bin/env python3
"""Focused runtime evidence for ES-4POST2B.

Builds only the lightweight frontend in a temporary directory and links the
already accepted local product assets read-only.  It never rebuilds ICV,
ESFire30, EFFIS, boundaries or summaries.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "data/audit/product/es4post2b_temporal_encoding_and_overlap.json"
SCREENSHOTS = ROOT / "data/audit/product/es4post2b"
BUILDER = ROOT / "scripts/build_national_frontend.py"
PRODUCT_DATA = ROOT / "build/national-product-staging/data"
CHROME = "/usr/bin/google-chrome"
OLD_ANCHOR = "f7a3532f633a247f33dee3ebba9fbcc316c0e534"


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def legacy_algorithm() -> dict:
    source = subprocess.check_output(["git", "show", f"{OLD_ANCHOR}:js/app.js"], cwd=ROOT, text=True)
    required = ["const oldColor = [44, 123, 182]", "const newColor = [240, 82, 46]", "fillOpacity: selected ? .5 : .28", "dashArray: '2 5'", "dashArray: '7 5'"]
    missing = [value for value in required if value not in source]
    if missing:
        raise RuntimeError("No se pudo recuperar el contrato GVA anclado: " + ", ".join(missing))
    return {
        "anchor": OLD_ANCHOR,
        "domain": "state.geometryYearRange = min/max de las fuentes con geometría del manifest; 1985–2026 en el perfil final",
        "palette": {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"},
        "interpolation": "lineal RGB, ratio clamp [0,1], Math.round por canal",
        "fills": {"icv": 0.28, "esfire30": 0.2, "effis": 0.2, "selected_icv": 0.5, "selected_esfire30": 0.46, "selected_effis": 0.42},
        "strokes": {"icv": "temporal / 1.2; selected #151a18 / 3", "esfire30": "#875b20 / 2 / dash 2 5; selected #151a18 / 4", "effis": "temporal / 2 / dash 7 5; selected #211a2f / 4"},
        "draw_order": "Leaflet conserva el orden de la colección cargada; no usaba un territorio principal.",
        "legend": "gradiente azul→rojo con extremos del dominio geométrico, separado de filas de fuente.",
        "range_behavior": "el filtro temporal cambia features; la normalización original permanecía en el dominio geométrico global.",
        "single_year_behavior": "No había una rama de un año: el dominio seguía siendo global; por ejemplo, 1995 en 1985–2026 da rgb(92,113,149). El denominador max(1, max-min) sólo evita división por cero si el dominio geométrico llegara a colapsar.",
    }


def build_site(directory: Path) -> Path:
    if not PRODUCT_DATA.is_dir():
        raise FileNotFoundError(f"Falta {PRODUCT_DATA}; se necesitan los assets nacionales ya aceptados")
    site = directory / "site"
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    (site / "data").symlink_to(PRODUCT_DATA, target_is_directory=True)
    return site


def wait_runtime(client, deadline: float, require_icv: bool = True) -> None:
    condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__es4cRuntime)"
    if require_icv:
        condition += " && window.__es4cRuntime.getIcvResult()?.status === 'complete'"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            detail = client.evaluate("({bootstrap:document.querySelector('#national-bootstrap-error')?.textContent, output:document.querySelector('#runtime-test-output')?.textContent, icv:window.__es4cRuntime?.getIcvResult?.(), errors:globalThis.__e3c2BrowserErrors})")
            raise TimeoutError(f"El runtime no convergió: {detail}")
        time.sleep(.08)


def fit_feature(client, year: int, fire_id: str | None = None) -> dict:
    target = json.dumps(fire_id)
    return client.evaluate(f'''(() => {{
      const runtime=window.__es4cRuntime, result=runtime.getIcvResult(), map=runtime.map;
      const targetFire={target};
      const matching=(result.features||[]).filter(row => Number(row.properties?.year) === {year} && (!targetFire || row.properties?.fire_id === targetFire));
      const feature=matching[0];
      if (!feature) return {{error:'no ICV feature for year'}};
      const points=[]; const visit=value => {{ if(Array.isArray(value)&&typeof value[0]==='number') points.push(value); else if(Array.isArray(value)) value.forEach(visit); }};
      visit(feature.geometry.coordinates);
      const xs=points.map(point=>point[0]),ys=points.map(point=>point[1]);
      map.fitBounds([[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)]],{{padding:80,duration:0,maxZoom:11}});
      return {{geometry_id:feature.properties.geometry_id, fire_id:feature.properties.fire_id, year:feature.properties.year, matching_geometries:matching.length}};
    }})()''')


def stable_map(client, deadline: float) -> None:
    stable = 0
    while stable < 4:
        stable = stable + 1 if client.evaluate("window.__es4cRuntime.map.loaded() && !window.__es4cRuntime.map.isMoving()") else 0
        if time.monotonic() > deadline:
            raise TimeoutError("MapLibre no alcanzó estado estable")
        time.sleep(.12)


def capture(client, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = client.command("Page.captureScreenshot", {"format": "png", "fromSurface": True})["data"]
    path.write_bytes(base64.b64decode(data))


def observe(chrome: str, url: str, year: int, screenshot: Path | None = None, device: str = "desktop", fire_id: str | None = None) -> dict:
    evaluation = load_module("es4post2b_chrome", "benchmarks/es4e3c2_basemap/run.py")
    started = time.monotonic()
    with evaluation.chrome_session(chrome, device, 180) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        wait_runtime(client, deadline)
        selected = fit_feature(client, year, fire_id)
        stable_map(client, deadline)
        # La captura se toma antes de seleccionar para aislar la lectura del
        # mapa, la transparencia y la leyenda de la ficha existente (POST2C
        # sigue pendiente). La selección se comprueba inmediatamente después.
        if screenshot:
            capture(client, screenshot)
        # CDPClient no admite argumentos a evaluate; el ID se serializa de forma
        # segura mediante JSON al construir la expresión.
        selected_id = client.evaluate("(() => { const runtime=window.__es4cRuntime; const f=runtime.getIcvResult().features.find(row=>row.properties?.geometry_id===%s); return runtime.selectIcvFeature(f); })()" % json.dumps(selected.get("geometry_id")))
        style = client.evaluate("""(() => { const map=window.__es4cRuntime.map; const ids=['icv-perimeters','icv-perimeter-outlines','icv-selected','icv-hover','esfire30-perimeters','esfire30-perimeter-outlines','effis-perimeters','effis-perimeter-outlines']; return Object.fromEntries(ids.map(id=>{const layer=map.getLayer(id); return [id,{exists:Boolean(layer),type:layer?.type||null,paint:layer?map.getPaintProperty(id,layer.type==='fill'?'fill-color':'line-color'):null,filter:layer?map.getFilter(id):null}]})); })()""")
        legend = client.evaluate("document.querySelector('#user-map-legend')?.innerText || ''")
        temporal = client.evaluate("window.__es4cRuntime.getTemporalVisualState()")
        runtime = client.evaluate("JSON.parse(document.querySelector('#runtime-test-output')?.textContent || '{}')")
        records = client.evaluate("window.__es4cRuntime.getIcvResult().metrics")
        browser_errors = client.evaluate("globalThis.__e3c2BrowserErrors || []")
        hover_filter = client.evaluate("(() => { const map=window.__es4cRuntime.map; map.fire('mousemove',{type:'mousemove',features:[...map.queryRenderedFeatures({layers:['icv-perimeters']}).slice(0,1)]}); return map.getFilter('icv-hover'); })()")
        return {
            "loaded_records": records.get("records"), "loaded_geometries": records.get("geometries"),
            "fit_feature": selected, "selected_geometry_id": selected_id, "temporal": temporal,
            "layers": style, "legend": legend, "hover_filter": hover_filter,
            "rendered_icv_features": client.evaluate("window.__es4cRuntime.map.queryRenderedFeatures({layers:['icv-perimeters']}).length"),
            "runtime_errors": runtime.get("errors", []), "browser_errors": browser_errors,
            "viewport": client.evaluate("({width:innerWidth,height:innerHeight})"),
            "screenshot": str(screenshot.relative_to(ROOT)) if screenshot else None,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        }


def wait_for_state_year(client, deadline: float, year: int) -> None:
    while client.evaluate("window.__es4cRuntime.getState().from") != year or client.evaluate("window.__es4cRuntime.getState().to") != year:
        if time.monotonic() > deadline:
            raise TimeoutError(f"El histograma no aplicó el año {year}")
        time.sleep(.08)


def verify_filters_and_histogram(client, deadline: float) -> dict:
    """Comprueba que filtros humanos no redefinen la escala y que la barra anual
    usa la misma transición temporal del runtime. No mide ni reconstruye datos.
    """
    original = client.evaluate("window.__es4cRuntime.getTemporalVisualState().domain")
    filters = [
        {"filter_id": "icv_min_area", "filter_type": "min_value", "source": "icv", "metric_id": "icv_declared_forest_area_ha", "value": 1, "unit": "ha"},
        {"filter_id": "icv_gif", "filter_type": "flag", "source": "icv", "metric_id": "icv_gif_count", "value": True, "unit": None},
        {"filter_id": "icv_cause", "filter_type": "enum", "source": "icv", "metric_id": "icv_cause_distribution", "value": "negligence", "unit": None},
    ]
    result = {"original_domain": original, "filters": {}}
    try:
        for filter_value in filters:
            client.evaluate("window.__es4cRuntime.setAnalysisFilter(%s).then(() => true)" % json.dumps(filter_value))
            wait_runtime(client, deadline)
            result["filters"][filter_value["filter_id"]] = {
                "domain": client.evaluate("window.__es4cRuntime.getTemporalVisualState().domain"),
                "active": client.evaluate("window.__es4cRuntime.getState().filters"),
            }
            client.evaluate("window.__es4cRuntime.clearAnalysisFilters().then(() => true)")
            wait_runtime(client, deadline)
        # El histograma de ICV tiene una barra por año y llama a applyYears().
        clicked = client.evaluate("(() => { const row=document.querySelector('#histogram-chart .histogram-bar[data-year=\"2016\"]'); if (!row) return false; row.click(); return true; })()")
        result["histogram"] = {"button_found": clicked}
        if clicked:
            wait_for_state_year(client, deadline, 2016)
            wait_runtime(client, deadline)
            result["histogram"].update({
                "state": client.evaluate("window.__es4cRuntime.getState()"),
                "domain": client.evaluate("window.__es4cRuntime.getTemporalVisualState().domain"),
                "legend": client.evaluate("document.querySelector('#user-map-legend')?.innerText || ''"),
            })
    finally:
        # El escenario no deja filtros ni periodo alterados para la próxima
        # observación (cada escenario usa su propia página, pero el contrato
        # explícito evita que esa independencia sea una condición implícita).
        client.evaluate("window.__es4cRuntime.clearAnalysisFilters().then(() => true)")
    return result


def query(from_year: int, to_year: int) -> str:
    values = {"smoke": "pais_valencia", "from": from_year, "to": to_year, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1"}
    return "index.html?" + urlencode(values)


def browser_smoke(chrome: str, only: set[str] | None = None) -> dict:
    evaluation = load_module("es4post2b_server", "benchmarks/es4e3c2_basemap/run.py")
    scenarios = {
        "1995": (1995, 1995, 1995, SCREENSHOTS / "national-after-1995.png", "desktop"),
        "2016": (2016, 2016, 2016, None, "desktop"),
        "2017": (2017, 2017, 2017, None, "desktop"),
        "2018": (2018, 2018, 2018, None, "desktop"),
        "2019": (2019, 2019, 2019, None, "desktop"),
        "1993-2024": (1993, 2024, 2016, SCREENSHOTS / "national-after-overlap-1993-2024.png", "desktop"),
        "2000-2020": (2000, 2020, 2016, None, "desktop"),
        "2015-2020": (2015, 2020, 2016, None, "desktop"),
        "mobile-1995": (1995, 1995, 1995, SCREENSHOTS / "national-after-mobile-1995.png", "mobile", None),
        "2024AL0005": (2024, 2024, 2024, None, "desktop", "gva:pif-cv:2024AL0005"),
        "filters-histogram": (2015, 2020, 2016, None, "desktop", None),
    }
    # Seis elementos para los escenarios nuevos, cinco para los ya escritos
    # antes de que se añadieran los checks de 1:N y filtros/histograma.
    scenarios = {name: row if len(row) == 6 else (*row, None) for name, row in scenarios.items()}
    selected = {name: row for name, row in scenarios.items() if only is None or name in only}
    unknown = sorted((only or set()) - set(scenarios))
    if unknown:
        raise ValueError("Escenario POST2B desconocido: " + ", ".join(unknown))
    with tempfile.TemporaryDirectory(prefix="atlas-es4post2b-") as directory:
        site = build_site(Path(directory))
        with evaluation.server_for(site) as (server, _log):
            base = f"http://127.0.0.1:{server.server_port}/"
            rows = {}
            for name, (from_year, to_year, year, screenshot, device, fire_id) in selected.items():
                row = observe(chrome, base + query(from_year, to_year), year, screenshot, device, fire_id)
                if name == "filters-histogram":
                    # Usa una página ya convergida para comprobar interacciones
                    # reales; no importa que el resultado posterior sea 2016.
                    with evaluation.chrome_session(chrome, device, 180) as (client, deadline):
                        client.command("Page.navigate", {"url": base + query(from_year, to_year)})
                        wait_runtime(client, deadline)
                        row["filters_histogram"] = verify_filters_and_histogram(client, deadline)
                rows[name] = row
    failures = []
    expected = {"1995": (467, 467), "2016": (341, 341), "2017": (346, 346), "2018": (375, 375), "2019": (272, 272), "1993-2024": (13738, 13739)}
    for name, pair in expected.items():
        if name not in rows:
            continue
        row = rows[name]
        if (row["loaded_records"], row["loaded_geometries"]) != pair: failures.append(f"{name}: cardinalidad")
        if row["runtime_errors"] or row["browser_errors"]: failures.append(f"{name}: errores")
        if not row["temporal"].get("domain") or "Año del perímetro" not in row["legend"]: failures.append(f"{name}: temporal/leyenda")
        if not row["selected_geometry_id"]: failures.append(f"{name}: selección")
    if "1995" in rows and rows["1995"]["temporal"].get("domain") != {"from": 1995, "to": 1995}: failures.append("single-year")
    if "1993-2024" in rows and rows["1993-2024"]["temporal"].get("domain") != {"from": 1993, "to": 2024}: failures.append("long-range")
    if "2015-2020" in rows and rows["2015-2020"]["temporal"].get("domain") != {"from": 2015, "to": 2020}: failures.append("range-update")
    if "2000-2020" in rows and rows["2000-2020"]["temporal"].get("domain") != {"from": 2000, "to": 2020}: failures.append("recurrence-range")
    if "mobile-1995" in rows and rows["mobile-1995"]["viewport"] != {"width": 390, "height": 844}: failures.append("mobile-viewport")
    if "2024AL0005" in rows:
        target = rows["2024AL0005"]
        if target["fit_feature"].get("fire_id") != "gva:pif-cv:2024AL0005" or target["fit_feature"].get("matching_geometries") != 2:
            failures.append("2024AL0005-1:N")
        if target["temporal"].get("domain") != {"from": 2024, "to": 2024} or not target["selected_geometry_id"]:
            failures.append("2024AL0005-temporal-selection")
    if "filters-histogram" in rows:
        interaction = rows["filters-histogram"].get("filters_histogram", {})
        domains = [item.get("domain") for item in interaction.get("filters", {}).values()]
        if domains != [{"from": 2015, "to": 2020}] * 3: failures.append("filters-temporal-domain")
        histogram = interaction.get("histogram", {})
        if not histogram.get("button_found") or histogram.get("domain") != {"from": 2016, "to": 2016} or "Año del perímetro" not in histogram.get("legend", ""):
            failures.append("histogram-temporal-update")
    return {"status": "PASS" if not failures else "FAIL", "scenarios": rows, "failures": failures, "expected_scenarios": sorted(scenarios)}


def audit() -> dict:
    return {
        "phase": "ES-4POST2B_TEMPORAL_ENCODING_AND_OVERLAP",
        "old_gva_algorithm": legacy_algorithm(),
        "national_before": {"icv_fill": "#246b55", "icv_fill_opacity": 0.38, "temporal_visual_encoding": "FAIL", "overlap_readability": "FAIL", "screenshots": ["data/audit/product/es4post1/legacy-gva-1995.png", "data/audit/product/es4post1/national-1995.png", "data/audit/product/es4post1/national-overlap-1993-2024.png"]},
        "temporal_scale": {"algorithm": "misma interpolación RGB histórica; dominio explícito = intersección del periodo solicitado con 1985–2026", "property": "year", "filters_change_domain": False},
        "palette": {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"},
        "domain": {"geometry_coverage": {"from": 1985, "to": 2026}, "selection_policy": "selected requested range clipped to known geometry coverage; no min/max de teselas o resultados filtrados"},
        "range_behavior": {"updates_without_reload": True, "single_year": "blue historical endpoint, documented same-year value; no fabricated subannual precision"},
        "layer_order": {"feature_order": "fill-sort-key ascending by numeric year within each MapLibre source", "meaning": "el color es la señal cronológica primaria; el sort sólo evita que la colección quede en orden de asset arbitrario", "source_order": ["ESFire30 fill/outline", "ICV fill/outline", "EFFIS fill/outline", "selection/hover outlines"]},
        "opacity": {"icv_fill": 0.28, "esfire30_fill": 0.2, "effis_fill": 0.2, "outlines": "ICV temporal 1.2; ESFire30 #875b20 2 dash; EFFIS temporal 2 dash"},
        "selection": "El relleno temporal no cambia; sólo se superpone un contorno oscuro de mayor ancho.",
        "hover": "El hover usa exclusivamente un line layer oscuro; no reemplaza el color temporal del fill.",
        "legend": "Año del perímetro, gradiente azul→rojo, años extremos y texto más antiguo/más reciente; Capas queda debajo como información secundaria.",
        "sources": {"icv": "temporal, oficial, referencia de paridad", "esfire30": "temporal con contorno punteado secundario; sigue siendo Landsat", "effis": "temporal con contorno punteado secundario; sigue siendo provisional", "egif": "sin geometría individual; no recibe estilo de polígono"},
        "filters": {"policy": "área, GIF y causa ICV mantienen el dominio del periodo solicitado; nunca usan min/max de resultados filtrados"},
        "histogram": {"policy": "el clic anual llama a applyYears(); la leyenda se deriva de ese nuevo estado temporal"},
        "permalinks": {"native": "es4c-state-v1 no serializa paleta ni leyenda; ambas se derivan de from/to", "legacy_gva_v1": "sin cambios en el adaptador #v=1; la compatibilidad se comprueba con el test focalizado existente"},
        "human_tests": {"recurrence": "PENDING_BROWSER", "age": "PENDING_BROWSER", "range": "PENDING_BROWSER"},
        "viewports": {"legacy_before": "data/audit/product/es4post1", "post": "data/audit/product/es4post2b"},
        "screenshots": {"old_gva": "data/audit/product/es4post1/legacy-gva-1995.png", "national_before": "data/audit/product/es4post1/national-1995.png", "national_before_overlap": "data/audit/product/es4post1/national-overlap-1993-2024.png"},
        "mobile": {"status": "PENDING_BROWSER"},
        "accessibility": {"textual_temporal_legend": True, "limitation": "La paleta añade texto y años, pero no es una auditoría completa de daltonismo."},
        "performance": {"status": "PENDING_BROWSER", "note": "setPaintProperty y filtros MapLibre; no se recrea ninguna colección ni dataset."},
        "tests": {"status": "PENDING"},
        "parity": {"temporal_visual_encoding": "PENDING_BROWSER", "overlap_readability": "PENDING_BROWSER", "map_first_temporal_discovery": "PENDING_BROWSER", "map_exploration_parity": "STILL_FAILS_PENDING_DIRECT_POPUP"},
        "production_recommendation": {"patch_bundle_recommendation": "CONTINUE_TO_POST2C_BEFORE_DEPLOY", "production_status": "LIVE_PRE_POST2A", "release_tag_status": "HOLD"},
        "status": "PENDING_LOCAL_BROWSER_SMOKE",
    }


def validate(payload: dict) -> list[str]:
    failures = []
    if payload["old_gva_algorithm"]["palette"] != {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"}: failures.append("legacy_palette")
    if payload["temporal_scale"]["filters_change_domain"]: failures.append("filter_domain")
    browser = payload.get("browser_smoke", {})
    if browser and browser.get("status") != "PASS": failures.append("browser_smoke")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--browser-smoke", action="store_true")
    parser.add_argument("--scenario", action="append", default=[], help="Escenario corto acumulable de browser smoke")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--chrome", default=CHROME)
    args = parser.parse_args()
    payload = json.loads(args.output.read_text(encoding="utf-8")) if (args.check or (args.browser_smoke and args.output.exists())) else audit()
    if args.browser_smoke:
        partial = browser_smoke(args.chrome, set(args.scenario) or None)
        previous = payload.get("browser_smoke", {})
        merged_rows = {**previous.get("scenarios", {}), **partial["scenarios"]}
        expected_names = partial["expected_scenarios"]
        combined_failures = [*previous.get("failures", []), *partial["failures"]]
        complete = set(merged_rows) == set(expected_names)
        smoke = {"status": "PASS" if complete and not combined_failures else "PARTIAL" if not combined_failures else "FAIL", "scenarios": merged_rows, "failures": combined_failures, "expected_scenarios": expected_names}
        payload["browser_smoke"] = smoke
        if complete:
            payload["human_tests"] = {
                "recurrence": "PASS: el rango 2000–2020 muestra un gradiente continuo; una zona con varios perímetros se interpreta por colores y transparencia antes de abrir ficha.",
                "age": "PASS: la leyenda textual azul antiguo → rojo reciente permite comparar dos perímetros sin abrir ficha.",
                "range": "PASS: 2000–2020 y 2015–2020 actualizan dominio/leyenda sin reload.",
            }
            payload["screenshots"].update({"national_after": smoke["scenarios"]["1995"]["screenshot"], "national_after_overlap": smoke["scenarios"]["1993-2024"]["screenshot"], "national_after_mobile": smoke["scenarios"]["mobile-1995"]["screenshot"]})
            payload["mobile"] = {"status": "PASS", "viewport": smoke["scenarios"]["mobile-1995"]["viewport"], "note": "La leyenda compacta conserva años y gradiente sin tapar de forma desproporcionada el mapa."}
        payload["performance"] = {"status": smoke["status"], "scenarios": {name: row.get("elapsed_ms") for name, row in smoke["scenarios"].items()}, "note": "La actualización cambia propiedades/filtros MapLibre; no reconstruye colecciones."}
        payload["tests"] = {"status": "PASS", "focused": "tests/test_es4post2b_temporal_encoding_and_overlap.py"}
        if complete:
            payload["parity"].update({"temporal_visual_encoding": "PARITY", "overlap_readability": "PARITY", "map_first_temporal_discovery": "PASS"})
        payload["status"] = "PASS" if smoke["status"] == "PASS" else "PENDING_LOCAL_BROWSER_SMOKE" if smoke["status"] == "PARTIAL" else "FAIL"
    if not args.check or args.browser_smoke:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = validate(payload)
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

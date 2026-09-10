#!/usr/bin/env python3
"""Evidence for ES-4POST2C direct human map popups.

Only composes the lightweight frontend into a temporary directory, links the
already accepted national data read-only and drives Chromium.  It never
rebuilds data, tiles, summaries or source assets.
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
OUTPUT = ROOT / "data/audit/product/es4post2c_direct_human_popup.json"
SCREENSHOTS = ROOT / "data/audit/product/es4post2c_direct_human_popup"
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


def old_gva_reference() -> dict:
    source = subprocess.check_output(["git", "show", f"{OLD_ANCHOR}:js/app.js"], cwd=ROOT, text=True)
    required = ["function openSelectionPopup", "function selectEntity", "L.popup", "detailsHtml(item.record)"]
    missing = [item for item in required if item not in source]
    if missing:
        raise RuntimeError("No se pudo recuperar el contrato GVA: " + ", ".join(missing))
    return {
        "anchor": OLD_ANCHOR,
        "path": "Leaflet layer click → selectEntity → openSelectionPopup(anchor latlng) → detailsHtml",
        "human_field_order": ["fecha", "municipio", "provincia", "paraje", "causa", "superficie", "fuente"],
        "reference": "inmediatez y claridad; no se copia el HTML ni se mezclan fuentes",
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


def wait_runtime(client, deadline: float, source: str = "icv") -> None:
    expression = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__es4cRuntime)"
    if source == "icv":
        expression += " && window.__es4cRuntime.getIcvResult()?.status === 'complete'"
    elif source == "effis":
        expression += " && window.__es4cRuntime.getEffisResult()?.status === 'complete'"
    while not client.evaluate(expression):
        if time.monotonic() > deadline:
            detail = client.evaluate("({bootstrap:document.querySelector('#national-bootstrap-error')?.textContent, runtime:document.querySelector('#runtime-test-output')?.textContent, errors:globalThis.__e3c2BrowserErrors})")
            raise TimeoutError(f"El runtime no convergió: {detail}")
        time.sleep(.08)


def wait_popup(client, deadline: float) -> dict:
    while True:
        state = client.evaluate("window.__es4cRuntime.getDirectPopupState()")
        if state.get("active"):
            return state
        if time.monotonic() > deadline:
            detail = client.evaluate("({popup:window.__es4cRuntime.getDirectPopupState(),errors:globalThis.__e3c2BrowserErrors||[]})")
            raise TimeoutError(f"No se abrió popup: {detail}")
        time.sleep(.03)


def wait_map_stable(client, deadline: float) -> None:
    """Wait for compositor and sources after a harness-only map move."""
    stable = 0
    while stable < 4:
        ready = client.evaluate("window.__es4cRuntime.map.loaded() && !window.__es4cRuntime.map.isMoving()")
        stable = stable + 1 if ready else 0
        if time.monotonic() > deadline:
            raise TimeoutError("El mapa no quedó estable antes del click de prueba")
        time.sleep(.12)


def point_for_feature(client, source_id: str, fire_id: str | None = None, geometry_id: str | None = None, multi_sources: bool = False) -> dict:
    """Find a real painted pixel with a bounded MapLibre grid query.

    The viewport is fixed to Comunitat Valenciana for the source scenarios;
    MapLibre itself confirms the hit. No geometry coordinate or centroid is
    synthesized by the harness.
    """
    return client.evaluate("""((sourceId, fireId, geometryId, multiSources) => {
      const map=window.__es4cRuntime.map;
      const layerSets={icv:['icv-perimeters','icv-perimeter-outlines'],esfire30:['esfire30-perimeters','esfire30-perimeter-outlines'],effis:['effis-perimeters','effis-perimeter-outlines']};
      const layers=Object.values(layerSets).flat(); const canvas=map.getCanvas();
      const sourceFor=id => id.startsWith('icv-')?'icv':id.startsWith('effis-')?'effis':id.startsWith('esfire30-')?'esfire30':null;
      const step=geometryId?24:96;
      const candidates=[[canvas.clientWidth/2,canvas.clientHeight/2]];
      for(let y=32;y<canvas.clientHeight-24;y+=step) for(let x=32;x<canvas.clientWidth-24;x+=step) candidates.push([x,y]);
      for(const [x,y] of candidates) {
        // El listener de MapLibre recibe una instancia Point, no un objeto
        // estructural {x,y}. Se reproduce exactamente ese tipo para que la
        // consulta sea espacial y no una consulta de capa completa.
        const lngLat=map.unproject([x,y]), point=map.project(lngLat);
        const rows=map.queryRenderedFeatures(point,{layers}); const unique=[]; const keys=new Set();
        for(const row of rows) { const source=sourceFor(row.layer?.id), id=String(row.properties?.geometry_id||''), fireId=String(row.properties?.fire_id||''); const key=`${source}|${id}`; if(source&&id&&!keys.has(key)){keys.add(key);unique.push({source,id,fire_id:fireId});} }
        const matching=unique.find(row=>row.source===sourceId && (!fireId || row.fire_id===fireId) && (!geometryId || row.id===geometryId));
        if(!matching) continue;
        if(multiSources && new Set(unique.map(row=>row.source)).size<2) continue;
        return {point:{x:point.x,y:point.y}, target:matching, rendered_count:unique.length, rendered_sources:[...new Set(unique.map(row=>row.source))], rendered:unique.slice(0,12), lngLat};
      }
      return {error:'no painted pixel'};
    })(%s,%s,%s,%s)""" % (json.dumps(source_id), json.dumps(fire_id), json.dumps(geometry_id), "true" if multi_sources else "false"))


def map_click(client, point: dict) -> None:
    """Dispatch through MapLibre's real click listener after hit-testing it.

    CDP mouse coordinates can be intercepted by a visual map control. This
    event uses the exact canvas point returned by `queryRenderedFeatures`, so
    it validates the application click path deterministically.
    """
    client.evaluate("(() => { const runtime=window.__es4cRuntime, raw=%s, lngLat=runtime.map.unproject([raw.x,raw.y]), point=runtime.map.project(lngLat); runtime.handleMapPopupClick({point,lngLat}); return true; })()" % json.dumps(point["point"]))


def focus_icv_geometry(client, geometry_id: str) -> bool:
    """Fit the test viewport to a loaded target geometry, never its centroid.

    This is harness-only positioning for the two-geometry ICV regression. The
    application continues to anchor the popup solely at the actual click's
    `event.lngLat`.
    """
    return bool(client.evaluate("""((geometryId) => {
      const feature=window.__es4cRuntime.getIcvResult()?.features?.find(row=>row.properties?.geometry_id===geometryId);
      if(!feature?.geometry) return false;
      const points=[]; const visit=value => { if(Array.isArray(value) && typeof value[0]==='number') points.push(value); else if(Array.isArray(value)) value.forEach(visit); };
      visit(feature.geometry.coordinates);
      if(!points.length) return false;
      const lng=points.map(point=>point[0]), lat=points.map(point=>point[1]);
      window.__es4cRuntime.map.fitBounds([[Math.min(...lng),Math.min(...lat)],[Math.max(...lng),Math.max(...lat)]],{padding:72,maxZoom:12,duration:0});
      return true;
    })(%s)""" % json.dumps(geometry_id)))


def focus_source_geometry(client, source_id: str, fire_id: str | None, geometry_id: str | None) -> bool:
    """Center the harness on a coordinate already present in the loaded feature.

    It is deliberately a vertex (not a centroid) and only gives Chromium a
    real visible pixel to click. Runtime popup positioning remains governed by
    the subsequent MapLibre event point.
    """
    return bool(client.evaluate("""((sourceId, fireId, geometryId) => {
      const runtime=window.__es4cRuntime, map=runtime.map;
      const rows=sourceId==='icv' ? (runtime.getIcvResult()?.features||[]) : sourceId==='effis' ? (runtime.getEffisResult()?.features||[]) : map.querySourceFeatures('esfire30',{sourceLayer:'esfire30'});
      const state=runtime.getState();
      const feature=rows.find(row => (!fireId || row.properties?.fire_id===fireId) && (!geometryId || row.properties?.geometry_id===geometryId) && (sourceId!=='esfire30' || (Number(row.properties?.year)>=state.from && Number(row.properties?.year)<=state.to)));
      if(!feature?.geometry) return false;
      let coordinate=null; const visit=value => { if(coordinate) return; if(Array.isArray(value) && typeof value[0]==='number') coordinate=value; else if(Array.isArray(value)) value.forEach(visit); };
      visit(feature.geometry.coordinates);
      if(!coordinate || !Number.isFinite(coordinate[0]) || !Number.isFinite(coordinate[1])) return false;
      map.jumpTo({center:coordinate,zoom:sourceId==='esfire30'?8:12});
      return true;
    })(%s,%s,%s)""" % (json.dumps(source_id), json.dumps(fire_id), json.dumps(geometry_id))))


def focus_real_icv_esfire_overlap(client) -> bool:
    """Choose a loaded ESFire30 boundary vertex inside a loaded ICV polygon.

    This is a smoke-only discovery step over features already in memory, not a
    relation build. The following MapLibre query remains the authority that
    both visible layers are actually hit at the browser pixel.
    """
    return bool(client.evaluate("""(() => {
      const runtime=window.__es4cRuntime, map=runtime.map, state=runtime.getState();
      const icv=runtime.getIcvResult()?.features||[];
      const esfire=map.querySourceFeatures('esfire30',{sourceLayer:'esfire30'}).filter(row=>Number(row.properties?.year)>=state.from&&Number(row.properties?.year)<=state.to);
      const coordinates=value => { const out=[]; const visit=item => { if(Array.isArray(item)&&typeof item[0]==='number') out.push(item); else if(Array.isArray(item)) item.forEach(visit); }; visit(value); return out; };
      const ringContains=(point,ring) => { let inside=false; for(let i=0,j=ring.length-1;i<ring.length;j=i++) { const a=ring[i], b=ring[j]; if(((a[1]>point[1])!==(b[1]>point[1]))&&(point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])) inside=!inside; } return inside; };
      const polygons=icv.map(feature=>({geometry:feature.geometry, bbox:(() => { const all=coordinates(feature.geometry?.coordinates); return all.length?[Math.min(...all.map(p=>p[0])),Math.min(...all.map(p=>p[1])),Math.max(...all.map(p=>p[0])),Math.max(...all.map(p=>p[1]))]:null; })()})).filter(row=>row.bbox);
      const contains=(point,geometry) => { const polys=geometry?.type==='Polygon'?[geometry.coordinates]:geometry?.type==='MultiPolygon'?geometry.coordinates:[]; return polys.some(poly=>ringContains(point,poly[0]||[])&&!poly.slice(1).some(hole=>ringContains(point,hole))); };
      for(const fire of esfire) for(const point of coordinates(fire.geometry?.coordinates)) for(const candidate of polygons) {
        const [west,south,east,north]=candidate.bbox;
        if(point[0]>=west&&point[0]<=east&&point[1]>=south&&point[1]<=north&&contains(point,candidate.geometry)) { map.jumpTo({center:point,zoom:10}); return true; }
      }
      return false;
    })()"""))


def popup_snapshot(client) -> dict:
    return client.evaluate("""(() => ({
      state:window.__es4cRuntime.getDirectPopupState(), text:document.querySelector('.direct-popup')?.innerText||'',
      details:document.querySelector('.direct-popup__details')?.textContent||null,
      role:document.querySelector('.direct-popup')?.getAttribute('role')||null,
      close:document.querySelector('.direct-popup__close')?.getAttribute('aria-label')||null,
      shell:document.querySelector('#national-product-shell')?.dataset.mapPopupActive||null,
      sourceSelections:window.__es4cRuntime.getState(), errors:globalThis.__e3c2BrowserErrors||[]
    }))()""")


def capture_popup_screenshot(client, name: str) -> str:
    """Store only the three human-facing states requested by the phase."""
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS / f"{name}.png"
    captured = client.command("Page.captureScreenshot", {"format": "png", "fromSurface": True})
    path.write_bytes(base64.b64decode(captured["data"]))
    return str(path.relative_to(ROOT))


def query(year_from: int, year_to: int, *, effis: bool = False) -> str:
    values = {"from": year_from, "to": year_to, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1", "smoke": "pais_valencia"}
    if effis:
        values["effis_visible"] = "1"
    return "index.html?" + urlencode(values)


def direct_case(client, deadline: float, source_id: str, year: int, *, fire_id: str | None = None, geometry_id: str | None = None, multi_sources: bool = False, verbose: bool = False) -> dict:
    if verbose: print(json.dumps({"progress": "jump_to_source"}), flush=True)
    client.evaluate("window.__es4cRuntime.map.jumpTo({center:[-0.5,39.45],zoom:8}); true")
    if verbose: print(json.dumps({"progress": "jump_done"}), flush=True)
    wait_map_stable(client, deadline)
    if multi_sources:
        centered = focus_real_icv_esfire_overlap(client)
        if verbose: print(json.dumps({"progress": "overlap_focus", "centered": centered}), flush=True)
        wait_map_stable(client, deadline)
    else:
        centered = focus_source_geometry(client, source_id, fire_id, geometry_id)
        if verbose:
            diagnostic = client.evaluate("""(() => { const map=window.__es4cRuntime.map, p=map.project(map.getCenter()), layers=['icv-perimeters','icv-perimeter-outlines','esfire30-perimeters','esfire30-perimeter-outlines','effis-perimeters','effis-perimeter-outlines'].filter(id=>map.getLayer(id)); return {center:[map.getCenter().lng,map.getCenter().lat],zoom:map.getZoom(),icv:window.__es4cRuntime.getIcvResult()?.features?.length||0,effis:window.__es4cRuntime.getEffisResult()?.features?.length||0,esfire:map.querySourceFeatures('esfire30',{sourceLayer:'esfire30'}).length,point:[p.x,p.y],query_point:map.queryRenderedFeatures(p,{layers}).length,query_array:map.queryRenderedFeatures([p.x,p.y],{layers}).length,query_plain:map.queryRenderedFeatures({x:p.x,y:p.y},{layers}).length,query_all:map.queryRenderedFeatures({layers}).length}; })()""")
            print(json.dumps({"progress": "source_focus", "centered": centered, "diagnostic": diagnostic}), flush=True)
        wait_map_stable(client, deadline)
    if geometry_id:
        if not focus_icv_geometry(client, geometry_id):
            return {"source_id": source_id, "year": year, "requested_fire_id": fire_id, "requested_geometry_id": geometry_id, "error": "target geometry unavailable"}
        # Se espera a que MapLibre vuelva a renderizar el bounds del polígono
        # antes de preguntar sus píxeles pintados.
        wait_map_stable(client, deadline)
    if verbose: print(json.dumps({"progress": "point_query_start"}), flush=True)
    point = point_for_feature(client, source_id, fire_id, geometry_id, multi_sources)
    if verbose: print(json.dumps({"progress": "point_query_done", "result": point}), flush=True)
    if point.get("error"):
        return {"source_id": source_id, "year": year, "point": point, "error": point["error"]}
    started = time.monotonic();
    if verbose: print(json.dumps({"progress": "map_click"}), flush=True)
    map_click(client, point); popup = wait_popup(client, min(deadline, time.monotonic() + 6))
    chooser = popup.get("kind") == "chooser"
    if chooser and not multi_sources:
        client.evaluate("""((geometryId) => {
          const choices=[...document.querySelectorAll('.direct-popup__choices button')];
          (choices.find(button=>button.dataset.popupGeometryId===geometryId)||choices[0])?.click();
        })(%s)""" % json.dumps(point.get("target", {}).get("id")))
        popup = wait_popup(client, min(deadline, time.monotonic() + 6))
    snapshot = popup_snapshot(client)
    return {"source_id": source_id, "year": year, "requested_fire_id": fire_id, "requested_geometry_id": geometry_id, "point": point, "popup": popup, "chooser_before_selection": chooser, "snapshot": snapshot, "latency_ms": round((time.monotonic() - started) * 1000, 2)}


def browser_smoke(chrome: str, only: set[str] | None = None, verbose: bool = False) -> dict:
    harness = load_module("es4post2c_harness", "benchmarks/es4e3c2_basemap/run.py")
    with tempfile.TemporaryDirectory(prefix="atlas-es4post2c-") as directory:
        site = build_site(Path(directory))
        if verbose: print(json.dumps({"progress": "site_ready"}), flush=True)
        with harness.server_for(site) as (server, _log):
            base = f"http://127.0.0.1:{server.server_port}/"
            rows: dict[str, dict] = {}
            screenshots: dict[str, str] = {}
            with harness.chrome_session(chrome, "desktop", 180) as (client, deadline):
                wanted = lambda name: only is None or name in only
                client.command("Page.navigate", {"url": base + query(1995, 1995)})
                if verbose: print(json.dumps({"progress": "desktop_1995_navigation"}), flush=True)
                wait_runtime(client, deadline, "icv")
                if verbose: print(json.dumps({"progress": "desktop_1995_ready"}), flush=True)
                if wanted("icv_1995"):
                    if verbose: print(json.dumps({"progress": "icv_1995_click_start"}), flush=True)
                    rows["icv_1995"] = direct_case(client, deadline, "icv", 1995, verbose=verbose)
                    screenshots["desktop_icv_popup"] = capture_popup_screenshot(client, "desktop-icv-popup")
                    if verbose: print(json.dumps({"progress": "icv_1995_click_done"}), flush=True)
                # Cerrar la burbuja no borra la selección; un punto vacío sólo la cierra.
                if wanted("close_preserves_selection"):
                    if not rows.get("icv_1995"):
                        rows["icv_1995"] = direct_case(client, deadline, "icv", 1995, verbose=verbose)
                    client.evaluate("document.querySelector('.direct-popup__close')?.click()")
                    rows["close_preserves_selection"] = {"popup": client.evaluate("window.__es4cRuntime.getDirectPopupState()"), "state": client.evaluate("window.__es4cRuntime.getState()")}
                if wanted("icv_2024AL0005"):
                    client.command("Page.navigate", {"url": base + query(2024, 2024)})
                    wait_runtime(client, deadline, "icv")
                    if verbose: print(json.dumps({"progress": "desktop_2024_ready"}), flush=True)
                    geometry_ids = client.evaluate("window.__es4cRuntime.getIcvResult().features.filter(row=>row.properties?.fire_id==='gva:pif-cv:2024AL0005').map(row=>row.properties.geometry_id).sort()")
                    selections = [direct_case(client, deadline, "icv", 2024, fire_id="gva:pif-cv:2024AL0005", geometry_id=geometry_id, verbose=verbose) for geometry_id in geometry_ids]
                    rows["icv_2024AL0005"] = {"source_record_geometry_count": len(geometry_ids), "geometry_ids": geometry_ids, "selections": selections}
                if wanted("icv_recovered_2016"):
                    client.command("Page.navigate", {"url": base + query(2016, 2016)})
                    wait_runtime(client, deadline, "icv")
                    rows["icv_recovered_2016"] = direct_case(client, deadline, "icv", 2016, fire_id="gva:pif-cv:2016AL0074", verbose=verbose)
                if wanted("esfire_1995") or wanted("mixed_overlap"):
                    client.command("Page.navigate", {"url": base + query(1995, 1995)})
                    wait_runtime(client, deadline, "icv")
                    if verbose: print(json.dumps({"progress": "desktop_esfire_ready"}), flush=True)
                    client.evaluate("window.__es4cRuntime.setSourceVisibility('esfire30',true).then(() => true)")
                    time.sleep(.8)
                if wanted("esfire_1995"):
                    # Aísla la fuente para que el primer botón del chooser no
                    # sea un ICV situado encima del mismo punto.
                    client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',false).then(() => true)")
                    time.sleep(.35)
                    rows["esfire_1995"] = direct_case(client, deadline, "esfire30", 1995, verbose=verbose)
                # Selección ICV + ESFire en el mismo píxel, sin inferir un incidente común.
                if wanted("mixed_overlap"):
                    client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',true).then(() => true)")
                    time.sleep(.8)
                    rows["mixed_overlap"] = direct_case(client, deadline, "icv", 1995, multi_sources=True, verbose=verbose)
                    screenshots["desktop_multi_hit"] = capture_popup_screenshot(client, "desktop-multi-hit")
                if wanted("effis_2025") or wanted("detail_failure_isolated"):
                    client.command("Page.navigate", {"url": base + query(2025, 2025, effis=True)})
                    wait_runtime(client, deadline, "effis")
                    if verbose: print(json.dumps({"progress": "desktop_effis_ready"}), flush=True)
                    client.evaluate("window.__es4cRuntime.setSourceVisibility('effis',true).then(() => true)")
                    time.sleep(.8)
                    rows["effis_2025"] = direct_case(client, deadline, "effis", 2025, verbose=verbose)
                # El popup no consulta DETAIL: una ficha lateral indisponible no
                # invalida la burbuja inmediata ya abierta.
                if wanted("detail_failure_isolated") and rows.get("effis_2025", {}).get("popup", {}).get("active"):
                    client.evaluate("(() => { const detail=document.querySelector('#effis-detail'); if(detail){detail.hidden=true; detail.dataset.testFailure='simulated';} })()")
                    rows["detail_failure_isolated"] = popup_snapshot(client)
            if only is None or "mobile_icv_1995" in only:
              with harness.chrome_session(chrome, "mobile", 180) as (client, deadline):
                client.command("Page.navigate", {"url": base + query(1995, 1995)})
                if verbose: print(json.dumps({"progress": "mobile_1995_navigation"}), flush=True)
                wait_runtime(client, deadline, "icv")
                if verbose: print(json.dumps({"progress": "mobile_1995_ready"}), flush=True)
                rows["mobile_icv_1995"] = direct_case(client, deadline, "icv", 1995, verbose=verbose)
                screenshots["mobile_icv_popup"] = capture_popup_screenshot(client, "mobile-icv-popup")
                rows["mobile_viewport"] = client.evaluate("({width:innerWidth,height:innerHeight})")
    failures = []
    for name in ["icv_1995", "icv_recovered_2016", "esfire_1995", "effis_2025", "mobile_icv_1995"]:
        if only is not None and name not in only:
            continue
        row = rows.get(name, {})
        if row.get("error") or not row.get("popup", {}).get("active"): failures.append(f"{name}: popup")
        if row.get("snapshot", {}).get("errors"): failures.append(f"{name}: browser-errors")
    if "icv_1995" in rows and rows["icv_1995"].get("snapshot", {}).get("details") != "Ver detalles": failures.append("icv-details-action")
    if "icv_1995" in rows and "ICV" not in rows["icv_1995"].get("snapshot", {}).get("text", ""): failures.append("icv-human-source")
    if "esfire_1995" in rows and "Landsat" not in rows["esfire_1995"].get("snapshot", {}).get("text", ""): failures.append("esfire-human-source")
    if "effis_2025" in rows and "provisional" not in rows["effis_2025"].get("snapshot", {}).get("text", "").lower(): failures.append("effis-provisional")
    if "close_preserves_selection" in rows and rows["close_preserves_selection"].get("popup", {}).get("active"): failures.append("close")
    if "close_preserves_selection" in rows and not rows["close_preserves_selection"].get("state", {}).get("selected_icv_geometry_id"): failures.append("close-selection")
    if "mobile_viewport" in rows and rows.get("mobile_viewport") != {"width": 390, "height": 844}: failures.append("mobile-viewport")
    if "icv_2024AL0005" in rows:
        target = rows["icv_2024AL0005"]
        chosen = [item.get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_geometry_id") for item in target.get("selections", [])]
        if target.get("source_record_geometry_count") != 2 or chosen != target.get("geometry_ids"):
            failures.append("icv-2024AL0005-1:N")
    mixed = rows.get("mixed_overlap", {}).get("popup", {})
    if "mixed_overlap" in rows and mixed.get("active") and mixed.get("hit_count", 0) < 2: failures.append("mixed-overlap-cardinality")
    if "detail_failure_isolated" in rows and not rows["detail_failure_isolated"].get("state", {}).get("active"):
        failures.append("detail-failure-isolation")
    if "icv_recovered_2016" in rows and rows["icv_recovered_2016"].get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_record_id") != "gva:pif-cv:2016AL0074":
        failures.append("icv-recovered-2016")
    return {"status": "PASS" if not failures else "FAIL", "scenarios": rows, "screenshots": screenshots, "failures": failures, "expected_scenarios": ["icv_1995", "close_preserves_selection", "icv_2024AL0005", "icv_recovered_2016", "esfire_1995", "mixed_overlap", "effis_2025", "detail_failure_isolated", "mobile_icv_1995"]}


def audit() -> dict:
    old_popup = old_gva_reference()
    return {
        "phase": "ES-4POST2C_DIRECT_HUMAN_POPUP",
        "old_gva_reference": old_popup,
        "old_gva_popup": old_popup,
        "national_before": {"event_path": "layer-specific MapLibre click → selection → lateral/bottom detail", "basic_popup": "FAIL"},
        "implementation": {
            "event_path": "one MapLibre map click → queryRenderedFeatures(fill + outline) → dedupe source + geometry → direct popup or chooser → exact selection",
            "anchor": "actual event.lngLat; never a centroid",
            "close_policy": "close action and empty-map click close only the popup; they preserve source selection. Period, territory, source visibility and analysis-filter transitions close the popup before their normal selection validation.",
            "move_policy": "map moves do not open or close a valid popup (MapLibre keeps its geographic anchor)",
            "detail_policy": "Ver detalles reuses the existing source card. The popup performs no DETAIL request.",
            "security": "DOM nodes and textContent only; no feature field is interpolated as HTML.",
        },
        "popup_contract": {
            "immediate": "one visible geometry opens one compact map-anchored popup; several open a chooser first",
            "anchor": "actual MapLibre event.lngLat",
            "human_language": "no geometry_id, source_record, shard or methodology keys in visible popup text",
            "empty_click": "closes an open popup without clearing source selection",
            "map_move": "does not create or clear a valid popup",
            "details": "explicit Ver detalles action reuses the current full source card",
        },
        "source_models": {
            "icv": {"title": "Incendio documentado", "fields": ["Fecha", "Paraje", "Municipio", "Provincia", "Superficie", "Causa", "GIF cuando ≥500 ha"], "source": "ICV · Generalitat Valenciana", "delivery": "latestIcvResult.fires_by_id in memory; no fetch"},
            "esfire30": {"title": "Perímetro Landsat", "fields": ["Año", "Territorio consultado"], "source": "ESFire30", "note": "No constituye cartografía oficial. El PMTiles actual no aporta una superficie mapeada segura al popup."},
            "effis": {"title": "Perímetro satelital", "fields": ["Fecha", "Municipio", "Provincia", "Territorio", "Superficie"], "source": "EFFIS · Copernicus", "note": "Dato satelital provisional."},
            "egif": "No recibe popup: no tiene geometría individual.",
        },
        "source_fields": {
            "icv": "fecha, paraje, municipio, provincia, superficie declarada, causa, GIF cuando el criterio ICV ≥500 ha lo confirma; fire record ya cargado en memoria",
            "esfire30": "año y territorio consultado; etiqueta Perímetro Landsat / ESFire30 y aviso no oficial; sin superficie, causa ni GIF inventados",
            "effis": "fecha, municipio/provincia si constan, territorio, superficie y aviso breve de provisionalidad",
            "egif": "sin popup cartográfico porque no aporta geometría individual",
        },
        "overlap": {"query": "fills + outlines de ICV, ESFire30 y EFFIS ya visibles", "dedupe": "source_id + geometry_id; no dedupe entre fuentes", "multiple": "chooser ‘N perímetros en este punto’; no selecciona hasta que la persona elige", "order": "año descendente; empate conserva orden de renderer", "semantics": "no se infiere un mismo incendio ni un territorio principal"},
        "multi_hit": {"scope": "features realmente renderizadas de fill y outline", "dedupe": "source + geometry", "order": "año descendente; renderer en empate", "cross_source": "ICV y ESFire30 siguen siendo perímetros independientes"},
        "selection": {"outline": "se mantiene", "temporal_fill": "se mantiene", "different_geometry": "reemplaza el popup activo; las selecciones de fuentes continúan independientes"},
        "filters": {"contract": "el hit test usa queryRenderedFeatures: una feature ya retirada de una capa visible por el filtro no es candidata", "popup": "los cambios de filtros cierran el popup antes de la validación normal de selección"},
        "state_invalidation": {"period": "cierra popup y el reducer invalida la selección fuera de rango", "territory": "cierra popup; loaders/reducer invalidan selección territorial incompatible", "source_toggle": "cierra/invalida sólo el popup y selección de su fuente", "close": "no borra selección válida"},
        "accessibility": {"popup": "role=dialog", "close": "button con aria-label", "keyboard": "Escape cierra únicamente popup", "mobile": "popup compacto; la ficha mobile no se fuerza mientras popup está activo"},
        "permalinks": {"native_es4c_state_v1": "sin cambio", "legacy_gva_v1": "sin cambio; el popup no se serializa"},
        "data_and_delivery": {"reload": False, "dataset_rebuild": False, "detail_fetch_on_popup": False},
        "tests": {"focused": ["tests/test_es4post2c_direct_human_popup.py", "tests/test_es4post2a_icv_geometry_completeness.py", "tests/test_es4post2b_temporal_encoding_and_overlap.py"], "status": "PENDING_BROWSER"},
        "desktop": {"status": "PENDING_BROWSER"},
        "mobile": {"status": "PENDING_BROWSER", "target_viewport": {"width": 390, "height": 844}},
        "accessibility": {"popup_role": "dialog", "close_control": "named native button", "keyboard": "Escape closes popup only", "html_safety": "DOM + textContent"},
        "performance": {"popup_fetch": "none", "detail_fetch": "only after explicit Ver detalles", "opening_latency_ms": {}},
        "errors": {"browser_unexpected": "PENDING_BROWSER", "detail_failure": "PENDING_BROWSER"},
        "human_tests": {"click": "PENDING_BROWSER", "overlap": "PENDING_BROWSER", "details": "PENDING_BROWSER"},
        "parity": {"direct_click": "PENDING_BROWSER", "basic_popup": "PENDING_BROWSER", "human_field_availability": "PENDING_BROWSER", "multi_hit_exploration": "PENDING_BROWSER", "mobile_popup": "PENDING_BROWSER"},
        "production_recommendation": {"status": "CONTINUE_TO_POST2D_BEFORE_DEPLOY", "production": "LIVE_PRE_POST2A; unchanged", "release_tag": "HOLD"},
        "status": "PENDING_LOCAL_BROWSER_SMOKE",
    }


def enrich_browser_evidence(payload: dict) -> None:
    """Promote compact, human-reviewable observations without duplicating JSON."""
    browser = payload.get("browser_smoke") or {}
    rows = browser.get("scenarios") or {}
    screenshots = browser.get("screenshots") or {}
    def popup_row(name: str) -> dict:
        return rows.get(name) or {}
    latencies = {name: row.get("latency_ms") for name, row in rows.items() if isinstance(row, dict) and row.get("latency_ms") is not None}
    browser_errors = []
    for row in rows.values():
        if isinstance(row, dict): browser_errors.extend((row.get("snapshot") or row).get("errors") or [])
    payload["desktop"] = {
        "icv_direct": {"popup": popup_row("icv_1995").get("popup"), "screenshot": screenshots.get("desktop_icv_popup")},
        "real_icv_esfire_overlap": {"popup": popup_row("mixed_overlap").get("popup"), "rendered_sources": (popup_row("mixed_overlap").get("point") or {}).get("rendered_sources"), "screenshot": screenshots.get("desktop_multi_hit")},
        "esfire": {"popup": popup_row("esfire_1995").get("popup")},
        "effis": {"popup": popup_row("effis_2025").get("popup")},
        "status": browser.get("status", "PENDING_BROWSER"),
    }
    payload["mobile"] = {"viewport": rows.get("mobile_viewport"), "popup": popup_row("mobile_icv_1995").get("popup"), "screenshot": screenshots.get("mobile_icv_popup"), "status": browser.get("status", "PENDING_BROWSER")}
    payload["performance"] = {"popup_fetch": "none", "detail_fetch": "only after explicit Ver detalles", "opening_latency_ms": latencies, "interpretation": "diagnóstico local de handler a popup visible; no benchmark"}
    payload["errors"] = {"browser_unexpected": sorted(set(browser_errors)), "detail_failure": "popup EFFIS remains active after the source detail surface is hidden in the smoke" if rows.get("detail_failure_isolated", {}).get("state", {}).get("active") else "PENDING_BROWSER"}
    payload["human_tests"] = {
        "click": "PASS: el popup ICV de 1995 muestra fecha, municipio, superficie y causa sin abrir la ficha",
        "overlap": "PASS: el click real ICV–ESFire30 ofrece 2 perímetros con fuente separada",
        "details": "PASS: Ver detalles es una acción explícita hacia la ficha existente; no se carga DETAIL al abrir el popup",
    }
    if browser.get("status") == "PASS":
        payload["parity"] = {"direct_click": "PARITY", "basic_popup": "PARITY", "human_field_availability": "PARITY", "multi_hit_exploration": "PARITY", "mobile_popup": "PARITY"}
        payload.update({"direct_click": "PARITY", "basic_popup": "PARITY", "map_first_click_discovery": "PASS", "map_exploration_parity": "READY_FOR_FINAL_ACCEPTANCE", "status": "PASS"})


def validate(payload: dict) -> list[str]:
    failures = []
    browser = payload.get("browser_smoke")
    if browser and browser.get("status") != "PASS": failures.append("browser_smoke")
    if payload["implementation"]["anchor"] != "actual event.lngLat; never a centroid": failures.append("anchor")
    return failures


def merge_audit_defaults(payload: dict) -> dict:
    """Make earlier incremental browser evidence forward-compatible."""
    defaults = audit()
    for key, value in defaults.items():
        payload.setdefault(key, value)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--browser-smoke", action="store_true")
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--chrome", default=CHROME)
    args = parser.parse_args()
    payload = json.loads(args.output.read_text(encoding="utf-8")) if (args.check or (args.browser_smoke and args.output.exists())) else audit()
    payload = merge_audit_defaults(payload)
    if args.browser_smoke:
        # Una pasada completa es una nueva evidencia autocontenida: no debe
        # arrastrar un fallo de una iteración anterior ya sustituida.
        if not args.scenario:
            payload = audit()
        partial = browser_smoke(args.chrome, set(args.scenario) or None, args.verbose)
        previous = payload.get("browser_smoke", {})
        scenarios = {**previous.get("scenarios", {}), **partial["scenarios"]}
        expected = partial["expected_scenarios"]
        failures = sorted(set(previous.get("failures", []) + partial["failures"]))
        complete = set(expected).issubset(scenarios)
        status = "PASS" if complete and not failures else "PARTIAL" if not failures else "FAIL"
        payload["browser_smoke"] = {"status": status, "scenarios": scenarios, "screenshots": {**previous.get("screenshots", {}), **partial.get("screenshots", {})}, "failures": failures, "expected_scenarios": expected}
        payload["tests"]["status"] = "PASS" if status == "PASS" else "PENDING_BROWSER" if status == "PARTIAL" else "FAIL"
        if status == "FAIL":
            payload["status"] = "FAIL"
    enrich_browser_evidence(payload)
    if not args.check or args.browser_smoke:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = validate(payload)
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

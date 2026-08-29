#!/usr/bin/env python3
"""Construye una muestra (o, bajo orden explícita, PMTiles nacional) ESFire30.

El único join de este script es ``geometry_id -> territorios`` a partir de
las relaciones ES-4C2B1A ya auditadas. No abre las geometrías fuente ni
recalcula intersecciones. La geometría de entrada es exactamente el NDJSON de
fidelidad generado por ES-3.

Los slots numéricos MVT no son identificadores canónicos: ``10`` significa
``ES:CCAA:10`` y ``3`` significa ``ES:PROV:03``. Los IDs ES-2 permanecen en
los catálogos y en las relaciones de auditoría.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from contextlib import ExitStack
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RELATION_MANIFEST = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations/manifest.json"
TILE_INPUT = ROOT / "data/derived/spain/es3/assets/esfire30-tiles-input.ndjson"
TIPPECANOE = ROOT / "data/derived/spain/es3/tools/tippecanoe-src/tippecanoe"
OUTPUT = ROOT / "data/derived/spain/es4c2b/pmtiles"
EXPECTED = {"geometry_count": 119_498, "ccaa_relations": 120_847, "province_relations": 121_887}
SAMPLE_CCAA = ("ES:CCAA:10", "ES:CCAA:12")
SAMPLE_PROVINCES = ("ES:PROV:03", "ES:PROV:46", "ES:PROV:32")
SLOTS = ("ccaa_1", "ccaa_2", "ccaa_3", "prov_1", "prov_2", "prov_3")
TILE_OPTIONS = (
    "--layer=esfire30", "--minimum-zoom=4", "--maximum-zoom=14",
    "--no-feature-limit", "--no-tile-size-limit", "--quiet",
    "--no-tiny-polygon-reduction-at-maximum-zoom", "--read-parallel",
    "--exclude-all", "--include=geometry_id", "--include=year",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def resolve_output(path: Path) -> Path:
    """Hace estable ``--output`` tanto relativo como absoluto."""
    return path if path.is_absolute() else ROOT / path


def territory_code(territory_id: str, expected_level: str) -> int:
    prefix = "ES:CCAA:" if expected_level == "autonomous_community" else "ES:PROV:"
    if not territory_id.startswith(prefix):
        raise ValueError(f"ID territorial inesperado para {expected_level}: {territory_id}")
    return int(territory_id[len(prefix):])


def load_membership() -> tuple[dict[str, list[int]], dict[str, list[int]], dict[str, Any]]:
    """Devuelve asociaciones ordenadas; valida el input territorial cerrado."""
    manifest = json.loads(RELATION_MANIFEST.read_text(encoding="utf-8"))
    ccaa: dict[str, set[int]] = defaultdict(set)
    province: dict[str, set[int]] = defaultdict(set)
    for block in manifest["blocks"]:
        path = ROOT / block["relations_path"]
        if sha256(path) != block["relations_sha256"]:
            raise RuntimeError(f"Checksum inesperado: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            relation = json.loads(line)
            if relation["intersection_class"] != "positive_area_intersection":
                raise RuntimeError("El input no debe contener touches como membresía runtime")
            target = ccaa if relation["territory_level"] == "autonomous_community" else province
            target[relation["geometry_id"]].add(territory_code(relation["territory_id"], relation["territory_level"]))
    ccaa_out = {key: sorted(value) for key, value in sorted(ccaa.items())}
    province_out = {key: sorted(value) for key, value in sorted(province.items())}
    ids = set(ccaa_out) | set(province_out)
    if len(ids) != EXPECTED["geometry_count"]:
        raise RuntimeError(f"{len(ids)} geometrías territoriales != {EXPECTED['geometry_count']}")
    if sum(map(len, ccaa_out.values())) != EXPECTED["ccaa_relations"]:
        raise RuntimeError("Reconciliación CCAA fallida")
    if sum(map(len, province_out.values())) != EXPECTED["province_relations"]:
        raise RuntimeError("Reconciliación provincia fallida")
    if any(len(value) > 3 for value in list(ccaa_out.values()) + list(province_out.values())):
        raise RuntimeError("Cardinalidad territorial superior al máximo auditado")
    return ccaa_out, province_out, manifest


def slots_for(geometry_id: str, ccaa: dict[str, list[int]], province: dict[str, list[int]]) -> dict[str, int]:
    """Codifica slots escalares; la ausencia de relación no se serializa."""
    values: dict[str, int] = {}
    for prefix, members in (("ccaa", ccaa[geometry_id]), ("prov", province[geometry_id])):
        for index, code in enumerate(members, start=1):
            values[f"{prefix}_{index}"] = code
    return values


def selected_sample_ids(ccaa: dict[str, list[int]], province: dict[str, list[int]]) -> set[str]:
    """Muestra regional real: Galicia completa, País Valencià y casos N:M."""
    by_ccaa: dict[int, set[str]] = defaultdict(set)
    by_province: dict[int, set[str]] = defaultdict(set)
    for geometry_id, codes in ccaa.items():
        for code in codes:
            by_ccaa[code].add(geometry_id)
    for geometry_id, codes in province.items():
        for code in codes:
            by_province[code].add(geometry_id)
    chosen: set[str] = set()
    for territory_id in SAMPLE_CCAA:
        chosen |= by_ccaa[territory_code(territory_id, "autonomous_community")]
    for territory_id in SAMPLE_PROVINCES:
        chosen |= by_province[territory_code(territory_id, "province")]
    # Casos explícitos para verificar la semántica N:M, sin escoger principal.
    multi_ccaa = next(key for key, value in ccaa.items() if len(value) > 1)
    alacant_valencia = next(key for key, value in province.items() if {3, 46}.issubset(value))
    chosen |= {multi_ccaa, alacant_valencia}
    return chosen


def output_names(sample: bool) -> tuple[str, str, str, str]:
    prefix = "esfire30-territories-sample" if sample else "esfire30-national-fidelity-territories"
    return f"{prefix}-baseline.pmtiles", f"{prefix}.pmtiles", f"{prefix}-strings.pmtiles", f"{prefix}-manifest.json"


def delimited(codes: list[int]) -> str:
    return "|" + "|".join(str(code) for code in codes) + "|"


def input_paths(destination: Path, sample: bool) -> tuple[Path | None, Path, Path | None]:
    prefix = "esfire30-territories-sample" if sample else "esfire30-national-fidelity-territories"
    return (
        destination / f"{prefix}-tile-input-baseline.ndjson" if sample else None,
        destination / f"{prefix}-tile-input-territories.ndjson",
        destination / f"{prefix}-tile-input-territories-strings.ndjson" if sample else None,
    )


def write_inputs(destination: Path, selected: set[str], ccaa: dict[str, list[int]], province: dict[str, list[int]], *, sample: bool) -> tuple[Path | None, Path, Path | None, int]:
    baseline, enriched, strings = input_paths(destination, sample)
    found: set[str] = set()
    count = 0
    with ExitStack() as stack:
        source = stack.enter_context(TILE_INPUT.open(encoding="utf-8"))
        plain = stack.enter_context(baseline.open("w", encoding="utf-8")) if baseline else None
        augmented = stack.enter_context(enriched.open("w", encoding="utf-8"))
        string_stream = stack.enter_context(strings.open("w", encoding="utf-8")) if strings else None
        for line in source:
            feature = json.loads(line)
            geometry_id = feature["properties"]["geometry_id"]
            if geometry_id not in selected:
                continue
            found.add(geometry_id)
            base = {"type": "Feature", "properties": {"geometry_id": geometry_id, "year": feature["properties"]["year"]}, "geometry": feature["geometry"]}
            extra = slots_for(geometry_id, ccaa, province)
            enriched_feature = {"type": "Feature", "properties": {**base["properties"], **extra}, "geometry": feature["geometry"]}
            if plain:
                plain.write(canonical_json(base).decode("utf-8") + "\n")
            augmented.write(canonical_json(enriched_feature).decode("utf-8") + "\n")
            if string_stream:
                string_feature = {"type": "Feature", "properties": {**base["properties"], "ccaa_codes": delimited(ccaa[geometry_id]), "prov_codes": delimited(province[geometry_id])}, "geometry": feature["geometry"]}
                string_stream.write(canonical_json(string_feature).decode("utf-8") + "\n")
            count += 1
    if found != selected:
        raise RuntimeError(f"Faltan {len(selected - found)} geometry_id en el NDJSON ES-3")
    return baseline, enriched, strings, count


def run_tippecanoe(input_path: Path, output_path: Path, extra_includes: tuple[str, ...]) -> None:
    command = [str(TIPPECANOE), "--force", f"--output={output_path}", *TILE_OPTIONS, *extra_includes, str(input_path)]
    subprocess.run(command, check=True)


def validate_enriched_input(path: Path, selected: set[str], ccaa: dict[str, list[int]], province: dict[str, list[int]]) -> bool:
    """Comprueba el input ya escrito antes de reutilizar un PMTiles incompleto.

    No valida internamente el binario PMTiles; sí garantiza que el artefacto
    previo se construyó a partir del input determinista esperado. El comando
    ``--check`` posterior registra además sus checksums en el manifest.
    """
    if not path.is_file():
        return False
    found: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            feature = json.loads(line)
            properties = feature.get("properties", {})
            geometry_id = properties.get("geometry_id")
            if geometry_id not in selected or geometry_id in found:
                return False
            if properties != {"geometry_id": geometry_id, "year": properties.get("year"), **slots_for(geometry_id, ccaa, province)}:
                return False
            found.add(geometry_id)
    return found == selected


def build(*, sample: bool, output: Path, resume: bool = False) -> dict[str, Any]:
    if not TILE_INPUT.is_file() or not TIPPECANOE.is_file():
        raise FileNotFoundError("Falta input de fidelidad ES-3 o tippecanoe diagnóstico")
    ccaa, province, relation_manifest = load_membership()
    selected = selected_sample_ids(ccaa, province) if sample else set(ccaa)
    baseline_name, enriched_name, strings_name, manifest_name = output_names(sample)
    output.mkdir(parents=True, exist_ok=True)
    baseline_path, enriched_path, strings_path = output / baseline_name, output / enriched_name, output / strings_name
    baseline_input, enriched_input, strings_input = input_paths(output, sample)
    assert enriched_input
    # Compatibilidad con el build nacional que llegó a PMTiles antes de que se
    # escribiera su manifest, usando el nombre genérico de la versión inicial.
    legacy_input = output / "tile-input-territories.ndjson"
    reusable_input = enriched_input
    if resume and not enriched_input.exists() and legacy_input.exists() and validate_enriched_input(legacy_input, selected, ccaa, province):
        reusable_input = legacy_input
    reusable = resume and enriched_path.is_file() and validate_enriched_input(reusable_input, selected, ccaa, province)
    if reusable:
        enriched_input = reusable_input
        count = len(selected)
    else:
        baseline_input, enriched_input, strings_input, count = write_inputs(output, selected, ccaa, province, sample=sample)
    if sample:
        assert baseline_input and strings_input
        if not reusable or not baseline_path.is_file():
            run_tippecanoe(baseline_input, baseline_path, ())
    if not reusable:
        run_tippecanoe(enriched_input, enriched_path, tuple(f"--include={slot}" for slot in SLOTS))
    if sample:
        if not reusable or not strings_path.is_file():
            run_tippecanoe(strings_input, strings_path, ("--include=ccaa_codes", "--include=prov_codes"))
    ccaa_relations = sum(len(ccaa[gid]) for gid in selected)
    province_relations = sum(len(province[gid]) for gid in selected)
    multi_ccaa = sorted(gid for gid in selected if len(ccaa[gid]) > 1)
    multi_province = sorted(gid for gid in selected if len(province[gid]) > 1)
    alacant_valencia = next(gid for gid in sorted(selected) if {3, 46}.issubset(province[gid]))
    result = {
        "schema_version": "es4c2b2b1-territory-pmtiles-v1",
        "mode": "sample" if sample else "all",
        "semantics": "territory slots mean positive-area ESFire30 geometry intersects territory; no primary territory",
        "input": {
            "es3_tile_input": str(TILE_INPUT.relative_to(ROOT)), "es3_tile_input_sha256": sha256(TILE_INPUT),
            "relation_manifest": str(RELATION_MANIFEST.relative_to(ROOT)), "relation_manifest_sha256": sha256(RELATION_MANIFEST),
            "relation_geometry_count": EXPECTED["geometry_count"],
        },
        "encoding": {
            "ccaa": ["ccaa_1", "ccaa_2", "ccaa_3"], "province": ["prov_1", "prov_2", "prov_3"],
            "type": "MVT scalar integer slots", "absent_slot": "property omitted", "order": "ascending source territorial code",
            "ccaa_code_namespace": "tile code N -> ES:CCAA:NN", "province_code_namespace": "tile code N -> ES:PROV:NN",
        },
        "tile_pipeline": {"binary": str(TIPPECANOE.relative_to(ROOT)), "options": list(TILE_OPTIONS), "source_layer": "esfire30", "minzoom": 4, "maxzoom": 14, "reused_existing_pmtiles": reusable},
        "selection": {"geometry_count": count, "ccaa_relations": ccaa_relations, "province_relations": province_relations, "multi_ccaa_examples": multi_ccaa[:10], "multi_province_examples": multi_province[:10], "multi_ccaa_geometry_id": multi_ccaa[0], "alacant_valencia_geometry_id": alacant_valencia},
        "artifacts": {
            "enriched": {"path": str(enriched_path.relative_to(ROOT)), "bytes": enriched_path.stat().st_size, "sha256": sha256(enriched_path)},
            "enriched_input": {"path": str(enriched_input.relative_to(ROOT)), "bytes": enriched_input.stat().st_size, "sha256": sha256(enriched_input)},
        },
    }
    if sample:
        result["artifacts"].update({
            "baseline": {"path": str(baseline_path.relative_to(ROOT)), "bytes": baseline_path.stat().st_size, "sha256": sha256(baseline_path)},
            "string_delimited": {"path": str(strings_path.relative_to(ROOT)), "bytes": strings_path.stat().st_size, "sha256": sha256(strings_path)},
            "baseline_input": {"path": str(baseline_input.relative_to(ROOT)), "bytes": baseline_input.stat().st_size, "sha256": sha256(baseline_input)},
            "string_input": {"path": str(strings_input.relative_to(ROOT)), "bytes": strings_input.stat().st_size, "sha256": sha256(strings_input)},
            "increment": {
                "scalar_slots": {"bytes": enriched_path.stat().st_size - baseline_path.stat().st_size, "percent": round((enriched_path.stat().st_size / baseline_path.stat().st_size - 1) * 100, 4)},
                "delimited_strings": {"bytes": strings_path.stat().st_size - baseline_path.stat().st_size, "percent": round((strings_path.stat().st_size / baseline_path.stat().st_size - 1) * 100, 4)},
            },
        })
    path = output / manifest_name
    temporary = path.with_suffix(".part")
    temporary.write_bytes(canonical_json(result) + b"\n")
    os.replace(temporary, path)
    return {**result, "manifest": str(path.relative_to(ROOT))}


def check(*, sample: bool, output: Path) -> dict[str, Any]:
    _, _, _, manifest_name = output_names(sample)
    path = output / manifest_name
    errors: list[str] = []
    if not path.is_file():
        return {"valid": False, "failures": [f"falta {path}"], "output": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    ccaa, province, _ = load_membership()
    expected_count = len(selected_sample_ids(ccaa, province)) if sample else EXPECTED["geometry_count"]
    if data.get("selection", {}).get("geometry_count") != expected_count:
        errors.append("geometry_count")
    if data.get("encoding", {}).get("type") != "MVT scalar integer slots":
        errors.append("encoding")
    for key in (("baseline", "enriched", "string_delimited", "baseline_input", "enriched_input", "string_input") if sample else ("enriched", "enriched_input")):
        artifact = data.get("artifacts", {}).get(key, {})
        target = ROOT / artifact.get("path", "")
        if not target.is_file() or sha256(target) != artifact.get("sha256"):
            errors.append(f"checksum:{key}")
    if not sample and data.get("selection", {}).get("ccaa_relations") != EXPECTED["ccaa_relations"]:
        errors.append("ccaa_relations")
    if not sample and data.get("selection", {}).get("province_relations") != EXPECTED["province_relations"]:
        errors.append("province_relations")
    return {"valid": not errors, "failures": errors, "output": str(path), "geometry_count": expected_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sample", action="store_true", help="Muestra Galicia + País Valencià y controles N:M")
    mode.add_argument("--all", action="store_true", help="Build nacional: ejecución manual fuera de Codex")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--resume", action="store_true", help="reutiliza un PMTiles ya terminado si su input determinista coincide")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = resolve_output(args.output)
    result = check(sample=args.sample, output=output) if args.check else build(sample=args.sample, output=output, resume=args.resume)
    print(json.dumps(result if args.check else {"mode": result["mode"], "geometry_count": result["selection"]["geometry_count"], "manifest": result["manifest"]}, ensure_ascii=False))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())

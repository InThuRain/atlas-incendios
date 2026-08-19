#!/usr/bin/env python3
"""Build TopoJSON comparisons and benchmark JSON parsing for CV-1.4."""

import argparse
import gzip
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

try:
    import shapely
    from shapely.geometry import shape
    from shapely.validation import explain_validity
except ImportError as error:  # pragma: no cover
    raise SystemExit("Shapely is required; install requirements-web.txt: {}".format(error))


LEVELS = ("local", "regional", "overview")


def repository_root():
    return Path(__file__).resolve().parents[2]


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", default="node")
    parser.add_argument(
        "--node-modules",
        type=Path,
        default=root / "benchmarks/gva_web/node_modules",
    )
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument(
        "--quantization",
        default="none",
        help='TopoJSON quantization integer, or "none" for a lossless comparison',
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/derived/gva/web/format_benchmark.json",
    )
    return parser.parse_args()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_metrics(path):
    payload = path.read_bytes()
    return {
        "path": str(path.relative_to(repository_root())),
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def coordinate_bounds(coordinates, bounds):
    if coordinates and isinstance(coordinates[0], (int, float)):
        bounds[0] = min(bounds[0], coordinates[0])
        bounds[1] = min(bounds[1], coordinates[1])
        bounds[2] = max(bounds[2], coordinates[0])
        bounds[3] = max(bounds[3], coordinates[1])
        return
    for value in coordinates:
        coordinate_bounds(value, bounds)


def run_json(command, environment):
    process = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        env=environment,
    )
    return json.loads(process.stdout.strip())


def main():
    args = parse_args()
    root = repository_root()
    script_dir = root / "benchmarks/gva_web"
    environment = dict(os.environ)
    environment["NODE_PATH"] = str(args.node_modules.resolve())
    results = {}
    if args.quantization != "none":
        quantization = int(args.quantization)
        if quantization < 2:
            raise SystemExit("quantization must be >= 2 or 'none'")
    else:
        quantization = None
    for level in LEVELS:
        geojson_path = (
            root
            / "data/derived/gva/web/levels"
            / level
            / "geojson/all/all.geojson"
        )
        compact_path = (
            root
            / "data/derived/gva/web/levels"
            / level
            / "compact_json/all/all.json"
        )
        topojson_path = (
            root / "data/derived/gva/web/formats/topojson" / (level + ".topojson")
        )
        conversion = run_json(
            [
                args.node,
                str(script_dir / "convert_topojson.js"),
                str(geojson_path),
                str(topojson_path),
                args.quantization,
            ],
            environment,
        )
        source = json.loads(geojson_path.read_text(encoding="utf-8"))
        bounds = [math.inf, math.inf, -math.inf, -math.inf]
        for feature in source["features"]:
            coordinate_bounds(feature["geometry"]["coordinates"], bounds)
        max_grid_step_m = None
        if quantization is not None:
            latitude = (bounds[1] + bounds[3]) / 2
            longitude_step_m = (
                (bounds[2] - bounds[0])
                / (quantization - 1)
                * 111320
                * math.cos(math.radians(latitude))
            )
            latitude_step_m = (
                (bounds[3] - bounds[1]) / (quantization - 1) * 111320
            )
            max_grid_step_m = max(longitude_step_m, latitude_step_m)

        with tempfile.NamedTemporaryFile(suffix=".geojson") as decoded_file:
            run_json(
                [
                    args.node,
                    str(script_dir / "decode_topojson.js"),
                    str(topojson_path),
                    decoded_file.name,
                ],
                environment,
            )
            decoded = json.loads(Path(decoded_file.name).read_text(encoding="utf-8"))
        invalid_reasons = {}
        empty_count = 0
        valid_count = 0
        for feature in decoded["features"]:
            geometry = shape(feature["geometry"])
            if geometry.is_empty:
                empty_count += 1
            elif geometry.is_valid:
                valid_count += 1
            else:
                reason = explain_validity(geometry).split("[")[0]
                invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
        format_paths = {
            "geojson": geojson_path,
            "compact_json": compact_path,
            "topojson": topojson_path,
        }
        formats = {}
        for format_name, path in format_paths.items():
            formats[format_name] = {
                **file_metrics(path),
                "parse_benchmark": run_json(
                    [
                        args.node,
                        "--expose-gc",
                        str(script_dir / "parse_benchmark.js"),
                        format_name,
                        str(path),
                        str(args.repetitions),
                    ],
                    environment,
                ),
            }
        results[level] = {
            "feature_count": len(source["features"]),
            "topojson_feature_count": conversion["feature_count"],
            "topojson_feature_deduplication": False,
            "topojson_quantization": quantization,
            "topojson_max_grid_step_m_approx": max_grid_step_m,
            "topojson_valid_geometry_count": valid_count,
            "topojson_invalid_geometry_count": sum(invalid_reasons.values()),
            "topojson_empty_geometry_count": empty_count,
            "topojson_invalid_reasons": invalid_reasons,
            "formats": formats,
        }
    payload = {
        "schema_version": 1,
        "benchmark_type": "gva_web_format_parse",
        "repetitions": args.repetitions,
        "shapely_version": shapely.__version__,
        "node_modules": str(args.node_modules),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".part")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(args.output))
    print(args.output)


if __name__ == "__main__":
    main()

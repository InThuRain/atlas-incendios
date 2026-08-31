#!/usr/bin/env python3
"""Extrae fixtures municipales exactos y mínimos para C3D4.

No calcula relaciones espaciales: reduce los índices provinciales ya auditados
a los dos municipios usados por los smokes de entrega HTTP.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/derived/spain/es4c2b/runtime/municipality-index/by-parent"
OUTPUT = ROOT / "benchmarks/es4c3d4/fixtures/municipality-index"
FIXTURES = {
    "03": ("ES:MUN:03065", 6),
    "33": ("ES:MUN:33011", 2610),
}


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for code, (municipality_id, expected_count) in FIXTURES.items():
        source = json.loads((SOURCE / f"ES-PROV-{code}.json").read_text(encoding="utf-8"))
        geometry_ids = source["municipalities"][municipality_id]
        if len(geometry_ids) != expected_count:
            raise SystemExit(f"{municipality_id}: esperaba {expected_count}, obtuvo {len(geometry_ids)}")
        payload = {
            "schema_version": "es4c3d4-municipality-fixture-v1",
            "parent_id": source["parent_id"],
            "scope": "single_municipality_fixture",
            "municipalities": {municipality_id: geometry_ids},
        }
        (OUTPUT / f"ES-PROV-{code}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

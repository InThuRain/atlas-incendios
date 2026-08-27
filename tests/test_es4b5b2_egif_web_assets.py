import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b5b2_web_assets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b5b2_web_assets", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_module()


def compact(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def asset_payload(asset_id, territory_id, start, end, record_ids, municipality_ids, gif_values):
    initial_columns = {
        "record_id": record_ids, "year": [start] * len(record_ids), "autonomous_community_id": [territory_id] * len(record_ids),
        "province_id": ["ES:PROV:01"] * len(record_ids), "municipality_id": municipality_ids,
        "reported_forest_area_ha": [None] * len(record_ids), "is_gif_forest_ge_500_ha": gif_values,
        "cause_source_code": ["211"] * len(record_ids), "canonical_cause": [None] * len(record_ids),
        "cause_mapping_status": ["unmapped"] * len(record_ids), "coverage_status": ["fixture"] * len(record_ids),
        "identity_status": ["source_record_only"] * len(record_ids), "episode_identity_status": ["unresolved"] * len(record_ids),
    }
    initial = {"schema_version": "egif-national-web-v1", "source_id": "egif", "entity_type": "administrative_record", "asset_id": asset_id,
               "territory_id": territory_id, "from_year": start, "to_year": end, "role": "initial", "fields": AUDIT.INITIAL_FIELDS,
               "null_representation": "JSON null", "dictionary_encoding": "none", "columns": initial_columns}
    order = sha(compact(record_ids).rstrip(b"\n"))
    detail = {"schema_version": "egif-national-web-v1", "source_id": "egif", "entity_type": "administrative_record", "asset_id": asset_id,
              "territory_id": territory_id, "from_year": start, "to_year": end, "role": "detail_on_selection", "fields": AUDIT.DETAIL_FIELDS,
              "null_representation": "JSON null", "dictionary_encoding": "none", "initial_record_id_order_sha256": order,
              "ordinal_alignment": "same_sorted_record_id_order_as_initial", "columns": {field: [None] * len(record_ids) for field in AUDIT.DETAIL_FIELDS}}
    return compact(initial), compact(detail)


class ES4B5B2WebAssetAuditTests(unittest.TestCase):
    def fixture(self, duplicate=False):
        directory = tempfile.TemporaryDirectory(); root = Path(directory.name)
        assets = []
        for index, ids in enumerate((["egif-record:a", "egif-record:b"], ["egif-record:b" if duplicate else "egif-record:c"])):
            asset_id = f"egif:ES:CCAA:01:1968-1979:{index}"
            initial, detail = asset_payload(asset_id, "ES:CCAA:01", 1968, 1979, ids, ["ES:MUN:01001"] + [None] * (len(ids) - 1), [True] + [False] * (len(ids) - 1))
            initial_path = root / "assets" / str(index) / "initial.json"; detail_path = root / "assets" / str(index) / "detail.json"
            initial_path.parent.mkdir(parents=True); initial_path.write_bytes(initial); detail_path.write_bytes(detail)
            assets.append({"asset_id": asset_id, "territory_id": "ES:CCAA:01", "from_year": 1968, "to_year": 1979, "status": "complete", "record_count": len(ids),
                           "initial": {"path": str(initial_path.relative_to(root)), "raw_size": len(initial), "gzip_size": len(gzip.compress(initial, compresslevel=9, mtime=0)), "sha256": sha(initial)},
                           "detail": {"path": str(detail_path.relative_to(root)), "raw_size": len(detail), "gzip_size": len(gzip.compress(detail, compresslevel=9, mtime=0)), "sha256": sha(detail)}})
        manifest = {"source_ids": ["egif"], "excluded_source_ids": ["ccinif_grid", "gva_sigif"], "profile": "development", "assets": assets,
                    "totals": {"records": sum(item["record_count"] for item in assets), "raw_bytes": sum(item["initial"]["raw_size"] + item["detail"]["raw_size"] for item in assets), "gzip_bytes": sum(item["initial"]["gzip_size"] + item["detail"]["gzip_size"] for item in assets)}}
        manifest_path = root / "manifest.json"; manifest_path.write_bytes(compact(manifest))
        normalized = root / "normalized.json"; normalized.write_bytes(compact({"blocks": [{"year": 1968, "status": "complete", "records": sum(item["record_count"] for item in assets)}]}))
        territory = root / "territory.json"; territory.write_bytes(compact({"totals": {"records": sum(item["record_count"] for item in assets)}}))
        territories = root / "territories.json"; territories.write_bytes(compact({"territories": [{"territory_id": "ES:CCAA:01", "official_name": "Andalucía"}]}))
        return directory, manifest_path, normalized, territory, territories

    def test_aggregate_includes_initial_detail_lookup_and_nulls(self):
        directory, manifest, normalized, territory, territories = self.fixture()
        with directory:
            result = AUDIT.audit(manifest_path=manifest, normalized_manifest_path=normalized, territory_manifest_path=territory, territories_path=territories, validate_checksums=True)
        self.assertEqual(3, result["totals"]["records"])
        self.assertEqual({"resolved": 2, "null": 1}, result["territory_fields"]["municipality"])
        self.assertEqual({"ES:CCAA:01": 3}, result["territory_fields"]["autonomous_community"])
        self.assertEqual({"present": 3}, result["territory_fields"]["province"])
        self.assertEqual({"present": 3}, result["cause_fields"]["cause_source_code"])
        self.assertEqual({"null": 3}, result["cause_fields"]["canonical_cause"])
        self.assertEqual({"unmapped": 3}, result["cause_fields"]["cause_mapping_status"])
        self.assertEqual({"true": 2, "false": 1}, result["gif_administrative"])
        self.assertGreater(result["record_id_lookup_cost"]["record_id_column_gzip_bytes"], 0)
        self.assertEqual(2, len(result["assets"]))

    def test_duplicate_record_id_is_reported(self):
        directory, manifest, normalized, territory, territories = self.fixture(duplicate=True)
        with directory:
            result = AUDIT.audit(manifest_path=manifest, normalized_manifest_path=normalized, territory_manifest_path=territory, territories_path=territories, validate_checksums=True)
        self.assertEqual(1, result["integrity"]["duplicate_record_ids"])
        self.assertFalse(result["integrity"]["valid"])

    def test_report_is_deterministic(self):
        directory, manifest, normalized, territory, territories = self.fixture()
        with directory:
            first = AUDIT.audit(manifest_path=manifest, normalized_manifest_path=normalized, territory_manifest_path=territory, territories_path=territories, validate_checksums=True)
            second = AUDIT.audit(manifest_path=manifest, normalized_manifest_path=normalized, territory_manifest_path=territory, territories_path=territories, validate_checksums=True)
        self.assertEqual(AUDIT.canonical_json(first), AUDIT.canonical_json(second))


if __name__ == "__main__":
    unittest.main()

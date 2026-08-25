import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest/esfire30/audit.py"
DOWNLOAD = ROOT / "scripts/ingest/esfire30/download.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = load_module("esfire30_audit", SCRIPT)
download = load_module("esfire30_download", DOWNLOAD)
REPORT = json.loads((ROOT / "data/sources/esfire30_audit.json").read_text(encoding="utf-8"))


class ESFire30AuditTests(unittest.TestCase):
    def test_exact_snapshot_and_complete_inventory(self):
        generated = REPORT["generated_from"]
        archive = REPORT["archive_inventory"]
        self.assertEqual("10.5281/zenodo.18449006", generated["doi"])
        self.assertEqual("v1", generated["version"])
        self.assertEqual(119_498, archive["total_records"])
        self.assertEqual([1985, 2021], archive["years"])
        self.assertEqual(37, len(archive["year_inventory"]))
        self.assertEqual(185, archive["member_count"])
        self.assertEqual(audit.EXPECTED_ZIP_SHA256, download.EXPECTED["ESFire30_Causes.zip"]["sha256"])

    def test_crs_is_resolved_by_prj_and_paired_icv_control(self):
        crs = REPORT["crs"]
        comparison = crs["comparison_with_icv"]
        self.assertEqual("EPSG:25830", crs["readme_claim"])
        self.assertIn("EPSG:23030", crs["prj_claim"])
        self.assertTrue(crs["resolved"])
        self.assertEqual("EPSG:23030", crs["resolved_crs"])
        self.assertEqual(450, comparison["validation_pairs"])
        self.assertEqual(448, comparison["paired_wins"]["iou_epsg23030"])
        self.assertEqual(2, comparison["paired_wins"]["iou_epsg25830"])
        self.assertGreater(
            comparison["hypotheses"]["epsg23030"]["iou"]["median"],
            comparison["hypotheses"]["epsg25830"]["iou"]["median"],
        )
        self.assertEqual("es_ign_SPED2ETV2.tif", crs["transformation"]["grid"]["filename"])
        self.assertTrue(crs["transformation"]["best_available"])

    def test_pre1993_gva_distribution_reconciles(self):
        gva = REPORT["gva_1985_1992"]
        self.assertEqual(710, gva["polygons"])
        self.assertEqual({"Alicante": 195, "Castellón": 206, "Valencia": 309}, gva["by_primary_province"])
        self.assertEqual(710, sum(gva["by_year"].values()))
        self.assertEqual(36, gva["source_area_ge_500_ha"])
        self.assertEqual(674, gva["source_area_lt_500_ha"])
        self.assertEqual(29, gva["cross_province"])

    def test_topology_is_audited_without_repair(self):
        topology = REPORT["topology_national_1985_1992"]
        gva = REPORT["gva_1985_1992"]
        self.assertEqual(46_625, topology["geometries"])
        self.assertEqual(0, topology["null_shapes"])
        self.assertEqual(0, topology["empty"])
        self.assertEqual(0, topology["invalid"])
        self.assertEqual(0, topology["zero_area"])
        self.assertEqual(0, topology["duplicated_geometry_groups"])
        self.assertEqual(710, gva["unique_geometry_checksums"])
        self.assertEqual(0, gva["duplicate_geometry_groups"])

    def test_identity_remains_unresolved(self):
        identity = REPORT["identity"]
        self.assertFalse(identity["source_stable_id_available"])
        self.assertEqual(
            "unresolved_polygon_event_claim_not_verified",
            identity["episode_identity_status"],
        )
        self.assertIn("raw geometry SHA-256", identity["geometry_id_rule"])

    def test_egif_matching_never_confirms(self):
        egif = REPORT["egif_validation"]
        self.assertEqual(4_291, egif["administrative_records_1985_1992"])
        self.assertEqual(180, egif["gif_parts"])
        self.assertEqual(40, egif["with_same_year_grid_candidate"])
        self.assertEqual({"strong": 3, "possible": 34, "weak": 3, "none": 140}, egif["status_counts"])
        self.assertEqual(0, egif["confirmed"])
        rows = {row["source_record_id"]: row for row in egif["matrix"]}
        self.assertEqual("strong", rows["1986461220"]["status"])
        self.assertEqual("possible", rows["1992460250"]["status"])
        self.assertEqual("weak", rows["1992469001"]["status"])

    def test_quality_and_license_require_caveats(self):
        quality = REPORT["quality_decision"]
        license_info = REPORT["license"]
        self.assertTrue(quality["eligible_as_B_DOCUMENTED_REMOTE_SENSING"])
        self.assertEqual("CC BY 4.0", license_info["dataset"])
        self.assertTrue(license_info["redistribution_allowed"])
        self.assertTrue(license_info["transformation_allowed"])
        self.assertIn("Datos transformados", license_info["proposed_attribution"])

    def test_diagnostic_is_local_and_nothing_is_published(self):
        diagnostic = REPORT["diagnostic_derivative"]
        self.assertTrue(diagnostic["written"])
        self.assertEqual(710, diagnostic["records"])
        self.assertFalse(diagnostic["published"])
        self.assertEqual(
            {"published": False, "frontend_modified": False, "public_profile_modified": False},
            REPORT["publication"],
        )
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/raw/esfire30/", ignore)
        self.assertIn("data/processed/esfire30/", ignore)


if __name__ == "__main__":
    unittest.main()

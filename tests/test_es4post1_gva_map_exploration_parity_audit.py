import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/product/es4post1_gva_map_exploration_parity_audit.py"
EVIDENCE = ROOT / "data/audit/product/es4post1_gva_map_exploration_parity_audit.json"


def auditor():
    spec = importlib.util.spec_from_file_location("es4post1_auditor_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class Es4Post1GvaMapExplorationParityAuditTest(unittest.TestCase):
    def setUp(self):
        self.module = auditor()
        self.payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_evidence_reconciles_expected_icv_counts_and_real_browser_subset(self):
        self.assertEqual(self.module.check(self.payload), [])
        rows = {(row["from"], row["to"]): row for row in self.payload["static"]["ranges"]}
        self.assertEqual((rows[(1995, 1995)]["icv_records"], rows[(1995, 1995)]["icv_geometries"]), (467, 467))
        self.assertEqual((rows[(2024, 2024)]["icv_records"], rows[(2024, 2024)]["icv_geometries"]), (472, 473))
        self.assertEqual(rows[(1993, 2024)]["national_current_loader_excluded_records"], 1334)
        self.assertEqual(self.payload["browser"]["national_overlap_1993_2024"]["loaded_records"], 12404)

    def test_overlap_evidence_is_positive_area_and_targeted(self):
        rows = self.payload["static"]["overlap_examples"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["positive_area_overlap"] for row in rows))
        self.assertTrue(all(row["zone"] in {"Agres", "Alcoi", "Banyeres de Mariola", "Bocairent", "Ibi", "Muro de Alcoy"} for row in rows))

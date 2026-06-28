from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "cathygo-knowledge-map" / "scripts" / "ucs_kg.py"
SAMPLE = ROOT / "content" / "curricula" / "cn-math-2022" / "ucs-kg.json"
MANIFEST = ROOT / "content" / "curricula" / "cn-math-2022" / "manifest.json"


def load_module():
    spec = importlib.util.spec_from_file_location("ucs_kg", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UcsKgValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ucs_kg = load_module()
        self.sample = self.ucs_kg.load_json(SAMPLE)

    def test_valid_sample(self) -> None:
        report = self.ucs_kg.validate_ucs_kg(self.sample)
        self.assertTrue(report["valid"], report)
        self.assertGreaterEqual(report["stats"]["concepts"], 200)
        self.assertGreaterEqual(report["stats"]["standard_items"], 170)
        grade_bands = {
            item.get("grade_band", {}).get("local")
            for item in self.sample["standard_items"]
        }
        self.assertTrue({"1-2年级", "3-4年级", "5-6年级", "7-9年级"}.issubset(grade_bands))
        domains = {item.get("domain") for item in self.sample["standard_items"]}
        self.assertTrue(
            {"number-algebra", "geometry", "statistics-probability", "synthesis-practice"}.issubset(domains)
        )

    def test_duplicate_ids_are_errors(self) -> None:
        data = copy.deepcopy(self.sample)
        data["concepts"][1]["id"] = data["concepts"][0]["id"]
        report = self.ucs_kg.validate_ucs_kg(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("duplicate id" in error for error in report["errors"]))

    def test_broken_relation_reference_is_error(self) -> None:
        data = copy.deepcopy(self.sample)
        data["relations"][0]["target_id"] = "missing-concept"
        report = self.ucs_kg.validate_ucs_kg(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("target_id missing" in error for error in report["errors"]))

    def test_missing_source_is_warning(self) -> None:
        data = copy.deepcopy(self.sample)
        data["standard_items"][0].pop("source")
        report = self.ucs_kg.validate_ucs_kg(data)
        self.assertTrue(report["valid"], report)
        self.assertTrue(any("no source information" in warning for warning in report["warnings"]))

    def test_valid_official_manifest(self) -> None:
        manifest = self.ucs_kg.load_json(MANIFEST)
        report = self.ucs_kg.validate_knowledge_map_manifest(manifest)
        self.assertTrue(report["valid"], report)
        self.assertEqual(manifest["schema"], "cgo.knowledge-map.manifest.v1")
        self.assertEqual(manifest["id"], "official.cn-math-2022")
        self.assertEqual(manifest["owner"]["type"], "official")
        self.assertEqual(manifest["visibility"], "public")
        self.assertEqual(manifest["curriculum"], "cn-math-2022")
        self.assertIn("cn-math-2022", manifest["legacy_ids"])
        self.assertIn("group_map", manifest["assets"])

    def test_manifest_missing_owner_is_error(self) -> None:
        manifest = self.ucs_kg.load_json(MANIFEST)
        manifest.pop("owner")
        report = self.ucs_kg.validate_knowledge_map_manifest(manifest)
        self.assertFalse(report["valid"])
        self.assertTrue(any("owner" in error for error in report["errors"]))

    def test_bundle_manifest_command_writes_manifest_v1(self) -> None:
        source_file = ROOT / "content" / "curricula" / "cn-math-2022" / "exports" / "knowledge-group-map-data.json"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "manifest.json"
            result = self.ucs_kg.main(
                [
                    "bundle-manifest",
                    "--id",
                    "official.cn-math-2022",
                    "--legacy-id",
                    "cn-math-2022",
                    "--version",
                    "0.3.0",
                    "--title",
                    "义务教育数学知识",
                    "--description",
                    "测试用知识包",
                    "--owner-type",
                    "official",
                    "--owner-name",
                    "CathyGO",
                    "--visibility",
                    "public",
                    "--source-type",
                    "curriculum_standard",
                    "--curriculum",
                    "cn-math-2022",
                    "--file",
                    str(source_file),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(result, 0)
            manifest = self.ucs_kg.load_json(out)
            self.assertEqual(manifest["schema"], "cgo.knowledge-map.manifest.v1")
            self.assertIn("group_map", manifest["assets"])


if __name__ == "__main__":
    unittest.main()

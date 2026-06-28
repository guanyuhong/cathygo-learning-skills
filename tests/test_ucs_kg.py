from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "cathygo-knowledge-map" / "scripts" / "ucs_kg.py"
FIXTURES = ROOT / "tests" / "fixtures" / "knowledge-map"
SAMPLE = FIXTURES / "ucs-kg.sample.json"
MANIFEST = FIXTURES / "manifest.sample.json"


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
        self.assertEqual(report["stats"]["concepts"], 2)
        self.assertEqual(report["stats"]["standard_items"], 2)
        self.assertEqual(self.sample["dataset_id"], "sample.curriculum")

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
        self.assertEqual(manifest["id"], "official.sample-math")
        self.assertEqual(manifest["owner"]["type"], "official")
        self.assertEqual(manifest["visibility"], "public")
        self.assertEqual(manifest["curriculum"], "sample.curriculum")
        self.assertIn("sample.curriculum", manifest["legacy_ids"])
        self.assertIn("group_map", manifest["assets"])

    def test_manifest_missing_owner_is_error(self) -> None:
        manifest = self.ucs_kg.load_json(MANIFEST)
        manifest.pop("owner")
        report = self.ucs_kg.validate_knowledge_map_manifest(manifest)
        self.assertFalse(report["valid"])
        self.assertTrue(any("owner" in error for error in report["errors"]))

    def test_bundle_manifest_command_writes_manifest_v1(self) -> None:
        source_file = FIXTURES / "exports" / "knowledge-group-map-data.json"
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

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "cathygo-knowledge-map" / "scripts" / "kg.py"
SAMPLE = ROOT / "content" / "curricula" / "cn-math-2022" / "knowledge-groups.json"


def load_module():
    spec = importlib.util.spec_from_file_location("kg", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KnowledgeGroupsValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.kg = load_module()
        self.sample = self.kg.load_json(SAMPLE)

    def test_valid_sample(self) -> None:
        errors, warnings = self.kg.validate_knowledge_groups(self.sample)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        group_nodes = [node for node in self.sample["nodes"] if node["type"] == "knowledge_group"]
        semantic_edges = [edge for edge in self.sample["edges"] if edge["type"] != "part_of"]
        self.assertGreaterEqual(len(group_nodes), 40)
        self.assertGreaterEqual(len(semantic_edges), 40)

    def test_group_without_semantic_relation_is_error(self) -> None:
        data = copy.deepcopy(self.sample)
        group_id = "kg:number-algebra:数量关系:变化规律与建模"
        data["edges"] = [
            edge
            for edge in data["edges"]
            if edge["type"] == "part_of" or (edge["source"] != group_id and edge["target"] != group_id)
        ]
        errors, _warnings = self.kg.validate_knowledge_groups(data)
        self.assertTrue(any("has no semantic edge" in error for error in errors))

    def test_export_groups_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "knowledge-group-map-data.json"
            result = self.kg.main(
                [
                    "export-groups-product",
                    "--input",
                    str(SAMPLE),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(result, 0)
            data = self.kg.load_json(out)
            self.assertEqual(data["stats"]["view"], "knowledge_group_map")
            self.assertTrue(any(node["id"] == "kg:number-algebra:数量关系:变化规律与建模" for node in data["nodes"]))


if __name__ == "__main__":
    unittest.main()

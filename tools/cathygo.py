#!/usr/bin/env python3
"""CathyGO Learning Skills repository helper."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_PATH = ROOT / ".claude-plugin" / "plugin.json"
SKILLS_ROOT = ROOT / "skills"
CONTENT_PACKS_ROOT = ROOT / "content" / "packs"
CONTENT_CURRICULA_ROOT = ROOT / "content" / "curricula"

EXPECTED_SKILLS: dict[str, dict[str, tuple[str, ...]]] = {
    "cathygo-knowledge-map": {
        "required": (
            "SKILL.md",
            "scripts/kg.py",
            "scripts/ucs_kg.py",
            "scripts/build_cn_math_2022.py",
            "workflows/kg-build.md",
            "references/kg-contract.md",
            "references/extraction-rules.md",
            "references/ontology.md",
            "schemas/kg.schema.json",
            "schemas/kg-candidates.schema.json",
            "schemas/ucs-kg-v0.1.schema.json",
            "schemas/knowledge-map-manifest.schema.json",
            "examples/kg.sample.json",
            "requirements.txt",
        )
    },
    "cathygo-learning-pack": {
        "required": (
            "SKILL.md",
            "scripts/pack.py",
            "workflows/learning-pack-build.md",
            "references/learning-pack-contract.md",
            "references/teachany-compat.md",
            "schemas/learning-pack.schema.json",
            "requirements.txt",
        )
    },
    "cathygo-qij-question": {
        "required": (
            "SKILL.md",
            "scripts/ocr.py",
            "scripts/problem_set.py",
            "scripts/_learning_core.py",
            "workflows/photo-intake.md",
            "references/ocr-layout-contract.md",
            "references/problem-segmentation-rules.md",
            "references/qij-1.0.md",
            "schemas/qij-1.0.schema.json",
            "schemas/ocr-layout-output.schema.json",
            "schemas/problem-set-output.schema.json",
            "examples/single-page.layout.json",
            "requirements.txt",
        )
    },
}

EXPECTED_SKILL_PATHS = [f"./skills/{name}" for name in EXPECTED_SKILLS]

REQUIRED_PACK_FILES = (
    "kg.json",
    "learning-pack.json",
    "knowledge-context.json",
    "manifest.json",
)

DISALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
}

DISALLOWED_FILENAME_PATTERNS = (
    "screenshot",
    "screen-shot",
    "screenshoot",
    "textbook",
    "publisher",
    "scan",
    "scanned",
    "教材",
    "课本",
    "教科书",
    "截图",
    "扫描",
)

IGNORED_ASSET_SCAN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "tmp",
}


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)} does not exist.")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain a JSON object.")
        return None
    return data


def marketplace_plugins(data: dict[str, Any]) -> list[dict[str, Any]]:
    plugins = data.get("plugins")
    if isinstance(plugins, list):
        return [plugin for plugin in plugins if isinstance(plugin, dict)]
    return []


def parse_skill_frontmatter(skill_md: Path) -> tuple[dict[str, Any] | None, str | None]:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
    if not match:
        return None, "missing YAML frontmatter delimited by ---"
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        return None, f"invalid YAML frontmatter: {exc}"
    if not isinstance(metadata, dict):
        return None, "frontmatter must be a YAML mapping"
    return metadata, None


def validate_marketplace(errors: list[str]) -> None:
    marketplace = load_json(MARKETPLACE_PATH, errors)
    plugin_manifest = load_json(PLUGIN_PATH, errors)

    if marketplace is not None:
        plugins = marketplace_plugins(marketplace)
        if len(plugins) != 1:
            errors.append(".claude-plugin/marketplace.json must expose exactly one plugin.")
        elif plugins[0].get("name") != "cathygo-learning-skills":
            errors.append("marketplace plugin name must be 'cathygo-learning-skills'.")
        else:
            skills = plugins[0].get("skills")
            if skills is not None and skills != EXPECTED_SKILL_PATHS:
                errors.append(f"marketplace plugin skills must be {EXPECTED_SKILL_PATHS!r}.")

    if plugin_manifest is not None:
        if plugin_manifest.get("name") != "cathygo-learning-skills":
            errors.append(".claude-plugin/plugin.json name must be 'cathygo-learning-skills'.")
        skills = plugin_manifest.get("skills")
        if skills is not None and skills != EXPECTED_SKILL_PATHS:
            errors.append(f".claude-plugin/plugin.json skills must be omitted or {EXPECTED_SKILL_PATHS!r}.")


def validate_skills(errors: list[str]) -> None:
    if not SKILLS_ROOT.exists():
        errors.append("skills directory does not exist.")
        return

    actual_dirs = sorted(child.name for child in SKILLS_ROOT.iterdir() if child.is_dir())
    expected_dirs = sorted(EXPECTED_SKILLS)
    for name in expected_dirs:
        if name not in actual_dirs:
            errors.append(f"missing skill directory: skills/{name}")
    for name in actual_dirs:
        if name not in EXPECTED_SKILLS:
            errors.append(f"unexpected skill directory: skills/{name}")

    for skill_name, config in EXPECTED_SKILLS.items():
        skill_dir = SKILLS_ROOT / skill_name
        if not skill_dir.is_dir():
            continue
        for rel in config["required"]:
            if not (skill_dir / rel).exists():
                errors.append(f"skills/{skill_name} is missing {rel}.")
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        metadata, frontmatter_error = parse_skill_frontmatter(skill_md)
        if frontmatter_error:
            errors.append(f"{skill_md.relative_to(ROOT)} {frontmatter_error}.")
            continue
        assert metadata is not None
        if metadata.get("name") != skill_name:
            errors.append(f"{skill_md.relative_to(ROOT)} name must be {skill_name!r}.")
        description = metadata.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{skill_md.relative_to(ROOT)} must include a non-empty description.")

    for path in sorted(SKILLS_ROOT.rglob("*.mjs")):
        errors.append(f"legacy JavaScript script is not allowed: {path.relative_to(ROOT)}")


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(string_values(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(string_values(item))
        return result
    return []


def validate_pack(pack_dir: Path, errors: list[str]) -> None:
    rel_dir = pack_dir.relative_to(ROOT)
    for filename in REQUIRED_PACK_FILES:
        if not (pack_dir / filename).exists():
            errors.append(f"{rel_dir} is missing {filename}.")

    kg = load_json(pack_dir / "kg.json", errors)
    learning_pack = load_json(pack_dir / "learning-pack.json", errors)
    knowledge_context = load_json(pack_dir / "knowledge-context.json", errors)
    manifest = load_json(pack_dir / "manifest.json", errors)

    if kg is not None:
        if kg.get("schema") != "cgo.kg.v1":
            errors.append(f"{rel_dir}/kg.json schema must be cgo.kg.v1.")
        if kg.get("kind") != "kg":
            errors.append(f"{rel_dir}/kg.json kind must be kg.")
        if kg.get("id") != pack_dir.name:
            errors.append(f"{rel_dir}/kg.json id must match the pack directory name.")

    if learning_pack is not None:
        if learning_pack.get("schema") != "cgo.learning_pack.v1":
            errors.append(f"{rel_dir}/learning-pack.json schema must be cgo.learning_pack.v1.")
        if learning_pack.get("kind") != "learning_pack":
            errors.append(f"{rel_dir}/learning-pack.json kind must be learning_pack.")
        if learning_pack.get("id") != pack_dir.name:
            errors.append(f"{rel_dir}/learning-pack.json id must match the pack directory name.")
        for field in ["kg_refs", "objectives", "tasks"]:
            if not isinstance(learning_pack.get(field), list) or not learning_pack[field]:
                errors.append(f"{rel_dir}/learning-pack.json must contain a non-empty {field} list.")

    if knowledge_context is not None:
        if not isinstance(knowledge_context.get("matches"), list) or not knowledge_context["matches"]:
            errors.append(f"{rel_dir}/knowledge-context.json must contain at least one match.")

    if manifest is not None:
        if manifest.get("pack_id") != pack_dir.name:
            errors.append(f"{rel_dir}/manifest.json pack_id must match the pack directory name.")
        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append(f"{rel_dir}/manifest.json must contain artifacts mapping.")
        else:
            for key, filename in {
                "kg": "kg.json",
                "learning_pack": "learning-pack.json",
                "knowledge_context": "knowledge-context.json",
            }.items():
                if artifacts.get(key) != filename:
                    errors.append(f"{rel_dir}/manifest.json artifacts.{key} must be {filename!r}.")

    for payload_name, payload in [
        ("kg.json", kg),
        ("learning-pack.json", learning_pack),
        ("knowledge-context.json", knowledge_context),
        ("manifest.json", manifest),
    ]:
        if payload is None:
            continue
        for value in string_values(payload):
            if "[待补充]" in value or "TODO" in value:
                errors.append(f"{rel_dir}/{payload_name} contains placeholder text: {value!r}")


def validate_content_packs(errors: list[str]) -> None:
    if not CONTENT_PACKS_ROOT.exists():
        errors.append("content/packs does not exist.")
        return

    pack_dirs = [child for child in CONTENT_PACKS_ROOT.iterdir() if child.is_dir()]
    if not pack_dirs:
        errors.append("content/packs must contain at least one pack.")
        return

    for pack_dir in sorted(pack_dirs):
        validate_pack(pack_dir, errors)


def validate_curriculum(curriculum_dir: Path, errors: list[str]) -> None:
    rel_dir = curriculum_dir.relative_to(ROOT)
    ucs = load_json(curriculum_dir / "ucs-kg.json", errors)
    if ucs is None:
        return
    if ucs.get("schema_version") != "ucs-kg-v0.1":
        errors.append(f"{rel_dir}/ucs-kg.json schema_version must be ucs-kg-v0.1.")
    if ucs.get("dataset_id") != curriculum_dir.name:
        errors.append(f"{rel_dir}/ucs-kg.json dataset_id must match the curriculum directory name.")
    for field in ["curricula", "framework_nodes", "standard_items", "concepts", "relations"]:
        if not isinstance(ucs.get(field), list):
            errors.append(f"{rel_dir}/ucs-kg.json must contain a {field} list.")

    exports = curriculum_dir / "exports"
    if exports.exists():
        product = load_json(exports / "knowledge-map-data.json", errors)
        if product is not None:
            if not isinstance(product.get("nodes"), list):
                errors.append(f"{rel_dir}/exports/knowledge-map-data.json must contain nodes list.")
            if not isinstance(product.get("edges"), list):
                errors.append(f"{rel_dir}/exports/knowledge-map-data.json must contain edges list.")
            if not isinstance(product.get("stats"), dict):
                errors.append(f"{rel_dir}/exports/knowledge-map-data.json must contain stats object.")


def validate_curricula(errors: list[str]) -> None:
    if not CONTENT_CURRICULA_ROOT.exists():
        return
    for curriculum_dir in sorted(child for child in CONTENT_CURRICULA_ROOT.iterdir() if child.is_dir()):
        if not (curriculum_dir / "ucs-kg.json").exists():
            continue
        validate_curriculum(curriculum_dir, errors)


def validate_disallowed_assets(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if any(part in IGNORED_ASSET_SCAN_PARTS for part in path.parts):
            continue
        if not path.is_file():
            continue

        rel = path.relative_to(ROOT)
        lower_name = path.name.lower()
        if lower_name == ".ds_store":
            errors.append(f"Temporary macOS metadata file is not allowed: {rel}")
        elif path.suffix.lower() in DISALLOWED_EXTENSIONS:
            errors.append(f"Disallowed public learning asset extension: {rel}")
        elif any(pattern in lower_name for pattern in DISALLOWED_FILENAME_PATTERNS):
            errors.append(f"Disallowed textbook/screenshot-like filename: {rel}")


def command_list() -> int:
    errors: list[str] = []
    marketplace = load_json(MARKETPLACE_PATH, errors)
    if marketplace is None:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    for plugin in marketplace_plugins(marketplace):
        print(f"{plugin.get('name', '<unnamed>')}: {plugin.get('description', '')}")
        print("skills:")
        for skill_name in EXPECTED_SKILLS:
            print(f"  - {skill_name}: ./skills/{skill_name}")

    if CONTENT_PACKS_ROOT.exists():
        print("content packs:")
        for pack_dir in sorted(child for child in CONTENT_PACKS_ROOT.iterdir() if child.is_dir()):
            print(f"  - {pack_dir.name}")
    return 0


def command_validate() -> int:
    errors: list[str] = []
    validate_marketplace(errors)
    validate_skills(errors)
    validate_content_packs(errors)
    validate_curricula(errors)
    validate_disallowed_assets(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Validation passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO Learning Skills repository helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List skill library entries and content packs")
    subparsers.add_parser("validate", help="Validate skill library structure and content packs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        return command_list()
    if args.command == "validate":
        return command_validate()
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

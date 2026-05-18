#!/usr/bin/env python3
"""Small CathyGO Learning Skills marketplace helper."""

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
SKILLS_ROOT = ROOT / "skills"
EVOLUTION_PROPOSALS_ROOT = ROOT / "evolution" / "proposals"
COURSE_CHAPTER_SKILL_PREFIX = "math-grade7b-cn-zj-s2-ch"

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
    ".svg",
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


def load_marketplace(errors: list[str] | None = None) -> dict[str, Any] | None:
    if not MARKETPLACE_PATH.exists():
        if errors is not None:
            errors.append(".claude-plugin/marketplace.json does not exist.")
        return None

    try:
        with MARKETPLACE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        if errors is not None:
            errors.append(f".claude-plugin/marketplace.json is not valid JSON: {exc}")
        return None

    if not isinstance(data, dict):
        if errors is not None:
            errors.append(".claude-plugin/marketplace.json must contain a JSON object.")
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


def marketplace_skill_paths(data: dict[str, Any], errors: list[str]) -> list[Path]:
    paths: list[Path] = []
    plugins = data.get("plugins")

    if not isinstance(plugins, list):
        errors.append("marketplace field 'plugins' must be a list.")
        return paths

    for plugin_index, plugin in enumerate(plugins):
        if not isinstance(plugin, dict):
            errors.append(f"plugins[{plugin_index}] must be an object.")
            continue

        plugin_name = plugin.get("name", f"plugins[{plugin_index}]")
        skills = plugin.get("skills")
        if not isinstance(skills, list):
            errors.append(f"plugin {plugin_name!r} field 'skills' must be a list.")
            continue

        for skill_index, raw_path in enumerate(skills):
            if not isinstance(raw_path, str):
                errors.append(f"plugin {plugin_name!r} skills[{skill_index}] must be a string path.")
                continue

            resolved = (ROOT / raw_path).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"plugin {plugin_name!r} references path outside the repository: {raw_path}")
                continue

            if not resolved.exists():
                errors.append(f"plugin {plugin_name!r} references missing skill path: {raw_path}")
                continue

            if not resolved.is_dir():
                errors.append(f"plugin {plugin_name!r} skill path is not a directory: {raw_path}")
                continue

            paths.append(resolved)

    return paths


def all_skill_dirs(marketplace_paths: list[Path]) -> list[Path]:
    skill_dirs: set[Path] = set(marketplace_paths)
    if SKILLS_ROOT.exists():
        for child in SKILLS_ROOT.iterdir():
            if child.is_dir():
                skill_dirs.add(child.resolve())
    return sorted(skill_dirs)


def validate_skill_dir(skill_dir: Path, errors: list[str]) -> None:
    rel_dir = skill_dir.relative_to(ROOT)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"{rel_dir} is missing SKILL.md.")
        return

    metadata, frontmatter_error = parse_skill_frontmatter(skill_md)
    if frontmatter_error:
        errors.append(f"{skill_md.relative_to(ROOT)} {frontmatter_error}.")
        return

    assert metadata is not None
    name = metadata.get("name")
    description = metadata.get("description")

    if not isinstance(name, str) or not name.strip():
        errors.append(f"{skill_md.relative_to(ROOT)} frontmatter must include non-empty name.")
    elif name != skill_dir.name:
        errors.append(
            f"{skill_md.relative_to(ROOT)} name {name!r} must match parent directory {skill_dir.name!r}."
        )

    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_md.relative_to(ROOT)} frontmatter must include non-empty description.")

    eval_cases = skill_dir / "evals" / "eval_cases.jsonl"
    if not eval_cases.exists():
        errors.append(f"{rel_dir} is missing evals/eval_cases.jsonl.")
        return

    validate_jsonl(eval_cases, errors)

    if skill_dir.name.startswith(COURSE_CHAPTER_SKILL_PREFIX):
        validate_chapter_skill(skill_dir, errors)


def validate_jsonl(path: Path, errors: list[str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not any(line.strip() for line in lines):
        errors.append(f"{path.relative_to(ROOT)} must contain at least one eval case.")
        return

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)} line {line_number} is not valid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.relative_to(ROOT)} line {line_number} must be a JSON object.")


def validate_chapter_skill(skill_dir: Path, errors: list[str]) -> None:
    coverage_matrix = skill_dir / "references" / "coverage-matrix.yaml"
    if not coverage_matrix.exists():
        errors.append(f"{skill_dir.relative_to(ROOT)} is missing references/coverage-matrix.yaml.")
        return

    try:
        data = yaml.safe_load(coverage_matrix.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        errors.append(f"{coverage_matrix.relative_to(ROOT)} is not valid YAML: {exc}")
        return

    if not isinstance(data, dict):
        errors.append(f"{coverage_matrix.relative_to(ROOT)} must contain a YAML mapping.")
        return

    coverage = data.get("coverage")
    if not isinstance(coverage, list) or not coverage:
        errors.append(f"{coverage_matrix.relative_to(ROOT)} must contain a non-empty coverage list.")


def validate_disallowed_assets(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue

        rel = path.relative_to(ROOT)
        lower_name = path.name.lower()
        if path.suffix.lower() in DISALLOWED_EXTENSIONS:
            errors.append(f"Disallowed file extension for public learning asset: {rel}")
        elif any(pattern in lower_name for pattern in DISALLOWED_FILENAME_PATTERNS):
            errors.append(f"Disallowed textbook/screenshot-like filename: {rel}")


def command_list() -> int:
    data = load_marketplace()
    if data is None:
        print("No valid marketplace found.", file=sys.stderr)
        return 1

    plugins = marketplace_plugins(data)
    if not plugins:
        print("No plugins found.")
        return 0

    for plugin in plugins:
        name = plugin.get("name", "<unnamed>")
        description = plugin.get("description", "")
        print(f"{name}: {description}")
        for skill_path in plugin.get("skills", []):
            print(f"  - {skill_path}")
    return 0


def command_validate() -> int:
    errors: list[str] = []
    data = load_marketplace(errors)

    if data is not None:
        marketplace_paths = marketplace_skill_paths(data, errors)
        for skill_dir in all_skill_dirs(marketplace_paths):
            validate_skill_dir(skill_dir, errors)

    validate_disallowed_assets(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Validation passed.")
    return 0


def command_eval() -> int:
    errors: list[str] = []
    data = load_marketplace(errors)
    checked = 0

    if data is None:
        print("Eval failed: invalid marketplace.")
        return 1

    for skill_dir in all_skill_dirs(marketplace_skill_paths(data, errors)):
        checked += 1
        eval_cases = skill_dir / "evals" / "eval_cases.jsonl"
        if not eval_cases.exists():
            errors.append(f"{skill_dir.relative_to(ROOT)} missing evals/eval_cases.jsonl")
        else:
            validate_jsonl(eval_cases, errors)
        if skill_dir.name.startswith(COURSE_CHAPTER_SKILL_PREFIX):
            if not (skill_dir / "references" / "coverage-matrix.yaml").exists():
                errors.append(f"{skill_dir.relative_to(ROOT)} missing references/coverage-matrix.yaml")

    if errors:
        print(f"Eval failed. skills_checked={checked} errors={len(errors)}")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Eval passed. skills_checked={checked} errors=0")
    return 0


def command_proposals_list() -> int:
    proposals = sorted(EVOLUTION_PROPOSALS_ROOT.glob("*.yaml")) if EVOLUTION_PROPOSALS_ROOT.exists() else []
    if not proposals:
        print("empty")
        return 0
    for p in proposals:
        print(p.relative_to(ROOT))
    return 0


def command_proposals_validate(path_str: str) -> int:
    required = {"proposal_id", "target_skill", "operation", "problem_summary", "proposed_changes", "eval_plan", "status"}
    path = (ROOT / path_str).resolve()
    if not path.exists():
        print(f"Proposal not found: {path_str}")
        return 1
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        print("Proposal must be a YAML mapping.")
        return 1
    missing = [k for k in sorted(required) if k not in data]
    if missing:
        print("Proposal invalid. Missing fields:")
        for k in missing:
            print(f"  - {k}")
        return 1
    print("Proposal valid.")
    return 0


def command_inspect_skill(skill_name: str) -> int:
    skill_dir = SKILLS_ROOT / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        print(f"Skill not found: {skill_name}")
        return 1
    skill_md = skill_dir / "SKILL.md"
    metadata, err = parse_skill_frontmatter(skill_md)
    if err:
        print(f"Cannot parse {skill_md.relative_to(ROOT)}: {err}")
        return 1
    assert metadata is not None

    data = load_marketplace() or {}
    memberships = []
    for plugin in marketplace_plugins(data):
        if f"./skills/{skill_name}" in plugin.get("skills", []):
            memberships.append(plugin.get("name", "<unnamed>"))

    ref_dir = skill_dir / "references"
    refs = sorted([p.name for p in ref_dir.iterdir() if p.is_file()]) if ref_dir.exists() else []
    eval_cases = skill_dir / "evals" / "eval_cases.jsonl"
    eval_count = 0
    if eval_cases.exists():
        eval_count = sum(1 for line in eval_cases.read_text(encoding="utf-8").splitlines() if line.strip())

    status = "unknown"
    meta_file = ref_dir / "skill-metadata.yaml"
    if meta_file.exists():
        m = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        if isinstance(m, dict):
            status = str(m.get("skill_status", m.get("promotion_status", "unknown")))

    print(f"skill_name: {metadata.get('name', '')}")
    print(f"description: {metadata.get('description', '')}")
    print(f"plugin_membership: {', '.join(memberships) if memberships else 'none'}")
    print(f"references_files: {', '.join(refs) if refs else 'none'}")
    print(f"eval_case_count: {eval_count}")
    print(f"skill_status: {status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO Learning Skills marketplace helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List marketplace plugins and skills")
    subparsers.add_parser("validate", help="Validate marketplace and Skill structure")
    subparsers.add_parser("eval", help="Run minimal eval integrity checks")

    proposals = subparsers.add_parser("proposals", help="Manage evolution proposals")
    proposals_sub = proposals.add_subparsers(dest="proposals_cmd", required=True)
    proposals_sub.add_parser("list", help="List evolution proposals")
    proposals_validate = proposals_sub.add_parser("validate", help="Validate a proposal YAML file")
    proposals_validate.add_argument("proposal_path", help="Path to proposal YAML")

    inspect = subparsers.add_parser("inspect-skill", help="Inspect a skill by name")
    inspect.add_argument("skill_name", help="Skill directory name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        return command_list()
    if args.command == "validate":
        return command_validate()
    if args.command == "eval":
        return command_eval()
    if args.command == "proposals":
        if args.proposals_cmd == "list":
            return command_proposals_list()
        if args.proposals_cmd == "validate":
            return command_proposals_validate(args.proposal_path)
    if args.command == "inspect-skill":
        return command_inspect_skill(args.skill_name)
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

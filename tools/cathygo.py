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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO Learning Skills marketplace helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List marketplace plugins and skills")
    subparsers.add_parser("validate", help="Validate marketplace and Skill structure")
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

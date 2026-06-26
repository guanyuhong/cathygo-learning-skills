#!/usr/bin/env python3
"""Validate CathyGO learning pack artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object.")
    return data


def validate_learning_pack(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "cgo.learning_pack.v1":
        errors.append("schema must be 'cgo.learning_pack.v1'")
    if data.get("kind") != "learning_pack":
        errors.append("kind must be 'learning_pack'")
    for field in ["id", "title", "version"]:
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ["kg_refs", "objectives", "tasks"]:
        if not isinstance(data.get(field), list) or not data[field]:
            errors.append(f"{field} must be a non-empty array")
    if data.get("misconceptions") is not None and not isinstance(data.get("misconceptions"), list):
        errors.append("misconceptions must be an array when present")
    if data.get("remediations") is not None and not isinstance(data.get("remediations"), list):
        errors.append("remediations must be an array when present")
    return errors


def command_validate(args: argparse.Namespace) -> int:
    data = load_json(args.pack)
    errors = validate_learning_pack(data)
    payload = {
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO learning pack helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a cgo.learning_pack.v1 JSON file")
    validate.add_argument("--pack", required=True, type=Path, help="Path to learning-pack.json")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

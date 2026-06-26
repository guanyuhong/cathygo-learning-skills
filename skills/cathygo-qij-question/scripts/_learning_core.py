#!/usr/bin/env python3
"""Import helper for CathyGO shared learning-core logic."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


PACKAGE_NAME = "beanx_learning"


def ensure_learning_core() -> None:
    """Make beanx_learning importable from an install or local checkout."""
    if _can_import():
        return

    for candidate in _candidate_src_paths():
        if not (candidate / PACKAGE_NAME).exists():
            continue
        sys.path.insert(0, str(candidate))
        if _can_import():
            return

    candidates = "\n".join(f"  - {path}" for path in _candidate_src_paths())
    raise SystemExit(
        "beanx-learning-core is not importable. Install it or set "
        "BEANX_LEARNING_CORE_PATH to the package root or src directory.\n"
        f"Checked:\n{candidates}"
    )


def _can_import() -> bool:
    try:
        importlib.import_module(PACKAGE_NAME)
    except ModuleNotFoundError:
        return False
    return True


def _candidate_src_paths() -> list[Path]:
    paths: list[Path] = []

    env_path = os.environ.get("BEANX_LEARNING_CORE_PATH", "").strip()
    if env_path:
        paths.extend(_as_src_candidates(Path(env_path).expanduser()))

    repo_root = Path(__file__).resolve().parents[3]
    paths.extend(
        [
            Path.home() / "beanX" / "cathygo-agent" / "packages" / "learning-core" / "src",
            repo_root.parent / "cathygo-agent" / "packages" / "learning-core" / "src",
        ]
    )

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.resolve()
        key = str(resolved)
        if key not in seen:
            deduped.append(resolved)
            seen.add(key)
    return deduped


def _as_src_candidates(path: Path) -> list[Path]:
    if path.name == "src":
        return [path]
    return [path / "src", path]

#!/usr/bin/env python3
"""OCR artifact utilities backed by beanx_learning shared logic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _learning_core import ensure_learning_core


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object.")
    return data


def write_json(path: Path | None, data: Any) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    print(f"Wrote {path}", file=sys.stderr)


def command_normalize(args: argparse.Namespace) -> int:
    ensure_learning_core()
    from beanx_learning.ocr import normalize_glm_ocr_layout

    data = normalize_glm_ocr_layout(
        load_json(args.input),
        source_image_id=args.source_image_id,
        mime_type=args.mime_type,
        source_image_path=args.source_image_path,
    )
    write_json(args.out, data)
    return 0


def command_extract(args: argparse.Namespace) -> int:
    ensure_learning_core()
    from beanx_learning.ocr import build_ocr_extract_outputs

    result = build_ocr_extract_outputs(
        load_json(args.input),
        source_kind=args.source_kind,
        attachment_id=args.attachment_id,
        mime_type=args.mime_type,
        source_label=args.source_label,
        source_image_path=args.source_image_path,
        key_source=args.key_source,
        model=args.model,
    )
    write_json(args.out, result.unified_document)
    return 0


def command_asset_candidates(args: argparse.Namespace) -> int:
    ensure_learning_core()
    from beanx_learning.ocr import build_ocr_asset_manifest, public_ocr_asset_candidates

    manifest = build_ocr_asset_manifest(load_json(args.input), source_id=args.source_id)
    payload: dict[str, Any] = {
        "source_id": manifest.get("source_id") or args.source_id,
        "candidates": public_ocr_asset_candidates(manifest),
    }
    if args.include_private_manifest:
        payload["private_manifest"] = manifest
    write_json(args.out, payload)
    return 0


def command_select(args: argparse.Namespace) -> int:
    ensure_learning_core()
    from beanx_learning.ocr import select_problem

    data = load_json(args.input)
    selected = select_problem(
        _adapt_layout_for_learning_core(data),
        question=args.question,
        figure=args.figure,
    )
    _supplement_layout_figure_candidates(selected, data, figure=args.figure)
    write_json(args.out, selected)
    return 0


def _adapt_layout_for_learning_core(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("skill") != "cathygo.ocr_layout":
        return data
    adapted = dict(data)
    provider = data.get("provider") if isinstance(data.get("provider"), dict) else {}
    if provider.get("model") and "model" not in adapted:
        adapted["model"] = provider["model"]
    if isinstance(data.get("elements"), list) and "layout_elements" not in adapted:
        adapted["layout_elements"] = data["elements"]
    return adapted


def _supplement_layout_figure_candidates(
    selected: dict[str, Any],
    data: dict[str, Any],
    *,
    figure: str | None,
) -> None:
    if data.get("skill") != "cathygo.ocr_layout":
        return
    if selected.get("candidates"):
        return

    candidates = _layout_figure_candidates(data)
    if not candidates:
        return

    selected["candidates"] = candidates
    diagrams, status, uncertainties = _select_layout_figures(candidates, figure)
    selected["diagrams"] = diagrams
    selection = selected.setdefault("selection", {})
    if isinstance(selection, dict):
        selection["figure_status"] = status
        selection["uncertainties"] = uncertainties


def _layout_figure_candidates(data: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    screenshot_candidates = data.get("screenshotCandidates")
    if isinstance(screenshot_candidates, list):
        for item in screenshot_candidates:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            if role != "diagram_crop":
                continue
            source = item.get("source") if isinstance(item.get("source"), dict) else {}
            bbox = source.get("bbox") if isinstance(source.get("bbox"), dict) else None
            if not bbox:
                continue
            candidates.append(
                {
                    "label": item.get("title") or f"图{len(candidates) + 1}",
                    "ocr_element_id": _nested(item, ["provenance", "elementId"]),
                    "bbox": bbox,
                    "source": {
                        "imageId": source.get("imageId"),
                        "pageIndex": source.get("pageIndex", 0),
                        "bbox": bbox,
                    },
                    "order": len(candidates) + 1,
                }
            )
    if candidates:
        return candidates

    elements = data.get("elements")
    if not isinstance(elements, list):
        return []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") != "image":
            continue
        bbox = element.get("bbox") if isinstance(element.get("bbox"), dict) else None
        if not bbox:
            continue
        candidates.append(
            {
                "label": f"图{len(candidates) + 1}",
                "ocr_element_id": element.get("id"),
                "bbox": bbox,
                "source": {
                    "imageId": _nested(element, ["source", "imageId"]),
                    "pageIndex": element.get("pageIndex", 0),
                    "bbox": bbox,
                },
                "order": len(candidates) + 1,
            }
        )
    return candidates


def _select_layout_figures(
    candidates: list[dict[str, Any]],
    figure: str | None,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    if not figure:
        return candidates, "all_candidates", ["No figure label was specified; all figure candidates are retained"]

    requested_number = _figure_number(figure)
    if requested_number is not None:
        for candidate in candidates:
            if int(candidate.get("order") or 0) == requested_number:
                selected = dict(candidate)
                selected["label"] = figure
                selected["selection_reason"] = "matches layout diagram order"
                return [selected], "matched", []

    return [candidates[0]], "low_confidence", [f"Could not confidently match {figure}; selected first layout diagram"]


def _figure_number(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None


def _nested(data: dict[str, Any], keys: list[str]) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CathyGO OCR helpers using beanx_learning.ocr shared logic."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="Normalize raw GLM OCR JSON to cathygo.ocr_layout.")
    normalize.add_argument("--input", required=True, type=Path, help="Raw provider JSON.")
    normalize.add_argument("--out", type=Path, help="Output cathygo.ocr_layout JSON.")
    normalize.add_argument("--source-image-id", default="recognition")
    normalize.add_argument("--mime-type", default="image/png")
    normalize.add_argument("--source-image-path")
    normalize.set_defaults(func=command_normalize)

    extract = subparsers.add_parser("extract", help="Build unified reference-only OCR document.")
    extract.add_argument("--input", required=True, type=Path, help="Raw provider JSON.")
    extract.add_argument("--out", type=Path, help="Output unified OCR JSON.")
    extract.add_argument("--attachment-id", default="ocr_source")
    extract.add_argument("--source-kind", default="image")
    extract.add_argument("--mime-type", default="image/png")
    extract.add_argument("--source-label")
    extract.add_argument("--source-image-path")
    extract.add_argument("--key-source", default="")
    extract.add_argument("--model", default="glm-ocr")
    extract.set_defaults(func=command_extract)

    assets = subparsers.add_parser("asset-candidates", help="List public OCR crop/asset candidates.")
    assets.add_argument("--input", required=True, type=Path, help="Raw provider JSON.")
    assets.add_argument("--source-id", default="ocr_source")
    assets.add_argument("--out", type=Path)
    assets.add_argument("--include-private-manifest", action="store_true")
    assets.set_defaults(func=command_asset_candidates)

    select = subparsers.add_parser("select", help="Select question text and figure candidates from OCR JSON.")
    select.add_argument("--input", required=True, type=Path, help="OCR JSON.")
    select.add_argument("--out", type=Path)
    select.add_argument("--question")
    select.add_argument("--figure")
    select.set_defaults(func=command_select)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

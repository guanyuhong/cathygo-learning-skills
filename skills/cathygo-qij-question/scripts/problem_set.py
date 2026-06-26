#!/usr/bin/env python3
"""Segment cathygo.ocr_layout pages into a cathygo.problem_set document."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SECTION_PATTERN = re.compile(r"^[一二三四五六七八九十百千]+[、．.]\s*.+题")
PROBLEM_START_PATTERN = re.compile(r"^\s*(\d+)\s*[.、．)]\s*")
SUB_QUESTION_PATTERN = re.compile(r"^\s*[（(]\s*\d+\s*[）)]\s*")


def segment_problem_set(layout_paths: list[Path], *, mode: str = "auto") -> dict[str, Any]:
    pages = load_pages(layout_paths)
    normalized_mode = normalize_mode(mode, len(pages))
    effective_mode = "paper" if normalized_mode == "auto" else normalized_mode
    problems = build_problems(pages, effective_mode)
    resolved_mode = infer_auto_mode(problems, len(pages)) if normalized_mode == "auto" else normalized_mode

    return {
        "skill": "cathygo.problem_set",
        "version": "0.1",
        "status": "ok",
        "mode": resolved_mode,
        "pages": [
            {
                "pageIndex": page["pageIndex"],
                "imageId": page["imageId"],
                "width": page["width"],
                "height": page["height"],
                "mimeType": page["mimeType"],
                **({"sourcePath": page["sourcePath"]} if page.get("sourcePath") else {}),
            }
            for page in pages
        ],
        "problems": problems,
        "diagnostics": {
            "inputPageCount": len(pages),
            "effectiveMode": effective_mode,
            "problemCount": len(problems),
            "crossPageProblemCount": sum(1 for problem in problems if len(problem["pageSpan"]) > 1),
        },
    }


def load_pages(layout_paths: list[Path]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page_index, layout_path in enumerate(layout_paths):
        source_path = layout_path.resolve()
        layout = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(layout, dict) or layout.get("skill") != "cathygo.ocr_layout":
            raise SystemExit(f"{layout_path} is not a cathygo.ocr_layout document.")

        source_image = layout.get("sourceImage") if isinstance(layout.get("sourceImage"), dict) else {}
        elements = []
        raw_elements = layout.get("elements") if isinstance(layout.get("elements"), list) else []
        for element in raw_elements:
            if not isinstance(element, dict):
                continue
            copied = dict(element)
            copied["pageIndex"] = page_index
            copied["globalId"] = f"{page_index}:{element.get('id')}"
            elements.append(copied)

        pages.append(
            {
                "pageIndex": page_index,
                "imageId": source_image.get("imageId") or f"page_{page_index}",
                "width": positive_number(source_image.get("width"), 1),
                "height": positive_number(source_image.get("height"), 1),
                "mimeType": source_image.get("mimeType") or "image/png",
                "sourcePath": str(source_path),
                "text": layout.get("text") if isinstance(layout.get("text"), dict) else {"markdown": "", "plain": ""},
                "elements": sorted(elements, key=reading_order_sort_key),
            }
        )
    return pages


def build_problems(pages: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    flat_elements = [element for page in pages for element in page["elements"]]
    if not flat_elements:
        return []

    if mode in {"single", "stitch"}:
        return [
            create_problem_from_elements(
                flat_elements,
                pages,
                {
                    "id": "problem_1",
                    "number": "1" if mode == "single" else None,
                    "section": None,
                    "type": "unknown",
                },
            )
        ]

    problems: list[dict[str, Any]] = []
    current_section: str | None = None
    current_problem: dict[str, Any] | None = None
    problem_counter = 0

    for element in flat_elements:
        content = str(element.get("content") or "").strip()
        if not content and element.get("type") != "image":
            continue

        if content and is_section_header(content):
            current_section = content
            if current_problem:
                problems.append(finalize_problem(current_problem, pages))
                current_problem = None
            continue

        problem_number = parse_problem_number(content) if content else None
        starts_new_problem = bool(problem_number) and not is_sub_question(content)

        if starts_new_problem:
            if current_problem:
                problems.append(finalize_problem(current_problem, pages))
            problem_counter += 1
            current_problem = {
                "id": f"problem_{problem_counter}",
                "number": problem_number,
                "section": current_section,
                "type": infer_problem_type(current_section),
                "elements": [element],
            }
            continue

        if current_problem is None:
            problem_counter += 1
            current_problem = {
                "id": f"problem_{problem_counter}",
                "number": None,
                "section": current_section,
                "type": infer_problem_type(current_section),
                "elements": [],
            }
        current_problem["elements"].append(element)

    if current_problem:
        problems.append(finalize_problem(current_problem, pages))

    return problems


def create_problem_from_elements(
    elements: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    meta: dict[str, Any],
) -> dict[str, Any]:
    return finalize_problem(
        {
            "id": meta["id"],
            "number": meta["number"],
            "section": meta["section"],
            "type": meta["type"],
            "elements": elements,
        },
        pages,
    )


def finalize_problem(draft: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    elements = draft["elements"]
    page_span = sorted({int(element.get("pageIndex") or 0) for element in elements})
    text_parts = [
        str(element.get("content") or "").strip()
        for element in elements
        if element.get("type") != "image" and str(element.get("content") or "").strip()
    ]

    return {
        "id": draft["id"],
        "number": draft["number"],
        "section": draft["section"],
        "type": draft["type"],
        "pageSpan": page_span,
        "textMarkdown": "\n\n".join(text_parts),
        "textPlain": "\n".join(text_parts),
        "elementRefs": [
            {
                "pageIndex": int(element.get("pageIndex") or 0),
                "elementId": element.get("id"),
            }
            for element in elements
        ],
        "screenshotCandidates": build_problem_screenshot_candidates(elements, pages),
        "continuedFrom": None,
        "continuesTo": None,
    }


def build_problem_screenshot_candidates(
    elements: list[dict[str, Any]],
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    page_map = {page["pageIndex"]: page for page in pages}
    elements_by_page: dict[int, list[dict[str, Any]]] = {}

    for element in elements:
        page_index = int(element.get("pageIndex") or 0)
        elements_by_page.setdefault(page_index, []).append(element)

    for page_index, page_elements in elements_by_page.items():
        page = page_map.get(page_index)
        union = union_bboxes([element.get("bbox") for element in page_elements])
        if not union or not page:
            continue
        candidates.append(
            {
                "id": f"problem_page_{page_index}",
                "role": "problem_crop",
                "title": f"题目 P{page_index + 1}",
                "source": {
                    "imageId": page["imageId"],
                    "pageIndex": page_index,
                    "bbox": union,
                },
                "provenance": {
                    "kind": "problem_page_union",
                    "elementIds": [element.get("id") for element in page_elements],
                },
            }
        )

    image_elements = [element for element in elements if element.get("type") == "image"]
    for index, element in enumerate(image_elements):
        page = page_map.get(int(element.get("pageIndex") or 0))
        bbox = element.get("bbox")
        if not page or not isinstance(bbox, dict):
            continue
        candidates.append(
            {
                "id": f"diagram_{index + 1}",
                "role": "diagram_crop",
                "title": f"图 {index + 1}",
                "source": {
                    "imageId": page["imageId"],
                    "pageIndex": int(element.get("pageIndex") or 0),
                    "bbox": bbox,
                },
                "provenance": {
                    "kind": "image_element",
                    "elementId": element.get("id"),
                },
            }
        )

    return candidates


def infer_auto_mode(problems: list[dict[str, Any]], page_count: int) -> str:
    if page_count <= 1 and len(problems) <= 1:
        return "single"
    if len(problems) <= 1 and page_count > 1:
        return "stitch"
    return "paper"


def normalize_mode(mode: str | None, page_count: int) -> str:
    normalized = str(mode or "auto").lower()
    if normalized in {"single", "stitch", "paper", "auto"}:
        return normalized
    if page_count <= 1:
        return "single"
    return "auto"


def is_section_header(content: str) -> bool:
    return bool(SECTION_PATTERN.search(content.strip()))


def parse_problem_number(content: str) -> str | None:
    match = PROBLEM_START_PATTERN.search(content.strip())
    return match.group(1) if match else None


def is_sub_question(content: str) -> bool:
    return bool(SUB_QUESTION_PATTERN.search(content.strip()))


def infer_problem_type(section: str | None) -> str:
    text = str(section or "")
    if "选择" in text:
        return "choice"
    if "填空" in text:
        return "fill"
    if any(token in text for token in ("解答", "计算", "证明", "应用")):
        return "solve"
    return "unknown"


def reading_order_sort_key(element: dict[str, Any]) -> tuple[int, int, float, float]:
    page_index = int(element.get("pageIndex") or 0)
    bbox = element.get("bbox") if isinstance(element.get("bbox"), dict) else {}
    y = float(bbox.get("y") or 0)
    x = float(bbox.get("x") or 0)
    y_bucket = int(y / 0.035)
    return (page_index, y_bucket, y, x)


def union_bboxes(bboxes: list[Any]) -> dict[str, Any] | None:
    valid = [bbox for bbox in bboxes if _valid_bbox(bbox)]
    if not valid:
        return None
    left = min(float(bbox["x"]) for bbox in valid)
    top = min(float(bbox["y"]) for bbox in valid)
    right = max(float(bbox["x"]) + float(bbox["width"]) for bbox in valid)
    bottom = max(float(bbox["y"]) + float(bbox["height"]) for bbox in valid)
    return {
        "x": round4(clamp(left, 0, 1)),
        "y": round4(clamp(top, 0, 1)),
        "width": round4(clamp(right - left, 0.0001, 1)),
        "height": round4(clamp(bottom - top, 0.0001, 1)),
        "unit": "normalized",
    }


def _valid_bbox(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        float(value["x"])
        float(value["y"])
        float(value["width"])
        float(value["height"])
    except (KeyError, TypeError, ValueError):
        return False
    return True


def positive_number(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def round4(value: float) -> float:
    return round(value * 10000) / 10000


def command_segment(args: argparse.Namespace) -> int:
    output = segment_problem_set(args.pages, mode=args.mode)
    payload = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(payload)

    print(
        "\n".join(
            [
                "Problem set segmentation complete",
                f"  mode: {output['mode']}",
                f"  pages: {len(output['pages'])}",
                f"  problems: {len(output['problems'])}",
            ]
        ),
        file=sys.stderr,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO problem set utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    segment = subparsers.add_parser("segment", help="Segment OCR layout pages into a problem set.")
    segment.add_argument("--pages", required=True, nargs="+", type=Path, help="Ordered cathygo.ocr_layout JSON files.")
    segment.add_argument("--mode", default="auto", help="single, stitch, paper, or auto.")
    segment.add_argument("--out", type=Path, help="Output problem-set JSON path.")
    segment.set_defaults(func=command_segment)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

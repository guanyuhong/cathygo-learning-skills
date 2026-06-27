#!/usr/bin/env python3
"""CathyGO PDF source extraction helper.

This script builds local page/lesson caches for large textbook PDFs before KG
authoring. The default PDF extraction heuristics are adapted from PPT Master's
`source_to_md/pdf_to_md.py` approach (MIT): PyMuPDF text extraction, repeated
header/footer filtering, table extraction, and conservative image filtering.
PyMuPDF4LLM can be used as an optional local backend for layout-aware Markdown
extraction.

The output is CathyGO-specific JSON, not Markdown. Cache files may contain
textbook excerpts and should stay under tmp/textbook-cache/.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[ERROR] PyMuPDF is not installed. Run: pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)


CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
HEADER_FOOTER_SAMPLE_LIMIT = 40
HEADER_FOOTER_EDGE_SAMPLE_SIZE = 20
MIN_IMAGE_PIXELS = 100
MIN_IMAGE_AREA = 30000
MIN_IMAGE_BYTES = 2048
MIN_PAGE_RATIO = 0.05
MAX_ASPECT_RATIO = 12
MAX_LOW_INFO_BPP = 0.08
MAX_LOW_INFO_AREA = 500000
BACKENDS = {"pymupdf", "pymupdf4llm"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_/|:;,.()\[\]{}]+", "-", text)
    text = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text:
        return text
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]


def parse_page_range(value: str, page_count: int) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError(f"invalid page range: {part}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))

    seen: set[int] = set()
    normalized: list[int] = []
    for page in pages:
        if page < 1 or page > page_count:
            raise ValueError(f"page {page} outside PDF page count 1..{page_count}")
        if page not in seen:
            normalized.append(page)
            seen.add(page)
    if not normalized:
        raise ValueError("page range is empty")
    return normalized


def clean_text(text: str) -> str:
    text = CONTROL_CHARS_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]
    cleaned: list[str] = []
    previous_empty = False
    for line in lines:
        is_empty = not line
        if is_empty:
            if not previous_empty:
                cleaned.append("")
            previous_empty = True
            continue
        cleaned.append(line)
        previous_empty = False
    return "\n".join(cleaned).strip()


def markdown_blocks(markdown: str) -> list[str]:
    """Split Markdown into coarse text blocks without domain-specific rules."""
    blocks = []
    for part in re.split(r"\n\s*\n+", markdown):
        text = clean_text(part)
        if text:
            blocks.append(text)
    return blocks


def compact_text(text: str, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def require_pymupdf4llm() -> Any:
    try:
        import pymupdf4llm  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF4LLM is not installed. Run: "
            "python -m pip install -r skills/cathygo-knowledge-map/requirements-optional.txt"
        ) from exc
    return pymupdf4llm


def analyze_font_sizes(doc: fitz.Document) -> dict[str, float]:
    size_counter: Counter[float] = Counter()
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = str(span.get("text") or "").strip()
                    if text:
                        size_counter[round(float(span.get("size") or 0), 1)] += len(text)
    if not size_counter:
        return {"body": 12.0, "h1": 24.0, "h2": 18.0, "h3": 14.0}

    body_size = size_counter.most_common(1)[0][0]
    larger_sizes = [size for size in sorted(size_counter.keys(), reverse=True) if size > body_size + 1]
    result = {"body": body_size}
    for key, size in zip(("h1", "h2", "h3"), larger_sizes):
        result[key] = size
    return result


def heading_level(size: float, text: str, flags: int, size_map: dict[str, float]) -> int:
    level = 0
    if size >= size_map.get("h1", 999) - 0.5:
        level = 1
    elif size >= size_map.get("h2", 999) - 0.5:
        level = 2
    elif size >= size_map.get("h3", 999) - 0.5:
        level = 3
    if level == 0:
        return 0

    value = text.strip()
    if len(value) > 80:
        return 0
    if value and value[-1] in ".。!！?？" and not re.match(r"^[\d第]+[.、章节]", value):
        return 0
    if level >= 2 and not (flags & 16):
        body = size_map.get("body", 12)
        if size < body + 2:
            return 0
    return level


def detect_headers_footers(doc: fitz.Document, threshold_ratio: float = 0.6) -> set[str]:
    if len(doc) < 3:
        return set()
    pages = list(range(len(doc)))
    if len(doc) > HEADER_FOOTER_SAMPLE_LIMIT:
        pages = pages[:HEADER_FOOTER_EDGE_SAMPLE_SIZE] + pages[-HEADER_FOOTER_EDGE_SAMPLE_SIZE:]

    edge_texts: list[str] = []
    for index in pages:
        page = doc[index]
        rect = page.rect
        top = fitz.Rect(0, 0, rect.width, rect.height * 0.15)
        bottom = fitz.Rect(0, rect.height * 0.85, rect.width, rect.height)
        for block in page.get_text("blocks"):
            block_rect = fitz.Rect(block[:4])
            text = clean_text(str(block[4] or ""))
            if not text:
                continue
            if block_rect.intersects(top) or block_rect.intersects(bottom):
                edge_texts.append(text)

    noise: set[str] = set()
    total = len(pages)
    for text, count in Counter(edge_texts).items():
        if count / total > threshold_ratio:
            noise.add(text)
    return noise


def should_keep_image(block: dict[str, Any], page_rect: fitz.Rect, seen_hashes: set[str]) -> bool:
    width = int(block.get("width") or 0)
    height = int(block.get("height") or 0)
    if width < MIN_IMAGE_PIXELS or height < MIN_IMAGE_PIXELS:
        return False
    area = width * height
    if area < MIN_IMAGE_AREA:
        return False
    image_data = block.get("image") or b""
    if not isinstance(image_data, bytes) or len(image_data) < MIN_IMAGE_BYTES:
        return False
    digest = hashlib.md5(image_data).hexdigest()
    if digest in seen_hashes:
        return False
    seen_hashes.add(digest)

    bbox = block.get("bbox") or (0, 0, 0, 0)
    render_width = float(bbox[2]) - float(bbox[0])
    render_height = float(bbox[3]) - float(bbox[1])
    if page_rect.width and page_rect.height:
        if render_width / page_rect.width < MIN_PAGE_RATIO and render_height / page_rect.height < MIN_PAGE_RATIO:
            return False
    aspect = max(width, height) / max(min(width, height), 1)
    if aspect > MAX_ASPECT_RATIO:
        return False
    bytes_per_pixel = len(image_data) / area
    if bytes_per_pixel < MAX_LOW_INFO_BPP and area < MAX_LOW_INFO_AREA:
        return False
    return True


def extract_page(
    doc: fitz.Document,
    page_number: int,
    pdf_path: Path,
    book_id: str,
    size_map: dict[str, float],
    noise_texts: set[str],
    assets_dir: Path | None,
    image_mode: str,
    seen_image_hashes: set[str],
) -> dict[str, Any]:
    page = doc[page_number - 1]
    blocks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            found_tables = page.find_tables()
    except Exception:
        found_tables = []

    table_rects: list[fitz.Rect] = []
    for table_index, table in enumerate(found_tables, 1):
        bbox = list(table.bbox)
        table_rects.append(fitz.Rect(table.bbox))
        try:
            markdown = table.to_markdown()
        except Exception:
            markdown = ""
        tables.append(
            {
                "id": f"p{page_number:03d}-table-{table_index:03d}",
                "bbox": bbox,
                "markdown": markdown,
            }
        )

    text_parts: list[str] = []
    text_block_index = 0
    image_index = 0
    for block in page.get_text("dict").get("blocks", []):
        block_rect = fitz.Rect(block.get("bbox") or (0, 0, 0, 0))
        if any((block_rect & rect).get_area() > 0.6 * block_rect.get_area() for rect in table_rects):
            continue

        block_type = block.get("type")
        if block_type == 0:
            lines: list[str] = []
            max_size = 0.0
            flags = 0
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = clean_text("".join(str(span.get("text") or "") for span in spans))
                if not line_text:
                    continue
                max_size = max(max_size, *(float(span.get("size") or 0) for span in spans))
                for span in spans:
                    flags |= int(span.get("flags") or 0)
                lines.append(line_text)
            text = clean_text("\n".join(lines))
            if not text or text in noise_texts:
                continue
            text_block_index += 1
            level = heading_level(max_size, text, flags, size_map)
            role = "heading" if level else "body"
            block_id = f"p{page_number:03d}-b{text_block_index:03d}"
            blocks.append(
                {
                    "id": block_id,
                    "type": "text",
                    "role": role,
                    "heading_level": level,
                    "bbox": list(block_rect),
                    "text": text,
                }
            )
            text_parts.append(text)
        elif block_type == 1 and image_mode != "none":
            keep = image_mode == "all" or should_keep_image(block, page.rect, seen_image_hashes)
            if not keep:
                continue
            image_data = block.get("image") or b""
            ext = str(block.get("ext") or "png").lower()
            if not isinstance(image_data, bytes):
                continue
            image_index += 1
            asset_id = f"p{page_number:03d}-image-{image_index:03d}"
            filename = f"{book_id}-{asset_id}.{ext}"
            rel_path = None
            if assets_dir is not None:
                assets_dir.mkdir(parents=True, exist_ok=True)
                asset_path = assets_dir / filename
                asset_path.write_bytes(image_data)
                rel_path = str(asset_path)
            assets.append(
                {
                    "id": asset_id,
                    "type": "image",
                    "filename": filename,
                    "path": rel_path,
                    "bbox": list(block.get("bbox") or []),
                    "width": block.get("width"),
                    "height": block.get("height"),
                    "bytes": len(image_data),
                    "sha1": hashlib.sha1(image_data).hexdigest(),
                }
            )

    return {
        "schema": "cgo.textbook_page_cache.v1",
        "kind": "textbook_page_cache",
        "book_id": book_id,
    "source": {
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "pdf_page": page_number,
        },
        "page": {
            "pdf_page": page_number,
            "page_index": page_number - 1,
            "width": page.rect.width,
            "height": page.rect.height,
        },
        "blocks": blocks,
        "tables": tables,
        "assets": assets,
        "text": clean_text("\n\n".join(text_parts)),
        "meta": {
            "extracted_at": utc_now(),
            "tool": "cathygo-knowledge-map/scripts/pdf_source.py",
        },
    }


def extract_pages_pymupdf4llm(
    pdf_path: Path,
    book_id: str,
    page_numbers: list[int],
) -> list[dict[str, Any]]:
    """Extract page caches through PyMuPDF4LLM's local layout-aware Markdown API."""
    pymupdf4llm = require_pymupdf4llm()
    zero_based_pages = [page_number - 1 for page_number in page_numbers]

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        raw_pages = pymupdf4llm.to_markdown(
            str(pdf_path),
            pages=zero_based_pages,
            page_chunks=True,
            write_images=False,
        )
    if isinstance(raw_pages, str):
        raw_pages = [{"text": raw_pages}]
    if not isinstance(raw_pages, list):
        raise RuntimeError("PyMuPDF4LLM returned an unsupported response shape")

    pages_by_number: dict[int, dict[str, Any]] = {}
    with fitz.open(pdf_path) as doc:
        for page_number in page_numbers:
            page = doc[page_number - 1]
            pages_by_number[page_number] = {
                "schema": "cgo.textbook_page_cache.v1",
                "kind": "textbook_page_cache",
                "book_id": book_id,
                "source": {
                    "pdf_name": pdf_path.name,
                    "pdf_path": str(pdf_path),
                    "pdf_page": page_number,
                },
                "page": {
                    "pdf_page": page_number,
                    "page_index": page_number - 1,
                    "width": page.rect.width,
                    "height": page.rect.height,
                },
                "blocks": [],
                "tables": [],
                "assets": [],
                "text": "",
                "meta": {
                    "extracted_at": utc_now(),
                    "tool": "cathygo-knowledge-map/scripts/pdf_source.py",
                    "backend": "pymupdf4llm",
                },
            }

    for fallback_index, item in enumerate(raw_pages):
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        page_number = (
            item.get("page")
            or item.get("page_number")
            or metadata.get("page")
            or metadata.get("page_number")
            or page_numbers[min(fallback_index, len(page_numbers) - 1)]
        )
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = page_numbers[min(fallback_index, len(page_numbers) - 1)]
        if page_number == 0:
            page_number = 1
        if page_number not in pages_by_number and 1 <= page_number + 1 <= max(page_numbers):
            page_number += 1
        if page_number not in pages_by_number:
            page_number = page_numbers[min(fallback_index, len(page_numbers) - 1)]

        text = clean_text(str(item.get("text") or item.get("markdown") or ""))
        blocks = []
        for block_index, block_text in enumerate(markdown_blocks(text), 1):
            blocks.append(
                {
                    "id": f"p{page_number:03d}-md{block_index:03d}",
                    "type": "text",
                    "role": "body",
                    "heading_level": 0,
                    "bbox": None,
                    "text": block_text,
                    "source_backend": "pymupdf4llm",
                }
            )
        page_cache = pages_by_number[page_number]
        page_cache["blocks"] = blocks
        page_cache["text"] = text
        page_cache["meta"]["pymupdf4llm_keys"] = sorted(str(key) for key in item.keys())
        if isinstance(item.get("tables"), list):
            page_cache["tables"] = item["tables"]
        if isinstance(item.get("images"), list):
            page_cache["assets"] = item["images"]

    return [pages_by_number[page_number] for page_number in page_numbers]


def infer_book_id(pdf_path: Path, provided: str | None) -> str:
    if provided:
        return slugify(provided)
    return slugify(pdf_path.stem)


def cmd_index(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).expanduser().resolve()
    book_id = infer_book_id(pdf_path, args.book_id)
    with fitz.open(pdf_path) as doc:
        size_map = analyze_font_sizes(doc)
        noise_texts = detect_headers_footers(doc)
        pages = []
        for page_number, page in enumerate(doc, 1):
            text = clean_text(page.get_text("text"))
            headings: list[str] = []
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = clean_text("".join(str(span.get("text") or "") for span in spans))
                    if not line_text:
                        continue
                    max_size = max((float(span.get("size") or 0) for span in spans), default=0.0)
                    flags = 0
                    for span in spans:
                        flags |= int(span.get("flags") or 0)
                    if heading_level(max_size, line_text, flags, size_map):
                        headings.append(line_text)
            pages.append(
                {
                    "pdf_page": page_number,
                    "char_count": len(text),
                    "headings": headings[:8],
                    "preview": compact_text(text, 260),
                }
            )

    value = {
        "schema": "cgo.textbook_page_map.v1",
        "kind": "textbook_page_map",
        "book_id": book_id,
        "source": {
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
        },
        "page_count": len(pages),
        "font_size_map": size_map,
        "noise_texts": sorted(noise_texts),
        "pages": pages,
        "meta": {
            "created_at": utc_now(),
            "tool": "cathygo-knowledge-map/scripts/pdf_source.py index",
        },
    }
    write_json(Path(args.out), value)
    print(json.dumps({"ok": True, "book_id": book_id, "pages": len(pages), "out": args.out}, ensure_ascii=False))
    return 0


def cmd_extract_pages(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).expanduser().resolve()
    book_id = infer_book_id(pdf_path, args.book_id)
    out_dir = Path(args.out_dir)
    assets_dir = Path(args.assets_dir) if args.assets_dir else out_dir.parent / "assets"
    with fitz.open(pdf_path) as doc:
        pages = parse_page_range(args.pages, len(doc))
    if args.backend == "pymupdf4llm":
        page_caches = extract_pages_pymupdf4llm(pdf_path, book_id, pages)
        written = []
        for page_cache in page_caches:
            page_number = int(page_cache["page"]["pdf_page"])
            out_path = out_dir / f"page-{page_number:03d}.json"
            write_json(out_path, page_cache)
            written.append(str(out_path))
        print(json.dumps({"ok": True, "book_id": book_id, "pages": pages, "backend": args.backend, "written": written}, ensure_ascii=False))
        return 0

    with fitz.open(pdf_path) as doc:
        size_map = analyze_font_sizes(doc)
        noise_texts = detect_headers_footers(doc)
        seen_hashes: set[str] = set()
        written = []
        for page_number in pages:
            page_cache = extract_page(
                doc=doc,
                page_number=page_number,
                pdf_path=pdf_path,
                book_id=book_id,
                size_map=size_map,
                noise_texts=noise_texts,
                assets_dir=assets_dir,
                image_mode=args.images,
                seen_image_hashes=seen_hashes,
            )
            out_path = out_dir / f"page-{page_number:03d}.json"
            write_json(out_path, page_cache)
            written.append(str(out_path))
    print(json.dumps({"ok": True, "book_id": book_id, "pages": pages, "backend": args.backend, "written": written}, ensure_ascii=False))
    return 0


def build_chunks(pages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_texts: list[str] = []
    current_blocks: list[str] = []
    current_pages: list[int] = []

    def flush() -> None:
        if not current_texts:
            return
        index = len(chunks) + 1
        chunks.append(
            {
                "id": f"chunk-{index:03d}",
                "locator": f"pdf-pages:{min(current_pages)}-{max(current_pages)}",
                "pdf_pages": sorted(set(current_pages)),
                "block_ids": list(current_blocks),
                "text": clean_text("\n\n".join(current_texts)),
            }
        )
        current_texts.clear()
        current_blocks.clear()
        current_pages.clear()

    for page in pages:
        pdf_page = int(page["page"]["pdf_page"])
        for block in page.get("blocks") or []:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = clean_text(str(block.get("text") or ""))
            if not text:
                continue
            if current_texts and sum(len(item) for item in current_texts) + len(text) > max_chars:
                flush()
            current_texts.append(text)
            current_blocks.append(str(block.get("id") or ""))
            current_pages.append(pdf_page)
    flush()
    return chunks


def cmd_extract_lesson(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).expanduser().resolve()
    book_id = infer_book_id(pdf_path, args.book_id)
    assets_dir = Path(args.assets_dir) if args.assets_dir else Path(args.out).parent.parent / "assets"
    with fitz.open(pdf_path) as doc:
        page_numbers = parse_page_range(args.pages, len(doc))
    if args.backend == "pymupdf4llm":
        page_caches = extract_pages_pymupdf4llm(pdf_path, book_id, page_numbers)
    else:
        with fitz.open(pdf_path) as doc:
            size_map = analyze_font_sizes(doc)
            noise_texts = detect_headers_footers(doc)
            seen_hashes: set[str] = set()
            page_caches = [
                extract_page(
                    doc=doc,
                    page_number=page_number,
                    pdf_path=pdf_path,
                    book_id=book_id,
                    size_map=size_map,
                    noise_texts=noise_texts,
                    assets_dir=assets_dir,
                    image_mode=args.images,
                    seen_image_hashes=seen_hashes,
                )
                for page_number in page_numbers
            ]

    chunks = build_chunks(page_caches, max_chars=args.max_chunk_chars)
    source_id = f"src:{book_id}:{slugify(args.lesson_id)}"
    for chunk in chunks:
        chunk["source_ref"] = f"{source_id}#{chunk['id']}"

    lesson = {
        "schema": "cgo.textbook_lesson_cache.v1",
        "kind": "textbook_lesson_cache",
        "book_id": book_id,
        "lesson_id": args.lesson_id,
        "title": args.title or args.lesson_id,
        "source": {
            "id": source_id,
            "type": "textbook_pdf",
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "pdf_pages": page_numbers,
        },
        "pages": page_caches,
        "chunks": chunks,
        "assets": [
            asset
            for page in page_caches
            for asset in (page.get("assets") or [])
            if isinstance(asset, dict)
        ],
        "meta": {
            "created_at": utc_now(),
            "tool": "cathygo-knowledge-map/scripts/pdf_source.py extract-lesson",
            "backend": args.backend,
            "copyright_boundary": "local cache only; do not commit textbook excerpts",
        },
    }
    write_json(Path(args.out), lesson)
    print(
        json.dumps(
            {
                "ok": True,
                "book_id": book_id,
                "lesson_id": args.lesson_id,
                "pages": page_numbers,
                "chunks": len(chunks),
                "backend": args.backend,
                "out": args.out,
            },
            ensure_ascii=False,
        )
    )
    return 0


def count_short_blocks(pages: list[dict[str, Any]], threshold: int = 24) -> int:
    count = 0
    for page in pages:
        for block in page.get("blocks") or []:
            if isinstance(block, dict) and len(str(block.get("text") or "").strip()) <= threshold:
                count += 1
    return count


def summarize_lesson_cache(path: Path) -> dict[str, Any]:
    data = load_json(path)
    pages = [page for page in data.get("pages") or [] if isinstance(page, dict)]
    chunks = [chunk for chunk in data.get("chunks") or [] if isinstance(chunk, dict)]
    chunk_lengths = [len(str(chunk.get("text") or "")) for chunk in chunks]
    page_chars = [len(str(page.get("text") or "")) for page in pages]
    return {
        "path": str(path),
        "backend": data.get("meta", {}).get("backend"),
        "pages": len(pages),
        "chunks": len(chunks),
        "blocks": sum(len(page.get("blocks") or []) for page in pages),
        "short_blocks": count_short_blocks(pages),
        "avg_page_chars": round(sum(page_chars) / len(page_chars), 1) if page_chars else 0,
        "avg_chunk_chars": round(sum(chunk_lengths) / len(chunk_lengths), 1) if chunk_lengths else 0,
        "min_chunk_chars": min(chunk_lengths) if chunk_lengths else 0,
        "max_chunk_chars": max(chunk_lengths) if chunk_lengths else 0,
        "first_chunk_preview": compact_text(str(chunks[0].get("text") or ""), 240) if chunks else "",
    }


def cmd_compare_backends(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = []

    for backend in args.backends:
        out_path = out_dir / f"{args.lesson_id}.{backend}.lesson.json"
        lesson_args = argparse.Namespace(
            pdf=str(pdf_path),
            pages=args.pages,
            lesson_id=args.lesson_id,
            title=args.title,
            out=str(out_path),
            assets_dir=None,
            book_id=args.book_id,
            images=args.images,
            max_chunk_chars=args.max_chunk_chars,
            backend=backend,
        )
        try:
            cmd_extract_lesson(lesson_args)
            summaries.append(summarize_lesson_cache(out_path))
        except Exception as exc:
            summaries.append({"backend": backend, "error": str(exc), "path": str(out_path)})

    report = {
        "schema": "cgo.pdf_source_backend_compare.v1",
        "kind": "pdf_source_backend_compare",
        "source": {
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "pages": args.pages,
        },
        "summaries": summaries,
        "meta": {
            "created_at": utc_now(),
            "tool": "cathygo-knowledge-map/scripts/pdf_source.py compare-backends",
        },
    }
    report_path = out_dir / "compare-report.json"
    write_json(report_path, report)
    print(json.dumps({"ok": True, "out": str(report_path), "summaries": summaries}, ensure_ascii=False))
    return 0


def cmd_candidates(args: argparse.Namespace) -> int:
    lesson_path = Path(args.lesson)
    lesson = load_json(lesson_path)
    if lesson.get("schema") != "cgo.textbook_lesson_cache.v1":
        raise ValueError("lesson must use schema cgo.textbook_lesson_cache.v1")

    book_id = str(lesson.get("book_id") or "book")
    lesson_id = str(lesson.get("lesson_id") or lesson_path.stem)
    source = lesson.get("source") if isinstance(lesson.get("source"), dict) else {}
    source_id = str(source.get("id") or f"src:{book_id}:{slugify(lesson_id)}")

    chunks = [chunk for chunk in lesson.get("chunks") or [] if isinstance(chunk, dict)]
    source_chunks = [
        {
            "id": str(chunk.get("id") or f"chunk-{index:03d}"),
            "locator": str(chunk.get("locator") or ""),
            "pdf_pages": chunk.get("pdf_pages") or [],
            "text": compact_text(str(chunk.get("text") or ""), args.excerpt_chars),
        }
        for index, chunk in enumerate(chunks, 1)
    ]

    node_candidates = []
    for chunk in source_chunks:
        source_ref = f"{source_id}#{chunk['id']}"
        node_candidates.append(
            {
                "id": f"candidate:source-chunk:{slugify(lesson_id)}:{chunk['id']}",
                "type": "source_chunk",
                "name": f"{lesson.get('title') or lesson_id} {chunk['id']}",
                "summary": chunk["text"],
                "source_refs": [source_ref],
                "confidence": 1.0,
                "review": {
                    "state": "draft",
                    "notes": "本节点是教材 lesson cache 的本地来源锚点，不是最终知识点。",
                },
                "properties": {
                    "locator": chunk["locator"],
                    "pdf_pages": chunk["pdf_pages"],
                    "local_cache": str(lesson_path),
                },
            }
        )

    batch = {
        "schema": "cgo.kg.candidates.v1",
        "kind": "kg_candidates",
        "id": f"batch:{book_id}:{slugify(lesson_id)}",
        "target_kg": args.target_kg or f"{book_id}-kg",
        "source_batch": {
            "source": {
                "id": source_id,
                "type": "textbook_pdf_lesson_cache",
                "title": lesson.get("title") or lesson_id,
                "origin": {
                    "pdf_name": source.get("pdf_name"),
                    "pdf_path": source.get("pdf_path"),
                    "pdf_pages": source.get("pdf_pages") or [],
                    "lesson_cache": str(lesson_path),
                },
                "chunks": source_chunks,
            },
            "copyright_boundary": "source chunks are for local review; do not publish textbook excerpts",
        },
        "node_candidates": node_candidates,
        "edge_candidates": [],
        "revisions": [],
        "retirements": [],
        "conflicts": [],
        "review_queue": [
            {
                "id": f"review:{slugify(lesson_id)}:extract-concepts",
                "task": "基于 lesson cache 提取稳定概念、过程、实验方法、技能、应用情境和学习素材线索；不要复制教材原文。",
                "source_refs": [f"{source_id}#{chunk['id']}" for chunk in source_chunks],
                "status": "todo",
            },
            {
                "id": f"review:{slugify(lesson_id)}:extract-relations",
                "task": "为候选知识点补充 part_of、requires、extends、applies_to 等关系；证据不足时保持 needs_review。",
                "source_refs": [f"{source_id}#{chunk['id']}" for chunk in source_chunks],
                "status": "todo",
            },
        ],
        "meta": {
            "created_at": utc_now(),
            "tool": "cathygo-knowledge-map/scripts/pdf_source.py candidates",
        },
    }
    write_json(Path(args.out), batch)
    print(
        json.dumps(
            {
                "ok": True,
                "id": batch["id"],
                "node_candidates": len(node_candidates),
                "edge_candidates": 0,
                "out": args.out,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build local PDF source caches and KG candidate scaffolds.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="Create a page map for a PDF")
    index.add_argument("--pdf", required=True, help="Input PDF path")
    index.add_argument("--out", required=True, help="Output page-map JSON")
    index.add_argument("--book-id", default=None, help="Stable book id")
    index.set_defaults(func=cmd_index)

    extract_pages = subparsers.add_parser("extract-pages", help="Extract page-level caches")
    extract_pages.add_argument("--pdf", required=True, help="Input PDF path")
    extract_pages.add_argument("--pages", required=True, help="Pages, e.g. 1-3,8")
    extract_pages.add_argument("--out-dir", required=True, help="Output directory for page JSON")
    extract_pages.add_argument("--assets-dir", default=None, help="Output directory for extracted assets")
    extract_pages.add_argument("--book-id", default=None, help="Stable book id")
    extract_pages.add_argument("--images", choices=["none", "filtered", "all"], default="filtered")
    extract_pages.add_argument("--backend", choices=sorted(BACKENDS), default="pymupdf")
    extract_pages.set_defaults(func=cmd_extract_pages)

    lesson = subparsers.add_parser("extract-lesson", help="Extract lesson-level cache")
    lesson.add_argument("--pdf", required=True, help="Input PDF path")
    lesson.add_argument("--pages", required=True, help="Pages, e.g. 12-20")
    lesson.add_argument("--lesson-id", required=True, help="Stable lesson id")
    lesson.add_argument("--title", default=None, help="Lesson title")
    lesson.add_argument("--out", required=True, help="Output lesson JSON")
    lesson.add_argument("--assets-dir", default=None, help="Output directory for extracted assets")
    lesson.add_argument("--book-id", default=None, help="Stable book id")
    lesson.add_argument("--images", choices=["none", "filtered", "all"], default="filtered")
    lesson.add_argument("--max-chunk-chars", type=int, default=1800)
    lesson.add_argument("--backend", choices=sorted(BACKENDS), default="pymupdf")
    lesson.set_defaults(func=cmd_extract_lesson)

    compare = subparsers.add_parser("compare-backends", help="Compare lesson extraction across PDF backends")
    compare.add_argument("--pdf", required=True, help="Input PDF path")
    compare.add_argument("--pages", required=True, help="Pages, e.g. 12-20")
    compare.add_argument("--lesson-id", required=True, help="Stable lesson id")
    compare.add_argument("--title", default=None, help="Lesson title")
    compare.add_argument("--out-dir", required=True, help="Output directory for comparison artifacts")
    compare.add_argument("--book-id", default=None, help="Stable book id")
    compare.add_argument("--images", choices=["none", "filtered", "all"], default="none")
    compare.add_argument("--max-chunk-chars", type=int, default=1800)
    compare.add_argument("--backends", nargs="+", choices=sorted(BACKENDS), default=["pymupdf", "pymupdf4llm"])
    compare.set_defaults(func=cmd_compare_backends)

    candidates = subparsers.add_parser("candidates", help="Create KG candidate scaffold from lesson cache")
    candidates.add_argument("--lesson", required=True, help="Input lesson cache JSON")
    candidates.add_argument("--out", required=True, help="Output kg-candidates JSON")
    candidates.add_argument("--target-kg", default=None, help="Target KG id")
    candidates.add_argument("--excerpt-chars", type=int, default=220)
    candidates.set_defaults(func=cmd_candidates)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

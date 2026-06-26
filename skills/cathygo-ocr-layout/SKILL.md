---
name: cathygo-ocr-layout
description: Use when extracting OCR Markdown, layout elements, and normalized screenshot candidates from ONE photographed K12/CathyGO problem image with GLM-OCR. Use this as the per-image upstream primitive before answering, grading, or paper segmentation. Do not use to solve questions, produce explanations, segment a multi-question paper, stitch a question across pages, render Web/HTML, or generate final image assets.
---

# CathyGO OCR Layout

Per-image OCR/layout extraction primitive. One photographed image in, deterministic structured layout out. It does not solve, explain, segment, or render.

## Goal

```text
one image
  -> GLM-OCR layout_parsing
  -> md_results + layout_details
  -> normalized text/formula/table/image elements
  -> screenshotCandidates
```

This Skill is the upstream extractor for every photo scenario (single question, cross-page question, full paper). Downstream segmentation is handled by `cathygo-problem-segment`; answering and grading happen in CathyGO Agent solving skills.

## Output contract

Emit `skill="cathygo.ocr_layout"` (see `schemas/ocr-layout-output.schema.json`) with:

- `text.markdown`: raw GLM-OCR Markdown.
- `text.plain`: Markdown with image placeholders and HTML stripped.
- `elements[]`: normalized `text` / `formula` / `table` / `image` / `figure_title` items in reading order.
- `screenshotCandidates[]`: `problem`, optional `diagram_all`, and optional `diagram_1..diagram_n`.
- `diagnostics.rawProvider`: raw provider response for debugging only.

All bbox values exposed downstream MUST be normalized:

```json
{ "x": 0, "y": 0, "width": 1, "height": 1, "unit": "normalized" }
```

If GLM-OCR returns pixel bbox values, divide by page width/height. If it returns `0..1` values, pass them through. This normalized contract is what makes the output portable across Codex, Cursor, and CathyGO Agent.

## Standard call

```bash
ZHIPU_API_KEY=... node scripts/run-zhipu-glm-ocr-layout.mjs \
  --image /path/to/problem.png \
  --out tmp/problem.ocr-layout.json
```

For a multi-page paper, run this Skill once per page image, producing one `*.ocr-layout.json` per page, then pass all of them to `cathygo-problem-segment`.

Use `--visualize` only for debugging. Avoid `--crop-images-debug` (provider crop URLs); CathyGO should crop its own local assets from the source image using the normalized bbox.

## Reasoning handoff

After OCR layout extraction, materialize LLM-ready assets locally:

```bash
npm install --prefix skills/cathygo-ocr-layout

node skills/cathygo-ocr-layout/scripts/build-reasoning-context.mjs \
  --input tmp/page.ocr-layout.json \
  --image /path/to/source.png \
  --out-dir tmp/crops/page \
  --out tmp/page.reasoning-context.json
```

This emits `skill="cathygo.reasoning_context"` with:

- one `text` part from OCR plain/markdown text;
- one `image` part per cropped diagram attachment;
- unique `attachment_id` values such as `att_page_diagram_1`, `att_page_diagram_2`;
- local PNG paths for runtime upload to CathyGO Agent attachments.

Use `--embed-base64` only for local API smoke tests. Production Agent flows should upload the PNG files and pass `attachment_id` references instead of inline base64.

## Hard rules

- Do not generate answers, explanations, CIPF, WebPageSpec, HTML, SVG, or final image files.
- Do not claim provider results before the script returns them.
- Do not commit photographed source images, textbook scans, or real exam OCR output into this repository; keep them under ignored local paths (for example `tmp/`).

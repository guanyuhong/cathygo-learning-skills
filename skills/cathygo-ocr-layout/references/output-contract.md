# CathyGO OCR Layout Output Contract

This reference defines the portable JSON contract for `cathygo.ocr_layout`. Downstream CathyGO Agent, Codex, and Cursor workflows should depend on this shape, not on provider-specific fields.

## Top-level fields

| Field | Required | Notes |
| --- | --- | --- |
| `skill` | yes | Must be `cathygo.ocr_layout` |
| `version` | yes | Current `0.1` |
| `status` | yes | `ok` or `failed` |
| `provider` | yes | `{ name, model }` |
| `sourceImage` | yes | `{ imageId, width, height, mimeType }` |
| `text` | yes | `{ markdown, plain }` |
| `elements` | yes | Normalized layout elements |
| `screenshotCandidates` | yes | Crop targets for downstream asset generation |
| `diagnostics` | yes | Debug metadata; `rawProvider` is diagnostics only |

## Normalized bbox

Every bbox exposed to downstream skills must use:

```json
{ "x": 0, "y": 0, "width": 1, "height": 1, "unit": "normalized" }
```

Rules:

- Coordinates are relative to the source image width and height.
- `x` and `y` are the top-left corner.
- `width` and `height` are positive spans in `0..1`.
- If the provider returns pixel coordinates, divide by page width/height.
- If the provider already returns `0..1` values, pass them through after clamping.

## Element shape

Each `elements[]` item should include:

- `id`: stable local identifier such as `layout_0_1`
- `pageIndex`: zero-based page index inside the source image
- `index`: provider reading index when available
- `type`: `text`, `formula`, `table`, `image`, or `figure_title`
- `label`, `nativeLabel`, `content`
- `bbox`: normalized bbox
- `source`: `{ provider, model, field, imageId }`

## Screenshot candidates

`screenshotCandidates[]` is the bbox source of truth for CathyGO asset cropping:

- `problem`: union of all layout elements on the page
- `diagram_all`: union of all image elements when present
- `diagram_1..diagram_n`: one candidate per image element

Downstream skills must crop local source images using these normalized bbox values. Provider crop URLs in `diagnostics.rawProvider` are debug-only and must not become production assets.

## Downstream handoff

- One photographed page image produces one `cathygo.ocr_layout` JSON.
- Multi-page papers run this primitive once per page, then pass the ordered JSON files to `cathygo-problem-segment`.
- Runtime then materializes `cathygo.reasoning_context` from OCR text plus locally cropped diagram PNG files.
- Solving, grading, explanation, and Web rendering happen in separate downstream skills.

## Reasoning context

`cathygo.reasoning_context` is the assembly format for downstream LLM calls:

- `parts[]`: one `text` part, then one `image` part per attachment;
- `attachments[]`: cropped PNG metadata with unique `attachment_id` values such as `att_<scope>_diagram_1`;
- `bbox` stays in attachment metadata for traceability, but the model consumes image pixels through attachments rather than bbox numbers.

Use `scripts/crop-layout-assets.mjs` to crop PNG files and `scripts/build-reasoning-context.mjs` to assemble the final bundle.

## Clean-room boundary

- Do not commit photographed source images, textbook scans, or real exam OCR output into this repository.
- Keep local debug artifacts under ignored paths such as `tmp/`.
- Examples in this Skill must use synthetic prompts and synthetic OCR output only.

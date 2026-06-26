---
name: cathygo-problem-segment
description: Use when turning one or more cathygo.ocr_layout JSON files into a normalized cathygo.problem_set with single-question, cross-page stitch, or multi-question paper segmentation. Use after cathygo-ocr-layout has produced per-page layout JSON. Do not use to call GLM-OCR, solve questions, grade answers, render Web/HTML, or generate final image assets.
---

# CathyGO Problem Segment

Structure layer for photographed K12 content. It consumes ordered per-page OCR layout JSON and emits a normalized problem set for CathyGO Agent, Codex, and Cursor workflows.

## Goal

```text
1..N cathygo.ocr_layout JSON (one per photographed page)
  -> section / question segmentation
  -> optional cross-page continuation merge
  -> cathygo.problem_set JSON
```

This Skill does not OCR images, solve questions, or render pages. Upstream OCR is `cathygo-ocr-layout`; downstream solving happens in CathyGO Agent skills such as `math-photo-quick-answer`.

## Modes

| Mode | Use when |
| --- | --- |
| `single` | One photographed page with one question |
| `stitch` | One question intentionally spans multiple photographed pages |
| `paper` | A worksheet or exam page with sections and numbered questions |
| `auto` | The caller does not know the scenario; run paper rules and infer the effective result |

`auto` is the default. It runs paper segmentation and reports `single`, `stitch`, or `paper` based on the resulting page and problem counts.

## Output contract

Emit `skill="cathygo.problem_set"` (see `schemas/problem-set-output.schema.json`) with:

- `mode`: requested or inferred segmentation mode
- `pages[]`: ordered page metadata from the input layout files
- `problems[]`: normalized questions with `number`, `section`, `type`, `pageSpan`, `textMarkdown`, `textPlain`, `elementRefs`, `screenshotCandidates`, `continuedFrom`, `continuesTo`
- `diagnostics`: page count, problem count, and cross-page problem count

BBox values in `screenshotCandidates` remain normalized, matching the upstream `cathygo.ocr_layout` contract.

## Standard call

```bash
node scripts/segment-problem-set.mjs \
  --pages tmp/page-1.ocr-layout.json tmp/page-2.ocr-layout.json \
  --mode auto \
  --out tmp/problem-set.json
```

Typical pipeline:

```text
photo page(s)
  -> cathygo-ocr-layout (once per page)
  -> cathygo-problem-segment
  -> CathyGO Agent solving / grading skills
```

## Hard rules

- Require valid `cathygo.ocr_layout` input for every page.
- Do not invent OCR text or bbox values that are not present in the input layouts.
- Do not generate answers, explanations, CIPF, WebPageSpec, HTML, SVG, or final image files.
- Do not commit photographed source images, textbook scans, or real exam OCR output into this repository.

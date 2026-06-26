# CathyGO Problem Segmentation Rules

Original heuristic rules for `cathygo-problem-segment`. These rules operate on normalized `cathygo.ocr_layout` elements in global reading order.

## Input assumptions

- Each photographed page produces one `cathygo.ocr_layout` JSON.
- Page order follows the `--pages` argument order.
- Elements already use normalized bbox values and provider reading order.

## Section detection

Treat a text element as a section header when its trimmed content matches:

```text
^[一二三四五六七八九十百千]+[、．.]\s*.+题
```

Examples:

- `一、选择题`
- `二、填空题`
- `三、解答题`

A section header updates the active section but does not by itself start a numbered problem.

## Problem start detection

Treat a text element as a new numbered problem when its trimmed content matches:

```text
^\s*(\d+)\s*[.、．)]\s*
```

and it is not a sub-question marker.

Captured group `1` becomes the problem `number`.

## Sub-question handling

Treat these as sub-parts of the current problem, not new top-level problems:

```text
^\s*[（(]\s*\d+\s*[）)]\s*
```

Examples:

- `（1）求 x 的值`
- `(2) explain why`

## Cross-page continuation

In `paper` mode, elements are processed sequentially across pages. A new problem starts only when a numbered problem header is detected.

If page 2 begins with continuation text instead of a new `N.` header, those elements stay in the current problem. The resulting `pageSpan` expands to include every page touched by that problem.

Use `stitch` mode when the caller already knows the input is one question across multiple photographed pages and does not want numbered-question splitting.

## Problem type inference

Infer `problems[].type` from the active section label:

| Section signal | Type |
| --- | --- |
| contains `选择` | `choice` |
| contains `填空` | `fill` |
| contains `解答`, `计算`, `证明`, or `应用` | `solve` |
| otherwise | `unknown` |

## Screenshot candidate generation

For each problem:

- Create one `problem_crop` per page that contains problem elements, using the union bbox of those elements on that page.
- Create `diagram_1..diagram_n` for image elements assigned to the problem.

## Mode summary

| Mode | Behavior |
| --- | --- |
| `single` | Force all elements into one problem |
| `stitch` | Merge all pages into one cross-page problem |
| `paper` | Apply section and numbered-question rules |
| `auto` | Run `paper`, then infer `single`, `stitch`, or `paper` from the result |

## Clean-room boundary

Examples and eval cases must use synthetic worksheet text only. Do not store photographed exams, textbook scans, or publisher page recreations in this Skill.

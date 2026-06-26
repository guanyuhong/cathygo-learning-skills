# KG Extraction Rules

## Create Nodes Only When

Create a node when source material supports at least one of:

- a concept with definition or explanation;
- a skill the learner must perform;
- a procedure with ordered steps;
- a misconception or barrier;
- an assessment target;
- a task/application context;
- a curriculum anchor or source chunk needed for traceability.

Do not create nodes for generic headings such as "Introduction" unless the heading is itself a teachable knowledge point.

## Create Edges Only When

Use explicit evidence first:

- `requires`: "需要先掌握", "depends on", "foundation", "before learning".
- `part_of`: "包括", "由...组成", "contains", "component".
- `extends`: "进一步", "推广", "extension", "advanced form".
- `applies_to`: "用于", "应用于", "solve", "model", "explain".
- `confuses_with`: "容易混淆", "not the same as", "误把".
- `misconception_of`: "常见错误", "错误认为", "trap".
- `assesses`: "检测", "考查", "practice checks".
- `remediates`: "纠正", "补救", "repair", "intervention".

If the source only says two concepts are connected but not how, use `related_to` with `review.state="needs_review"` and explain why relation typing is unresolved.

## Confidence

- `0.95-1.0`: directly encoded in structured fields or explicit source wording.
- `0.80-0.94`: explicit but normalized across wording, language, or ID.
- `0.60-0.79`: plausible from local context; needs review before runtime use.
- `<0.60`: keep in candidates; do not merge unless explicitly accepted.

## Duplicate Control

Before creating a node:

1. Search exact ID.
2. Search normalized name and aliases.
3. Search within the same subject/stage/curriculum.
4. If likely duplicate, create `same_as` candidate or revise the existing node instead of adding a new node.

## Clean-Room Boundaries

Store only source references and short review excerpts when source material may be copyrighted. Do not commit textbook pages, scans, copied exercises, or long copied prose.

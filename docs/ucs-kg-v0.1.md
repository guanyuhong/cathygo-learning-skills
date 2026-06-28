# UCS-KG v0.1

UCS-KG is CathyGO's curriculum-standard graph format. It preserves curriculum
standards before they are distilled into CathyGO learning content.

## Shape

```json
{
  "schema_version": "ucs-kg-v0.1",
  "dataset_id": "cn-math-2022",
  "metadata": {},
  "curricula": [],
  "framework_nodes": [],
  "standard_items": [],
  "concepts": [],
  "competencies": [],
  "learning_evidence": [],
  "activities": [],
  "assessments": [],
  "relations": [],
  "alignments": []
}
```

## Layers

- `curricula`: curriculum metadata such as country, subject, language, version,
  publisher, and source.
- `framework_nodes`: structure such as stage, grade band, domain, theme, topic,
  cluster, or standard group.
- `standard_items`: faithful curriculum statements. Do not collapse these into
  knowledge points.
- `concepts`: teachable, assessable, diagnosable knowledge nodes distilled from
  one or more standard items.
- `competencies`: transferable abilities, practices, literacies, or core
  competencies.
- `learning_evidence`: observable learner behaviors that prove mastery.
- `activities` and `assessments`: source-backed or clean-room learning and
  evaluation tasks.
- `relations`: typed links inside the dataset.
- `alignments`: cross-curriculum mappings.

## Required Validation

- `schema_version` must be `ucs-kg-v0.1`.
- All IDs are globally unique across object arrays.
- `curriculum_id`, `parent_id`, `framework_node_ids`, `source_standard_ids`,
  `concept_id`, `concept_ids`, `competency_ids`, and relation endpoints must
  resolve.
- `confidence`, when present, must be in `[0, 1]`.
- Concepts should include `source_standard_ids` and at least one linked
  learning evidence item.
- Standard items should include source information.

## Export Pipeline

Use `skills/cathygo-knowledge-map/scripts/ucs_kg.py`:

```bash
python skills/cathygo-knowledge-map/scripts/ucs_kg.py validate \
  --input content/curricula/cn-math-2022/ucs-kg.json

python skills/cathygo-knowledge-map/scripts/ucs_kg.py export-candidates \
  --input content/curricula/cn-math-2022/ucs-kg.json \
  --out content/curricula/cn-math-2022/cgo-kg-candidates.json

python skills/cathygo-knowledge-map/scripts/ucs_kg.py export-cgo-kg \
  --input content/curricula/cn-math-2022/ucs-kg.json \
  --out content/curricula/cn-math-2022/cgo-kg.json

python skills/cathygo-knowledge-map/scripts/kg.py export-product \
  --kg content/curricula/cn-math-2022/cgo-kg.json \
  --out content/curricula/cn-math-2022/exports/knowledge-map-data.json
```

Keep OCR output and textbook/page excerpts under `tmp/textbook-cache/`. Public
content should contain clean-room statements plus source refs, not copied
textbook pages or long source excerpts.

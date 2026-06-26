# CathyGO KG Contract

`kg.json` is the canonical content-production graph. It must be usable by authoring agents, review tools, and future CathyGO Agent exporters.

## Top-Level Shape

```json
{
  "schema": "cgo.kg.v1",
  "kind": "kg",
  "id": "math-grade7-fractions",
  "title": "Grade 7 Algebraic Fractions",
  "version": "0.1.0",
  "language": "zh-CN",
  "profile": "learning-kg",
  "meta": {},
  "compat": {},
  "sources": [],
  "nodes": [],
  "edges": [],
  "collections": [],
  "views": [],
  "quality": {}
}
```

## Sources

Sources preserve provenance and future compatibility.

```json
{
  "id": "src-fractions-note-001",
  "type": "markdown",
  "title": "Original algebraic fractions notes",
  "origin": {
    "path": "examples/fractions-source.md",
    "provider": "local",
    "license": "original"
  },
  "chunks": [
    {
      "id": "c001",
      "locator": "paragraph:1",
      "text": "Short review excerpt or summary."
    }
  ]
}
```

Use source refs as `source_id#chunk_id`. If only whole-file provenance is known, use `source_id`.

## Nodes

Required:

- `id`: stable graph ID.
- `type`: canonical node type.
- `name`: learner-facing or author-facing name.
- `source_refs`: source references unless the node is an internal collection anchor.
- `confidence`: `0..1`.
- `review.state`: `accepted`, `needs_review`, `rejected`, or `draft`.

Recommended:

- `definition`
- `summary`
- `aliases`
- `subject`
- `stage`
- `grade_band`
- `curriculum`
- `tags`
- `compat.external_ids`
- `properties.raw`

## Edges

Required:

- `id`
- `type`
- `source`
- `target`
- `evidence` or `reason`
- `source_refs`
- `confidence`
- `review.state`

Direction rules:

- `requires`: prerequisite `source` -> dependent `target`.
- `part_of`: component `source` -> parent `target`.
- `extends`: base/simple `source` -> extension `target`.
- `applies_to`: concept/skill `source` -> task/context `target`.
- `procedure_step_of`: step `source` -> procedure `target`.
- `misconception_of`: misconception `source` -> target concept `target`.
- `assesses`: assessment `source` -> assessed node `target`.
- `remediates`: remediation `source` -> misconception/barrier `target`.
- `same_as`: canonical node `source` -> duplicate/alias node `target`.
- `confuses_with` and `related_to`: store one canonical edge only.

## Candidate Batches

`kg-candidates.json` is not a disposable patch. It is a reviewed production record:

```json
{
  "schema": "cgo.kg.candidates.v1",
  "kind": "kg_candidates",
  "id": "batch-001",
  "target_kg": "math-grade7-fractions",
  "source_batch": {},
  "node_candidates": [],
  "edge_candidates": [],
  "revisions": [],
  "retirements": [],
  "conflicts": [],
  "review_queue": []
}
```

Use candidate batches for iterative production, imports, reviewer decisions, and audit trails.

## Compatibility

Put external integration details in `compat`:

```json
{
  "compat": {
    "external_ids": {
      "teachany": "math-m-fraction-equation"
    },
    "exports": {
      "cathygo-agent": {
        "preferred_extract_depth": 2
      }
    }
  }
}
```

The core graph must remain meaningful without any external system.

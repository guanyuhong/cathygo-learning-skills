---
name: cathygo-kg-build
description: Use when building, iterating, validating, searching, or extracting CathyGO learning knowledge graphs from source materials such as OCR text, Markdown notes, curriculum outlines, structured JSON, or reviewed authoring drafts. Do not use for live tutoring answers, generic lesson planning without graph artifacts, or copying textbook material into a Skill.
---

# CathyGO KG Build

Use this Skill for content production workflows that create or improve a durable CathyGO learning knowledge graph. A KG is not just a patch target; it is a versioned artifact that must preserve provenance, review state, relationship semantics, and compatibility metadata.

## Artifacts

Use short names for files and explicit schema names inside files:

- `kg.json`: canonical graph, `schema="cgo.kg.v1"`.
- `kg-candidates.json`: candidate batch, `schema="cgo.kg.candidates.v1"`.
- `kg.report.md`: graph health report.
- `kg.review.md`: human review queue for unresolved or weak claims.
- `subgraph.json`: focused graph extract for downstream task/courseware generation.

## When Building

1. Scope subject, learner band, source list, and downstream compatibility.
2. Inventory sources and chunks before extracting nodes.
3. Search the existing graph before adding nodes.
4. Extract candidates with source references, confidence, evidence, and review state.
5. Merge only accepted or high-confidence well-evidenced candidates.
6. Validate graph structure, edge endpoints, evidence, duplicate risk, and prerequisite cycles.
7. Produce `kg.report.md` and `kg.review.md` before handoff.

## Core Graph Contract

Read `references/kg-contract.md` before authoring or changing graph JSON.

Canonical node types:

- `concept`
- `skill`
- `procedure`
- `misconception`
- `task`
- `assessment`
- `resource`
- `curriculum`
- `source_chunk`

Canonical edge types:

- `requires`: prerequisite to dependent node.
- `part_of`: component to parent.
- `extends`: base/simple node to extension node.
- `applies_to`: concept/skill to task/context.
- `procedure_step_of`: step to procedure.
- `confuses_with`: likely confusion pair.
- `misconception_of`: misconception to target concept.
- `assesses`: assessment to target node.
- `remediates`: remediation to barrier or misconception.
- `same_as`: canonical node to duplicate/alias node.
- `related_to`: last resort, requires review reason.

## Commands

Run commands from this Skill directory:

```bash
python3 scripts/kg.py validate --kg examples/kg.sample.json
python3 scripts/kg.py report --kg examples/kg.sample.json --out /tmp/kg.report.md
python3 scripts/kg.py search --kg examples/kg.sample.json --query "denominator" --limit 5
python3 scripts/kg.py extract --kg examples/kg.sample.json --center denominator-not-zero --depth 2 --out /tmp/subgraph.json
python3 scripts/kg.py validate-candidates --candidates examples/kg-candidates.sample.json
python3 scripts/kg.py merge --kg examples/kg.sample.json --candidates examples/kg-candidates.sample.json --out /tmp/kg.next.json
```

Use `ingest` to create source-only candidate batches from Markdown/TXT, or conservative candidates from simple structured JSON:

```bash
python3 scripts/kg.py ingest --input examples/fractions-source.md --out /tmp/kg-candidates.json --source-id fractions-note-001
```

## Search And Extract

Use graph retrieval during authoring:

- Search before creating nodes to avoid duplicates.
- Extract a small neighborhood around a center node before generating taskware or courseware.
- Extract edges by type to audit prerequisites, misconceptions, or assessments.
- Do not pass a whole graph into downstream generation if a focused subgraph is enough.

## Review Rules

Block promotion to canonical KG when:

- a node lacks source references;
- an edge lacks evidence or reason;
- a relation type is unclear but not marked `related_to`;
- `requires` creates a cycle;
- duplicate risk is unresolved;
- source material cannot be stored clean-room.

## Compatibility

Keep CathyGO schema stable. Put external IDs and import-specific fields under `compat` or `properties.raw`. Do not make the canonical graph depend on TeachAny, a vector DB, or a runtime service.

## Clean-Room Rule

Do not commit textbook PDFs, scans, screenshots, copied textbook prose, copied exercises, publisher diagrams, or answer keys. Store source references and short review excerpts only when legally appropriate.

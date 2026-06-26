# Retrieval And Extract

KG production includes retrieval because agents need to inspect the graph before creating or using content.

## Search

```bash
python3 scripts/kg.py search --kg kg.json --query "common denominator" --limit 10
```

Search fields:

- node `id`
- `name`
- `aliases`
- `definition`
- `summary`
- `tags`
- edge `type`, `label`, `evidence`, `reason`

Search is lexical and dependency-free.

## Extract

```bash
python3 scripts/kg.py extract --kg kg.json --center denominator-not-zero --depth 2 --out subgraph.json
```

Default extraction treats edges as undirected for neighborhood discovery but preserves edge direction in output.

Use extracted subgraphs for:

- taskware generation;
- review of a node family;
- concept remediation planning;
- edge type audits;
- small model-context handoff.

## Review Queries

```bash
python3 scripts/kg.py report --kg kg.json --out kg.report.md
python3 scripts/kg.py search --kg kg.json --query "needs_review"
python3 scripts/kg.py extract --kg kg.json --center <node-id> --depth 1 --edge-type requires
```

Do not pass a large full graph into a lesson-generation prompt when a focused subgraph is enough.

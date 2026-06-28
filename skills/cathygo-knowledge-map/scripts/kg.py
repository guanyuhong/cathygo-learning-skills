#!/usr/bin/env python3
"""CathyGO KG authoring helper.

Commands:
- ingest: create a conservative candidate batch from Markdown/TXT or simple JSON.
- validate: validate canonical cgo.kg.v1 graph health.
- validate-candidates: validate cgo.kg.candidates.v1 candidate batches.
- merge: merge accepted or high-confidence candidates into a graph.
- search: lexical search across nodes and edges.
- extract: extract a focused subgraph around a center node.
- report: write a Markdown graph health report.
- export-product: export cgo.kg.v1 to the product knowledge-map-data shape.
- validate-product: validate the product knowledge-map-data shape.

The script intentionally has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NODE_TYPES = {
    "concept",
    "skill",
    "procedure",
    "misconception",
    "task",
    "assessment",
    "resource",
    "curriculum",
    "source_chunk",
}

EDGE_TYPES = {
    "requires",
    "part_of",
    "extends",
    "applies_to",
    "procedure_step_of",
    "confuses_with",
    "misconception_of",
    "assesses",
    "remediates",
    "same_as",
    "related_to",
}

REVIEW_STATES = {"accepted", "needs_review", "rejected", "draft"}
SYMMETRIC_EDGE_TYPES = {"confuses_with", "related_to", "same_as"}
KNOWLEDGE_GROUP_NODE_TYPES = {"domain", "knowledge_group"}
KNOWLEDGE_GROUP_EDGE_TYPES = {"part_of", "requires", "extends", "related_to", "applies_to"}
KNOWLEDGE_GROUP_EXPORT_EDGE_TYPES = {"part_of", "requires", "extends", "related_to", "applies_to"}
PRODUCT_NODE_FIELDS = [
    "id",
    "name",
    "name_en",
    "subject",
    "grade",
    "domain",
    "difficulty",
    "definition",
    "skills",
    "stage",
    "curriculum",
    "tree_path",
    "display_name",
]
PRODUCT_DEFAULT_EDGE_TYPES = {
    "requires",
    "part_of",
    "extends",
    "applies_to",
    "procedure_step_of",
    "assesses",
    "related_to",
}
PRODUCT_DEFAULT_NODE_TYPES = {
    "concept",
    "skill",
    "procedure",
    "task",
    "assessment",
}
SUBJECT_SLUGS = {
    "\u79d1\u5b66": "science",
    "\u7269\u7406": "physics",
    "\u5316\u5b66": "chemistry",
    "\u751f\u7269": "biology",
    "\u6570\u5b66": "math",
    "\u8bed\u6587": "chinese",
    "\u82f1\u8bed": "english",
    "\u5730\u7406": "geography",
    "\u5386\u53f2": "history",
    "\u9053\u5fb7\u4e0e\u6cd5\u6cbb": "morality-law",
    "\u4fe1\u606f\u6280\u672f": "it",
}
STAGE_SLUGS = {
    "\u5c0f\u5b66": "elementary",
    "\u521d\u4e2d": "middle",
    "\u9ad8\u4e2d": "high",
    "\u5927\u5b66": "university",
}
GRADE_CHARS = {
    "\u4e00": 1,
    "\u4e8c": 2,
    "\u4e09": 3,
    "\u56db": 4,
    "\u4e94": 5,
    "\u516d": 6,
    "\u4e03": 7,
    "\u516b": 8,
    "\u4e5d": 9,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_/|:;,.()\[\]{}]+", "-", text)
    text = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text:
        return text
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]


def stable_edge_id(edge_type: str, source: str, target: str) -> str:
    if edge_type in SYMMETRIC_EDGE_TYPES:
        source, target = sorted([source, target])
    raw = f"{edge_type}|{source}|{target}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"edge:{edge_type}:{slugify(source)}:{slugify(target)}:{digest}"


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def review_state(item: dict[str, Any]) -> str:
    review = item.get("review")
    if isinstance(review, dict):
        state = str(review.get("state") or "").strip()
        if state:
            return state
    return ""


def confidence(item: dict[str, Any]) -> float | None:
    value = item.get("confidence")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_promotable(item: dict[str, Any]) -> bool:
    state = review_state(item)
    if state == "rejected":
        return False
    if state == "accepted":
        return True
    conf = confidence(item)
    return bool(conf is not None and conf >= 0.8 and as_list(item.get("source_refs")))


def normalize_name(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("subject") or ""),
        str(item.get("stage") or ""),
        str(item.get("curriculum") or ""),
        str(item.get("name") or ""),
    ]
    return "|".join(slugify(part) for part in parts)


def collect_source_refs(kg: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for source in kg.get("sources") or []:
        if not isinstance(source, dict) or not source.get("id"):
            continue
        sid = str(source["id"])
        refs.add(sid)
        for chunk in source.get("chunks") or []:
            if isinstance(chunk, dict) and chunk.get("id"):
                refs.add(f"{sid}#{chunk['id']}")
    return refs


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if value and count > 1)


def detect_requires_cycle(nodes: set[str], edges: list[dict[str, Any]]) -> list[str]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("type") == "requires":
            graph[str(edge.get("source"))].append(str(edge.get("target")))

    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> list[str]:
        visiting.add(node)
        path.append(node)
        for nxt in graph.get(node, []):
            if nxt in visiting:
                idx = path.index(nxt) if nxt in path else 0
                return path[idx:] + [nxt]
            if nxt not in visited:
                found = dfs(nxt)
                if found:
                    return found
        visiting.remove(node)
        visited.add(node)
        path.pop()
        return []

    for node in sorted(nodes):
        if node not in visited:
            found = dfs(node)
            if found:
                return found
    return []


def validate_kg(kg: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if kg.get("schema") != "cgo.kg.v1":
        errors.append("top-level schema must be cgo.kg.v1")
    if kg.get("kind") != "kg":
        errors.append("top-level kind must be kg")

    sources = kg.get("sources") or []
    nodes = kg.get("nodes") or []
    edges = kg.get("edges") or []
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        sources = []
    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []

    source_ids = [str(s.get("id") or "") for s in sources if isinstance(s, dict)]
    for sid in duplicate_values(source_ids):
        errors.append(f"duplicate source id: {sid}")
    known_refs = collect_source_refs(kg)

    node_ids = [str(n.get("id") or "") for n in nodes if isinstance(n, dict)]
    for nid in duplicate_values(node_ids):
        errors.append(f"duplicate node id: {nid}")
    node_set = set(node_ids)

    name_index: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("node entry must be an object")
            continue
        nid = str(node.get("id") or "")
        if not nid:
            errors.append("node missing id")
        if node.get("type") not in NODE_TYPES:
            errors.append(f"node {nid} has invalid type: {node.get('type')}")
        if not str(node.get("name") or "").strip():
            errors.append(f"node {nid} missing name")
        state = review_state(node)
        if state and state not in REVIEW_STATES:
            errors.append(f"node {nid} has invalid review state: {state}")
        conf = confidence(node)
        if conf is None:
            errors.append(f"node {nid} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"node {nid} confidence outside [0,1]")
        refs = [str(ref) for ref in as_list(node.get("source_refs")) if str(ref).strip()]
        if node.get("type") != "source_chunk" and not refs:
            errors.append(f"node {nid} missing source_refs")
        for ref in refs:
            if known_refs and ref not in known_refs:
                warnings.append(f"node {nid} references unknown source ref: {ref}")
        name_index[normalize_name(node)].append(nid)

    for key, ids in name_index.items():
        if key.strip("|") and len(ids) > 1:
            warnings.append(f"duplicate name risk: {', '.join(ids)}")

    edge_ids = [str(e.get("id") or "") for e in edges if isinstance(e, dict)]
    for eid in duplicate_values(edge_ids):
        errors.append(f"duplicate edge id: {eid}")

    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("edge entry must be an object")
            continue
        eid = str(edge.get("id") or "")
        etype = edge.get("type")
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if not eid:
            errors.append("edge missing id")
        if etype not in EDGE_TYPES:
            errors.append(f"edge {eid} has invalid type: {etype}")
        if source not in node_set:
            errors.append(f"edge {eid} source missing: {source}")
        if target not in node_set:
            errors.append(f"edge {eid} target missing: {target}")
        if source == target:
            errors.append(f"edge {eid} self-loop is not allowed")
        if not str(edge.get("evidence") or edge.get("reason") or "").strip():
            errors.append(f"edge {eid} missing evidence or reason")
        refs = [str(ref) for ref in as_list(edge.get("source_refs")) if str(ref).strip()]
        if not refs:
            errors.append(f"edge {eid} missing source_refs")
        for ref in refs:
            if known_refs and ref not in known_refs:
                warnings.append(f"edge {eid} references unknown source ref: {ref}")
        state = review_state(edge)
        if state and state not in REVIEW_STATES:
            errors.append(f"edge {eid} has invalid review state: {state}")
        conf = confidence(edge)
        if conf is None:
            errors.append(f"edge {eid} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"edge {eid} confidence outside [0,1]")
        if etype == "related_to" and state == "accepted":
            warnings.append(f"edge {eid} is accepted related_to; consider stronger typing")

    cycle = detect_requires_cycle(node_set, [e for e in edges if isinstance(e, dict)])
    if cycle:
        errors.append("requires cycle: " + " -> ".join(cycle))

    return errors, warnings


def validate_candidates(batch: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if batch.get("schema") != "cgo.kg.candidates.v1":
        errors.append("top-level schema must be cgo.kg.candidates.v1")
    if batch.get("kind") != "kg_candidates":
        errors.append("top-level kind must be kg_candidates")
    node_candidates = batch.get("node_candidates") or []
    edge_candidates = batch.get("edge_candidates") or []
    if not isinstance(node_candidates, list):
        errors.append("node_candidates must be a list")
        node_candidates = []
    if not isinstance(edge_candidates, list):
        errors.append("edge_candidates must be a list")
        edge_candidates = []

    seen_nodes: set[str] = set()
    for node in node_candidates:
        if not isinstance(node, dict):
            errors.append("node candidate must be an object")
            continue
        nid = str(node.get("id") or "")
        if not nid:
            errors.append("node candidate missing id")
        if nid in seen_nodes:
            errors.append(f"duplicate node candidate id: {nid}")
        seen_nodes.add(nid)
        if node.get("type") not in NODE_TYPES:
            errors.append(f"node candidate {nid} has invalid type: {node.get('type')}")
        if not str(node.get("name") or "").strip():
            errors.append(f"node candidate {nid} missing name")
        if not as_list(node.get("source_refs")):
            errors.append(f"node candidate {nid} missing source_refs")
        state = review_state(node)
        if state and state not in REVIEW_STATES:
            errors.append(f"node candidate {nid} has invalid review state: {state}")
        conf = confidence(node)
        if conf is None:
            errors.append(f"node candidate {nid} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"node candidate {nid} confidence outside [0,1]")

    seen_edges: set[str] = set()
    for edge in edge_candidates:
        if not isinstance(edge, dict):
            errors.append("edge candidate must be an object")
            continue
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        etype = str(edge.get("type") or "")
        eid = str(edge.get("id") or "") or stable_edge_id(etype, source, target)
        if eid in seen_edges:
            errors.append(f"duplicate edge candidate id: {eid}")
        seen_edges.add(eid)
        if etype not in EDGE_TYPES:
            errors.append(f"edge candidate {eid} has invalid type: {etype}")
        if not source or not target:
            errors.append(f"edge candidate {eid} missing endpoint")
        if source == target:
            errors.append(f"edge candidate {eid} self-loop is not allowed")
        if not str(edge.get("evidence") or edge.get("reason") or "").strip():
            errors.append(f"edge candidate {eid} missing evidence or reason")
        if not as_list(edge.get("source_refs")):
            errors.append(f"edge candidate {eid} missing source_refs")
        state = review_state(edge)
        if state and state not in REVIEW_STATES:
            errors.append(f"edge candidate {eid} has invalid review state: {state}")
        conf = confidence(edge)
        if conf is None:
            errors.append(f"edge candidate {eid} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"edge candidate {eid} confidence outside [0,1]")
        if etype == "related_to" and state != "needs_review":
            warnings.append(f"edge candidate {eid} related_to should normally need review")
    return errors, warnings


def split_text_chunks(text: str) -> list[dict[str, str]]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[dict[str, str]] = []
    for idx, paragraph in enumerate(paragraphs, start=1):
        chunks.append(
            {
                "id": f"c{idx:03d}",
                "locator": f"paragraph:{idx}",
                "text": paragraph[:1200],
            }
        )
    return chunks


def command_ingest(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    source_id = args.source_id or slugify(input_path.stem)
    source_type = "markdown" if input_path.suffix.lower() in {".md", ".markdown"} else "text"
    batch = {
        "schema": "cgo.kg.candidates.v1",
        "kind": "kg_candidates",
        "id": args.batch_id or f"batch-{source_id}",
        "target_kg": args.target_kg or "",
        "source_batch": {
            "id": source_id,
            "sources": [],
        },
        "node_candidates": [],
        "edge_candidates": [],
        "revisions": [],
        "retirements": [],
        "conflicts": [],
        "review_queue": [],
    }

    if input_path.suffix.lower() in {".json"}:
        payload = load_json(input_path)
        if payload.get("schema") == "cgo.kg.v1":
            batch["source_batch"]["sources"] = payload.get("sources") or []
            batch["node_candidates"] = payload.get("nodes") or []
            batch["edge_candidates"] = payload.get("edges") or []
        else:
            batch["node_candidates"] = normalize_import_nodes(payload.get("nodes") or [], source_id)
            batch["edge_candidates"] = normalize_import_edges(payload.get("edges") or [])
    else:
        text = input_path.read_text(encoding="utf-8")
        chunks = split_text_chunks(text)
        batch["source_batch"]["sources"] = [
            {
                "id": source_id,
                "type": source_type,
                "title": args.title or input_path.stem,
                "origin": {
                    "path": str(input_path),
                    "provider": "local",
                    "license": args.license or "unknown",
                },
                "chunks": chunks,
            }
        ]
        batch["review_queue"].append(
            {
                "id": f"review-{source_id}",
                "type": "source_extraction",
                "reason": "Source chunks created. Agent must author grounded node and edge candidates from chunks.",
                "source_refs": [f"{source_id}#{chunk['id']}" for chunk in chunks],
            }
        )

    write_json(Path(args.out), batch)
    print(f"wrote {args.out}")
    return 0


def normalize_import_nodes(items: list[Any], source_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nid = str(item.get("id") or slugify(item.get("name") or item.get("name_en") or "node"))
        node = {
            "id": nid,
            "type": item.get("type") if item.get("type") in NODE_TYPES else "concept",
            "name": item.get("name") or item.get("display_name") or item.get("name_en") or nid,
            "aliases": [x for x in [item.get("display_name"), item.get("name_en")] if x],
            "definition": item.get("definition") or "",
            "subject": item.get("subject") or "",
            "stage": item.get("stage") or "",
            "curriculum": item.get("curriculum") or "",
            "tags": [str(item.get("domain"))] if item.get("domain") else [],
            "source_refs": as_list(item.get("source_refs")) or [source_id],
            "confidence": float(item.get("confidence") or 0.75),
            "review": item.get("review") if isinstance(item.get("review"), dict) else {"state": "needs_review", "reason": "Imported structured node needs review."},
            "compat": {
                "external_ids": {},
            },
            "properties": {
                "raw": item,
            },
        }
        out.append(node)
    return out


def normalize_import_edges(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or item.get("from") or "")
        target = str(item.get("target") or item.get("to") or "")
        if not source or not target:
            continue
        etype = item.get("type") if item.get("type") in EDGE_TYPES else "related_to"
        edge = {
            "id": item.get("id") or stable_edge_id(etype, source, target),
            "type": etype,
            "source": source,
            "target": target,
            "evidence": item.get("evidence") or "",
            "reason": item.get("reason") or "Imported edge did not provide enough relationship semantics.",
            "source_refs": as_list(item.get("source_refs")),
            "confidence": float(item.get("confidence") or (0.55 if etype == "related_to" else 0.75)),
            "review": item.get("review") if isinstance(item.get("review"), dict) else {"state": "needs_review", "reason": "Imported edge needs semantic review."},
            "properties": {
                "raw": item,
            },
        }
        out.append(edge)
    return out


def command_validate(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    errors, warnings = validate_kg(kg)
    result = {"valid": not errors, "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def command_validate_candidates(args: argparse.Namespace) -> int:
    batch = load_json(Path(args.candidates))
    errors, warnings = validate_candidates(batch)
    result = {"valid": not errors, "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def command_merge(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    batch = load_json(Path(args.candidates))
    errors, warnings = validate_candidates(batch)
    if errors:
        print(json.dumps({"merged": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 2

    node_ids = {str(node.get("id")) for node in kg.get("nodes") or [] if isinstance(node, dict)}
    edge_ids = {str(edge.get("id")) for edge in kg.get("edges") or [] if isinstance(edge, dict)}
    added_nodes = 0
    added_edges = 0
    skipped: list[str] = []

    existing_sources = {str(src.get("id")) for src in kg.get("sources") or [] if isinstance(src, dict)}
    for source in (batch.get("source_batch") or {}).get("sources") or []:
        if isinstance(source, dict) and source.get("id") and source["id"] not in existing_sources:
            kg.setdefault("sources", []).append(source)
            existing_sources.add(str(source["id"]))

    for node in batch.get("node_candidates") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if nid in node_ids:
            skipped.append(f"node exists: {nid}")
            continue
        if not is_promotable(node):
            skipped.append(f"node not promotable: {nid}")
            continue
        promoted = dict(node)
        promoted.setdefault("review", {"state": "accepted"})
        promoted.setdefault("confidence", 0.8)
        kg.setdefault("nodes", []).append(promoted)
        node_ids.add(nid)
        added_nodes += 1

    for edge in batch.get("edge_candidates") or []:
        if not isinstance(edge, dict):
            continue
        etype = str(edge.get("type") or "")
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        eid = str(edge.get("id") or "") or stable_edge_id(etype, source, target)
        if eid in edge_ids:
            skipped.append(f"edge exists: {eid}")
            continue
        if source not in node_ids or target not in node_ids:
            skipped.append(f"edge endpoint missing: {eid}")
            continue
        if not is_promotable(edge):
            skipped.append(f"edge not promotable: {eid}")
            continue
        promoted = dict(edge)
        promoted["id"] = eid
        promoted.setdefault("review", {"state": "accepted"})
        promoted.setdefault("confidence", 0.8)
        kg.setdefault("edges", []).append(promoted)
        edge_ids.add(eid)
        added_edges += 1

    kg.setdefault("quality", {})["last_merge"] = {
        "at": utc_now(),
        "candidate_batch": batch.get("id"),
        "added_nodes": added_nodes,
        "added_edges": added_edges,
        "skipped": skipped,
    }
    graph_errors, graph_warnings = validate_kg(kg)
    if graph_errors:
        print(json.dumps({"merged": False, "errors": graph_errors, "warnings": graph_warnings, "skipped": skipped}, ensure_ascii=False, indent=2))
        return 2
    write_json(Path(args.out), kg)
    print(json.dumps({"merged": True, "out": args.out, "added_nodes": added_nodes, "added_edges": added_edges, "skipped": skipped, "warnings": graph_warnings}, ensure_ascii=False, indent=2))
    return 0


def searchable_text(item: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("id", "type", "name", "definition", "summary", "label", "evidence", "reason", "subject", "stage", "curriculum"):
        if item.get(key) is not None:
            values.append(str(item.get(key)))
    for key in ("aliases", "tags", "source_refs"):
        values.extend(str(v) for v in as_list(item.get(key)))
    return " ".join(values).lower()


def command_search(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    terms = [term.lower() for term in re.split(r"\s+", args.query.strip()) if term.strip()]
    results: list[dict[str, Any]] = []
    for node in kg.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        text = searchable_text(node)
        score = sum(text.count(term) for term in terms)
        if score:
            results.append({"kind": "node", "score": score, "id": node.get("id"), "name": node.get("name"), "type": node.get("type")})
    for edge in kg.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        text = searchable_text(edge)
        score = sum(text.count(term) for term in terms)
        if score:
            results.append({"kind": "edge", "score": score, "id": edge.get("id"), "type": edge.get("type"), "source": edge.get("source"), "target": edge.get("target")})
    results.sort(key=lambda item: (-int(item["score"]), str(item.get("kind")), str(item.get("id"))))
    print(json.dumps({"query": args.query, "count": len(results), "results": results[: args.limit]}, ensure_ascii=False, indent=2))
    return 0


def command_extract(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    nodes_by_id = {str(node.get("id")): node for node in kg.get("nodes") or [] if isinstance(node, dict) and node.get("id")}
    if args.center not in nodes_by_id:
        print(json.dumps({"error": f"center node not found: {args.center}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    relevant_edges = [
        edge
        for edge in kg.get("edges") or []
        if isinstance(edge, dict)
        and (not args.edge_type or edge.get("type") == args.edge_type)
    ]
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in relevant_edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if not source or not target:
            continue
        adjacency[source].append(target)
        if not args.directed:
            adjacency[target].append(source)

    selected: set[str] = {args.center}
    queue: deque[tuple[str, int]] = deque([(args.center, 0)])
    while queue:
        node_id, depth = queue.popleft()
        if depth >= args.depth:
            continue
        for nxt in adjacency.get(node_id, []):
            if nxt in selected:
                continue
            selected.add(nxt)
            queue.append((nxt, depth + 1))

    sub_edges = [
        edge
        for edge in relevant_edges
        if str(edge.get("source") or "") in selected and str(edge.get("target") or "") in selected
    ]
    refs = set()
    for node_id in selected:
        refs.update(str(ref).split("#")[0] for ref in as_list(nodes_by_id[node_id].get("source_refs")))
    for edge in sub_edges:
        refs.update(str(ref).split("#")[0] for ref in as_list(edge.get("source_refs")))
    sources = [source for source in kg.get("sources") or [] if isinstance(source, dict) and str(source.get("id")) in refs]
    out = {
        "schema": "cgo.kg.v1",
        "kind": "kg",
        "id": f"{kg.get('id', 'kg')}-extract-{slugify(args.center)}",
        "title": f"Extract around {args.center}",
        "version": str(kg.get("version") or "0.1.0"),
        "language": kg.get("language", ""),
        "profile": "learning-kg-extract",
        "meta": {
            "source_kg": kg.get("id"),
            "center": args.center,
            "depth": args.depth,
            "edge_type": args.edge_type or "",
            "generated_at": utc_now(),
        },
        "compat": kg.get("compat", {}),
        "sources": sources,
        "nodes": [nodes_by_id[node_id] for node_id in sorted(selected)],
        "edges": sub_edges,
        "collections": [],
        "views": [],
        "quality": {},
    }
    if args.out:
        write_json(Path(args.out), out)
        print(f"wrote {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def build_report(kg: dict[str, Any], errors: list[str], warnings: list[str]) -> str:
    nodes = [node for node in kg.get("nodes") or [] if isinstance(node, dict)]
    edges = [edge for edge in kg.get("edges") or [] if isinstance(edge, dict)]
    node_ids = {str(node.get("id")) for node in nodes}
    connected = {str(edge.get("source")) for edge in edges} | {str(edge.get("target")) for edge in edges}
    orphan_nodes = sorted(node_ids - connected)
    review_nodes = [node for node in nodes if review_state(node) in {"needs_review", "draft"}]
    review_edges = [edge for edge in edges if review_state(edge) in {"needs_review", "draft"}]

    lines = [
        "# KG Report",
        "",
        f"- KG: `{kg.get('id', '')}`",
        f"- Generated: `{utc_now()}`",
        f"- Valid: `{str(not errors).lower()}`",
        f"- Sources: {len(kg.get('sources') or [])}",
        f"- Nodes: {len(nodes)}",
        f"- Edges: {len(edges)}",
        "",
        "## Node Types",
        "",
    ]
    for key, count in Counter(str(node.get("type")) for node in nodes).most_common():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Edge Types", ""])
    for key, count in Counter(str(edge.get("type")) for edge in edges).most_common():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Review Queue", ""])
    lines.append(f"- Nodes needing review/draft: {len(review_nodes)}")
    lines.append(f"- Edges needing review/draft: {len(review_edges)}")
    for node in review_nodes[:20]:
        lines.append(f"  - node `{node.get('id')}`: {node.get('name')}")
    for edge in review_edges[:20]:
        lines.append(f"  - edge `{edge.get('id')}`: {edge.get('source')} -> {edge.get('target')}")
    lines.extend(["", "## Orphans", ""])
    lines.append(f"- Orphan nodes: {len(orphan_nodes)}")
    for node_id in orphan_nodes[:30]:
        lines.append(f"  - `{node_id}`")
    lines.extend(["", "## Errors", ""])
    if errors:
        for item in errors:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def command_report(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    errors, warnings = validate_kg(kg)
    report = build_report(kg, errors, warnings)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0 if not errors else 2


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def nested_text(item: dict[str, Any], *path: str) -> str:
    value: Any = item
    for key in path:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return first_text(value)


def normalize_slug(value: Any, mapping: dict[str, str], fallback: str = "") -> str:
    text = first_text(value)
    if not text:
        return fallback
    if text in mapping:
        return mapping[text]
    lowered = text.lower()
    if re.fullmatch(r"[a-z][a-z0-9_-]*", lowered):
        return lowered
    return slugify(text) or fallback


def parse_grade(value: Any, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    text = first_text(value)
    if not text:
        return fallback
    match = re.search(r"\d+", text)
    if match:
        return int(match.group(0))
    for char, grade in GRADE_CHARS.items():
        if char in text:
            return grade
    return fallback


def product_node_definition(node: dict[str, Any]) -> str:
    definition = first_text(
        node.get("definition"),
        nested_text(node, "properties", "definition"),
        node.get("summary"),
    )
    return re.sub(r"\s+", " ", definition).strip()


def product_node_skills(node: dict[str, Any]) -> list[str]:
    values = node.get("skills")
    if values is None and isinstance(node.get("properties"), dict):
        values = node["properties"].get("skills")
    skills: list[str] = []
    for value in as_list(values):
        text = first_text(value)
        if text and text not in skills:
            skills.append(text)
    return skills


def product_node_name_en(node: dict[str, Any]) -> str:
    name_en = first_text(
        node.get("name_en"),
        nested_text(node, "properties", "name_en"),
        nested_text(node, "compat", "name_en"),
    )
    if name_en:
        return name_en
    for alias in as_list(node.get("aliases")):
        text = first_text(alias)
        if text and re.fullmatch(r"[A-Za-z0-9 ,;:()/_-]+", text):
            return text
    return ""


def product_node_id(node: dict[str, Any]) -> str:
    return first_text(
        nested_text(node, "compat", "external_ids", "knowledge_map"),
        nested_text(node, "compat", "external_ids", "product"),
        nested_text(node, "properties", "product_id"),
        node.get("id"),
    )


def product_domain(node: dict[str, Any], fallback: str) -> str:
    domain = first_text(
        nested_text(node, "properties", "domain"),
        node.get("domain"),
    )
    if domain:
        return normalize_slug(domain, {}, fallback)
    for tag in as_list(node.get("tags")):
        text = first_text(tag)
        if text and text not in {"lesson-anchor"}:
            return normalize_slug(text, {}, fallback)
    return fallback


def product_difficulty(node: dict[str, Any], fallback: int) -> int:
    value = node.get("difficulty")
    if value is None and isinstance(node.get("properties"), dict):
        value = node["properties"].get("difficulty")
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def product_node_from_kg(node: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    grade_band = node.get("grade_band") if isinstance(node.get("grade_band"), dict) else {}
    subject = normalize_slug(args.subject or node.get("subject"), SUBJECT_SLUGS, args.default_subject)
    stage = normalize_slug(args.stage or node.get("stage") or grade_band.get("stage"), STAGE_SLUGS, args.default_stage)
    grade = parse_grade(args.grade if args.grade is not None else node.get("grade") or node.get("grade_band"), args.default_grade)
    curriculum = first_text(args.curriculum, node.get("curriculum"), args.default_curriculum)
    tree_path = first_text(args.tree_path, nested_text(node, "properties", "tree_path"), f"{curriculum}/{subject}.json" if curriculum and subject else "")
    name = first_text(node.get("name"), node.get("id"))
    product_node: dict[str, Any] = {
        "id": product_node_id(node),
        "name": name,
        "name_en": product_node_name_en(node),
        "type": first_text(node.get("type")),
        "subject": subject,
        "grade": grade,
        "domain": normalize_slug(args.domain, {}, "") if args.domain else product_domain(node, args.default_domain),
        "difficulty": product_difficulty(node, args.default_difficulty),
        "definition": product_node_definition(node),
        "skills": product_node_skills(node),
        "stage": stage,
        "curriculum": curriculum,
        "tree_path": tree_path,
        "display_name": first_text(node.get("display_name"), nested_text(node, "properties", "display_name"), name),
    }
    if grade_band:
        product_node["grade_band"] = grade_band
    refs = [str(ref) for ref in as_list(node.get("source_refs")) if str(ref).strip()]
    if refs:
        product_node["source_refs"] = refs
    conf = confidence(node)
    if conf is not None:
        product_node["confidence"] = conf
    if isinstance(node.get("properties"), dict):
        product_node["properties"] = node["properties"]
    return product_node


def parse_csv_set(value: str | None, default: set[str]) -> set[str]:
    if not value:
        return set(default)
    return {item.strip() for item in value.split(",") if item.strip()}


def product_stats(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    by_subject = Counter(str(node.get("subject") or "") for node in nodes)
    by_grade = Counter(str(node.get("grade") or "") for node in nodes)
    by_id = {str(node.get("id")): node for node in nodes}
    cn_unified = [node for node in nodes if node.get("curriculum") == "cn-unified"]
    sci_cross_edges = 0
    for edge in edges:
        source = by_id.get(str(edge.get("source")))
        target = by_id.get(str(edge.get("target")))
        if not source or not target:
            continue
        if source.get("subject") == "science" and target.get("subject") and target.get("subject") != "science":
            sci_cross_edges += 1
        elif target.get("subject") == "science" and source.get("subject") and source.get("subject") != "science":
            sci_cross_edges += 1
    return {
        "generated_at": utc_now(),
        "totalNodes": len(nodes),
        "totalEdges": len(edges),
        "subjects": sorted(key for key in by_subject if key),
        "bySubject": dict(sorted(by_subject.items())),
        "byGrade": dict(sorted(by_grade.items(), key=lambda item: item[0])),
        "cnUnifiedNodes": len(cn_unified),
        "internationalNodes": len(nodes) - len(cn_unified),
        "stageBridgeEdges": 0,
        "universityBridgeEdges": 0,
        "sciElementaryNodes": sum(1 for node in nodes if node.get("subject") == "science" and node.get("stage") == "elementary"),
        "sciCrossEdges": sci_cross_edges,
        "translated_at": "",
    }


def command_export_product(args: argparse.Namespace) -> int:
    kg = load_json(Path(args.kg))
    node_types = parse_csv_set(args.node_types, PRODUCT_DEFAULT_NODE_TYPES)
    edge_types = parse_csv_set(args.edge_types, PRODUCT_DEFAULT_EDGE_TYPES)
    review_states = parse_csv_set(args.review_states, {"accepted", "needs_review", "draft", ""})
    nodes: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    product_ids_by_internal_id: dict[str, str] = {}
    for node in kg.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        node_id = first_text(node.get("id"))
        if not node_id:
            continue
        if first_text(node.get("type")) not in node_types:
            continue
        if review_state(node) not in review_states:
            continue
        conf = confidence(node)
        if conf is not None and conf < args.min_confidence:
            continue
        product_node = product_node_from_kg(node, args)
        if args.require_definition and not product_node["definition"]:
            continue
        nodes.append(product_node)
        selected_ids.add(node_id)
        product_ids_by_internal_id[node_id] = product_node["id"]

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in kg.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if first_text(edge.get("type")) not in edge_types:
            continue
        if review_state(edge) not in review_states:
            continue
        conf = confidence(edge)
        if conf is not None and conf < args.min_confidence:
            continue
        source = first_text(edge.get("source"))
        target = first_text(edge.get("target"))
        if source not in selected_ids or target not in selected_ids or source == target:
            continue
        product_source = product_ids_by_internal_id[source]
        product_target = product_ids_by_internal_id[target]
        edge_type = first_text(edge.get("type"))
        key = (product_source, product_target, edge_type)
        if key in seen_edges:
            continue
        product_edge: dict[str, Any] = {"source": product_source, "target": product_target}
        if edge_type:
            product_edge["type"] = edge_type
        conf = confidence(edge)
        if conf is not None:
            product_edge["confidence"] = conf
        refs = [str(ref) for ref in as_list(edge.get("source_refs")) if str(ref).strip()]
        if refs:
            product_edge["source_refs"] = refs
        edges.append(product_edge)
        seen_edges.add(key)

    out = {
        "nodes": sorted(nodes, key=lambda item: str(item.get("id"))),
        "edges": sorted(edges, key=lambda item: (str(item.get("source")), str(item.get("target")))),
    }
    out["stats"] = product_stats(out["nodes"], out["edges"])
    errors, warnings = validate_product_graph(out)
    if errors:
        print(json.dumps({"exported": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(Path(args.out), out)
    print(json.dumps({"exported": True, "out": args.out, "nodes": len(out["nodes"]), "edges": len(out["edges"]), "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def validate_product_graph(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    nodes = data.get("nodes")
    edges = data.get("edges")
    stats = data.get("stats")
    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []
    if not isinstance(stats, dict):
        errors.append("stats must be an object")
        stats = {}

    node_ids: set[str] = set()
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{idx}] must be an object")
            continue
        missing = [field for field in PRODUCT_NODE_FIELDS if field not in node]
        if missing:
            errors.append(f"node {node.get('id') or idx} missing fields: {', '.join(missing)}")
        node_id = first_text(node.get("id"))
        if not node_id:
            errors.append(f"nodes[{idx}] missing id")
        elif node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        if not first_text(node.get("name")):
            errors.append(f"node {node_id or idx} missing name")
        if not isinstance(node.get("skills"), list):
            errors.append(f"node {node_id or idx} skills must be a list")
        if parse_grade(node.get("grade"), -1) < 0:
            errors.append(f"node {node_id or idx} grade must be a non-negative integer")
        if not first_text(node.get("definition")):
            warnings.append(f"node {node_id or idx} has empty definition")

    seen_edges: set[tuple[str, str]] = set()
    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{idx}] must be an object")
            continue
        source = first_text(edge.get("source"))
        target = first_text(edge.get("target"))
        if not source or not target:
            errors.append(f"edge {idx} must contain source and target")
        edge_type = first_text(edge.get("type"))
        conf = confidence(edge)
        if "confidence" in edge and conf is None:
            errors.append(f"edge {idx} confidence must be numeric")
        elif conf is not None and (conf < 0 or conf > 1):
            errors.append(f"edge {idx} confidence outside [0,1]")
        if source not in node_ids:
            errors.append(f"edge {idx} source missing: {source}")
        if target not in node_ids:
            errors.append(f"edge {idx} target missing: {target}")
        if source == target:
            errors.append(f"edge {idx} self-loop is not allowed: {source}")
        key = (source, target, edge_type)
        if key in seen_edges:
            errors.append(f"duplicate edge: {source} -> {target} ({edge_type})")
        seen_edges.add(key)

    expected_nodes = stats.get("totalNodes")
    expected_edges = stats.get("totalEdges")
    if isinstance(expected_nodes, int) and expected_nodes != len(nodes):
        warnings.append(f"stats.totalNodes mismatch: {expected_nodes} != {len(nodes)}")
    if isinstance(expected_edges, int) and expected_edges != len(edges):
        warnings.append(f"stats.totalEdges mismatch: {expected_edges} != {len(edges)}")
    return errors, warnings


def command_validate_product(args: argparse.Namespace) -> int:
    data = load_json(Path(args.input))
    errors, warnings = validate_product_graph(data)
    result = {"valid": not errors, "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def validate_knowledge_groups(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schema") != "cgo.knowledge_groups.v1":
        errors.append("top-level schema must be cgo.knowledge_groups.v1")
    if data.get("kind") != "knowledge_groups":
        errors.append("top-level kind must be knowledge_groups")

    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []

    node_ids: set[str] = set()
    group_ids: set[str] = set()
    semantic_edge_count: dict[str, int] = defaultdict(int)
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        node_id = first_text(node.get("id"))
        node_type = first_text(node.get("type"))
        if not node_id:
            errors.append(f"nodes[{index}] missing id")
            continue
        if node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        if node_type not in KNOWLEDGE_GROUP_NODE_TYPES:
            errors.append(f"node {node_id} has invalid type: {node_type}")
        if node_type == "knowledge_group":
            group_ids.add(node_id)
            points = node.get("points")
            props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
            if not isinstance(points, list) or not [item for item in points if first_text(item)]:
                errors.append(f"knowledge group {node_id} missing points")
            if not first_text(node.get("summary"), node.get("definition"), props.get("core_understanding")):
                warnings.append(f"knowledge group {node_id} has sparse detail")
        if not first_text(node.get("name")):
            errors.append(f"node {node_id} missing name")
        if not first_text(node.get("domain")):
            errors.append(f"node {node_id} missing domain")
        if not [ref for ref in as_list(node.get("source_refs")) if first_text(ref)]:
            errors.append(f"node {node_id} missing source_refs")
        state = review_state(node)
        if state and state not in REVIEW_STATES:
            errors.append(f"node {node_id} has invalid review state: {state}")
        conf = confidence(node)
        if conf is None:
            errors.append(f"node {node_id} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"node {node_id} confidence outside [0,1]")

    edge_ids: set[str] = set()
    normalized_edges: list[dict[str, Any]] = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{index}] must be an object")
            continue
        edge_id = first_text(edge.get("id"))
        edge_type = first_text(edge.get("type"))
        source = first_text(edge.get("source"))
        target = first_text(edge.get("target"))
        if not edge_id:
            errors.append(f"edges[{index}] missing id")
        elif edge_id in edge_ids:
            errors.append(f"duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)
        if edge_type not in KNOWLEDGE_GROUP_EDGE_TYPES:
            errors.append(f"edge {edge_id or index} has invalid type: {edge_type}")
        if source not in node_ids:
            errors.append(f"edge {edge_id or index} source missing: {source}")
        if target not in node_ids:
            errors.append(f"edge {edge_id or index} target missing: {target}")
        if source and source == target:
            errors.append(f"edge {edge_id or index} self-loop is not allowed")
        if not first_text(edge.get("evidence"), edge.get("reason")):
            errors.append(f"edge {edge_id or index} missing evidence or reason")
        if not [ref for ref in as_list(edge.get("source_refs")) if first_text(ref)]:
            errors.append(f"edge {edge_id or index} missing source_refs")
        state = review_state(edge)
        if state and state not in REVIEW_STATES:
            errors.append(f"edge {edge_id or index} has invalid review state: {state}")
        conf = confidence(edge)
        if conf is None:
            errors.append(f"edge {edge_id or index} missing numeric confidence")
        elif conf < 0 or conf > 1:
            errors.append(f"edge {edge_id or index} confidence outside [0,1]")
        if edge_type != "part_of":
            if source in group_ids:
                semantic_edge_count[source] += 1
            if target in group_ids:
                semantic_edge_count[target] += 1
        normalized_edges.append({"type": edge_type, "source": source, "target": target})

    cycle = detect_requires_cycle(node_ids, normalized_edges)
    if cycle:
        errors.append("requires cycle: " + " -> ".join(cycle))

    for node in nodes:
        if not isinstance(node, dict) or first_text(node.get("type")) != "knowledge_group":
            continue
        node_id = first_text(node.get("id"))
        props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
        if semantic_edge_count.get(node_id, 0) == 0 and not first_text(props.get("relationship_note")):
            errors.append(f"knowledge group {node_id} has no semantic edge or relationship_note")

    return errors, warnings


def command_validate_groups(args: argparse.Namespace) -> int:
    data = load_json(Path(args.input))
    errors, warnings = validate_knowledge_groups(data)
    result = {"valid": not errors, "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


def group_node_definition(node: dict[str, Any]) -> str:
    props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
    if first_text(node.get("summary")):
        return first_text(node.get("summary"))
    if first_text(node.get("definition")):
        return first_text(node.get("definition"))
    if first_text(props.get("core_understanding")):
        return first_text(props.get("core_understanding"))
    if first_text(node.get("type")) == "domain":
        return f"{first_text(node.get('name'))}是义务教育数学课程标准中的学习领域。"
    return f"{first_text(node.get('name'))}是{first_text(props.get('domain_name'), node.get('domain'))}领域下的知识点组。"


def domain_layout(nodes: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    domain_y = {
        "number-algebra": 5.2,
        "geometry": 1.7,
        "statistics-probability": -1.8,
        "synthesis-practice": -5.0,
    }
    domain_counts: dict[str, int] = defaultdict(int)
    positions: dict[str, tuple[float, float]] = {}
    for node in sorted(nodes, key=lambda item: (int((item.get("properties") or {}).get("order", 999)), str(item.get("id")))):
        node_id = first_text(node.get("id"))
        domain = first_text(node.get("domain"), "core")
        node_type = first_text(node.get("type"))
        if node_type == "domain":
            positions[node_id] = (-12.0, domain_y.get(domain, 0.0))
            continue
        index = domain_counts[domain]
        domain_counts[domain] += 1
        columns = 9 if domain == "number-algebra" else 7 if domain == "geometry" else 8
        column = index % columns
        row = index // columns
        width = 20.0
        x = -9.5 + (width / max(columns - 1, 1)) * column
        y = domain_y.get(domain, 0.0) - row * 1.18
        positions[node_id] = (x, y)
    return positions


def fallback_position(index: int, total: int) -> tuple[float, float]:
    angle = (math.pi * 2 * index) / max(total, 1)
    radius = max(4.0, math.sqrt(max(total, 1)))
    return (math.cos(angle) * radius, math.sin(angle) * radius)


def group_node_to_product(node: dict[str, Any], positions: dict[str, tuple[float, float]], args: argparse.Namespace) -> dict[str, Any]:
    props = dict(node.get("properties") if isinstance(node.get("properties"), dict) else {})
    node_type = first_text(node.get("type"), "knowledge_group")
    points = [first_text(item) for item in as_list(node.get("points") or props.get("knowledge_points")) if first_text(item)]
    domain = first_text(node.get("domain"), props.get("domain"), args.default_domain)
    node_id = first_text(node.get("id"))
    fallback = fallback_position(len(positions), max(len(positions), 1))
    x, y = positions.get(node_id, fallback)
    props.setdefault("section_type", node_type)
    props.setdefault("layout", "knowledge_group_map")
    props.setdefault("knowledge_points", points)
    props.setdefault("framework_path", ["数学", first_text(props.get("domain_name"), domain), first_text(props.get("theme_name"), node.get("theme")), first_text(node.get("name"))])
    props.setdefault("core_understanding", first_text(node.get("core_understanding"), props.get("core_understanding")))
    props["x"] = x
    props["y"] = y
    product_node: dict[str, Any] = {
        "id": node_id,
        "name": first_text(node.get("name"), node_id),
        "name_en": first_text(node.get("name_en")),
        "type": node_type,
        "subject": first_text(node.get("subject"), args.default_subject),
        "grade": parse_grade(node.get("grade"), args.default_grade),
        "domain": domain,
        "difficulty": product_difficulty(node, args.default_difficulty),
        "definition": group_node_definition(node),
        "skills": points[:8],
        "stage": first_text(node.get("stage"), "general"),
        "curriculum": first_text(node.get("curriculum"), args.default_curriculum),
        "tree_path": first_text(node.get("tree_path"), f"{args.default_curriculum}/knowledge-groups.json"),
        "display_name": first_text(node.get("display_name"), node.get("name"), node_id),
        "properties": props,
    }
    grade_band = node.get("grade_band") if isinstance(node.get("grade_band"), dict) else {"local": "1-9年级", "min_grade": 1, "max_grade": 9, "stage": "general"}
    product_node["grade_band"] = grade_band
    refs = [first_text(ref) for ref in as_list(node.get("source_refs")) if first_text(ref)]
    if refs:
        product_node["source_refs"] = refs
    conf = confidence(node)
    if conf is not None:
        product_node["confidence"] = conf
    return product_node


def command_export_groups_product(args: argparse.Namespace) -> int:
    data = load_json(Path(args.input))
    errors, warnings = validate_knowledge_groups(data)
    if errors:
        print(json.dumps({"exported": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    review_states = parse_csv_set(args.review_states, {"accepted"})
    edge_types = parse_csv_set(args.edge_types, KNOWLEDGE_GROUP_EXPORT_EDGE_TYPES)
    source_nodes = [
        node
        for node in data.get("nodes") or []
        if isinstance(node, dict)
        and first_text(node.get("type")) in KNOWLEDGE_GROUP_NODE_TYPES
        and review_state(node) in review_states
    ]
    positions = domain_layout(source_nodes)
    nodes = [group_node_to_product(node, positions, args) for node in source_nodes]
    node_ids = {first_text(node.get("id")) for node in nodes}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in data.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        edge_type = first_text(edge.get("type"))
        if edge_type not in edge_types or review_state(edge) not in review_states:
            continue
        source = first_text(edge.get("source"))
        target = first_text(edge.get("target"))
        if source not in node_ids or target not in node_ids:
            continue
        key = (source, target, edge_type)
        if key in seen_edges:
            continue
        product_edge: dict[str, Any] = {
            "source": source,
            "target": target,
            "type": edge_type,
        }
        conf = confidence(edge)
        if conf is not None:
            product_edge["confidence"] = conf
        refs = [first_text(ref) for ref in as_list(edge.get("source_refs")) if first_text(ref)]
        if refs:
            product_edge["source_refs"] = refs
        for key_name in ("evidence", "reason"):
            text = first_text(edge.get(key_name))
            if text:
                product_edge[key_name] = text
        if isinstance(edge.get("properties"), dict):
            product_edge["properties"] = edge["properties"]
        edges.append(product_edge)
        seen_edges.add(key)

    out = {
        "nodes": sorted(nodes, key=lambda item: (nodeTypeOrderForProduct(item), str(item.get("domain")), str(item.get("id")))),
        "edges": sorted(edges, key=lambda item: (str(item.get("type")), str(item.get("source")), str(item.get("target")))),
    }
    stats = product_stats(out["nodes"], out["edges"])
    stats.update(
        {
            "id": first_text(data.get("id"), "cn-math-2022-knowledge-groups"),
            "title": first_text(data.get("title"), "义务教育数学课程标准（2022年版）知识点组图谱"),
            "view": "knowledge_group_map",
            "curriculum": first_text(data.get("curriculum"), args.default_curriculum),
            "semanticEdges": sum(1 for edge in out["edges"] if edge.get("type") != "part_of"),
        }
    )
    out["stats"] = stats
    product_errors, product_warnings = validate_product_graph(out)
    if product_errors:
        print(json.dumps({"exported": False, "errors": product_errors, "warnings": product_warnings + warnings}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(Path(args.out), out)
    print(json.dumps({"exported": True, "out": args.out, "nodes": len(out["nodes"]), "edges": len(out["edges"]), "warnings": warnings + product_warnings}, ensure_ascii=False, indent=2))
    return 0


def nodeTypeOrderForProduct(node: dict[str, Any]) -> int:
    node_type = first_text(node.get("type"))
    if node_type == "domain":
        return 0
    if node_type == "knowledge_group":
        return 1
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CathyGO KG authoring helper")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--out", required=True)
    ingest.add_argument("--source-id")
    ingest.add_argument("--batch-id")
    ingest.add_argument("--target-kg")
    ingest.add_argument("--title")
    ingest.add_argument("--license")
    ingest.set_defaults(func=command_ingest)

    validate = sub.add_parser("validate")
    validate.add_argument("--kg", required=True)
    validate.set_defaults(func=command_validate)

    validate_candidates_cmd = sub.add_parser("validate-candidates")
    validate_candidates_cmd.add_argument("--candidates", required=True)
    validate_candidates_cmd.set_defaults(func=command_validate_candidates)

    merge = sub.add_parser("merge")
    merge.add_argument("--kg", required=True)
    merge.add_argument("--candidates", required=True)
    merge.add_argument("--out", required=True)
    merge.set_defaults(func=command_merge)

    search = sub.add_parser("search")
    search.add_argument("--kg", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=command_search)

    extract = sub.add_parser("extract")
    extract.add_argument("--kg", required=True)
    extract.add_argument("--center", required=True)
    extract.add_argument("--depth", type=int, default=1)
    extract.add_argument("--edge-type", choices=sorted(EDGE_TYPES))
    extract.add_argument("--directed", action="store_true")
    extract.add_argument("--out")
    extract.set_defaults(func=command_extract)

    report = sub.add_parser("report")
    report.add_argument("--kg", required=True)
    report.add_argument("--out", required=True)
    report.set_defaults(func=command_report)

    export_product = sub.add_parser("export-product")
    export_product.add_argument("--kg", required=True)
    export_product.add_argument("--out", required=True)
    export_product.add_argument("--subject", help="Override product subject slug, for example science or physics.")
    export_product.add_argument("--stage", help="Override product stage slug, for example elementary, middle, high.")
    export_product.add_argument("--grade", type=int, help="Override numeric product grade.")
    export_product.add_argument("--domain", help="Override product domain slug.")
    export_product.add_argument("--curriculum", help="Override product curriculum slug.")
    export_product.add_argument("--tree-path", help="Override product tree_path.")
    export_product.add_argument("--default-subject", default="science")
    export_product.add_argument("--default-stage", default="middle")
    export_product.add_argument("--default-grade", type=int, default=0)
    export_product.add_argument("--default-domain", default="")
    export_product.add_argument("--default-curriculum", default="cn-unified")
    export_product.add_argument("--default-difficulty", type=int, default=0)
    export_product.add_argument("--node-types", help="Comma-separated cgo.kg.v1 node types to export.")
    export_product.add_argument("--edge-types", help="Comma-separated cgo.kg.v1 edge types to export.")
    export_product.add_argument("--review-states", help="Comma-separated review states to export.")
    export_product.add_argument("--min-confidence", type=float, default=0.0)
    export_product.add_argument("--require-definition", action="store_true")
    export_product.set_defaults(func=command_export_product)

    validate_product = sub.add_parser("validate-product")
    validate_product.add_argument("--input", required=True)
    validate_product.set_defaults(func=command_validate_product)

    validate_groups = sub.add_parser("validate-groups")
    validate_groups.add_argument("--input", required=True)
    validate_groups.set_defaults(func=command_validate_groups)

    export_groups_product = sub.add_parser("export-groups-product")
    export_groups_product.add_argument("--input", required=True)
    export_groups_product.add_argument("--out", required=True)
    export_groups_product.add_argument("--default-subject", default="mathematics")
    export_groups_product.add_argument("--default-grade", type=int, default=0)
    export_groups_product.add_argument("--default-domain", default="mathematics")
    export_groups_product.add_argument("--default-curriculum", default="cn-math-2022")
    export_groups_product.add_argument("--default-difficulty", type=int, default=0)
    export_groups_product.add_argument("--edge-types", help="Comma-separated group edge types to export.")
    export_groups_product.add_argument("--review-states", help="Comma-separated review states to export.")
    export_groups_product.set_defaults(func=command_export_groups_product)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

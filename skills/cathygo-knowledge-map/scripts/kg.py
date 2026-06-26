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

The script intentionally has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

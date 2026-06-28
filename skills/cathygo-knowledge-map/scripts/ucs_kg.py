#!/usr/bin/env python3
"""Validate and export UCS-KG curriculum-standard graph artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ucs-kg-v0.1"
OBJECT_ARRAYS = (
    "curricula",
    "framework_nodes",
    "standard_items",
    "concepts",
    "competencies",
    "learning_evidence",
    "activities",
    "assessments",
    "relations",
    "alignments",
)
REQUIRED_TOP_LEVEL = ("schema_version", "dataset_id", "curricula", "framework_nodes", "standard_items", "concepts", "relations")
REQUIRED_FIELDS = {
    "curricula": ("id", "type", "name", "country", "subject", "language", "version"),
    "framework_nodes": ("id", "type", "curriculum_id", "name"),
    "standard_items": ("id", "type", "curriculum_id", "subject", "statement"),
    "concepts": ("id", "type", "name", "subject", "definition", "grade_band"),
    "competencies": ("id", "type", "name", "subject", "description"),
    "learning_evidence": ("id", "type", "concept_id", "statement"),
    "activities": ("id", "type", "title"),
    "assessments": ("id", "type", "title"),
    "relations": ("id", "type", "source_id", "target_id"),
    "alignments": ("id", "type", "source_id", "target_id", "alignment_type"),
}
CGO_NODE_TYPES = {"concept", "skill", "task", "assessment"}
RELATION_TO_CGO_EDGE = {
    "part_of": "part_of",
    "prerequisite_for": "requires",
    "requires": "requires",
    "progresses_to": "extends",
    "extends": "extends",
    "applies_to": "applies_to",
    "supports_competency": "applies_to",
    "represented_by": "related_to",
    "contrasts_with": "confuses_with",
    "example_of": "related_to",
}
KNOWLEDGE_MAP_MANIFEST_SCHEMA = "cgo.knowledge-map.manifest.v1"
KNOWLEDGE_MAP_OWNER_TYPES = {"official", "user", "shared", "local"}
KNOWLEDGE_MAP_VISIBILITIES = {"public", "private", "shared", "draft"}
ASSET_KEYS_BY_FILE_NAME = {
    "ucs-kg.json": "ucs_kg",
    "cgo-kg-candidates.json": "kg_candidates",
    "cgo-kg.json": "kg",
    "knowledge-groups.json": "knowledge_groups",
    "knowledge-map-data.json": "map",
    "knowledge-group-map-data.json": "group_map",
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


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_/|:;,.()\[\]{}]+", "-", text)
    text = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if text:
        return text
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]


def confidence(item: dict[str, Any]) -> float | None:
    value = item.get("confidence")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def object_items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key) or []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def object_index(data: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    out: dict[str, tuple[str, dict[str, Any]]] = {}
    for key in OBJECT_ARRAYS:
        for item in object_items(data, key):
            item_id = first_text(item.get("id"))
            if item_id:
                out[item_id] = (key, item)
    return out


def validate_ucs_kg(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    stats = {key: len(object_items(data, key)) for key in OBJECT_ARRAYS}

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    for key in OBJECT_ARRAYS:
        if key in data and not isinstance(data.get(key), list):
            errors.append(f"{key} must be a list")

    all_ids: list[str] = []
    for key in OBJECT_ARRAYS:
        for item in object_items(data, key):
            item_id = first_text(item.get("id"))
            if not item_id:
                errors.append(f"{key} item missing id")
            all_ids.append(item_id)
            for field in REQUIRED_FIELDS.get(key, ()):
                if field not in item or item.get(field) in (None, ""):
                    errors.append(f"{key}.{item_id or '<missing-id>'} missing required field: {field}")
            conf = confidence(item)
            if conf is not None and (conf < 0 or conf > 1):
                errors.append(f"{key}.{item_id} confidence outside [0,1]")

    for item_id, count in Counter(all_ids).items():
        if item_id and count > 1:
            errors.append(f"duplicate id: {item_id}")

    ids = object_index(data)
    curriculum_ids = {item["id"] for item in object_items(data, "curricula") if item.get("id")}
    framework_ids = {item["id"] for item in object_items(data, "framework_nodes") if item.get("id")}
    standard_ids = {item["id"] for item in object_items(data, "standard_items") if item.get("id")}
    concept_ids = {item["id"] for item in object_items(data, "concepts") if item.get("id")}
    competency_ids = {item["id"] for item in object_items(data, "competencies") if item.get("id")}

    for item in object_items(data, "framework_nodes") + object_items(data, "standard_items"):
        curriculum_id = first_text(item.get("curriculum_id"))
        if curriculum_id and curriculum_id not in curriculum_ids:
            errors.append(f"{item.get('id')} references missing curriculum_id: {curriculum_id}")
    for item in object_items(data, "framework_nodes"):
        parent_id = first_text(item.get("parent_id"))
        if parent_id and parent_id not in framework_ids:
            errors.append(f"{item.get('id')} references missing parent_id: {parent_id}")
    for item in object_items(data, "standard_items"):
        for ref in as_list(item.get("framework_node_ids")):
            if str(ref) not in framework_ids:
                errors.append(f"{item.get('id')} references missing framework_node_id: {ref}")
        if not isinstance(item.get("source"), dict):
            warnings.append(f"standard item {item.get('id')} has no source information")
    for item in object_items(data, "concepts"):
        for ref in as_list(item.get("source_standard_ids")):
            if str(ref) not in standard_ids:
                errors.append(f"{item.get('id')} references missing source_standard_id: {ref}")
        if not as_list(item.get("source_standard_ids")):
            warnings.append(f"concept {item.get('id')} has no source_standard_ids")
    evidence_by_concept = Counter()
    for item in object_items(data, "learning_evidence"):
        concept_id = first_text(item.get("concept_id"))
        if concept_id not in concept_ids:
            errors.append(f"{item.get('id')} references missing concept_id: {concept_id}")
        evidence_by_concept[concept_id] += 1
    for item in object_items(data, "concepts"):
        if evidence_by_concept[first_text(item.get("id"))] == 0:
            warnings.append(f"concept {item.get('id')} has no learning_evidence")
    for key in ("activities", "assessments"):
        for item in object_items(data, key):
            for ref in as_list(item.get("concept_ids")):
                if str(ref) not in concept_ids:
                    errors.append(f"{item.get('id')} references missing concept_id: {ref}")
            for ref in as_list(item.get("competency_ids")):
                if str(ref) not in competency_ids:
                    errors.append(f"{item.get('id')} references missing competency_id: {ref}")
    for key in ("relations", "alignments"):
        for item in object_items(data, key):
            source_id = first_text(item.get("source_id"))
            target_id = first_text(item.get("target_id"))
            if source_id and source_id not in ids:
                errors.append(f"{item.get('id')} source_id missing: {source_id}")
            if target_id and target_id not in ids and not item.get("target_framework_hint"):
                errors.append(f"{item.get('id')} target_id missing: {target_id}")
            if key == "relations" and not first_text(item.get("rationale")) and (confidence(item) or 0) < 0.9:
                warnings.append(f"relation {item.get('id')} has no rationale and confidence below 0.9")
            if key == "alignments" and not first_text(item.get("rationale")):
                warnings.append(f"alignment {item.get('id')} has no rationale")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }


def source_ref_for_standard(dataset_id: str, concept: dict[str, Any]) -> list[str]:
    refs = [f"src:{dataset_id}#{ref}" for ref in as_list(concept.get("source_standard_ids")) if str(ref).strip()]
    return refs or [f"src:{dataset_id}"]


def concept_to_cgo_node(dataset_id: str, concept: dict[str, Any], *, review_state: str) -> dict[str, Any]:
    node_id = first_text(concept.get("id"))
    grade_band = concept.get("grade_band") if isinstance(concept.get("grade_band"), dict) else {}
    properties = {"raw_ucs_id": node_id}
    if isinstance(concept.get("properties"), dict):
        properties.update(concept["properties"])
    return {
        "id": node_id,
        "type": "concept",
        "name": first_text(concept.get("name"), node_id),
        "definition": first_text(concept.get("definition"), concept.get("summary")),
        "subject": first_text(concept.get("subject")),
        "stage": first_text(grade_band.get("stage"), concept.get("stage")),
        "grade_band": grade_band,
        "curriculum": first_text(concept.get("curriculum_id"), dataset_id),
        "domain": first_text(concept.get("domain")),
        "tags": [first_text(concept.get("domain")), first_text(concept.get("concept_type"))],
        "source_refs": source_ref_for_standard(dataset_id, concept),
        "confidence": confidence(concept) if confidence(concept) is not None else 0.82,
        "review": {"state": review_state, "reason": "Exported from UCS-KG curriculum standard concept."},
        "properties": properties,
    }


def competency_to_cgo_node(dataset_id: str, item: dict[str, Any], *, review_state: str) -> dict[str, Any]:
    node_id = first_text(item.get("id"))
    grade_band = item.get("grade_band") if isinstance(item.get("grade_band"), dict) else {}
    return {
        "id": node_id,
        "type": "skill",
        "name": first_text(item.get("name"), node_id),
        "definition": first_text(item.get("description")),
        "subject": first_text(item.get("subject")),
        "stage": first_text(grade_band.get("stage"), item.get("stage")),
        "grade_band": grade_band,
        "curriculum": dataset_id,
        "source_refs": [f"src:{dataset_id}"],
        "confidence": confidence(item) if confidence(item) is not None else 0.8,
        "review": {"state": review_state, "reason": "Exported from UCS-KG competency."},
        "properties": {"raw_ucs_id": node_id},
    }


def evidence_to_cgo_node(
    dataset_id: str,
    item: dict[str, Any],
    concept_by_id: dict[str, dict[str, Any]],
    *,
    review_state: str,
) -> dict[str, Any]:
    node_id = first_text(item.get("id"))
    concept_id = first_text(item.get("concept_id"))
    concept = concept_by_id.get(concept_id, {})
    grade_band = item.get("grade_band") if isinstance(item.get("grade_band"), dict) else {}
    if not grade_band and isinstance(concept.get("grade_band"), dict):
        grade_band = concept["grade_band"]
    properties = {"raw_ucs_id": node_id, "concept_id": concept_id}
    if isinstance(concept.get("properties"), dict):
        properties.update(concept["properties"])
    if isinstance(item.get("properties"), dict):
        properties.update(item["properties"])
    return {
        "id": node_id,
        "type": "assessment",
        "name": first_text(item.get("title"), item.get("statement"), node_id),
        "summary": first_text(item.get("statement")),
        "subject": first_text(item.get("subject"), concept.get("subject")),
        "stage": first_text(grade_band.get("stage"), item.get("stage"), concept.get("stage")),
        "grade_band": grade_band,
        "curriculum": dataset_id,
        "domain": first_text(item.get("domain"), concept.get("domain")),
        "tags": [first_text(item.get("domain"), concept.get("domain")), "learning_evidence"],
        "source_refs": source_ref_for_standard(dataset_id, concept) if concept else [f"src:{dataset_id}#{concept_id}"],
        "confidence": confidence(item) if confidence(item) is not None else 0.75,
        "review": {"state": review_state, "reason": "Exported from UCS-KG learning evidence."},
        "properties": properties,
    }


def build_cgo_nodes(data: dict[str, Any], *, review_state: str) -> list[dict[str, Any]]:
    dataset_id = first_text(data.get("dataset_id"), "ucs-kg")
    concept_by_id = {first_text(item.get("id")): item for item in object_items(data, "concepts") if first_text(item.get("id"))}
    nodes: list[dict[str, Any]] = []
    for item in object_items(data, "concepts"):
        nodes.append(concept_to_cgo_node(dataset_id, item, review_state=review_state))
    for item in object_items(data, "competencies"):
        nodes.append(competency_to_cgo_node(dataset_id, item, review_state=review_state))
    for item in object_items(data, "learning_evidence"):
        nodes.append(evidence_to_cgo_node(dataset_id, item, concept_by_id, review_state=review_state))
    return nodes


def relation_to_cgo_edge(data: dict[str, Any], relation: dict[str, Any], exported_ids: set[str], *, review_state: str) -> dict[str, Any] | None:
    relation_type = first_text(relation.get("type"))
    source = first_text(relation.get("source_id"))
    target = first_text(relation.get("target_id"))
    edge_type = RELATION_TO_CGO_EDGE.get(relation_type)
    if relation_type == "assessed_by":
        source, target = target, source
        edge_type = "assesses"
    if not edge_type or source not in exported_ids or target not in exported_ids or source == target:
        return None
    edge_id = first_text(relation.get("id"), f"edge:{edge_type}:{slugify(source)}:{slugify(target)}")
    return {
        "id": edge_id,
        "type": edge_type,
        "source": source,
        "target": target,
        "evidence": first_text(relation.get("rationale"), "Derived from UCS-KG typed relation."),
        "source_refs": [f"src:{first_text(data.get('dataset_id'), 'ucs-kg')}#{edge_id}"],
        "confidence": confidence(relation) if confidence(relation) is not None else 0.75,
        "review": {"state": review_state, "reason": "Exported from UCS-KG relation."},
        "properties": {"raw_ucs_type": relation_type},
    }


def build_cgo_edges(data: dict[str, Any], nodes: list[dict[str, Any]], *, review_state: str) -> list[dict[str, Any]]:
    exported_ids = {first_text(node.get("id")) for node in nodes}
    edges = []
    for relation in object_items(data, "relations"):
        edge = relation_to_cgo_edge(data, relation, exported_ids, review_state=review_state)
        if edge is not None:
            edges.append(edge)
    for evidence in object_items(data, "learning_evidence"):
        concept_id = first_text(evidence.get("concept_id"))
        evidence_id = first_text(evidence.get("id"))
        if concept_id in exported_ids and evidence_id in exported_ids:
            edges.append(
                {
                    "id": f"edge:assesses:{slugify(evidence_id)}:{slugify(concept_id)}",
                    "type": "assesses",
                    "source": evidence_id,
                    "target": concept_id,
                    "evidence": first_text(evidence.get("statement"), "Learning evidence assesses concept mastery."),
                    "source_refs": [f"src:{first_text(data.get('dataset_id'), 'ucs-kg')}#{evidence_id}"],
                    "confidence": 0.8,
                    "review": {"state": review_state, "reason": "Derived from UCS-KG learning_evidence.concept_id."},
                }
            )
    return edges


def source_object(data: dict[str, Any]) -> dict[str, Any]:
    dataset_id = first_text(data.get("dataset_id"), "ucs-kg")
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    chunks: list[dict[str, str]] = []
    seen_chunk_ids: set[str] = set()

    def add_chunk(item: dict[str, Any], locator: str, text: str) -> None:
        chunk_id = first_text(item.get("id"))
        if not chunk_id or chunk_id in seen_chunk_ids:
            return
        chunks.append({"id": chunk_id, "locator": locator, "text": text})
        seen_chunk_ids.add(chunk_id)

    for item in object_items(data, "standard_items"):
        add_chunk(
            item,
            first_text((item.get("source") or {}).get("native_ref"), item.get("native_code"), item.get("id")),
            first_text(item.get("statement")),
        )
    for item in object_items(data, "concepts"):
        add_chunk(
            item,
            first_text(item.get("native_code"), item.get("name"), item.get("id")),
            first_text(item.get("definition"), item.get("summary"), item.get("name")),
        )
    for item in object_items(data, "competencies"):
        add_chunk(item, first_text(item.get("name"), item.get("id")), first_text(item.get("description"), item.get("name")))
    for item in object_items(data, "learning_evidence"):
        add_chunk(item, first_text(item.get("concept_id"), item.get("id")), first_text(item.get("statement"), item.get("title")))
    for item in object_items(data, "relations"):
        add_chunk(
            item,
            first_text(item.get("type"), item.get("id")),
            first_text(item.get("rationale"), f"{first_text(item.get('source_id'))} -> {first_text(item.get('target_id'))}"),
        )

    return {
        "id": f"src:{dataset_id}",
        "type": "curriculum_standard",
        "title": first_text(metadata.get("title"), dataset_id),
        "origin": {
            "dataset_id": dataset_id,
            "schema_version": data.get("schema_version"),
            "provider": "local",
            "license": first_text(metadata.get("license"), "public curriculum standard"),
        },
        "chunks": chunks[:5000],
    }


def build_cgo_kg(data: dict[str, Any], *, review_state: str) -> dict[str, Any]:
    dataset_id = first_text(data.get("dataset_id"), "ucs-kg")
    nodes = build_cgo_nodes(data, review_state=review_state)
    return {
        "schema": "cgo.kg.v1",
        "kind": "kg",
        "id": dataset_id,
        "title": first_text((data.get("metadata") or {}).get("title") if isinstance(data.get("metadata"), dict) else "", dataset_id),
        "version": "0.1.0",
        "language": first_text((data.get("metadata") or {}).get("language") if isinstance(data.get("metadata"), dict) else "", "zh-CN"),
        "profile": "curriculum-standard-kg",
        "meta": {"source_schema": SCHEMA_VERSION, "generated_at": utc_now()},
        "compat": {},
        "sources": [source_object(data)],
        "nodes": nodes,
        "edges": build_cgo_edges(data, nodes, review_state=review_state),
        "collections": [],
        "views": [],
        "quality": {},
    }


def build_candidate_batch(data: dict[str, Any]) -> dict[str, Any]:
    dataset_id = first_text(data.get("dataset_id"), "ucs-kg")
    nodes = build_cgo_nodes(data, review_state="needs_review")
    edges = build_cgo_edges(data, nodes, review_state="needs_review")
    return {
        "schema": "cgo.kg.candidates.v1",
        "kind": "kg_candidates",
        "id": f"batch:{dataset_id}:ucs-kg-export",
        "target_kg": dataset_id,
        "source_batch": {
            "source": source_object(data),
            "source_schema": SCHEMA_VERSION,
        },
        "node_candidates": nodes,
        "edge_candidates": edges,
        "revisions": [],
        "retirements": [],
        "conflicts": [],
        "review_queue": [
            {
                "id": f"review:{dataset_id}:curriculum-standard-export",
                "task": "Review UCS-KG concepts, competencies, learning evidence, and typed relations before promotion.",
                "status": "todo",
            }
        ],
        "meta": {"created_at": utc_now(), "tool": "ucs_kg.py export-candidates"},
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_asset_key(path: Path) -> str:
    return ASSET_KEYS_BY_FILE_NAME.get(path.name, slugify(path.stem).replace("-", "_"))


def manifest_asset_entry(path: Path) -> dict[str, Any]:
    return {
        "path": path.name,
        "source_path": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def build_knowledge_map_manifest(args: argparse.Namespace) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    for file_arg in args.file:
        path = Path(file_arg)
        assets[manifest_asset_key(path)] = manifest_asset_entry(path)
    task_links = {
        "learning_paths": [],
        "diagnostics": [],
        "practice_sets": [],
        "projects": [],
    }
    overlays = {
        "user_progress": [],
        "user_notes": [],
        "custom_edges": [],
    }
    return {
        "schema": KNOWLEDGE_MAP_MANIFEST_SCHEMA,
        "kind": "knowledge_map",
        "id": args.id,
        "legacy_ids": list(args.legacy_id or []),
        "title": args.title,
        "description": args.description or "",
        "version": args.version,
        "language": args.language,
        "curriculum": args.curriculum or "",
        "owner": {
            "type": args.owner_type,
            "name": args.owner_name,
        },
        "visibility": args.visibility,
        "source_type": args.source_type,
        "assets": assets,
        "task_links": task_links,
        "overlays": overlays,
        "generated_at": utc_now(),
    }


def validate_knowledge_map_manifest(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("schema") != KNOWLEDGE_MAP_MANIFEST_SCHEMA:
        errors.append(f"schema must be {KNOWLEDGE_MAP_MANIFEST_SCHEMA}")
    if data.get("kind") != "knowledge_map":
        errors.append("kind must be knowledge_map")
    for field in ("id", "title", "version", "owner", "visibility", "source_type", "assets"):
        if field not in data or data.get(field) in (None, ""):
            errors.append(f"missing required field: {field}")

    owner = data.get("owner")
    if not isinstance(owner, dict):
        errors.append("owner must be an object")
    else:
        owner_type = first_text(owner.get("type"))
        if owner_type not in KNOWLEDGE_MAP_OWNER_TYPES:
            errors.append(f"owner.type must be one of {sorted(KNOWLEDGE_MAP_OWNER_TYPES)}")
        if not first_text(owner.get("name")):
            errors.append("owner.name is required")

    visibility = first_text(data.get("visibility"))
    if visibility not in KNOWLEDGE_MAP_VISIBILITIES:
        errors.append(f"visibility must be one of {sorted(KNOWLEDGE_MAP_VISIBILITIES)}")

    legacy_ids = data.get("legacy_ids", [])
    if legacy_ids is not None and not isinstance(legacy_ids, list):
        errors.append("legacy_ids must be a list")

    assets = data.get("assets")
    if not isinstance(assets, dict) or not assets:
        errors.append("assets must be a non-empty object")
        assets = {}
    for key, asset in assets.items():
        if not first_text(key):
            errors.append("asset key must be non-empty")
        if isinstance(asset, str):
            if not asset.strip():
                errors.append(f"asset {key} path is required")
            continue
        if not isinstance(asset, dict):
            errors.append(f"asset {key} must be a path string or object")
            continue
        if not first_text(asset.get("path")):
            errors.append(f"asset {key} missing path")
        bytes_value = asset.get("bytes")
        if bytes_value is not None:
            try:
                if int(bytes_value) < 0:
                    errors.append(f"asset {key} bytes must be non-negative")
            except (TypeError, ValueError):
                errors.append(f"asset {key} bytes must be numeric")
        sha = first_text(asset.get("sha256"))
        if sha and not re.fullmatch(r"[0-9a-f]{64}", sha):
            errors.append(f"asset {key} sha256 must be a 64-character hex digest")

    task_links = data.get("task_links", {})
    if task_links is not None and not isinstance(task_links, dict):
        errors.append("task_links must be an object")
    overlays = data.get("overlays", {})
    if overlays is not None and not isinstance(overlays, dict):
        errors.append("overlays must be an object")
    if "group_map" not in assets and "map" not in assets and "kg" not in assets:
        warnings.append("manifest has no group_map, map, or kg asset")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def command_validate(args: argparse.Namespace) -> int:
    report = validate_ucs_kg(load_json(Path(args.input)))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


def command_export_candidates(args: argparse.Namespace) -> int:
    data = load_json(Path(args.input))
    report = validate_ucs_kg(data)
    if report["errors"]:
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(Path(args.out), build_candidate_batch(data))
    print(json.dumps({"ok": True, "out": args.out}, ensure_ascii=False, indent=2))
    return 0


def command_export_cgo_kg(args: argparse.Namespace) -> int:
    data = load_json(Path(args.input))
    report = validate_ucs_kg(data)
    if report["errors"]:
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(Path(args.out), build_cgo_kg(data, review_state=args.review_state))
    print(json.dumps({"ok": True, "out": args.out}, ensure_ascii=False, indent=2))
    return 0


def command_bundle_manifest(args: argparse.Namespace) -> int:
    manifest = build_knowledge_map_manifest(args)
    report = validate_knowledge_map_manifest(manifest)
    if report["errors"]:
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(Path(args.out), manifest)
    print(json.dumps({"ok": True, "out": args.out, "assets": len(manifest["assets"])}, ensure_ascii=False, indent=2))
    return 0


def command_validate_manifest(args: argparse.Namespace) -> int:
    report = validate_knowledge_map_manifest(load_json(Path(args.input)))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and export UCS-KG artifacts")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.set_defaults(func=command_validate)

    candidates = sub.add_parser("export-candidates")
    candidates.add_argument("--input", required=True)
    candidates.add_argument("--out", required=True)
    candidates.set_defaults(func=command_export_candidates)

    cgo_kg = sub.add_parser("export-cgo-kg")
    cgo_kg.add_argument("--input", required=True)
    cgo_kg.add_argument("--out", required=True)
    cgo_kg.add_argument("--review-state", choices=["accepted", "needs_review", "draft"], default="accepted")
    cgo_kg.set_defaults(func=command_export_cgo_kg)

    bundle = sub.add_parser("bundle-manifest")
    bundle.add_argument("--id", required=True)
    bundle.add_argument("--version", required=True)
    bundle.add_argument("--title", required=True)
    bundle.add_argument("--description", default="")
    bundle.add_argument("--owner-type", default="local", choices=sorted(KNOWLEDGE_MAP_OWNER_TYPES))
    bundle.add_argument("--owner-name", default="local")
    bundle.add_argument("--visibility", default="private", choices=sorted(KNOWLEDGE_MAP_VISIBILITIES))
    bundle.add_argument("--source-type", default="unknown")
    bundle.add_argument("--language", default="zh-CN")
    bundle.add_argument("--curriculum", default="")
    bundle.add_argument("--legacy-id", action="append")
    bundle.add_argument("--file", action="append", required=True)
    bundle.add_argument("--out", required=True)
    bundle.set_defaults(func=command_bundle_manifest)

    manifest = sub.add_parser("validate-manifest")
    manifest.add_argument("--input", required=True)
    manifest.set_defaults(func=command_validate_manifest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

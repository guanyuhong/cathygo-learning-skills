# CathyGO Knowledge Map Manifest v1

`cgo.knowledge-map.manifest.v1` describes a publishable knowledge asset package. It is the product/package boundary around `cgo.kg.v1`, product graph exports, layouts, and future user overlays.

## Shape

```json
{
  "schema": "cgo.knowledge-map.manifest.v1",
  "kind": "knowledge_map",
  "id": "official.cn-math-2022",
  "legacy_ids": ["cn-math-2022"],
  "title": "义务教育数学知识",
  "description": "覆盖 1-9 年级数学知识点组、阶段推进、先修关系与应用关系。",
  "version": "0.3.0",
  "language": "zh-CN",
  "curriculum": "cn-math-2022",
  "owner": {
    "type": "official",
    "name": "CathyGO"
  },
  "visibility": "public",
  "source_type": "curriculum_standard",
  "assets": {
    "kg": {
      "path": "cgo-kg.json",
      "source_path": "packages/official.cn-math-2022/source/ucs-kg.json",
      "bytes": 123,
      "sha256": "..."
    },
    "group_map": {
      "path": "knowledge-group-map-data.json",
      "source_path": "dist/official.cn-math-2022/knowledge-group-map-data.json",
      "bytes": 123,
      "sha256": "..."
    }
  },
  "task_links": {
    "learning_paths": [],
    "diagnostics": [],
    "practice_sets": [],
    "projects": []
  },
  "overlays": {
    "user_progress": [],
    "user_notes": [],
    "custom_edges": []
  },
  "generated_at": "2026-06-28T00:00:00Z"
}
```

## Rules

- User-facing product copy should call these packages "知识"; the protocol may keep "knowledge-map" terminology.
- `id` is the package id. Official packages use `official.<domain>`, user-local packages use `user.local.<slug>`.
- `legacy_ids` preserves old curriculum or package ids for migration and URL compatibility.
- `owner.type` is `official`, `user`, `shared`, or `local`.
- `visibility` is `public`, `private`, `shared`, or `draft`.
- `assets.group_map` is the preferred frontend overview when present; `assets.map` and `assets.kg` are fallbacks.
- User overlays must not mutate official assets. Store progress, notes, and custom edges separately.
- Official full content source lives in `cathygo-knowledge`. This skill repository keeps the schema and validation/export tools only.

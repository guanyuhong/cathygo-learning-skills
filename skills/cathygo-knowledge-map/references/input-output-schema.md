# 输入输出 Schema

本文件描述 `cathygo-knowledge-map` 处理结构化知识点、LLM 抽取结果和规范图谱时使用的最小数据形状。字段名、枚举值和 JSON key 保持英文。

## 输入：产品图谱风格 JSON

```json
{
  "nodes": [
    {
      "id": "abio-biochemistry-allosteric-enzyme-regulation",
      "name": "变构酶调控",
      "name_en": "Allosteric Enzyme Regulation",
      "subject": "advanced-biology",
      "grade": 0,
      "domain": "abio-biochemistry",
      "difficulty": 0,
      "definition": "...",
      "skills": [],
      "stage": "university",
      "curriculum": "cn-unified",
      "tree_path": "cn-unified/advanced-biology.json",
      "display_name": "变构酶调控"
    }
  ],
  "edges": []
}
```

## 输入：LLM 抽取图谱 JSON

```json
{
  "nodes": [
    {
      "id": "optional-stable-id",
      "type": "KnowledgePoint",
      "name": "概念中文名",
      "name_en": "English Name",
      "definition": "定义，必须来自材料",
      "subject": "advanced-biology",
      "domain": "abio-biochemistry",
      "stage": "university",
      "curriculum": "cn-unified",
      "difficulty": 0,
      "source_refs": ["source:chapter1:chunk003"]
    }
  ],
  "edges": [
    {
      "source": "node-id-a",
      "target": "node-id-b",
      "type": "PREREQUISITE_OF",
      "confidence": 0.9,
      "evidence": "材料中的证据句或概括",
      "source_refs": ["source:chapter1:chunk003"]
    }
  ],
  "candidate_edges": []
}
```

## 输出：规范图谱 JSON

```json
{
  "meta": {
    "version": "1.0",
    "generated_at": "ISO-8601 datetime",
    "source_files": [],
    "stats": {}
  },
  "nodes": [],
  "edges": [],
  "warnings": []
}
```

## CSV 输出

`nodes.csv` 列：

- `id`
- `type`
- `name`
- `name_en`
- `subject`
- `domain`
- `stage`
- `curriculum`
- `source_refs`

`edges.csv` 列：

- `id`
- `source`
- `target`
- `type`
- `confidence`
- `evidence`
- `source_refs`

## LLM 抽取要求

- 只能基于给定材料抽取，不得引入材料外事实。
- `definition` 必须来自材料；不确定时留空或放入候选。
- `PREREQUISITE_OF`、`PART_OF`、`RELATED_TO` 必须包含 `evidence`、`confidence` 和 `source_refs`。
- 证据不足的关系放入 `candidate_edges`，不要直接写入生产边。

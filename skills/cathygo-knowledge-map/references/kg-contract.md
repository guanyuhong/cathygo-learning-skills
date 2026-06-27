# CathyGO KG 契约

`kg.json` 是内容生产中的规范图谱。它必须能被 authoring agent、review 工具和未来 CathyGO Agent exporter 使用。

## 顶层形状

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

`sources` 保存来源追踪信息，并为未来兼容做准备。

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

source ref 使用 `source_id#chunk_id`。如果只能追踪到整个文件，使用 `source_id`。

## Nodes

必填字段：

- `id`：稳定的 graph ID。
- `type`：规范 node type。
- `name`：面向学习者或作者的名称。
- `source_refs`：来源引用；内部 collection anchor 除外。
- `confidence`：`0..1`。
- `review.state`：`accepted`、`needs_review`、`rejected` 或 `draft`。

推荐字段：

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

必填字段：

- `id`
- `type`
- `source`
- `target`
- `evidence` 或 `reason`
- `source_refs`
- `confidence`
- `review.state`

方向规则：

- `requires`：前置知识 `source` -> 依赖它的 `target`。
- `part_of`：组成部分 `source` -> 父级 `target`。
- `extends`：基础/简单形态 `source` -> 扩展形态 `target`。
- `applies_to`：概念/技能 `source` -> 任务/情境 `target`。
- `procedure_step_of`：步骤 `source` -> 流程 `target`。
- `assesses`：评测项 `source` -> 被评测 node `target`。
- `same_as`：规范 node `source` -> 重复/别名 node `target`。
- `confuses_with` 和 `related_to`：只保留一条规范 edge。

## Candidate Batches

`kg-candidates.json` 不是一次性 patch，而是经过 review 的生产记录：

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

候选批次用于迭代生产、导入、reviewer 决策和审计追踪。

## 兼容信息

外部集成细节放在 `compat` 中：

```json
{
  "compat": {
    "external_ids": {
      "product": "math-m-fraction-equation"
    },
    "exports": {
      "cathygo-agent": {
        "preferred_extract_depth": 2
      }
    }
  }
}
```

核心图谱必须在没有任何外部系统时仍然有意义。

## 产品图谱导出

`cgo.kg.v1` 是生产和 review 格式，包含 node type、edge type、evidence、review 状态和来源引用。产品侧 `knowledge-map-data` 是展示/检索格式，形状更扁平：

```json
{
  "nodes": [
    {
      "id": "phy-m-energy-conservation",
      "name": "能量转化与守恒定律",
      "name_en": "",
      "subject": "physics",
      "grade": 9,
      "domain": "mechanics",
      "difficulty": 0,
      "definition": "课标或 clean-room 定义摘要",
      "skills": ["能量守恒分析方法"],
      "stage": "middle",
      "curriculum": "cn-unified",
      "tree_path": "cn-unified/physics.json",
      "display_name": "能量转化与守恒定律"
    }
  ],
  "edges": [
    { "source": "phy-m-mechanical-energy", "target": "phy-m-energy-conservation" }
  ],
  "stats": {}
}
```

导出原则：

- 产品导出只保留可教学、可展示、可复用的典型知识点，默认不导出 `source_chunk`、lesson anchor 或资源节点。
- `requires` 在产品图中仍表示先修方向：前置知识点 `source` -> 依赖它的知识点 `target`。
- 其他边导出后会丢失 type，因此只导出已经 review 或语义足够明确的关系。
- `definition` 应是原创摘要或课程标准式要点，不提交教材长段原文。
- 课程包、课件覆盖率、社区精选、更新时间等 UI 状态不属于核心 KG；它们由 learning pack manifest 或产品数据库补充。

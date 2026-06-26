# 知识图谱本体

本文件定义 `cathygo-knowledge-map` 默认使用的节点、边和 provenance 规则。字段名和枚举值保持英文。

## Node schema

每个 node 至少遵循下面的形状：

```json
{
  "id": "string",
  "type": "KnowledgePoint | Skill | Domain | Subject | Curriculum | Stage | Grade | ReferenceChunk",
  "name": "string",
  "name_en": "string|null",
  "aliases": ["string"],
  "properties": {},
  "source_refs": ["source:file:chunk"]
}
```

## KnowledgePoint properties

推荐属性：

- `subject`
- `grade`
- `domain`
- `difficulty`
- `definition`
- `stage`
- `curriculum`
- `tree_path`
- `display_name`
- `skills`

不属于规范字段的原始输入保留在 `properties.raw` 下。

## Edge schema

```json
{
  "id": "edge:source:type:target",
  "source": "node_id",
  "target": "node_id",
  "type": "BELONGS_TO_DOMAIN | BELONGS_TO_SUBJECT | BELONGS_TO_CURRICULUM | FOR_STAGE | FOR_GRADE | USES_SKILL | PREREQUISITE_OF | PART_OF | RELATED_TO | ALIAS_OF | SUPPORTED_BY",
  "confidence": 1.0,
  "evidence": "short quote or paraphrase from reference material",
  "source_refs": ["source:file:chunk"],
  "properties": {}
}
```

## 方向规则

- `PREREQUISITE_OF`：先修知识点 -> 依赖它的知识点。
- `PART_OF`：子概念或子模块 -> 父概念或父模块。
- `BELONGS_TO_*`：知识点 -> 分类节点。
- `USES_SKILL`：知识点 -> 技能。
- `SUPPORTED_BY`：图谱 node/edge -> reference chunk。
- `RELATED_TO`：source -> target；语义上可以对称，但只保留一条规范边。

## 置信度规则

- `1.0`：由结构化字段或明确陈述直接编码。
- `0.8-0.95`：文本明确给出关系，但需要归一化。
- `0.6-0.8`：基于局部上下文的强推断，必须保留 evidence。
- `<0.6`：只能作为候选关系，不应默认进入生产图谱。

## Provenance 规则

- 所有非结构关系必须包含 `evidence` 和 `source_refs`。
- 由字段派生的结构边应设置 `properties.derivation = "field"`。
- 合并重复节点时必须保留所有来源引用，不要覆盖更具体的定义。

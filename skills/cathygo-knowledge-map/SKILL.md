---
name: cathygo-knowledge-map
description: "用于基于指定参考材料构建、校验和增量维护 CathyGO 知识图谱。适用于知识点抽取、KG candidate review、先修/层级/相关关系构建、TeachAny node JSON 到 cgo.kg.v1 转换、GraphRAG schema 准备；不用于学习包编写、课件页面生成、题目构建或直接解题。"
---

# CathyGO Knowledge Map

本 Skill 只负责知识图谱。目标是把指定参考材料转换成可追溯、可 review、可增量合并的 `cgo.kg.v1` artifact。

## 边界

- 输入可以是 clean-room Markdown、课程标准摘录、TeachAny node JSON、结构化 KG candidate 或已存在的 `kg.json`。
- 输出是 `kg.json`、`kg-candidates.json`、子图、报告或 review 后的合并图。
- 不生成 learning pack、TeachAny HTML 课件、QIJ 题目或答案讲解。
- 所有非结构关系必须有 evidence 或 source refs；不要凭常识补不可追溯关系。

## 工作流

按任务读取对应文档：

- KG 构建流程：`workflows/kg-build.md`
- CathyGO KG contract：`references/kg-contract.md`
- 抽取规则：`references/extraction-rules.md`
- 检索与子图导出：`references/retrieval-and-extract.md`
- 图谱本体参考：`references/ontology.md`
- LLM 抽取输入输出：`references/input-output-schema.md`

## 常用命令

从仓库根运行：

```bash
python skills/cathygo-knowledge-map/scripts/kg.py validate \
  --kg content/packs/algebraic-fractions-demo/kg.json

python skills/cathygo-knowledge-map/scripts/kg.py report \
  --kg content/packs/algebraic-fractions-demo/kg.json \
  --out /tmp/kg.report.md

python skills/cathygo-knowledge-map/scripts/kg.py search \
  --kg content/packs/algebraic-fractions-demo/kg.json \
  --query "denominator" \
  --limit 5

python skills/cathygo-knowledge-map/scripts/kg.py extract \
  --kg content/packs/algebraic-fractions-demo/kg.json \
  --center denominator-not-zero \
  --depth 2 \
  --out /tmp/subgraph.json
```

## 输出要求

- 添加 node 前先搜索已有 KG，避免重复。
- 新 node / edge 先进入 candidate，review 后再 merge。
- `source_refs` 必须指向 clean-room source chunk 或明确来源。
- 不要提交教材 PDF、截图、扫描件、复制来的教材例题或答案。

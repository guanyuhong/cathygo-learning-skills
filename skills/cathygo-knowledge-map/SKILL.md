---
name: cathygo-knowledge-map
description: "用于从教材、课标和本地资料中抽取可复用学习素材，并构建、校验和增量维护 CathyGO 知识图谱。适用于知识点、课标要点、实验活动、应用情境、素材线索、先修/层级/相关关系抽取、KG candidate review、cgo.kg.v1 维护和产品图谱导出。"
---

# CathyGO Knowledge Map

本 Skill 负责学习素材导向的知识图谱生产。目标是把参考材料转换成可追溯、可 review、可增量合并的 `cgo.kg.v1`，同时沉淀可复用学习素材线索。

## 做什么

- 输入：clean-room Markdown、课程标准摘录、教材 PDF 的本地 lesson cache、结构化 KG candidate 或已存在的 `kg.json`。
- 输出：`kg.json`、`kg-candidates.json`、产品图谱导出、子图、报告或 review 后的合并图。
- 抽取学习素材线索：知识点定义、课标要点、实验/观察/探究活动、应用情境、例子、关键技能、过程步骤、资源入口和产品挂载线索。
- 建立学习路径关系：`requires`、`part_of`、`extends`、`applies_to`、`procedure_step_of`、`related_to`。
- 为每个非结构 node、edge 和素材线索保留 `source_refs`、`evidence` 或 `reason`。

## 怎么做

1. 先定位来源范围：课程、章节、页码、课标条目或已有 KG。
2. 从来源中挑选高信号内容，不按段落机械全量抽取。
3. 先生成 `kg-candidates.json`，将新 node、edge、修订和冲突放入 review 队列。
4. 对 candidate 做去重、命名、关系方向和来源检查。
5. review 后再合并到正式 `kg.json`。
6. 需要产品使用时，再从 `cgo.kg.v1` 导出产品图谱格式。

## 评估标准

优先保留能被后续学习内容复用的素材：

- 稳定知识点：有清晰名称、定义、年级、学科和领域。
- 学习素材：能变成讲解段落、实验活动、探究任务、素材卡片、例子或应用情境。
- 学习路径关系：方向明确，有来源或结构字段支持。
- 产品线索：有资源入口、外部 ID、课程/内容挂载或可进入内容包 manifest 的信息。

低质量内容不要进入主图：章节导语、价值口号、重复课标句、页面装饰文本、无来源的宽泛总结。具体好坏例子见 `references/learning-material-quality.md`。

## 工作流

按任务读取对应文档：

- KG 构建流程：`workflows/kg-build.md`
- 教材 PDF 到 KG candidates：`workflows/pdf-source-kg-build.md`
- CathyGO KG contract：`references/kg-contract.md`
- 抽取规则：`references/extraction-rules.md`
- 检索与子图导出：`references/retrieval-and-extract.md`
- 图谱本体参考：`references/ontology.md`
- LLM 抽取输入输出：`references/input-output-schema.md`
- 教材来源与缓存边界：`references/pdf-source-policy.md`
- 学习素材质量例子：`references/learning-material-quality.md`

当用户要求从教材 PDF、电子课本、整本书或指定页码中提取知识点时，不要直接把整本 PDF 放进上下文。先读取 `workflows/pdf-source-kg-build.md`，使用 `scripts/pdf_source.py` 生成 page/lesson cache，再基于 lesson cache 构建可 review 的 `kg-candidates.json`。

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

python skills/cathygo-knowledge-map/scripts/kg.py export-product \
  --kg content/packs/algebraic-fractions-demo/kg.json \
  --subject science \
  --stage middle \
  --grade 7 \
  --curriculum cn-unified \
  --tree-path cn-unified/science.json \
  --out /tmp/knowledge-map-data.sample.json

python skills/cathygo-knowledge-map/scripts/pdf_source.py index \
  --pdf "/path/to/source.pdf" \
  --out tmp/textbook-cache/book-id/page-map.json

python skills/cathygo-knowledge-map/scripts/pdf_source.py extract-lesson \
  --pdf "/path/to/source.pdf" \
  --pages 12-20 \
  --lesson-id ch01-l01 \
  --out tmp/textbook-cache/book-id/lessons/ch01-l01.json

python skills/cathygo-knowledge-map/scripts/pdf_source.py compare-backends \
  --pdf "/path/to/source.pdf" \
  --pages 12-20 \
  --lesson-id ch01-l01 \
  --out-dir /tmp/cathygo-pdf-backend-eval

python skills/cathygo-knowledge-map/scripts/pdf_source.py candidates \
  --lesson tmp/textbook-cache/book-id/lessons/ch01-l01.json \
  --out tmp/textbook-cache/book-id/candidates/ch01-l01.kg-candidates.json
```

## 输出要求

- 添加 node 前先搜索已有 KG，避免重复。
- 长 PDF 抽取时优先保留典型、高信号知识点和学习素材线索，不为了覆盖所有段落创建低质量 node。
- 新 node / edge 先进入 candidate，review 后再 merge。
- `source_refs` 必须指向 clean-room source chunk 或明确来源。
- 不要提交教材 PDF、截图、扫描件、复制来的教材例题或答案。

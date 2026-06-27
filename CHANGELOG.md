# 更新记录

## 0.3.1

- 为 `cathygo-knowledge-map` 新增教材 PDF 输入通道，支持 page map、lesson cache 和 KG candidates scaffold。
- 借鉴 PPT Master 的 PyMuPDF 抽取范式，保留 CathyGO 自己的 page/lesson cache 输出结构。
- 新增 `pymupdf4llm` 可选 backend 和 backend 对比命令，用于评估 layout-aware 抽取质量。
- 新增教材来源与缓存边界说明，明确 PDF、截图、大段教材原文和本地缓存不进入公开内容包。
- 新增产品图谱导出/校验命令，支持把 `cgo.kg.v1` 转成类似 `knowledge-map-data.txt` 的 `nodes/edges/stats` 结构。
- 更新 KG 抽取规则，强调长 PDF 抽取时优先保留典型高信号知识点，避免为了求全创建低质量 node。
- 新增学习素材质量例子文档，用好/坏 node、edge 和素材线索示例明确 KG 抽取质量标准。
- 调整 `cathygo-knowledge-map` Skill 入口定位，从纯知识图谱构建改为“学习素材导向的知识图谱生产”，明确抽取知识点、课标要点、实验活动、应用情境和课件挂载线索。

## 0.3.0

- 将仓库调整为类似 `taste-skill` 的单仓多 Skill library。
- 新增三个可选安装 Skill：`cathygo-knowledge-map`、`cathygo-learning-pack`、`cathygo-qij-question`。
- 移除 `cathygo-learning` umbrella Skill，避免 KG、learning pack 和题目构建触发边界混乱。
- 更新 marketplace、README、`skill.sh` 和仓库校验逻辑以支持按 frontmatter `name` 安装。

## 0.2.0

- 将仓库重新定位为一个内容优先的 CathyGO Learning Skill。
- 将 KG、OCR layout、题目分割和学习包生产能力集中到 `skills/cathygo-learning/`。
- 新增 `content/packs/`，作为未来学习内容的主要存放位置。
- 从公开插件入口移除旧的多 Skill marketplace 模型。

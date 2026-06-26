---
name: cathygo-learning-pack
description: "用于基于已有知识图谱和学习目标构建 CathyGO learning pack、TeachAny 兼容 knowledge-context 和内容包 manifest。适用于学习目标、任务、误区、补救策略、课件上游内容包和 TeachAny compatibility 输出；不用于原始材料 KG 抽取、QIJ 题目协议定义、OCR 入库或完整 TeachAny 页面发布。"
---

# CathyGO Learning Pack

本 Skill 负责把已 review 的知识图谱节点组织成可消费的学习内容包。它面向上游内容设计，不直接实现完整 TeachAny HTML runtime。

## 边界

- 输入通常是 `kg.json`、选定 KG node IDs、学习目标、学段、课程场景和可选题目引用。
- 输出是 `learning-pack.json`、`knowledge-context.json`、`manifest.json` 或它们的 review 建议。
- TeachAny 兼容只到 `knowledge-context.json` 和 manifest compat 字段，不复制 TeachAny 发布链路。
- 题目可以通过 `question_refs` 引用 QIJ artifact，但题目构建属于 `cathygo-qij-question`。

## 工作流

按任务读取对应文档：

- 学习包构建：`workflows/learning-pack-build.md`
- Learning pack contract：`references/learning-pack-contract.md`
- TeachAny 兼容说明：`references/teachany-compat.md`

## 常用命令

从仓库根运行：

```bash
python skills/cathygo-learning-pack/scripts/pack.py validate \
  --pack content/packs/algebraic-fractions-demo/learning-pack.json
```

## 输出要求

- `learning-pack.json` 使用 `schema: "cgo.learning_pack.v1"` 和 `kind: "learning_pack"`。
- `kg_refs`、`objectives`、`tasks` 必须非空。
- 每个目标、任务、误区和补救策略应尽量引用 KG node ID 或 source ref。
- 外部 runtime 字段放在 `compat` 或 `properties.raw` 下；规范 CathyGO artifact 不依赖 TeachAny 才能理解。

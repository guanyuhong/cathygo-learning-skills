---
name: cathygo-qij-question
description: "用于构建 CathyGO 题目 artifact 和 QIJ 1.0 题目包。适用于拍照/OCR 入库、题目分割、单题/整卷 problem-set、QIJ schema 对齐、题目内容/作答/评分/解法结构化；不用于知识图谱关系推理、learning pack 编写、完整课件发布或实时解题。"
---

# CathyGO QIJ Question

本 Skill 负责题目侧 artifact：OCR layout、problem set、QIJ 1.0 文档和题目包预处理。它只做题目结构化，不直接承担 KG 构建或课件页面实现。

## 边界

- 输入可以是 raw OCR provider JSON、`cathygo.ocr_layout`、题干文本、题目图片或 QIJ draft。
- 输出是 `problem-set.json`、`.qij.json`、OCR selection 或题目包 review 建议。
- 不直接解题或给答案；如需包含答案、评分或解法，必须按 QIJ 的 `answerKey` / `solution` 结构显式隔离。
- OCR provider API 调用属于 runtime 或 agent 层，本 Skill 的 Python CLI 从 raw provider JSON 或已有 OCR JSON 开始。

## 工作流

按任务读取对应文档：

- 拍照/OCR 入库：`workflows/photo-intake.md`
- OCR layout contract：`references/ocr-layout-contract.md`
- 题目分割规则：`references/problem-segmentation-rules.md`
- QIJ 1.0 规范：`references/qij-1.0.md`

## 共享逻辑

OCR helper 复用 CathyGO Agent 的 `learning-core`：

```bash
export BEANX_LEARNING_CORE_PATH=/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core/src
```

## 常用命令

从仓库根运行：

```bash
python skills/cathygo-qij-question/scripts/problem_set.py segment \
  --pages skills/cathygo-qij-question/examples/single-page.layout.json \
  --mode auto \
  --out /tmp/cathygo-problem-set.json

BEANX_LEARNING_CORE_PATH=/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core/src \
python skills/cathygo-qij-question/scripts/ocr.py select \
  --input skills/cathygo-qij-question/examples/ocr-layout.example-output.json \
  --question 1 \
  --figure 图1 \
  --out /tmp/cathygo-ocr-selection.json
```

## 输出要求

- QIJ 文档必须使用 `spec: "qij"` 和 `version: "1.0"`。
- 题目内容、作答项、评分规则和解法要分离。
- JSON 中不得包含任意 JavaScript；复杂 widget 必须有 fallback。
- 不要把真实拍照题、教材截图、扫描件或 provider 原始输出提交进仓库。

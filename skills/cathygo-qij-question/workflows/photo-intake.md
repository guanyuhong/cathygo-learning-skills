# 拍照入库流程

当需要把拍照得到的 K12 内容转成结构化 OCR layout 和 problem set 时，使用这个 workflow。

## Pipeline

```text
拍照页面
  -> runtime/agent 层产出的原始 OCR provider JSON
  -> 每张图片一个 cathygo.ocr_layout JSON
  -> 可选的 unified reference-only OCR JSON
  -> cathygo.problem_set JSON
  -> 下游解题/批改，不在这个 Skill 中完成
```

## 共享 OCR Core

Python OCR 命令使用 CathyGO Agent `learning-core` 包中的 `beanx_learning.ocr`。

当该 package 没有安装时，设置：

```bash
export BEANX_LEARNING_CORE_PATH=/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core/src
```

## 单图 OCR Layout

从原始 OCR provider JSON 开始。Provider API 调用预期发生在这个 Skill 之外。

```bash
python3 scripts/ocr.py normalize \
  --input /tmp/raw-glm-ocr.json \
  --out /tmp/page.ocr-layout.json
```

所有暴露给下游 CathyGO artifact 的 bbox 都必须归一化为 `{x,y,width,height,unit:"normalized"}`。

## Unified OCR 抽取

当下游 runtime 需要 `learning-core` 产出的新版 reference-only OCR document 时，使用这个命令。

```bash
python3 scripts/ocr.py extract \
  --input /tmp/raw-glm-ocr.json \
  --attachment-id page_1 \
  --out /tmp/page.unified-ocr.json
```

## 图形和题目选择

用 selection 把题目文本、公开图形候选和私有 provider diagnostics 分开。

```bash
python3 scripts/ocr.py select \
  --input /tmp/page.ocr-layout.json \
  --question 1 \
  --figure 图1 \
  --out /tmp/page.selection.json
```

## 题目分割

```bash
python3 scripts/problem_set.py segment \
  --pages /tmp/page-1.ocr-layout.json /tmp/page-2.ocr-layout.json \
  --mode auto \
  --out /tmp/problem-set.json
```

Modes：`single`、`stitch`、`paper`、`auto`。

## 规则

- 不要编造 OCR 文本、公式、表格值或 bbox 坐标。
- 不要在这个 workflow 中解题或讲解题目。
- Provider raw output 只能放在 diagnostics 中。
- 不要提交真实拍照页面、裁剪图、OCR output 或原始 provider payload。

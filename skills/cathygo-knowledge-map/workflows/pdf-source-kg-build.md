# 教材 PDF 到 KG Candidates 工作流

这个流程用于处理整本电子课本、章节 PDF 或指定页码范围。目标不是一次性生成最终 `kg.json`，而是先生成可追溯、可 review、可重复执行的中间缓存和 `kg-candidates.json`。

## 核心原则

- 不把整本 PDF 放入上下文。
- 不提交教材 PDF、页面截图、扫描图、出版社图片或大段教材原文。
- 缓存默认放在 `tmp/textbook-cache/<book-id>/`，作为本地工作产物。
- 每个后续 node / edge 必须能追溯到 `source_refs`。
- 先按章节或课时处理，试点通过后再批量处理整本书。

## 推荐目录

```text
tmp/textbook-cache/<book-id>/
  page-map.json
  pages/
    page-001.json
  lessons/
    ch01-l01.json
  assets/
    page-012-image-001.png
  candidates/
    ch01-l01.kg-candidates.json
```

`tmp/` 下的缓存可以包含教材抽取文本，只用于本机处理和人工 review；不要提交到 Git。

## 流程

1. 建立页码索引：

```bash
python skills/cathygo-knowledge-map/scripts/pdf_source.py index \
  --pdf "/path/to/source.pdf" \
  --out tmp/textbook-cache/<book-id>/page-map.json
```

2. 选择一个章节或课时做试点，不要先跑全书：

```bash
python skills/cathygo-knowledge-map/scripts/pdf_source.py extract-lesson \
  --pdf "/path/to/source.pdf" \
  --pages 12-20 \
  --lesson-id ch01-l01 \
  --title "第一章 第一节" \
  --out tmp/textbook-cache/<book-id>/lessons/ch01-l01.json
```

3. 如需评估增强抽取能力，可以对比本地 backend：

```bash
python skills/cathygo-knowledge-map/scripts/pdf_source.py compare-backends \
  --pdf "/path/to/source.pdf" \
  --pages 12-20 \
  --lesson-id ch01-l01 \
  --out-dir /tmp/cathygo-pdf-backend-eval
```

默认 backend 是 `pymupdf`。`pymupdf4llm` 是可选本地增强 backend，未安装时运行：

```bash
python -m pip install -r skills/cathygo-knowledge-map/requirements-optional.txt
```

4. 生成可 review 的 candidates scaffold：

```bash
python skills/cathygo-knowledge-map/scripts/pdf_source.py candidates \
  --lesson tmp/textbook-cache/<book-id>/lessons/ch01-l01.json \
  --out tmp/textbook-cache/<book-id>/candidates/ch01-l01.kg-candidates.json
```

5. Codex 基于 lesson cache 和 candidates scaffold 补充真实知识点候选：

- 优先提取稳定概念、实验方法、过程、技能、应用情境和学习素材线索。
- 不直接复制教材解释、例题、答案或图文。
- 对非结构关系保守处理；证据不足时放入 `review_queue`。
- 输出仍保持 `review.state: draft` 或 `needs_review`。

6. 人工 review 后再合并到正式内容包：

```text
content/packs/<pack-id>/kg.json
```

## 失败处理

- 如果 PDF 是扫描版且没有可抽取文本，先停止并报告需要 OCR，不要猜内容。
- 如果页码索引识别不准，人工指定 `--pages`。
- 如果抽取文本包含大量页眉、页脚、目录噪声，先调整 lesson 页码范围，不要在 KG 层补救。

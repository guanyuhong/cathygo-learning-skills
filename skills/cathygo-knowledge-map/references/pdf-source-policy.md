# 教材来源与缓存边界

本仓库可以使用教材 PDF 作为本地输入来辅助构建 CathyGO 知识图谱，但公开提交内容必须遵守 clean-room 规则。

## 可以保留在本地缓存的内容

- page-level 抽取文本
- lesson-level 抽取文本
- 图片、图表、表格的本地缓存元数据
- 面向 review 的临时 `kg-candidates.json`

这些内容默认放在 `tmp/textbook-cache/`，不提交到 Git。

## 可以提交到仓库的内容

- 人工 review 后的 clean-room `kg.json`
- 原创的 learning pack、解释、练习、任务设计
- 仅包含来源定位的 `source_refs`
- 不包含教材正文的摘要性来源说明

## 不要提交的内容

- 教材 PDF
- 教材截图、扫描图、页面截取
- 出版社插图、实验图、照片、页面布局复刻
- 大段教材正文
- 复制来的教材例题、答案、答案解析

## 来源引用

KG 节点和关系使用 `source_refs` 追踪来源，推荐格式：

```json
[
  "src:zj-science-7a-2024:ch01-l01#chunk-003"
]
```

公开内容中可以保留页码、章节和 chunk id，但不要把 chunk 的教材原文提交进正式内容包。

## 实现来源

`scripts/pdf_source.py` 的 PDF 抽取层借鉴了 `/Users/guanyuhong/solo/ppt-master-main` 中 `pdf_to_md.py` 的工程思路：PyMuPDF 抽取、页眉页脚过滤、图片过滤、表格读取和按页缓存。PPT Master 使用 MIT 协议；本仓库只复用通用处理范式，不复用其 PPT 生成流程。

# CathyGO 题目分割规则

这是 `cathygo.problem_set` 的启发式分割规则。规则作用于按全局阅读顺序排列的归一化 `cathygo.ocr_layout` elements。

## 输入假设

- 每张拍照页面生成一个 `cathygo.ocr_layout` JSON。
- 页面顺序遵循 `--pages` 参数顺序。
- Elements 已经使用归一化 bbox，并保留 provider reading order。

## Section 检测

当一个文本 element 的 trim 后内容匹配以下正则时，视为 section header：

```text
^[一二三四五六七八九十百千]+[、．.]\s*.+题
```

示例：

- `一、选择题`
- `二、填空题`
- `三、解答题`

Section header 会更新 active section，但它本身不会启动一道编号题。

## 题目开始检测

当一个文本 element 的 trim 后内容匹配以下正则，并且它不是 sub-question marker 时，视为新的编号题：

```text
^\s*(\d+)\s*[.、．)]\s*
```

捕获组 `1` 会成为 problem `number`。

## Sub-question 处理

以下形式视为当前题目的子问，不作为新的顶层题目：

```text
^\s*[（(]\s*\d+\s*[）)]\s*
```

示例：

- `（1）求 x 的值`
- `(2) explain why`

## 跨页延续

在 `paper` mode 中，elements 会跨页顺序处理。只有检测到新的编号题头时，才开始新题。

如果第 2 页以延续文本开始，而不是新的 `N.` 题头，这些 elements 会保留在当前题目中。结果中的 `pageSpan` 会扩展到该题涉及的所有页面。

当调用方已经知道输入是同一道跨多张照片的题目，并且不想按题号拆分时，使用 `stitch` mode。

## Problem type 推断

从 active section label 推断 `problems[].type`：

| Section signal | Type |
| --- | --- |
| 包含 `选择` | `choice` |
| 包含 `填空` | `fill` |
| 包含 `解答`、`计算`、`证明` 或 `应用` | `solve` |
| 其他情况 | `unknown` |

## Screenshot candidate 生成

对每道题：

- 为每个包含该题 elements 的页面创建一个 `problem_crop`，bbox 使用该页相关 elements 的 union bbox。
- 为分配到该题的 image elements 创建 `diagram_1..diagram_n`。

## Mode 总结

| Mode | 行为 |
| --- | --- |
| `single` | 强制把所有 elements 合并为一道题 |
| `stitch` | 把所有页面合并为一道跨页题 |
| `paper` | 应用 section 和编号题规则 |
| `auto` | 先运行 `paper`，再根据结果推断 `single`、`stitch` 或 `paper` |

## Clean-room 边界

示例和 eval case 只能使用合成 worksheet 文本。不要在这个 Skill 中存储真实拍照试卷、教材扫描件或出版社页面复刻。

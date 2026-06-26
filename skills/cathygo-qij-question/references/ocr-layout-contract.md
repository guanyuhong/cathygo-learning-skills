# CathyGO OCR Layout 输出契约

这份参考定义 `cathygo.ocr_layout` 的可移植 JSON 契约。下游 CathyGO Agent、Codex 和 Cursor workflow 应依赖这个形状，而不是依赖 provider-specific 字段。

## 顶层字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `skill` | 是 | 必须是 `cathygo.ocr_layout` |
| `version` | 是 | 当前为 `0.1` |
| `status` | 是 | `ok` 或 `failed` |
| `provider` | 是 | `{ name, model }` |
| `sourceImage` | 是 | `{ imageId, width, height, mimeType }` |
| `text` | 是 | `{ markdown, plain }` |
| `elements` | 是 | 归一化 layout elements |
| `screenshotCandidates` | 是 | 下游 asset generation 的裁剪目标 |
| `diagnostics` | 是 | 调试元数据；`rawProvider` 只能用于 diagnostics |

## 归一化 bbox

所有暴露给下游 skills 的 bbox 必须使用：

```json
{ "x": 0, "y": 0, "width": 1, "height": 1, "unit": "normalized" }
```

规则：

- 坐标相对于 source image 的宽高。
- `x` 和 `y` 是左上角。
- `width` 和 `height` 是 `0..1` 内的正跨度。
- 如果 provider 返回像素坐标，除以 page width/height。
- 如果 provider 已经返回 `0..1` 值，clamp 后透传。

## Element 形状

每个 `elements[]` item 应包含：

- `id`：稳定的本地标识，例如 `layout_0_1`
- `pageIndex`：source image 内的零基页面索引
- `index`：可用时使用 provider reading index
- `type`：`text`、`formula`、`table`、`image` 或 `figure_title`
- `label`、`nativeLabel`、`content`
- `bbox`：归一化 bbox
- `source`：`{ provider, model, field, imageId }`

## Screenshot candidates

`screenshotCandidates[]` 是 CathyGO asset cropping 的 bbox source of truth：

- `problem`：页面上所有 layout elements 的 union
- `diagram_all`：存在 image elements 时，所有 image elements 的 union
- `diagram_1..diagram_n`：每个 image element 一个 candidate

下游 runtime 代码可以用这些归一化 bbox 裁剪本地 source image。`diagnostics.rawProvider` 中的 provider crop URL 只能用于调试，不能成为生产 asset。

## Python helpers

通过这个 Skill 的 Python CLI 使用共享 `beanx_learning.ocr` 逻辑：

```bash
python3 scripts/ocr.py normalize --input raw-glm-ocr.json --out /tmp/page.ocr-layout.json
python3 scripts/ocr.py extract --input raw-glm-ocr.json --attachment-id page_1 --out /tmp/page.unified-ocr.json
python3 scripts/ocr.py asset-candidates --input raw-glm-ocr.json --source-id page_1 --out /tmp/page.assets.json
python3 scripts/ocr.py select --input /tmp/page.ocr-layout.json --question 1 --out /tmp/page.selection.json
```

`cathygo.ocr_layout` 仍然是这个仓库中的可移植 layout 契约。Unified OCR extract 是连接当前 CathyGO Agent `learning-core` document format 的桥接格式。

## 下游交接

- 一张拍照页面图片生成一个 `cathygo.ocr_layout` JSON。
- 多页试卷先对每页运行这个 primitive，再把有序 JSON 文件传给 `scripts/problem_set.py`。
- 解题、批改、讲解、裁剪 materialization 和 Web rendering 都发生在独立的下游 runtime 或 agent 代码中。

## Clean-room 边界

- 不要把拍照 source image、教材扫描件或真实试卷 OCR output 提交到这个仓库。
- 本地 debug artifact 放在 `tmp/` 等 ignored path 下。
- 这个 Skill 中的示例只能使用合成 prompt 和合成 OCR output。

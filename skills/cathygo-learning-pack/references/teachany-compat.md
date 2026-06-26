# TeachAny 兼容说明

CathyGO 内容包可以导出 TeachAny 兼容的 `manifest.json` 和 `knowledge-context.json`，但 CathyGO 仍然是 source of truth。

## Manifest 映射

| CathyGO field | TeachAny field |
| --- | --- |
| `id` | `course_id`, `id` |
| `compat.teachany.node_id` | `node_id` |
| `title` | `name` |
| `subject` | `subject` |
| `stage` | `stage` |
| `objectives[].text` | `learning_objectives[]` |
| `prerequisites` | `prerequisites[]` |
| `leads_to` | `leads_to[]` |

## Knowledge Context 形状

`knowledge-context.json` 应保持紧凑结构：

```json
{
  "topic": "Algebraic Fractions",
  "subject": "math",
  "match_count": 1,
  "matches": [
    {
      "node_id": "math-m-algebraic-fractions",
      "name_zh": "代数分式",
      "subject": "math",
      "stage": "middle",
      "curriculum_excerpts": [],
      "exercises": [],
      "common_errors": [],
      "prerequisites": [],
      "extends": [],
      "gaps": []
    }
  ],
  "_source": "cathygo-learning-pack"
}
```

## 边界

- 不要在这个 Skill 中生成 TeachAny HTML 页面。
- 不要从这个仓库写入 TeachAny registry 文件。
- TeachAny 专用值放在 `compat.teachany` 下。

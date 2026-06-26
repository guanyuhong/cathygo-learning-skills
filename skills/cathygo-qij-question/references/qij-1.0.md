# Question Interchange JSON（QIJ）1.0

> 一套面向 AI 生成、Web 渲染、用户作答、评分和分步讲解的轻量 JSON 题目格式。

- **状态**：Draft Specification（Schema Complete）
- **版本**：1.0
- **建议扩展名**：`.qij.json`
- **正式 Schema**：`schema/qij-1.0.schema.json`
- **数据格式**：JSON
- **文档语言**：中文

---

## 0. 名称

本规范名称为 **Question Interchange JSON**，缩写为 **QIJ**。

- `QijDocument`：TypeScript 和实现中的根文档类型；
- `qij`：JSON 中 `spec` 字段的固定值；
- `.qij.json`：推荐文件扩展名；
- `qij-1.0.schema.json`：1.0 版正式 JSON Schema。

本规范不使用 `QIF`。该缩写已经被 Quicken Interchange Format 和 ISO 23952 Quality Information Framework 等成熟格式使用，继续复用会造成文件扩展名、搜索结果和工具链歧义。

参考：

- [Quicken Interchange Format](https://www.w3.org/2000/10/swap/pim/qif-doc/QIF-doc.htm)
- [ISO 23952 Quality Information Framework](https://www.iso.org/standard/77461.html)

---

## 1. 目标

QIJ 用一份 JSON 描述：

- 单题、多题和共享材料题；
- 文本、公式、图片、音视频、表格、代码和互动示意图；
- 选择、判断、填空、数值、表达式、排序、匹配和开放作答；
- 标准答案、评分规则和部分分；
- 一种或多种解题方法；
- 多步骤讲解、步骤检查点和配图动作；
- Web 端如何选择组件并渲染。

QIJ 不使用不断膨胀的 `questionType` 枚举。题目由以下四部分组合：

```text
题目 = 内容 Content + 作答 Response + 评分 Grading + 解法 Solution
```

例如：

```text
单选题 = 文本内容 + choice 作答
填空题 = 文本内容 + text/number/expression 作答
大题   = group + 多个子题，或 question + 多个作答项
图形题 = 文本内容 + widget 资源 + 普通或 widget 作答
```

### 1.1 设计原则

1. JSON 只描述数据，不包含任意 JavaScript；
2. 内容、作答、评分和解法相互分离；
3. 一个题目可以有多个作答项；
4. 答案集中在 `answerKey`，学生端可整体移除；
5. 普通 Web 客户端可以只实现核心类型；
6. 复杂互动必须有 fallback；
7. 新能力通过命名空间扩展，而不是修改已有字段语义。

### 1.2 非目标

QIJ 1.0 不直接定义：

- 用户、账号和权限；
- 监考和防作弊；
- 自适应选题算法；
- 学习行为事件流；
- 任意插件执行环境；
- 大模型内部推理过程。

---

## 2. 规范用语

- **必须（MUST）**：不满足则不符合规范；
- **应该（SHOULD）**：通常应满足，除非有充分理由；
- **可以（MAY）**：可选能力。

所有文档必须是符合 RFC 8259 的 JSON。不得使用注释、尾随逗号、`NaN` 或 `Infinity`。

字段名使用 `camelCase`。枚举值使用小写英文和连字符，例如 `after-submit`。

---

## 3. 核心模型

```text
QijDocument
├── delivery                 展示和提交策略
├── assets                   图片、音视频和互动组件
├── items[]                  题目或题组
│   ├── question
│   │   ├── content[]        题目内容
│   │   └── responses[]      用户如何作答
│   └── group
│       ├── content[]        共享材料
│       └── items[]          子题
└── answerKey                答案、评分和解法
    └── <questionId>
        ├── grading
        └── solution
```

QIJ 只定义两种 Item：

- `question`：可以作答和评分；
- `group`：包含共享内容和子题，自身不作答。

---

## 4. 最小有效示例

```json
{
  "$schema": "../schema/qij-1.0.schema.json",
  "spec": "qij",
  "version": "1.0",
  "id": "math-demo-001",
  "title": "基础练习",
  "language": "zh-CN",
  "items": [
    {
      "kind": "question",
      "id": "q1",
      "points": 1,
      "content": [
        {
          "type": "markdown",
          "text": "计算 $1+1$。"
        }
      ],
      "responses": [
        {
          "id": "answer",
          "type": "number",
          "label": "答案"
        }
      ]
    }
  ],
  "answerKey": {
    "q1": {
      "grading": {
        "answer": {
          "type": "numeric",
          "expected": 2,
          "points": 1
        }
      },
      "solution": {
        "final": [
          {
            "type": "math",
            "latex": "2",
            "display": "block"
          }
        ]
      }
    }
  }
}
```

---

## 5. 顶层文档

下面是字段结构示意。空 `items` 仅用于展示顶层字段，不是有效的完整文档。

```json
{
  "$schema": "../schema/qij-1.0.schema.json",
  "spec": "qij",
  "version": "1.0",
  "id": "document-id",
  "title": "题目集标题",
  "language": "zh-CN",
  "delivery": {},
  "assets": {},
  "items": [],
  "answerKey": {},
  "metadata": {},
  "extensions": {}
}
```

| 字段 | 必填 | 类型 | 说明 |
|---|---:|---|---|
| `$schema` | 否 | string | Schema URI 或相对路径，便于编辑器校验 |
| `spec` | 是 | string | 固定为 `qij` |
| `version` | 是 | string | 当前为 `1.0` |
| `id` | 是 | string | 文档唯一 ID |
| `title` | 是 | string | 文档标题 |
| `language` | 是 | string | 文档默认语言，使用 BCP 47 标签，如 `zh-CN` |
| `delivery` | 否 | object | 展示和提交策略 |
| `assets` | 否 | object | 资源表，键为 Asset ID |
| `items` | 是 | array | 至少一个 Item |
| `answerKey` | 否 | object | 答案、评分和解法 |
| `metadata` | 否 | object | 学科、年级、知识点等 |
| `extensions` | 否 | object | 命名空间扩展 |

### 5.1 ID

ID 应满足：

```regex
^[A-Za-z][A-Za-z0-9._-]{0,63}$
```

规则：

- Item ID 在整个文档中唯一；
- Asset ID 在 `assets` 中唯一；
- Response ID 在所属 Question 中唯一；
- Option ID 在所属 Response 中唯一；
- Method ID 在所属 Solution 中唯一；
- Step ID 在所属 Method 中唯一。

显示名称变化时，不应修改稳定 ID。

Item 和 ContentBlock 可以使用可选的 `language` 字段覆盖文档默认语言。

### 5.2 `delivery`

```json
{
  "mode": "practice",
  "submitMode": "item",
  "solutionMode": "after-submit",
  "shuffleItems": false
}
```

| 字段 | 可选值 | 默认值 |
|---|---|---|
| `mode` | `practice` / `exam` / `tutor` | `practice` |
| `submitMode` | `item` / `all` | `item` |
| `solutionMode` | `never` / `after-submit` / `step-by-step` | `after-submit` |
| `shuffleItems` | boolean | `false` |

`delivery` 只是展示建议，不是安全边界。答案是否下发必须由服务端控制。

---

## 6. Item

### 6.1 Question

下面是结构片段；有效 Question 的 `responses` 至少包含一个元素。

```json
{
  "kind": "question",
  "id": "q1",
  "title": "可选标题",
  "points": 2,
  "content": [],
  "responses": [],
  "metadata": {},
  "extensions": {}
}
```

规则：

- `kind` 固定为 `question`；
- `points` 必须为非负数；
- `content` 是有序内容块；
- `responses` 至少包含一个作答项；
- 一个 Question 可以包含多个 Response；
- 未在内容中显式放置的 Response，应在题目内容末尾按声明顺序渲染；
- 当 `answerKey` 中存在完整评分规则时，`points` 应等于这些规则的最高总分。

### 6.2 Group

下面是结构片段；有效 Group 的 `items` 至少包含一个元素。

```json
{
  "kind": "group",
  "id": "reading-1",
  "title": "阅读材料，回答问题",
  "content": [],
  "items": [],
  "metadata": {},
  "extensions": {}
}
```

规则：

- `kind` 固定为 `group`；
- Group 自身不评分；
- 共享材料放在 `content`；
- 子题放在 `items`；
- 子 Item 可以是 Question 或 Group；
- Group 的共享 `content` 不得放置正式 Response；
- 建议嵌套深度不超过 3 层。

Group 可表示阅读理解、一题多问、共享图表、材料分析和试卷章节。

---

## 7. ContentBlock

`content` 是有序数组。QIJ 1.0 定义七种内容块：

| `type` | 用途 |
|---|---|
| `markdown` | 普通富文本 |
| `math` | 独立数学公式 |
| `asset` | 图片、音视频或 Widget 引用 |
| `table` | 表格 |
| `code` | 代码文本 |
| `response` | 放置作答控件 |
| `template` | 文本、公式和输入框行内混排 |

### 7.1 Markdown

```json
{
  "type": "markdown",
  "text": "已知函数 $y=2x+1$，求 $x=3$ 时的函数值。"
}
```

- 建议支持 CommonMark；
- 可以约定 `$...$` 和 `$$...$$` 表示 LaTeX；
- 默认禁止原始 HTML；
- Web 端必须对白名单外内容进行清洗。

### 7.2 Math

```json
{
  "type": "math",
  "latex": "k=\\frac{y_2-y_1}{x_2-x_1}",
  "display": "block",
  "alt": "k 等于纵坐标差除以横坐标差"
}
```

`display` 为 `inline` 或 `block`，默认 `block`。

### 7.3 Asset 引用

```json
{
  "type": "asset",
  "assetId": "figure-1",
  "caption": "图 1"
}
```

`assetId` 必须存在于顶层 `assets`。

### 7.4 Table

```json
{
  "type": "table",
  "columns": ["x", "y"],
  "rows": [
    [1, 2],
    [3, 6]
  ],
  "caption": "坐标数据"
}
```

单元格可以是字符串、数字、布尔值或 `null`。

### 7.5 Code

```json
{
  "type": "code",
  "codeLanguage": "python",
  "code": "def add(a, b):\n    return a + b",
  "lineNumbers": true
}
```

`codeLanguage` 表示编程语言或语法高亮标识；ContentBlock 自然语言覆盖仍使用可选的 `language`。代码块只是文本，执行代码必须使用独立沙箱。

### 7.6 Response 位置

```json
{
  "type": "response",
  "responseId": "answer"
}
```

### 7.7 Template

用于行内填空：

```json
{
  "type": "template",
  "parts": [
    {"type": "text", "text": "当 "},
    {"type": "math", "latex": "x=2"},
    {"type": "text", "text": " 时，"},
    {"type": "math", "latex": "x+3="},
    {"type": "response", "responseId": "blank-1"},
    {"type": "text", "text": "。"}
  ]
}
```

`parts` 只支持 `text`、`math` 和 `response`，并在同一行或同一段落按顺序渲染。

---

## 8. Assets

`assets` 是以 Asset ID 为键的对象：

```json
{
  "assets": {
    "figure-1": {
      "type": "image",
      "src": "assets/figure-1.svg",
      "mimeType": "image/svg+xml",
      "alt": "坐标系中直线经过 A 和 B 两点"
    }
  }
}
```

QIJ 1.0 定义：

| `type` | 关键字段 |
|---|---|
| `image` | `src`、`mimeType`、`alt`、可选宽高 |
| `audio` | `src`、`mimeType`、可选 `transcript` |
| `video` | `src`、`mimeType`、可选字幕和文字稿 |
| `file` | `src`、`mimeType`、`name` |
| `widget` | `name`、`props`、`alt`、`fallbackAssetId` |

### 8.1 Image

```json
{
  "type": "image",
  "src": "assets/triangle.png",
  "mimeType": "image/png",
  "alt": "直角三角形 ABC，其中 C 为直角",
  "width": 800,
  "height": 600
}
```

### 8.2 Audio / Video

```json
{
  "type": "audio",
  "src": "assets/listening.mp3",
  "mimeType": "audio/mpeg",
  "transcript": "音频文字稿"
}
```

```json
{
  "type": "video",
  "src": "assets/experiment.mp4",
  "mimeType": "video/mp4",
  "captionSrc": "assets/experiment.zh-CN.vtt",
  "transcript": "实验视频文字说明"
}
```

### 8.3 Widget

```json
{
  "type": "widget",
  "name": "geometry2d",
  "alt": "可交互坐标系，包含 A、B 两点和直线 AB",
  "props": {
    "points": [
      {"id": "A", "x": 1, "y": 2},
      {"id": "B", "x": 3, "y": 6}
    ],
    "lines": [
      {"id": "AB", "through": ["A", "B"]}
    ]
  },
  "fallbackAssetId": "figure-1-static"
}
```

规则：

- `name` 必须对应客户端预注册组件；
- `props` 只能包含 JSON 数据，不能包含函数或代码；
- 不支持该 Widget 的客户端必须使用 fallback；
- Widget 默认不得访问网络、Cookie、LocalStorage 或宿主页面 DOM。

---

## 9. Response

公共字段：

```json
{
  "id": "answer",
  "type": "text",
  "label": "答案",
  "required": true,
  "placeholder": "请输入"
}
```

| 字段 | 必填 | 说明 |
|---|---:|---|
| `id` | 是 | Question 内唯一 |
| `type` | 是 | 作答类型 |
| `label` | 是 | 可见或无障碍标签 |
| `required` | 否 | 默认 `true` |
| `placeholder` | 否 | 输入提示 |
| `extensions` | 否 | 命名空间扩展 |

QIJ 1.0 的 Response 类型：

| `type` | 作答值 |
|---|---|
| `choice` | option ID 或 option ID 数组 |
| `boolean` | boolean |
| `text` | string |
| `number` | number，或提交前的原始字符串 |
| `expression` | string |
| `ordering` | option ID 数组 |
| `matching` | 左侧 ID 到右侧 ID 的对象 |
| `widget` | 组件定义的可序列化 JSON |

### 9.1 Choice

```json
{
  "id": "answer",
  "type": "choice",
  "label": "请选择正确答案",
  "multiple": false,
  "shuffle": false,
  "options": [
    {
      "id": "A",
      "content": [{"type": "markdown", "text": "选项 A"}]
    },
    {
      "id": "B",
      "content": [{"type": "markdown", "text": "选项 B"}]
    }
  ]
}
```

Option 的 `content` 不得包含 `response` 内容块，也不得在 `template` 中嵌入 Response。

`multiple` 默认 `false`，`shuffle` 默认 `false`。

多选时：

```json
{
  "id": "answer",
  "type": "choice",
  "label": "请选择所有正确答案",
  "multiple": true,
  "minSelections": 1,
  "maxSelections": 3,
  "options": []
}
```

### 9.2 Boolean

```json
{
  "id": "answer",
  "type": "boolean",
  "label": "请选择正确或错误",
  "trueLabel": "正确",
  "falseLabel": "错误"
}
```

### 9.3 Text

```json
{
  "id": "answer",
  "type": "text",
  "label": "作答内容",
  "multiline": true,
  "maxLength": 2000
}
```

### 9.4 Number

```json
{
  "id": "answer",
  "type": "number",
  "label": "长度",
  "unit": "cm",
  "min": 0,
  "step": 0.1
}
```

`unit` 是固定显示单位。超出 JSON 安全整数范围的整数、精确分数或高精度小数，应使用 `expression` 或 `text`。

### 9.5 Expression

```json
{
  "id": "answer",
  "type": "expression",
  "label": "函数表达式",
  "variables": ["x"],
  "inputFormat": "latex"
}
```

`inputFormat` 为 `latex` 或 `text`。

### 9.6 Ordering

```json
{
  "id": "answer",
  "type": "ordering",
  "label": "请按正确顺序排列",
  "options": [
    {"id": "a", "content": [{"type": "markdown", "text": "审题"}]},
    {"id": "b", "content": [{"type": "markdown", "text": "列式"}]},
    {"id": "c", "content": [{"type": "markdown", "text": "计算"}]}
  ]
}
```

### 9.7 Matching

```json
{
  "id": "answer",
  "type": "matching",
  "label": "请完成匹配",
  "left": [
    {"id": "l1", "content": [{"type": "markdown", "text": "H₂O"}]}
  ],
  "right": [
    {"id": "r1", "content": [{"type": "markdown", "text": "水"}]}
  ]
}
```

### 9.8 Widget Response

```json
{
  "id": "answer",
  "type": "widget",
  "label": "请绘制函数图像",
  "name": "graph-plot",
  "props": {
    "xMin": -5,
    "xMax": 5,
    "yMin": -5,
    "yMax": 5
  },
  "fallback": {
    "type": "text",
    "label": "请用关键坐标描述图像",
    "multiline": true
  }
}
```

Widget Response 必须输出可序列化 JSON，并提供可用 fallback。 QIJ 1.0 的 fallback 可以是 `choice`、`boolean`、`text`、`number` 或 `expression`，不得再次使用 `widget`。

---

## 10. AnswerKey 与 Grading

`answerKey` 以 Question ID 为键，`grading` 以 Response ID 为键：

```json
{
  "answerKey": {
    "q1": {
      "grading": {
        "answer": {
          "type": "numeric",
          "expected": 2,
          "points": 2
        }
      },
      "solution": {}
    }
  }
}
```

QIJ 1.0 定义六种评分规则：

| `type` | 用途 |
|---|---|
| `exact` | 单选、判断、文本精确匹配 |
| `set` | 多选集合匹配 |
| `numeric` | 数值和容差 |
| `expression` | 数学表达式等价 |
| `rubric` | 开放题评分点 |
| `manual` | 人工评分 |

### 10.1 Exact

```json
{
  "type": "exact",
  "accepted": ["B"],
  "points": 1,
  "normalization": {
    "trim": true,
    "caseSensitive": false,
    "collapseWhitespace": true
  }
}
```

`accepted` 可以包含任意 JSON 值。数组和对象使用深度相等比较；`normalization` 只作用于字符串。默认值为 `trim=true`、`caseSensitive=true`、`collapseWhitespace=false`。

### 10.2 Set

```json
{
  "type": "set",
  "expected": ["A", "C"],
  "points": 2,
  "partialCredit": false
}
```

默认不关心顺序，`partialCredit` 默认 `false`。`partialCredit=false` 时，实际集合必须与期望集合完全相等；`partialCredit=true` 时，必须按下面的公式计算：

```text
ratio = clamp((正确选择数 - 错误选择数) / 期望答案数, 0, 1)
score = points × ratio
```

### 10.3 Numeric

```json
{
  "type": "numeric",
  "expected": 3.14,
  "absoluteTolerance": 0.01,
  "relativeTolerance": 0,
  "points": 2
}
```

`absoluteTolerance` 和 `relativeTolerance` 默认均为 `0`。通过条件：

```text
|actual - expected| <= absoluteTolerance
或
|actual - expected| <= |expected| × relativeTolerance
```

### 10.4 Expression

```json
{
  "type": "expression",
  "expected": "2*x+1",
  "variables": ["x"],
  "equivalence": "symbolic",
  "points": 2
}
```

`equivalence`：

- `symbolic`：CAS 或专用服务判等；
- `numeric-sampling`：定义域内采样；
- `exact-text`：规范化字符串匹配。

`equivalence` 默认 `symbolic`。复杂表达式判等不应由普通 Web 客户端实现。

### 10.5 Rubric

```json
{
  "type": "rubric",
  "points": 3,
  "criteria": [
    {"id": "formula", "description": "公式正确", "points": 1},
    {"id": "process", "description": "推导合理", "points": 1},
    {"id": "result", "description": "结果正确", "points": 1}
  ]
}
```

### 10.6 Manual

```json
{
  "type": "manual",
  "points": 10
}
```

### 10.7 Feedback

在正式 Question 的 `grading` 中，每条规则必须包含 `points`；Checkpoint 内的规则可以省略。`number.unit` 表示固定显示单位，不参与单位换算；需要自由输入单位或单位转换时，应使用 Expression、Text 或扩展评分器。

任意评分规则可以包含：

```json
{
  "feedback": {
    "correct": [
      {"type": "markdown", "text": "回答正确。"}
    ],
    "incorrect": [
      {"type": "markdown", "text": "请检查计算顺序。"}
    ]
  }
}
```

---

## 11. Solution

Solution 表示可展示的教学讲解，不表示模型内部隐藏推理。除 Checkpoint 外，Solution、Feedback 和 Option 的内容不得包含正式 `response` 内容块，也不得在 `template` 中引用正式 Response。

```json
{
  "final": [
    {"type": "markdown", "text": "最终答案或结论。"}
  ]
}
```

`final`、`methods` 和 `commonMistakes` 均为可选字段；出现时数组至少包含一个元素。一个 Solution 至少包含其中之一。

### 11.1 多种方法

```json
{
  "methods": [
    {
      "id": "formula-method",
      "title": "公式法",
      "summary": "直接使用公式计算。",
      "steps": [
        {
          "id": "step-1",
          "content": [
            {"type": "markdown", "text": "写出并使用目标公式。"}
          ]
        }
      ]
    },
    {
      "id": "graph-method",
      "title": "图像法",
      "summary": "从图像关系得到结果。",
      "steps": [
        {
          "id": "step-1",
          "content": [
            {"type": "markdown", "text": "读取图像中的关键关系。"}
          ]
        }
      ]
    }
  ]
}
```

### 11.2 Step

```json
{
  "id": "step-1",
  "title": "确定已知条件",
  "content": [
    {"type": "markdown", "text": "已知 $A(1,2)$ 和 $B(3,6)$。"}
  ]
}
```

步骤按数组顺序线性播放。QIJ 1.0 不定义任意流程图或循环。

### 11.3 VisualAction

```json
{
  "assetId": "figure-1",
  "action": "highlight",
  "targetIds": ["A", "B"],
  "params": {"emphasis": "strong"}
}
```

通用动作：

| `action` | 含义 |
|---|---|
| `highlight` | 高亮对象 |
| `show` | 显示对象 |
| `hide` | 隐藏对象 |
| `set` | 修改组件支持的参数 |
| `reset` | 恢复初始状态 |

不支持某个动作时，客户端应忽略动作，但继续展示步骤文本。

### 11.4 Checkpoint

```json
{
  "checkpoint": {
    "prompt": [
      {"type": "markdown", "text": "先计算 $6-2$。"}
    ],
    "response": {
      "id": "checkpoint-answer",
      "type": "number",
      "label": "结果"
    },
    "grading": {
      "type": "numeric",
      "expected": 4
    },
    "hint": [
      {"type": "markdown", "text": "$6-2=4$。"}
    ]
  }
}
```

Checkpoint：

- 只用于讲解互动，不计入正式分数；
- 复用 Response 和 Grading；
- Web 可以答对后展开下一步，也可以允许跳过。

---

## 12. 常见题型映射

| 常见题型 | QIJ 表示 |
|---|---|
| 单选 | `choice`，`multiple=false` |
| 多选 | `choice`，`multiple=true` |
| 判断 | `boolean` |
| 填空 | `template` + `text` / `number` / `expression` |
| 多空 | 一个 Question + 多个 Response |
| 简答 | `text`，`multiline=true` |
| 一题多问 | Group + 多个子 Question |
| 阅读理解 | Group 的共享 Content + 子 Question |
| 图表题 | Asset + 普通 Response |
| 互动图形题 | Widget Asset + 普通或 Widget Response |
| 编程题 | Code + Text 或 Widget Response |
| 作文题 | Text + Rubric |

---

## 13. Authoring 与 Delivery

### 13.1 Authoring Document

用于编辑、审核和存储，可以包含：

```text
items
assets
answerKey.grading
answerKey.solution
metadata
```

### 13.2 Delivery Document

用于学生作答。服务端必须移除整个：

```text
answerKey
```

示例：

```ts
function toDeliveryDocument(document: QijDocument): QijDocument {
  const { answerKey: _removed, ...delivery } = document;
  return delivery;
}
```

考试模式不能依赖 CSS 隐藏答案。答案数据不得进入浏览器。

练习模式建议在提交后按题从服务端返回 Feedback 和 Solution，而不是初始预加载。

---

## 14. Web 解析

推荐流程：

```text
1. JSON.parse
2. JSON Schema 校验
3. 检查 spec 和主版本
4. 建立 Asset Registry
5. 递归渲染 Item
6. 按 ContentBlock.type 选择组件
7. 按 Response.type 选择输入组件
8. 以 questionId + responseId 保存状态
9. 提交服务端评分
10. 按策略显示 Feedback 和 Solution
```

### 14.1 Renderer Registry

```ts
const contentRenderers = {
  markdown: MarkdownBlock,
  math: MathBlock,
  asset: AssetBlock,
  table: TableBlock,
  code: CodeBlock,
  response: ResponseBlock,
  template: TemplateBlock
};

const responseRenderers = {
  choice: ChoiceInput,
  boolean: BooleanInput,
  text: TextInput,
  number: NumberInput,
  expression: ExpressionInput,
  ordering: OrderingInput,
  matching: MatchingInput,
  widget: WidgetInput
};
```

### 14.2 状态结构

```json
{
  "q1": {
    "answer": 2
  },
  "q2": {
    "blank-1": "北京",
    "blank-2": "上海"
  }
}
```

### 14.3 未知类型

- 未知 ContentBlock：显示“不支持此内容”；
- 未知核心 Response：阻止该题提交并显示错误；
- 未知 Widget：使用 fallback；
- 未知扩展：忽略，不得导致页面崩溃。

---

## 15. 推荐 Attempt 格式

Attempt 不属于 QIJ 核心，但推荐使用：

```json
{
  "spec": "qij-attempt",
  "version": "1.0",
  "attemptId": "attempt-001",
  "documentId": "math-demo-001",
  "responses": {
    "q1": {
      "answer": 2
    }
  },
  "status": "in-progress"
}
```

`status` 可为 `in-progress`、`submitted` 或 `graded`。

---

## 16. Metadata 与 Extensions

### 16.1 Metadata

```json
{
  "metadata": {
    "subject": "math",
    "grade": "8",
    "difficulty": 2,
    "skills": ["linear-function.slope"],
    "tags": ["一次函数", "斜率"],
    "createdAt": "2026-06-26T10:00:00Z"
  }
}
```

元数据不影响核心渲染。`difficulty` 的量表由业务定义。

### 16.2 Extensions

非标准数据必须放入 `extensions`，键使用反向域名。`extensions` 可以出现在文档、Item、Response、Asset、Solution、Method 或 Step 等可扩展对象中：

```json
{
  "extensions": {
    "com.example.aiProvenance": {
      "model": "example-model",
      "workflowVersion": "2.1",
      "reviewed": false
    }
  }
}
```

规则：

- 扩展不得改变核心字段语义；
- 客户端应忽略未知扩展；
- 作答所必需的扩展必须提供标准 fallback；
- 扩展不得包含可执行代码。

---

## 17. 版本兼容

`version` 格式：

```text
<major>.<minor>
```

规则：

- 主版本变化可能不兼容；
- 次版本只能增加可选字段或能力；
- Renderer 必须拒绝不支持的主版本；
- `qij-1.0.schema.json` 严格校验 `version: "1.0"`，并拒绝未知核心字段；
- 后续次版本必须发布对应 Schema，例如 `qij-1.1.schema.json`；
- Renderer 只有在显式支持或协商到对应次版本时，才应接受更高次版本；
- 同一主版本内不得删除字段或改变字段原义；
- 跨实现扩展优先放入 `extensions`，避免依赖宽松解析。

---

## 18. 校验

正式实现必须执行两层校验：

1. **结构校验**：使用 `schema/qij-1.0.schema.json`，校验字段、枚举、必填项和基本数据范围；
2. **语义校验**：检查跨对象引用、ID 唯一性、答案选项、分值汇总和 Widget fallback 等 JSON Schema 无法通用表达的规则。

本文中的若干结构片段为了展示字段使用了空数组；只有同时通过结构和语义校验的实例才是有效 QIJ 文档：

1. Item ID 全局唯一；
2. Asset 引用存在；
3. Response 引用存在；
4. `answerKey` 中的 Question 存在；
5. Grading 中的 Response 存在；
6. Choice 答案引用有效 Option ID；
7. Question `points` 等于正式评分规则的最高总分；
8. Rubric criteria 分值之和等于 Rubric `points`；
9. Widget fallback 存在、指向非 Widget 资源，且不存在 fallback 环；
10. Solution Action 引用有效 Asset；
11. Group 至少包含一个子 Item；
12. Method 和 Step ID 在作用域内唯一；
13. Table 每行单元格数与 `columns` 数量一致；
14. Number Response 的 `min` 不大于 `max`；
15. Choice 的选择数量范围有效，且不超过 Option 数量。

推荐错误格式：

```json
{
  "valid": false,
  "errors": [
    {
      "path": "/items/0/content/1/assetId",
      "code": "ASSET_NOT_FOUND",
      "message": "Asset 'figure-x' does not exist."
    }
  ]
}
```

---

## 19. 安全

实现必须：

1. 默认禁止 Markdown 原始 HTML；
2. 对渲染输出进行白名单清洗；
3. 禁止执行 JSON 中的 JavaScript、事件处理器和动态表达式；
4. Widget 只能从客户端注册表加载；
5. 清理 SVG 中的脚本、事件属性、`foreignObject` 和危险外链；
6. 禁止 `javascript:` 和不安全的 `data:` URL；
7. 学生端不得收到未授权的 `answerKey`；
8. 代码题必须使用资源受限的沙箱；
9. 服务端必须重新校验所有用户提交；
10. 上传资源必须进行类型、大小和恶意文件检查。

---

## 20. 可访问性

Web Renderer 应以 WCAG 2.2 AA 为目标，并至少做到：

- 图片和 Widget 提供 `alt`；
- 每个 Response 提供 `label`；
- 所有控件支持键盘操作；
- 拖拽交互提供非拖拽替代方案；
- 颜色不是唯一信息载体；
- 音频提供 transcript；
- 视频提供字幕或 transcript；
- 公式提供可访问 MathML、文本说明或等价输出；
- 焦点顺序与内容顺序一致；
- 动画支持暂停，并尊重 `prefers-reduced-motion`。

---

## 21. 完整示例

```json
{
  "spec": "qij",
  "version": "1.0",
  "id": "linear-function-001",
  "title": "一次函数练习",
  "language": "zh-CN",
  "delivery": {
    "mode": "tutor",
    "submitMode": "item",
    "solutionMode": "step-by-step",
    "shuffleItems": false
  },
  "assets": {
    "figure-1-static": {
      "type": "image",
      "src": "assets/line-ab.svg",
      "mimeType": "image/svg+xml",
      "alt": "坐标系中一条直线经过 A(1,2) 和 B(3,6)"
    },
    "figure-1": {
      "type": "widget",
      "name": "geometry2d",
      "alt": "可交互坐标系中一条直线经过 A 和 B 两点",
      "props": {
        "viewport": {
          "xMin": -1,
          "xMax": 5,
          "yMin": -1,
          "yMax": 8
        },
        "points": [
          {"id": "A", "x": 1, "y": 2, "label": "A"},
          {"id": "B", "x": 3, "y": 6, "label": "B"}
        ],
        "lines": [
          {"id": "AB", "through": ["A", "B"]}
        ]
      },
      "fallbackAssetId": "figure-1-static"
    }
  },
  "items": [
    {
      "kind": "question",
      "id": "q1",
      "title": "求直线斜率",
      "points": 2,
      "content": [
        {
          "type": "markdown",
          "text": "直线经过点 $A(1,2)$ 和 $B(3,6)$，求直线的斜率。"
        },
        {
          "type": "asset",
          "assetId": "figure-1",
          "caption": "直线 AB"
        },
        {
          "type": "response",
          "responseId": "answer"
        }
      ],
      "responses": [
        {
          "id": "answer",
          "type": "number",
          "label": "斜率 k",
          "placeholder": "请输入斜率"
        }
      ],
      "metadata": {
        "subject": "math",
        "grade": "8",
        "difficulty": 2,
        "skills": ["linear-function.slope"]
      }
    }
  ],
  "answerKey": {
    "q1": {
      "grading": {
        "answer": {
          "type": "numeric",
          "expected": 2,
          "absoluteTolerance": 0,
          "relativeTolerance": 0,
          "points": 2,
          "feedback": {
            "correct": [
              {"type": "markdown", "text": "回答正确。"}
            ],
            "incorrect": [
              {"type": "markdown", "text": "请检查两个坐标差的顺序。"}
            ]
          }
        }
      },
      "solution": {
        "final": [
          {
            "type": "math",
            "latex": "k=2",
            "display": "block"
          }
        ],
        "methods": [
          {
            "id": "formula-method",
            "title": "斜率公式法",
            "summary": "使用两点式斜率公式。",
            "steps": [
              {
                "id": "step-1",
                "title": "确定两点坐标",
                "content": [
                  {
                    "type": "markdown",
                    "text": "两点为 $A(1,2)$ 和 $B(3,6)$。"
                  }
                ],
                "actions": [
                  {
                    "assetId": "figure-1",
                    "action": "highlight",
                    "targetIds": ["A", "B"]
                  }
                ]
              },
              {
                "id": "step-2",
                "title": "写出公式",
                "content": [
                  {
                    "type": "math",
                    "latex": "k=\\frac{y_2-y_1}{x_2-x_1}",
                    "display": "block"
                  }
                ],
                "checkpoint": {
                  "prompt": [
                    {"type": "markdown", "text": "先计算 $6-2$。"}
                  ],
                  "response": {
                    "id": "checkpoint-answer",
                    "type": "number",
                    "label": "纵坐标之差"
                  },
                  "grading": {
                    "type": "numeric",
                    "expected": 4
                  },
                  "hint": [
                    {"type": "markdown", "text": "$6-2=4$。"}
                  ]
                }
              },
              {
                "id": "step-3",
                "title": "代入计算",
                "content": [
                  {
                    "type": "math",
                    "latex": "k=\\frac{6-2}{3-1}=\\frac{4}{2}=2",
                    "display": "block"
                  }
                ],
                "actions": [
                  {
                    "assetId": "figure-1",
                    "action": "highlight",
                    "targetIds": ["AB"]
                  }
                ]
              }
            ]
          }
        ],
        "commonMistakes": [
          {
            "type": "markdown",
            "text": "分子和分母必须使用相同的点顺序。"
          }
        ]
      }
    }
  },
  "metadata": {
    "subject": "math",
    "grade": "8",
    "tags": ["一次函数", "斜率"]
  }
}
```

---

## 22. TypeScript 类型包

正式 TypeScript 包位于：

```text
packages/typescript/
├── package.json
├── tsconfig.json
└── src/
    ├── types.ts
    ├── guards.ts
    ├── semantic-validator.ts
    └── index.ts
```

包导出：

- 完整判别联合类型，包括所有 Item、ContentBlock、Asset、Response、GradingRule 和 Solution；
- `looksLikeQijDocument` 浅层守卫；
- `validateQijSemantics` 跨引用与分值语义校验器；
- `ValidationIssue` 和 `SemanticValidationResult` 错误类型。

示例：

```ts
import {
  looksLikeQijDocument,
  validateQijSemantics,
  type QijDocument
} from "@qij/types";

const parsed: unknown = JSON.parse(source);

// 正式实现应先运行 qij-1.0.schema.json。
if (!looksLikeQijDocument(parsed)) {
  throw new Error("Not a QIJ 1.0 document");
}

const document: QijDocument = parsed;
const result = validateQijSemantics(document);

if (!result.valid) {
  console.error(result.errors);
}
```

类型包不替代 JSON Schema。推荐执行顺序始终是：

```text
JSON.parse -> JSON Schema -> validateQijSemantics -> Web Renderer
```

---

## 23. 设计审查结论

### 23.1 不定义顶层题型枚举

“填空题”可能填写文字、数字或公式；“大题”可能同时包含选择和开放作答。使用 Content 与 Response 组合，比维护无限增长的 `questionType` 更稳定。

### 23.2 Question 支持多个 Response

它可以覆盖多空题、结果加理由、多个评分点和行内输入，无需额外定义特殊题型。

### 23.3 AnswerKey 集中存放

这样可以整体剥离答案，简化权限控制和按题加载解法，也避免答案散落在题目节点中。

### 23.4 Solution 使用线性步骤

线性步骤易于 AI 生成、Web 播放、版本兼容和无障碍实现。复杂分支由上层 Tutor Runtime 根据 Checkpoint 结果处理，不进入 1.0 核心。

### 23.5 Widget 不包含代码

Widget 通过注册组件名和数据 Props 实现互动，并强制 fallback，兼顾安全和可移植性。

### 23.6 内容协议与运行 API 分离

QIJ 核心描述题目内容。用户身份、事件流、考试状态和自适应算法由独立系统负责，避免协议膨胀。

---

## 24. 仓库结构

```text
qij-1.0/
├── .github/workflows/ci.yml
├── README.md
├── DESIGN-REVIEW.md
├── CHANGELOG.md
├── package.json
├── package-lock.json
├── requirements-dev.txt
├── spec/
│   └── qij-1.0.md
├── schema/
│   └── qij-1.0.schema.json
├── examples/
│   ├── minimal.qij.json
│   ├── choice.qij.json
│   ├── fill-blank.qij.json
│   ├── group.qij.json
│   ├── interactive-math.qij.json
│   └── open-rubric.qij.json
├── tests/
│   ├── manifest.json
│   ├── valid/
│   └── invalid/
│       ├── schema/
│       └── semantic/
├── packages/
│   └── typescript/
└── scripts/
    ├── validate_schema.py
    └── run-semantic-tests.mjs
```

运行全部校验：

```bash
npm test
```

当前仓库不依赖第三方 Node.js 运行时库。Schema 测试脚本需要 Python `jsonschema`；TypeScript 构建需要 `tsc`。

---

## 25. 参考标准

QIJ 是独立协议，建议实现遵循以下通用标准：

- [RFC 8259 — JSON](https://www.rfc-editor.org/rfc/rfc8259)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [BCP 47 / RFC 5646 — Language Tags](https://www.rfc-editor.org/rfc/rfc5646)
- [RFC 3339 — Date and Time](https://www.rfc-editor.org/rfc/rfc3339)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [MathML Core](https://www.w3.org/TR/mathml-core/)

---

## 26. 发布前清单

- [x] 确定正式名称和缩写：Question Interchange JSON（QIJ）；
- [ ] 确定维护者和治理方式；
- [ ] 确定许可证；
- [x] 发布完整 JSON Schema；
- [x] 发布有效和无效示例集；
- [x] 实现 TypeScript 类型包；
- [x] 实现参考语义 Validator；
- [ ] 实现基础 Web Renderer；
- [ ] 完成安全评审；
- [ ] 完成可访问性评审；
- [ ] 固化 1.0 兼容政策。

---

## 27. 变更记录

### 1.0 Draft

- 正式名称确定为 Question Interchange JSON（QIJ）；
- 发布 Draft 2020-12 JSON Schema；
- 发布结构与语义有效/无效测试集；
- 发布 TypeScript 判别联合类型和语义校验器；
- 将代码块编程语言字段固定为 `codeLanguage`；
- 定义 QIJ 顶层文档；
- 定义 Question、Group、ContentBlock、Asset 和 Response；
- 定义集中式 AnswerKey；
- 定义基础评分规则；
- 定义多方法、线性步骤 Solution；
- 定义 Widget、fallback、VisualAction 和 Checkpoint；
- 定义 Web 渲染、安全、可访问性和版本兼容要求。

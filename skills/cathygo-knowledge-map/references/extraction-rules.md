# KG 抽取规则

## 什么时候创建 Node

只有当来源材料支持以下至少一类内容时，才创建 node：

- 有定义或解释的概念；
- 学习者必须执行的技能；
- 有顺序步骤的流程；
- 误区或学习障碍；
- 评测目标；
- 任务/应用情境；
- 为追踪来源所需的课程锚点或 source chunk。

不要为 “Introduction” 这类通用标题创建 node，除非标题本身就是可教学的知识点。

## 什么时候创建 Edge

优先使用明确证据：

- `requires`：“需要先掌握”、`depends on`、`foundation`、`before learning`。
- `part_of`：“包括”、“由...组成”、`contains`、`component`。
- `extends`：“进一步”、“推广”、`extension`、`advanced form`。
- `applies_to`：“用于”、“应用于”、`solve`、`model`、`explain`。
- `confuses_with`：“容易混淆”、`not the same as`、“误把”。
- `misconception_of`：“常见错误”、“错误认为”、`trap`。
- `assesses`：“检测”、“考查”、`practice checks`。
- `remediates`：“纠正”、“补救”、`repair`、`intervention`。

如果来源只说明两个概念相关，但没有说明关系类型，使用 `related_to`，设置 `review.state="needs_review"`，并解释为什么关系类型尚未确定。

## Confidence

- `0.95-1.0`：结构化字段或来源措辞中直接表达。
- `0.80-0.94`：来源明确，但做过措辞、语言或 ID 归一化。
- `0.60-0.79`：从局部上下文推断合理；运行时使用前需要 review。
- `<0.60`：保留在 candidates 中；除非明确接受，否则不要合并。

## 重复控制

创建 node 前：

1. 搜索精确 ID。
2. 搜索归一化后的名称和 aliases。
3. 在相同 subject/stage/curriculum 内搜索。
4. 如果可能重复，创建 `same_as` candidate，或修订已有 node，而不是添加新 node。

## Clean-room 边界

当来源材料可能受版权保护时，只保存来源引用和短小 review excerpt。不要提交教材页面、扫描件、复制题目或长段复制正文。

# CathyGO 学习包契约

`learning-pack.json` 是经过 review 的学习内容包，可被 CathyGO Agent、TeachAny exporter 和未来的练习/任务生成器消费。

## 顶层形状

```json
{
  "schema": "cgo.learning_pack.v1",
  "kind": "learning_pack",
  "id": "algebraic-fractions-demo",
  "title": "Algebraic Fractions Demo",
  "version": "0.1.0",
  "language": "en",
  "subject": "math",
  "stage": "middle",
  "grade_band": "grade7",
  "source_refs": [],
  "kg_refs": [],
  "objectives": [],
  "knowledge_context": {},
  "tasks": [],
  "misconceptions": [],
  "remediations": [],
  "assessment": [],
  "compat": {},
  "review": {
    "state": "draft"
  }
}
```

## 必填字段

- `schema`：必须是 `cgo.learning_pack.v1`。
- `kind`：必须是 `learning_pack`。
- `id`、`title`、`version`：稳定身份信息。
- `subject`、`stage`：学习者上下文。
- `kg_refs`：该 pack 使用的 graph node ID 或 edge ID。
- `objectives`：可衡量的学习目标。
- `tasks`：原创 clean-room 任务 prompt 或任务 spec。
- `review.state`：`draft`、`needs_review`、`accepted` 或 `rejected`。

## Objective Item

```json
{
  "id": "obj-domain-check",
  "text": "Check candidate answers against the original denominators.",
  "kg_refs": ["fraction-equation-check"],
  "level": "B"
}
```

## Task Item

```json
{
  "id": "task-precheck-001",
  "type": "pretest",
  "prompt": "Which values must be excluded before simplifying an algebraic fraction?",
  "answer_key": "Values that make the original denominator zero.",
  "kg_refs": ["denominator-not-zero"],
  "source_refs": ["fractions-source#c002"],
  "review": { "state": "accepted" }
}
```

## 兼容信息

运行时专用字段放在 `compat` 中：

```json
{
  "compat": {
    "teachany": {
      "node_id": "math-m-algebraic-fractions",
      "lesson_type": "new-concept"
    }
  }
}
```

核心 pack 必须在没有任何外部 runtime 时仍然有意义。

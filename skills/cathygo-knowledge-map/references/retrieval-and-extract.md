# 检索与抽取

KG 生产包含检索步骤，因为 agent 在创建或使用内容前需要先检查图谱。

## 搜索

```bash
python3 scripts/kg.py search --kg kg.json --query "common denominator" --limit 10
```

搜索字段：

- node `id`
- `name`
- `aliases`
- `definition`
- `summary`
- `tags`
- edge `type`、`label`、`evidence`、`reason`

搜索是词法检索，不依赖外部服务。

## 抽取

```bash
python3 scripts/kg.py extract --kg kg.json --center denominator-not-zero --depth 2 --out subgraph.json
```

默认抽取在发现邻居时把 edge 当作无向边处理，但输出时保留原始 edge 方向。

抽取出的 subgraph 可用于：

- taskware 生成；
- 一个 node family 的 review；
- 概念补救规划；
- edge type 审计；
- 小上下文模型 handoff。

## Review 查询

```bash
python3 scripts/kg.py report --kg kg.json --out kg.report.md
python3 scripts/kg.py search --kg kg.json --query "needs_review"
python3 scripts/kg.py extract --kg kg.json --center <node-id> --depth 1 --edge-type requires
```

当聚焦 subgraph 已经足够时，不要把大型完整图谱塞进 lesson-generation prompt。

# 知识图谱构建流程

当需要生产或改进 `kg.json`、`kg-candidates.json`、`subgraph.json`、`kg.report.md` 或 `kg.review.md` 时，使用这个 workflow。

## 流程

1. 明确学科范围、学习者阶段、来源列表和下游消费者。
2. 阅读 `references/kg-contract.md`，然后检查目标 `kg.json`。
3. 添加 node 前先搜索：

```bash
python3 scripts/kg.py search --kg <kg.json> --query "<concept>" --limit 10
```

4. 下游编写前先抽取聚焦上下文：

```bash
python3 scripts/kg.py extract --kg <kg.json> --center <node-id> --depth 2 --out /tmp/subgraph.json
```

5. 创建或校验 candidates，只合并已接受或高置信且有来源依据的条目。
6. 校验并生成报告：

```bash
python3 scripts/kg.py validate --kg <kg.json>
python3 scripts/kg.py report --kg <kg.json> --out <kg.report.md>
```

## 规则

- 使用 `references/kg-contract.md` 中定义的规范 edge 方向。
- 不确定的关系标记为 `related_to`，并写明 review reason，不要猜测语义 edge。
- 没有 source refs、evidence/reason、confidence 和 review state 的条目不要合并。
- 重复风险和 prerequisite cycle 都应视为 promotion blocker。

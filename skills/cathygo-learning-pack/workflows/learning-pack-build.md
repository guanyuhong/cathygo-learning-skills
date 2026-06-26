# 学习包构建流程

当需要创建或 review `content/packs/<pack-id>/` 下的内容包时，使用这个 workflow。

## 包文件

每个内容包应包含：

- `kg.json`：该包的规范图谱或聚焦图谱。
- `learning-pack.json`：学习目标、任务清单、误区图谱和 KG 引用。
- `knowledge-context.json`：TeachAny 兼容的紧凑上下文。
- `manifest.json`：元数据和兼容标记。

## 流程

1. 先创建或校验 KG。
2. 针对学习目标抽取聚焦 subgraph。
3. 按 `references/learning-pack-contract.md` 编写 `learning-pack.json`。
4. 按 `references/teachany-compat.md` 的兼容形状导出 `knowledge-context.json`。
5. 在仓库根目录运行 `python tools/cathygo.py validate`。

## 规则

- 内容包是 content artifact，不是可安装 Skill。
- 每个 objective、task、misconception 和 remediation item 应尽量引用 KG node ID 或 source ref。
- TeachAny 专用 ID 放在 `compat.teachany` 下，不要让核心 pack 依赖 TeachAny。
- 不要在公开 pack 文件中留下 `[待补充]` 这类 placeholder。

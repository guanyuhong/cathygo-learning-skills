# 更新记录

## 0.3.0

- 将仓库调整为类似 `taste-skill` 的单仓多 Skill library。
- 新增三个可选安装 Skill：`cathygo-knowledge-map`、`cathygo-learning-pack`、`cathygo-qij-question`。
- 移除 `cathygo-learning` umbrella Skill，避免 KG、learning pack 和题目构建触发边界混乱。
- 更新 marketplace、README、`skill.sh` 和仓库校验逻辑以支持按 frontmatter `name` 安装。

## 0.2.0

- 将仓库重新定位为一个内容优先的 CathyGO Learning Skill。
- 将 KG、OCR layout、题目分割和学习包生产能力集中到 `skills/cathygo-learning/`。
- 新增 `content/packs/`，作为未来学习内容的主要存放位置。
- 从公开插件入口移除旧的多 Skill marketplace 模型。

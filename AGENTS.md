# Codex 仓库规则

这个仓库是 CathyGO Learning 的内容生产 Skill library。
它采用单仓多 Skill 模式，用户可以通过 `npx skills add ... --skill "<frontmatter name>"` 按需安装。

## 文档语言

- 仓库内面向人阅读的 `.md` 文档默认使用简体中文。
- 命令、路径、schema 字段、JSON key、代码标识、包名、Skill name 保持英文原文。
- 面向外部工具的机器可读文件按工具要求书写，不强制翻译。
- 引用英文协议或第三方概念时，可以保留英文术语，但说明文字优先中文。

## 定位

- 只维护三个公开 Skill：
  - `skills/cathygo-knowledge-map`
  - `skills/cathygo-learning-pack`
  - `skills/cathygo-qij-question`
- 不保留 `cathygo-learning` umbrella Skill；README 承担导航职责。
- 普通课程、章节、知识点内容不要新增成独立可安装 Skill。
- 新知识点、章节、课程优先添加到 `content/packs/<pack-id>/`。
- CathyGO Agent 运行时代码属于 `cathygo-agent`，不要放在这里。

## Skill 边界

- `cathygo-knowledge-map`：只做 KG 构建、校验、review、merge、检索和子图导出。
- `cathygo-learning-pack`：只做 learning pack、knowledge-context、manifest 和 TeachAny compatibility。
- `cathygo-qij-question`：只做 OCR 入库、problem-set、QIJ 题目 artifact 和题目包预处理。
- 内容包不是 Skill；内容包由上述 Skill 读取、校验、转换。

## Clean-room 内容规则

- 所有公开内容必须 clean-room authored。
- 不要提交教材 PDF。
- 不要提交教材截图、扫描件、页面截取或页面布局复刻。
- 不要提交复制来的教材正文、教材例题、答案、答案解析或出版社图片。
- 通用事实可以使用，例如 “分母不能为 0”；但解释、例题、评测、故事和视觉场景必须原创。

## Skill 结构

- 每个 Skill 目录必须包含 `SKILL.md`，frontmatter 只使用 `name` 和 `description`。
- `name` 必须与目录名一致。
- 详细契约放在 `references/` 和 `schemas/`。
- 可重复执行、需要稳定性的逻辑放在 `scripts/`。
- 示例必须是合成的 clean-room 内容。
- 不要求内容包包含 `evals/`；内容包是数据 artifact，不是 Skill。

## 脚本

- `skills/*/scripts/` 里的脚本默认使用 Python。
- 优先做薄 CLI，复用 `/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core` 里的共享纯逻辑。
- 当共享包没有安装时，使用 `BEANX_LEARNING_CORE_PATH`：

```bash
export BEANX_LEARNING_CORE_PATH=/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core/src
```

- 不要重新引入旧的 `.mjs` OCR/题目分割工具链，除非仓库方向被明确改变。
- provider API 调用和托管 runtime 集成尽量放在这个仓库之外；这里负责转换、校验和打包内容 artifact。

## 验证

修改 Skill 内容、内容包、marketplace 元数据或校验代码后，运行：

```bash
python tools/cathygo.py validate
```

脚本级改动还要运行对应的聚焦命令，例如：

```bash
python skills/cathygo-knowledge-map/scripts/kg.py validate --kg content/packs/algebraic-fractions-demo/kg.json
python skills/cathygo-learning-pack/scripts/pack.py validate --pack content/packs/algebraic-fractions-demo/learning-pack.json
python skills/cathygo-qij-question/scripts/problem_set.py segment --pages skills/cathygo-qij-question/examples/single-page.layout.json --mode auto --out /tmp/cathygo-problem-set.json
```

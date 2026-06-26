# CathyGO Learning Skills

CathyGO Learning Skills 是 CathyGO 的内容生产 Skill library。它采用类似 `taste-skill` 的单仓多 Skill 模式：一个仓库包含多个可选安装 Skill，用户按 `SKILL.md` frontmatter 里的 `name` 精确安装。

## 可安装 Skill

| Install name | 用途 |
| --- | --- |
| `cathygo-knowledge-map` | 基于指定参考材料构建、校验和增量维护 `cgo.kg.v1` 知识图谱。 |
| `cathygo-learning-pack` | 基于 KG 和学习目标构建 `learning-pack.json`、`knowledge-context.json` 和内容包 manifest。 |
| `cathygo-qij-question` | 构建 OCR layout、problem set、QIJ 1.0 题目包和题目侧 artifact。 |

推荐按需安装：

```bash
npx skills add https://github.com/guanyuhong/cathygo-learning-skills --skill "cathygo-knowledge-map"
npx skills add https://github.com/guanyuhong/cathygo-learning-skills --skill "cathygo-learning-pack"
npx skills add https://github.com/guanyuhong/cathygo-learning-skills --skill "cathygo-qij-question"
```

本地查看 Skill 路径：

```bash
source ./skill.sh cathygo-knowledge-map
source ./skill.sh cathygo-learning-pack
source ./skill.sh cathygo-qij-question
```

## 结构

```text
cathygo-learning-skills/
  .claude-plugin/
    marketplace.json
    plugin.json
  skills/
    cathygo-knowledge-map/
      SKILL.md
      scripts/
      workflows/
      references/
      schemas/
      examples/
    cathygo-learning-pack/
      SKILL.md
      scripts/
      workflows/
      references/
      schemas/
    cathygo-qij-question/
      SKILL.md
      scripts/
      workflows/
      references/
      schemas/
      examples/
  content/
    packs/
      algebraic-fractions-demo/
        kg.json
        learning-pack.json
        knowledge-context.json
        manifest.json
  tools/
    cathygo.py
```

## 内容包边界

`content/packs/<pack-id>/` 是内容沉淀位置，不是 Skill。内容包由三个专业 Skill 读取、校验和转换。

每个内容包当前至少包含：

- `kg.json`：`cgo.kg.v1`
- `learning-pack.json`：`cgo.learning_pack.v1`
- `knowledge-context.json`：TeachAny 兼容上下文
- `manifest.json`：内容包元数据和 compat 信息

未来题目内容优先放在内容包内部的 `questions/*.qij.json` 或 `problem-set.json`，由 `cathygo-qij-question` 维护。

## 常用命令

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

校验仓库结构和内容包：

```bash
python tools/cathygo.py list
python tools/cathygo.py validate
```

校验 KG：

```bash
python skills/cathygo-knowledge-map/scripts/kg.py validate \
  --kg content/packs/algebraic-fractions-demo/kg.json
```

校验 learning pack：

```bash
python skills/cathygo-learning-pack/scripts/pack.py validate \
  --pack content/packs/algebraic-fractions-demo/learning-pack.json
```

分割 OCR layout 示例：

```bash
python skills/cathygo-qij-question/scripts/problem_set.py segment \
  --pages skills/cathygo-qij-question/examples/single-page.layout.json \
  --mode auto \
  --out /tmp/cathygo-problem-set.json
```

从 OCR JSON 中选择题目和图形候选：

```bash
BEANX_LEARNING_CORE_PATH=/Users/guanyuhong/beanX/cathygo-agent/packages/learning-core/src \
python skills/cathygo-qij-question/scripts/ocr.py select \
  --input skills/cathygo-qij-question/examples/ocr-layout.example-output.json \
  --question 1 \
  --figure 图1 \
  --out /tmp/cathygo-ocr-selection.json
```

## Clean-room 规则

不要提交教材 PDF、扫描件、截图、复制来的教材正文、复制来的练习题、出版社图片或答案。只有在法律和授权允许时，才保留来源引用和短小 review excerpt。

# 学习素材质量标准

本文件用于评估从教材、课标、课程资料或本地材料中抽取的 KG node、edge 和学习素材线索是否值得进入 `cgo.kg.v1`。

## 好素材标准

好的学习素材通常满足至少三项：

- 名称清楚：学习者和内容作者能理解它指向什么。
- 可教学：能支撑讲解段落、实验活动、探究任务、例子、应用情境或素材卡片。
- 可定位：有学科、学段、年级、领域或章节归属。
- 可追溯：能给出 `source_refs`，关系能给出 `evidence` 或 `reason`。
- 可连接：能和已有知识点形成先修、组成、扩展、应用或过程关系。
- 可复用：后续 learning pack、课件或产品图谱可以直接引用它。

## 坏素材信号

以下内容通常不要进入主图：

- 章节导语、口号、价值表述。
- 只重复课标原句，缺少可教学边界。
- 页面装饰、图片说明、目录、页眉页脚。
- 过细的临时活动步骤，离开当前页面后不可复用。
- 没有来源定位的常识总结。
- 和已有 node 同义但没有新增边界或关系。
- 为了覆盖页面而强行拆出的短语。

## 好 Node 例子

```json
{
  "id": "sci-m-scientific-observation",
  "type": "skill",
  "name": "科学观察",
  "definition": "科学观察是有目的、有计划地获取自然现象信息，可借助感官和工具记录事实。",
  "subject": "科学",
  "stage": "初中",
  "grade_band": "七年级上",
  "tags": ["scientific-inquiry"],
  "source_refs": ["src:zj-science-7a-2024:ch01-l01#chunk-001"],
  "confidence": 0.82,
  "review": {
    "state": "needs_review",
    "reason": "来源支持该技能作为科学探究的核心方法。"
  }
}
```

为什么好：

- 名称稳定，能进入产品图谱。
- 是可训练技能，不是页面短语。
- 可以连接到“科学探究过程”。
- 定义是 clean-room 表述，保留来源。

## 坏 Node 例子

```json
{
  "id": "science-around-us",
  "type": "concept",
  "name": "科学就在我们身边",
  "definition": "科学就在我们身边。",
  "source_refs": ["src:zj-science-7a-2024:ch01-l01#chunk-001"],
  "confidence": 0.6,
  "review": {
    "state": "needs_review"
  }
}
```

为什么不好：

- 更像章节标题或导语，不是稳定知识点。
- 定义没有提供可教学边界。
- 很难形成明确先修、组成或应用关系。
- 后续课件难以直接复用。

## 好 Edge 例子

```json
{
  "id": "edge:requires:facts-and-evidence:scientific-reasoning",
  "type": "requires",
  "source": "facts-and-evidence",
  "target": "scientific-reasoning",
  "evidence": "科学推理需要基于观察和实验获得的事实证据进行分析。",
  "source_refs": ["src:zj-science-7a-2024:ch01-l01#chunk-001"],
  "confidence": 0.8,
  "review": {
    "state": "needs_review",
    "reason": "关系方向为前置知识到依赖知识。"
  }
}
```

为什么好：

- 关系类型明确。
- 方向符合 `requires` 约定。
- evidence 解释了为什么建立这条边。

## 坏 Edge 例子

```json
{
  "id": "edge:related:science:life",
  "type": "related_to",
  "source": "science",
  "target": "life",
  "reason": "科学和生活有关。",
  "source_refs": [],
  "confidence": 0.5,
  "review": {
    "state": "needs_review"
  }
}
```

为什么不好：

- 两端 node 过于宽泛。
- 关系没有教学用途。
- 缺少来源。
- 不能支持学习路径或内容生产。

## 好学习素材线索例子

```json
{
  "kind": "learning_material_hint",
  "target_node": "scientific-experiment",
  "material_type": "experiment_activity",
  "summary": "用简单实验展示观察、记录、证据和结论之间的关系。",
  "source_refs": ["src:zj-science-7a-2024:ch01-l01#chunk-002"],
  "review": {
    "state": "needs_review"
  }
}
```

为什么好：

- 可以被 learning pack 转成活动设计。
- 没有复制教材原文。
- 明确挂到目标知识点。

## 评估流程

1. 先判断是不是稳定知识点或可复用素材线索。
2. 再判断是否有来源和可教学定义。
3. 搜索已有 KG，避免同义重复。
4. 为能确定方向的关系选择强类型 edge。
5. 不能确定的内容保留在 candidate 或 review note，不进入主图。

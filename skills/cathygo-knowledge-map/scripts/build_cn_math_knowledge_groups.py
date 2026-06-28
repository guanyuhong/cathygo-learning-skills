#!/usr/bin/env python3
"""Build the reviewable CN Math 2022 knowledge-group graph."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRICULUM_ID = "cn-math-2022"
SOURCE_REF = "src:cn-math-2022"
TITLE = "义务教育数学课程标准（2022年版）知识点组图谱"

DOMAIN_META = {
    "number-algebra": {"name": "数与代数", "color": "#2563eb", "order": 1},
    "geometry": {"name": "图形与几何", "color": "#059669", "order": 2},
    "statistics-probability": {"name": "统计与概率", "color": "#d97706", "order": 3},
    "synthesis-practice": {"name": "综合与实践", "color": "#db2777", "order": 4},
}

PILOT_REFS = [
    "src:cn-math-2022#std-cn-math-2022-stage1-number-algebra-quantity-relation-content-02",
    "src:cn-math-2022#std-cn-math-2022-stage2-number-algebra-quantity-relation-content-02",
    "src:cn-math-2022#std-cn-math-2022-stage3-number-algebra-quantity-relation-content-03",
    "src:cn-math-2022#std-cn-math-2022-stage3-number-algebra-quantity-relation-content-05",
    "src:cn-math-2022#std-cn-math-2022-stage4-number-algebra-function-content-01",
    "src:cn-math-2022#std-cn-math-2022-stage4-synthesis-practice-theme-activity-academic-08",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[\s_/|:;,.()\[\]{}]+", "-", text)
    text = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", text)
    return re.sub(r"-+", "-", text).strip("-")


def group_id(domain: str, theme: str, name: str) -> str:
    return f"kg:{domain}:{slugify(theme)}:{slugify(name)}"


def group(domain: str, theme: str, name: str, points: list[str], **detail: Any) -> dict[str, Any]:
    return {
        "id": group_id(domain, theme, name),
        "type": "knowledge_group",
        "name": name,
        "subject": "mathematics",
        "stage": "general",
        "curriculum": CURRICULUM_ID,
        "domain": domain,
        "theme": theme,
        "points": points,
        "source_refs": detail.pop("source_refs", [SOURCE_REF]),
        "confidence": detail.pop("confidence", 0.82),
        "review": detail.pop("review", {"state": "accepted", "reason": "Seeded from the CN Math 2022 curriculum taxonomy."}),
        **detail,
    }


PILOT_DETAIL = {
    "summary": "用数、符号、表格、图像或式子发现和表达变化中的数量关系，是从算术问题走向函数、方程和真实问题建模的过渡性知识点组。",
    "core_understanding": "变化规律不是孤立的找规律技巧，而是把情境中的对应关系抽象成可表达、可预测、可解释的数学模型。",
    "grade_progression": [
        {"band": "1-2年级", "focus": "用数或符号表达简单情境中的变化规律。"},
        {"band": "3-4年级", "focus": "在计算、常见数量关系和实际问题中探索简单规律。"},
        {"band": "5-6年级", "focus": "用字母表示关系、性质和规律，认识成正比例的量。"},
        {"band": "7-9年级", "focus": "从变量、函数表示和函数图象角度分析变化规律，建立函数模型。"},
    ],
    "typical_tasks": [
        "从数表、图形序列或生活情境中找出变化规则并解释理由。",
        "用文字、符号、表格或式子表达两个量之间的对应关系。",
        "判断正比例、反比例或一般函数关系，并说明变量意义。",
        "把真实问题中的变化关系转化为方程、函数或统计表达。",
    ],
    "misconceptions": [
        "把规律理解为只求下一项，不能说明变量之间的对应关系。",
        "只套用公式，忽略情境中量的含义和单位。",
        "混淆正比例、反比例和一般变化关系。",
    ],
    "source_refs": PILOT_REFS,
    "confidence": 0.9,
    "review": {"state": "accepted", "reason": "Pilot group manually enriched from curriculum standard refs."},
}

GROUPS = [
    group("number-algebra", "数与运算", "数的认识与表示", ["自然数", "万以内数", "万以上数", "小数", "分数", "负数", "有理数", "实数"]),
    group("number-algebra", "数与运算", "数位与计数", ["数位", "位值", "十进制计数法", "计数单位", "科学记数法"]),
    group("number-algebra", "数与运算", "数的大小与数轴", ["相等与不等", "数的大小比较", "数轴", "相反数", "绝对值"]),
    group("number-algebra", "数与运算", "运算意义与算理", ["加法意义", "减法意义", "乘法意义", "除法意义", "四则混合运算", "运算一致性"]),
    group("number-algebra", "数与运算", "运算方法与策略", ["整数运算", "小数运算", "分数运算", "有理数运算", "估算", "近似计算"]),
    group("number-algebra", "数与运算", "运算律与性质", ["加法交换律", "加法结合律", "乘法交换律", "乘法结合律", "乘法分配律", "等式基本性质", "不等式基本性质"]),
    group("number-algebra", "数与运算", "数的整除与分解", ["倍数", "因数", "公倍数与最小公倍数", "公因数与最大公因数", "奇数与偶数", "质数与合数"]),
    group("number-algebra", "数量关系", "常见数量关系", ["总价=单价×数量", "路程=速度×时间", "工作量关系", "数量关系表达"]),
    group("number-algebra", "数量关系", "等量关系", ["等量关系", "等量代换", "等式表示数量关系"]),
    group("number-algebra", "数量关系", "比与比例", ["比", "比值", "比例", "按比例分配"]),
    group("number-algebra", "数量关系", "变化规律与建模", ["变化规律", "成正比例的量", "成反比例的量", "实际问题建模"], **PILOT_DETAIL),
    group("number-algebra", "数与式", "字母与代数式", ["字母表示数", "代数式", "代数式的值", "公式表示"]),
    group("number-algebra", "数与式", "式的运算", ["整式", "分式", "幂", "科学记数法", "式的化简"]),
    group("number-algebra", "数与式", "根式与数的扩充", ["平方根", "算术平方根", "立方根", "根式", "实数"]),
    group("number-algebra", "方程与不等式", "方程", ["方程", "方程解", "一元一次方程", "二元一次方程组", "一元二次方程", "分式方程"]),
    group("number-algebra", "方程与不等式", "不等式", ["不等式", "不等式解集", "一元一次不等式", "不等式组"]),
    group("number-algebra", "函数", "函数基础", ["常量与变量", "函数概念", "函数表示法", "函数值", "函数图象"]),
    group("number-algebra", "函数", "函数类型", ["正比例函数", "一次函数", "反比例函数", "二次函数"]),
    group("geometry", "图形的认识与测量", "几何基本概念与关系", ["点", "线", "面", "角", "线段、射线、直线", "平行与垂直", "两点间距离"]),
    group("geometry", "图形的认识与测量", "图形认识与分类", ["平面图形", "立体图形", "三角形", "四边形", "圆", "长方体、正方体、圆柱、圆锥、球", "图形分类"]),
    group("geometry", "图形的认识与测量", "图形度量与计算", ["长度单位", "面积单位", "体积单位", "角度", "周长", "面积", "体积", "表面积"]),
    group("geometry", "图形的认识与测量", "图形公式与推导", ["长方形和正方形周长", "长方形和正方形面积", "平行四边形面积", "三角形面积", "梯形面积", "圆周长", "圆面积", "长方体和正方体体积", "圆柱体积"]),
    group("geometry", "图形的认识与测量", "观察物体与视图", ["从不同方向观察物体", "主视图、左视图、俯视图", "展开图", "根据视图想象几何体"]),
    group("geometry", "图形的位置与运动", "方向、位置与路线", ["方向", "位置", "路线图", "参照点", "距离描述"]),
    group("geometry", "图形的位置与运动", "图形运动", ["平移", "旋转", "轴对称", "图形放缩", "比例尺"]),
    group("geometry", "图形的性质", "相交线与平行线", ["相交线", "平行线", "对顶角", "余角", "补角", "垂线"]),
    group("geometry", "图形的性质", "三角形与全等", ["三角形性质", "三角形内角和", "三边关系", "全等三角形", "三角形证明"]),
    group("geometry", "图形的性质", "四边形与多边形", ["四边形性质", "平行四边形", "矩形", "菱形", "正方形", "多边形内角和"]),
    group("geometry", "图形的性质", "圆的性质", ["圆", "弧", "弦", "圆心角", "圆周角", "垂径定理"]),
    group("geometry", "图形的变化", "图形变换", ["轴对称变换", "旋转变换", "平移变换", "中心对称"]),
    group("geometry", "图形的变化", "相似与投影", ["图形相似", "相似三角形", "投影", "视图", "锐角三角函数"]),
    group("geometry", "图形与坐标", "坐标与图形", ["平面直角坐标系", "坐标表示位置", "坐标与图形变换", "坐标与函数图象"]),
    group("statistics-probability", "数据分类", "分类与标准", ["分类标准", "分类方法", "分类结果表达"]),
    group("statistics-probability", "数据的收集、整理与表达", "数据收集与整理", ["数据收集", "调查", "数据整理", "统计表"]),
    group("statistics-probability", "数据的收集、整理与表达", "统计图表", ["条形统计图", "折线统计图", "扇形统计图", "频数直方图"]),
    group("statistics-probability", "数据的收集、整理与表达", "统计量", ["平均数", "中位数", "众数", "加权平均数", "百分数统计意义"]),
    group("statistics-probability", "随机现象发生的可能性", "随机现象与可能性", ["随机现象", "可能结果", "可能性大小"]),
    group("statistics-probability", "抽样与数据分析", "抽样与样本", ["抽样调查", "简单随机抽样", "样本", "总体", "样本估计总体"]),
    group("statistics-probability", "抽样与数据分析", "数据分布与离散程度", ["频数", "频率", "集中趋势", "离散程度", "方差"]),
    group("statistics-probability", "随机事件的概率", "概率", ["随机事件", "等可能结果", "列表法", "树状图", "概率计算", "频率估计概率"]),
    group("synthesis-practice", "主题活动", "生活情境活动", ["生活中的量", "方向与位置活动", "数学游戏", "度量实践", "生活问题解决"]),
    group("synthesis-practice", "项目学习", "项目学习流程", ["项目选题", "调查研究", "数据分析", "方案设计", "成果表达", "反思改进"]),
    group("synthesis-practice", "跨学科主题学习", "真实问题建模", ["真实情境数学化", "建立数学模型", "数据与实验", "跨学科应用", "合作探究", "论证表达"]),
]


def rel(edge_type: str, source: str, target: str, evidence: str, *, refs: list[str] | None = None, confidence: float = 0.84) -> dict[str, Any]:
    return {
        "type": edge_type,
        "source_name": source,
        "target_name": target,
        "evidence": evidence,
        "source_refs": refs or [SOURCE_REF],
        "confidence": confidence,
    }


RELATIONS = [
    rel("requires", "数的认识与表示", "数位与计数", "数位和计数单位依赖对数的意义与表示的理解。"),
    rel("requires", "数位与计数", "数的大小与数轴", "数的大小比较需要理解位值和计数单位。"),
    rel("requires", "数的认识与表示", "运算意义与算理", "理解运算意义需要以数的意义和表示为基础。"),
    rel("requires", "运算意义与算理", "运算方法与策略", "算法和策略建立在对运算意义与算理的理解上。"),
    rel("extends", "运算方法与策略", "运算律与性质", "从会算走向解释和概括运算结构。"),
    rel("requires", "数的认识与表示", "数的整除与分解", "倍数、因数和质合数以自然数认识为基础。"),
    rel("applies_to", "运算意义与算理", "常见数量关系", "数量关系通常用运算意义解释情境中的量。"),
    rel("requires", "常见数量关系", "等量关系", "等量关系是在具体数量关系中抽象相等关系。"),
    rel("requires", "等量关系", "方程", "方程用符号化等量关系表达未知量问题。"),
    rel("requires", "常见数量关系", "比与比例", "比与比例是数量关系的特殊结构。"),
    rel("requires", "常见数量关系", "变化规律与建模", "变化规律来自情境中数量关系的持续对应。", refs=PILOT_REFS, confidence=0.9),
    rel("extends", "变化规律与建模", "字母与代数式", "用字母表示变化规律是从具体关系到一般表达的延伸。", refs=PILOT_REFS, confidence=0.9),
    rel("requires", "字母与代数式", "式的运算", "式的运算需要理解字母和代数式的意义。"),
    rel("requires", "式的运算", "方程", "解方程需要代数式变形和等式性质。"),
    rel("extends", "方程", "不等式", "不等式是在比较关系中对方程思想的扩展。"),
    rel("related_to", "数的整除与分解", "式的运算", "分解思想会在代数式因式分解中继续出现。"),
    rel("requires", "式的运算", "根式与数的扩充", "根式学习需要代数式和数的扩充经验。"),
    rel("requires", "变化规律与建模", "函数基础", "函数基础把变化规律明确为变量之间的对应关系。", refs=PILOT_REFS, confidence=0.9),
    rel("requires", "函数基础", "函数类型", "函数类型建立在函数概念、表示法和图象理解上。"),
    rel("related_to", "比与比例", "函数类型", "正比例和反比例是比例关系向函数关系的延伸。"),
    rel("related_to", "方程", "函数基础", "方程和函数都可表达变量关系并服务实际问题建模。"),
    rel("requires", "几何基本概念与关系", "图形认识与分类", "图形分类依赖点、线、面、角等基本对象和关系。"),
    rel("requires", "图形认识与分类", "图形度量与计算", "测量和计算需要先识别图形对象及其要素。"),
    rel("requires", "图形度量与计算", "图形公式与推导", "公式推导建立在单位、周长、面积、体积等度量经验上。"),
    rel("related_to", "图形认识与分类", "观察物体与视图", "视图活动需要识别平面图形和立体图形。"),
    rel("requires", "方向、位置与路线", "图形运动", "描述图形运动需要方向、位置和路线经验。"),
    rel("requires", "图形认识与分类", "图形运动", "平移、旋转、轴对称等运动作用于已认识的图形。"),
    rel("requires", "几何基本概念与关系", "相交线与平行线", "相交线和平行线建立在线、角和位置关系上。"),
    rel("requires", "相交线与平行线", "三角形与全等", "三角形性质和证明依赖角、平行线等基础关系。"),
    rel("extends", "三角形与全等", "四边形与多边形", "多边形性质可分解到三角形和基本证明。"),
    rel("requires", "几何基本概念与关系", "圆的性质", "圆的性质需要点、线、角和距离关系。"),
    rel("requires", "图形运动", "图形变换", "图形变换是平移、旋转、轴对称等运动的系统化。"),
    rel("requires", "三角形与全等", "相似与投影", "相似和投影学习需要三角形性质与对应关系经验。"),
    rel("related_to", "坐标与图形", "函数基础", "函数图象需要用坐标表示点和变化关系。"),
    rel("related_to", "图形公式与推导", "字母与代数式", "面积、体积等公式是字母表达数量关系的重要场景。"),
    rel("requires", "分类与标准", "数据收集与整理", "数据整理需要先明确分类标准和记录方式。"),
    rel("requires", "数据收集与整理", "统计图表", "统计图表建立在数据收集、整理和统计表基础上。"),
    rel("requires", "统计图表", "统计量", "理解统计量需要能读图表并把握数据整体。"),
    rel("extends", "统计量", "数据分布与离散程度", "从集中趋势延伸到分布形态和离散程度。"),
    rel("requires", "数据收集与整理", "抽样与样本", "抽样学习需要知道如何收集和整理数据。"),
    rel("requires", "抽样与样本", "数据分布与离散程度", "用样本分析总体需要理解数据分布。"),
    rel("requires", "随机现象与可能性", "概率", "概率是对随机事件发生可能性的数量化表达。"),
    rel("related_to", "数据分布与离散程度", "概率", "频率、分布和随机事件概率共同服务数据推断。"),
    rel("extends", "生活情境活动", "项目学习流程", "项目学习把生活情境中的问题解决组织成完整流程。"),
    rel("extends", "项目学习流程", "真实问题建模", "跨学科主题学习需要从项目流程走向模型建立和解释。"),
    rel("applies_to", "常见数量关系", "生活情境活动", "生活情境活动常用数量关系解释和解决问题。"),
    rel("applies_to", "图形度量与计算", "生活情境活动", "生活中的量、面积和体积问题依赖图形度量。"),
    rel("applies_to", "数据收集与整理", "项目学习流程", "项目学习中的调查研究需要数据收集与整理。"),
    rel("applies_to", "统计图表", "项目学习流程", "成果表达常需要用统计图表呈现数据。"),
    rel("applies_to", "变化规律与建模", "真实问题建模", "真实问题建模需要识别变量关系和变化规律。", refs=PILOT_REFS, confidence=0.9),
    rel("applies_to", "函数基础", "真实问题建模", "函数模型是解释连续变化关系的重要工具。"),
    rel("applies_to", "图形变换", "真实问题建模", "空间和图形问题常需要变换思想建模。"),
    rel("applies_to", "数据分布与离散程度", "真实问题建模", "真实问题中的数据解释需要分析分布和离散程度。"),
]


def default_summary(item: dict[str, Any], domain_name: str) -> str:
    return f"{item['name']}组织{domain_name} / {item['theme']}中的核心概念、方法和表达方式，支撑后续知识点的学习和应用。"


def default_progression(item: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"band": "1-2年级", "focus": f"在直观情境中感知{item['name']}的基本对象或经验。"},
        {"band": "3-4年级", "focus": f"在具体问题中使用{item['name']}的表示、方法或规则。"},
        {"band": "5-6年级", "focus": f"逐步概括{item['name']}中的关系、性质和一般方法。"},
        {"band": "7-9年级", "focus": f"用更形式化的语言和模型理解并应用{item['name']}。"},
    ]


def enrich_group(item: dict[str, Any], order: int) -> dict[str, Any]:
    meta = DOMAIN_META[item["domain"]]
    points = item["points"]
    summary = item.get("summary") or default_summary(item, meta["name"])
    core = item.get("core_understanding") or f"理解{item['name']}时，需要把{points[0]}等核心对象与情境、表示和方法联系起来。"
    typical = item.get("typical_tasks") or [f"解释{points[0]}的意义或作用。", f"用{item['name']}解决熟悉情境中的问题。"]
    misconceptions = item.get("misconceptions") or ["只记结论，忽略适用条件。", "不能在具体情境中选择合适的表示方式。"]
    props = {
        "section_type": "knowledge_group",
        "domain_name": meta["name"],
        "theme_name": item["theme"],
        "framework_path": ["数学", meta["name"], item["theme"], item["name"]],
        "knowledge_points": points,
        "core_understanding": core,
        "grade_progression": item.get("grade_progression") or default_progression(item),
        "typical_tasks": typical,
        "misconceptions": misconceptions,
        "detail_status": "pilot_detailed" if item["name"] == "变化规律与建模" else "seeded",
        "order": order,
    }
    return {
        **item,
        "summary": summary,
        "properties": props,
    }


def build_nodes() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for domain, meta in DOMAIN_META.items():
        nodes.append(
            {
                "id": f"domain:{domain}",
                "type": "domain",
                "name": meta["name"],
                "subject": "mathematics",
                "stage": "general",
                "curriculum": CURRICULUM_ID,
                "domain": domain,
                "source_refs": [SOURCE_REF],
                "confidence": 1.0,
                "review": {"state": "accepted", "reason": "Curriculum standard learning domain."},
                "properties": {
                    "section_type": "domain",
                    "domain_name": meta["name"],
                    "framework_path": ["数学", meta["name"]],
                    "color": meta["color"],
                    "order": meta["order"] * 100,
                },
            }
        )
    for index, item in enumerate(GROUPS, 1):
        nodes.append(enrich_group(item, index))
    return nodes


def build_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups_by_name = {node["name"]: node for node in nodes if node["type"] == "knowledge_group"}
    if len(groups_by_name) != len([node for node in nodes if node["type"] == "knowledge_group"]):
        raise ValueError("knowledge group names must be unique in this seed")

    edges: list[dict[str, Any]] = []
    for node in nodes:
        if node["type"] != "knowledge_group":
            continue
        target = f"domain:{node['domain']}"
        edges.append(
            {
                "id": f"kgrel:part-of:{slugify(node['name'])}:{slugify(node['domain'])}",
                "type": "part_of",
                "source": node["id"],
                "target": target,
                "evidence": "知识点组隶属于对应数学学习领域。",
                "source_refs": [SOURCE_REF],
                "confidence": 1.0,
                "review": {"state": "accepted", "reason": "Structural taxonomy relation."},
                "properties": {"visibility": "anchor"},
            }
        )
    for item in RELATIONS:
        source = groups_by_name[item["source_name"]]
        target = groups_by_name[item["target_name"]]
        edge_type = item["type"]
        edges.append(
            {
                "id": f"kgrel:{edge_type}:{slugify(item['source_name'])}:{slugify(item['target_name'])}",
                "type": edge_type,
                "source": source["id"],
                "target": target["id"],
                "evidence": item["evidence"],
                "source_refs": item["source_refs"],
                "confidence": item["confidence"],
                "review": {"state": "accepted", "reason": "Seeded relation for group-map pilot review."},
                "properties": {"visibility": "featured"},
            }
        )
    return edges


def build_graph() -> dict[str, Any]:
    nodes = build_nodes()
    edges = build_edges(nodes)
    return {
        "schema": "cgo.knowledge_groups.v1",
        "kind": "knowledge_groups",
        "id": "cn-math-2022-knowledge-groups",
        "title": TITLE,
        "version": "0.1.0",
        "language": "zh-CN",
        "subject": "mathematics",
        "curriculum": CURRICULUM_ID,
        "generated_at": utc_now(),
        "source_policy": "clean-room structured graph; source_refs point to curriculum standard chunks or the public curriculum source",
        "nodes": nodes,
        "edges": edges,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CN Math 2022 knowledge-group seed graph")
    parser.add_argument("--out", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    graph = build_graph()
    write_json(Path(args.out), graph)
    print(json.dumps({"ok": True, "out": args.out, "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

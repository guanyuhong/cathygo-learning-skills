#!/usr/bin/env python3
"""Build a reviewable CN Math 2022 UCS-KG from local OCR page caches."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


CURRICULUM_ID = "cn-math-2022"
SOURCE_TITLE = "义务教育数学课程标准（2022年版）"
SECTION_LABELS = {
    "content_requirement": "内容要求",
    "academic_requirement": "学业要求",
    "teaching_hint": "教学提示",
}
SECTION_SLUGS = {
    "content_requirement": "content",
    "academic_requirement": "academic",
    "teaching_hint": "teaching",
}
STAGES = {
    "第一学段": {"slug": "stage1", "local": "1-2年级", "min_grade": 1, "max_grade": 2, "stage": "elementary", "order": 1},
    "第二学段": {"slug": "stage2", "local": "3-4年级", "min_grade": 3, "max_grade": 4, "stage": "elementary", "order": 2},
    "第三学段": {"slug": "stage3", "local": "5-6年级", "min_grade": 5, "max_grade": 6, "stage": "elementary", "order": 3},
    "第四学段": {"slug": "stage4", "local": "7-9年级", "min_grade": 7, "max_grade": 9, "stage": "middle", "order": 4},
}
DOMAINS = {
    "数与代数": {"slug": "number-algebra", "order": 1},
    "图形与几何": {"slug": "geometry", "order": 2},
    "统计与概率": {"slug": "statistics-probability", "order": 3},
    "综合与实践": {"slug": "synthesis-practice", "order": 4},
}
THEME_SLUGS = {
    "数与运算": "number-operation",
    "数量关系": "quantity-relation",
    "数与式": "number-expression",
    "方程与不等式": "equation-inequality",
    "函数": "function",
    "图形的认识与测量": "shape-measurement",
    "图形的位置与运动": "position-motion",
    "图形的性质": "shape-properties",
    "图形的变化": "shape-transformation",
    "图形与坐标": "shape-coordinate",
    "数据分类": "data-classification",
    "数据的收集、整理与表达": "data-collection-expression",
    "随机现象发生的可能性": "random-phenomena-possibility",
    "随机事件的概率": "random-event-probability",
    "抽样与数据分析": "sampling-data-analysis",
    "主题活动": "theme-activity",
    "项目学习": "project-learning",
    "跨学科主题学习": "interdisciplinary-theme-learning",
}
COMPETENCIES = {
    "数感": "理解数量、数的表示、数的大小、数的运算和数量关系，并能在真实情境中作出合理判断。",
    "符号意识": "理解并运用数字、运算符号、关系符号、字母和式子表达数学对象及其关系。",
    "运算能力": "理解算理和算法，能选择合适方法进行运算、估算和结果解释。",
    "推理意识": "能基于事实、规则和模式进行归纳、类比、演绎和解释。",
    "几何直观": "能借助图形、图示和空间表征理解数量关系和几何问题。",
    "空间观念": "能识别、想象和描述图形的位置、形状、大小及变化。",
    "量感": "能理解度量对象、单位和测量过程，并合理估计与表达量。",
    "数据意识": "能收集、整理、表达和解释数据，并用数据支持判断。",
    "数据观念": "能从数据角度理解随机现象、样本、统计图表和推断结果。",
    "模型意识": "能从真实情境中抽象数量关系、图形关系或数据关系并用于解决问题。",
    "模型观念": "能建立、解释、评价和应用数学模型解决较复杂的问题。",
    "应用意识": "能主动把数学知识和方法用于生活、学科和社会情境。",
    "创新意识": "能提出有意义的问题，尝试开放性探索并反思改进方案。",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_spaces(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_ocr_line(line: str) -> str:
    line = line.strip()
    if not line:
        return ""
    replacements = {
        "（": "(",
        "）": ")",
        "〈": "(",
        "〉": ")",
        "【教学提示了": "【教学提示】",
        "【教学提示了】": "【教学提示】",
        "FR": "年级",
        "4S": "年级",
        "王": "=",
        "Bil": "例",
        "Chil": "例",
        "Cl)": "(1)",
        "CL)": "(1)",
    }
    for old, new in replacements.items():
        line = line.replace(old, new)
    return compact_spaces(line)


def is_noise(line: str) -> bool:
    if not line:
        return True
    if re.fullmatch(r"\d{1,3}", line):
        return True
    if "义务教育" in line and "课程标准" in line:
        return True
    if line.startswith("四、课程内容"):
        return True
    if line in {"续表", "==="}:
        return True
    if re.fullmatch(r"[|_=\-—\s]+", line):
        return True
    return False


def stage_grade_band(stage_name: str) -> dict[str, Any]:
    info = STAGES[stage_name]
    return {
        "local": info["local"],
        "min_grade": info["min_grade"],
        "max_grade": info["max_grade"],
        "stage": info["stage"],
    }


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[\s_/|:;,.()\[\]{}]+", "-", text)
    text = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", text)
    return re.sub(r"-+", "-", text).strip("-")


def page_number(path: Path, payload: dict[str, Any]) -> int:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if isinstance(source.get("pdf_page"), int):
        return source["pdf_page"]
    match = re.search(r"page-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def read_page_lines(pages_dir: Path, start_page: int, end_page: int) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for path in sorted(pages_dir.glob("page-*.json")):
        payload = load_json(path)
        page = page_number(path, payload)
        if page < start_page or page > end_page:
            continue
        text = str(payload.get("text") or "")
        for raw_line in text.splitlines():
            line = normalize_ocr_line(raw_line)
            if not is_noise(line):
                entries.append((page, line))
    return entries


def detect_domain(line: str) -> str | None:
    for domain in DOMAINS:
        if domain in line and (line.startswith("(") or line.startswith("一") or len(line) <= 18):
            return domain
    return None


def detect_stage(line: str) -> str | None:
    for stage in STAGES:
        if stage in line:
            return stage
    return None


def detect_section(line: str) -> str | None:
    if "内容要求" in line:
        return "content_requirement"
    if "学业要求" in line:
        return "academic_requirement"
    if "教学提示" in line:
        return "teaching_hint"
    return None


def detect_theme(line: str, domain: str | None) -> str | None:
    cleaned = re.sub(r"^[0-9一二三四五六七八九十]+[.、]\s*", "", line).strip()
    cleaned = cleaned.replace(" ", "")
    if cleaned in THEME_SLUGS:
        return cleaned
    if domain == "综合与实践":
        for theme in ("主题活动", "项目学习", "跨学科主题学习"):
            if theme in cleaned:
                return theme
    return None


def context_key(stage: str, domain: str, theme: str, section: str) -> tuple[str, str, str, str]:
    return (stage, domain, theme, section)


def collect_context_lines(entries: list[tuple[int, str]]) -> dict[tuple[str, str, str, str], list[tuple[int, str]]]:
    buffers: dict[tuple[str, str, str, str], list[tuple[int, str]]] = defaultdict(list)
    stage: str | None = None
    domain: str | None = None
    theme: str | None = None
    section: str | None = None

    for page, line in entries:
        next_domain = detect_domain(line)
        if next_domain:
            domain = next_domain
            theme = None
            section = None
            continue
        next_stage = detect_stage(line)
        if next_stage:
            stage = next_stage
            theme = None
            section = None
            continue
        next_section = detect_section(line)
        if next_section:
            section = next_section
            continue
        next_theme = detect_theme(line, domain)
        if next_theme:
            theme = next_theme
            continue

        if domain == "综合与实践" and not theme:
            theme = "跨学科主题学习"
        if stage and domain and theme and section:
            buffers[context_key(stage, domain, theme, section)].append((page, line))
    return buffers


ITEM_MARKER_RE = re.compile(r"^\(?\s*([0-9]{1,2})\s*\)")


def clean_statement(text: str, *, max_chars: int = 180) -> str:
    text = compact_spaces(text)
    text = re.sub(r"^\(?\s*[0-9]{1,2}\s*\)\s*", "", text)
    text = re.sub(r"例\s*\d+", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("。;", "。").replace(";。", "。")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for punctuation in "。；;":
        pos = cut.rfind(punctuation)
        if pos >= 60:
            return cut[: pos + 1]
    return cut.rstrip("，,、") + "。"


def split_items(entries: list[tuple[int, str]], section: str) -> list[dict[str, Any]]:
    if not entries:
        return []
    items: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_pages: set[int] = set()

    def flush() -> None:
        if not current_lines:
            return
        statement = clean_statement("\n".join(current_lines), max_chars=220 if section == "teaching_hint" else 180)
        if len(statement) >= 8:
            items.append({"statement": statement, "pages": sorted(current_pages)})

    for page, line in entries:
        starts_item = bool(ITEM_MARKER_RE.match(line))
        if section != "teaching_hint" and starts_item and current_lines:
            flush()
            current_lines = []
            current_pages = set()
        current_lines.append(line)
        current_pages.add(page)
    flush()

    if items:
        return items

    text = clean_statement("\n".join(line for _, line in entries), max_chars=220)
    chunks = [text[index : index + 180] for index in range(0, len(text), 180)]
    pages = sorted({page for page, _ in entries})
    return [{"statement": chunk.rstrip("，,、") + ("。" if not chunk.endswith("。") else ""), "pages": pages} for chunk in chunks if len(chunk) >= 8]


def statement_name(statement: str, section: str, stage: str, theme: str) -> str:
    text = re.sub(r"[。；;].*$", "", statement)
    text = text.strip("，,、:： ")
    if len(text) > 26:
        text = text[:26].rstrip("，,、")
    return f"{stage} {theme} {SECTION_LABELS[section]}：{text}"


def concept_definition(statement: str, section: str) -> str:
    prefix = {
        "content_requirement": "课程内容要求：",
        "academic_requirement": "学业表现要求：",
        "teaching_hint": "教学提示：",
    }[section]
    return prefix + statement


def infer_dimensions(statement: str, section: str) -> tuple[list[str], list[str]]:
    processes: list[str] = []
    dimensions: list[str] = []
    for keyword, process in [
        ("认识", "recognize"),
        ("理解", "understand"),
        ("探索", "explore"),
        ("掌握", "master"),
        ("会", "apply"),
        ("解决", "solve"),
        ("解释", "explain"),
        ("描述", "describe"),
        ("比较", "compare"),
        ("估算", "estimate"),
        ("推理", "reason"),
    ]:
        if keyword in statement and process not in processes:
            processes.append(process)
    for keyword, dimension in [
        ("意义", "conceptual"),
        ("算法", "procedural"),
        ("方法", "procedural"),
        ("解决", "application"),
        ("情境", "application"),
        ("活动", "practice"),
        ("数据", "data"),
        ("图形", "spatial"),
    ]:
        if keyword in statement and dimension not in dimensions:
            dimensions.append(dimension)
    if section == "academic_requirement" and "evidence" not in dimensions:
        dimensions.append("evidence")
    if section == "teaching_hint" and "teaching" not in dimensions:
        dimensions.append("teaching")
    return processes or ["understand"], dimensions or ["conceptual"]


def detect_competency_refs(statement: str) -> list[str]:
    refs = []
    for name in COMPETENCIES:
        if name in statement:
            refs.append(f"math.competency.{slugify(name)}")
    return refs


def build_framework_nodes() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = [
        {
            "id": "cn-math-2022-primary",
            "type": "stage_group",
            "curriculum_id": CURRICULUM_ID,
            "name": "小学部分",
            "grade_band": {"local": "1-6年级", "min_grade": 1, "max_grade": 6, "stage": "elementary"},
            "order": 1,
        },
        {
            "id": "cn-math-2022-middle",
            "type": "stage_group",
            "curriculum_id": CURRICULUM_ID,
            "name": "初中部分",
            "grade_band": {"local": "7-9年级", "min_grade": 7, "max_grade": 9, "stage": "middle"},
            "order": 2,
        },
    ]
    for stage_name, info in STAGES.items():
        nodes.append(
            {
                "id": f"cn-math-2022-{info['slug']}",
                "type": "grade_band",
                "curriculum_id": CURRICULUM_ID,
                "parent_id": "cn-math-2022-primary" if info["stage"] == "elementary" else "cn-math-2022-middle",
                "name": stage_name,
                "native_code": info["slug"],
                "grade_band": stage_grade_band(stage_name),
                "order": info["order"],
            }
        )
    for domain_name, domain_info in DOMAINS.items():
        nodes.append(
            {
                "id": f"cn-math-2022-{domain_info['slug']}",
                "type": "domain",
                "curriculum_id": CURRICULUM_ID,
                "name": domain_name,
                "order": domain_info["order"],
            }
        )
    return nodes


def source_for_item(stage: str, domain: str, theme: str, section: str, pages: list[int]) -> dict[str, Any]:
    if pages:
        page_label = f"PDF page {pages[0]}" if len(pages) == 1 else f"PDF pages {pages[0]}-{pages[-1]}"
    else:
        page_label = "PDF page unknown"
    return {
        "title": SOURCE_TITLE,
        "section": f"四、课程内容 / {domain} / {stage} / {theme} / {SECTION_LABELS[section]}",
        "page": pages[0] if pages else 0,
        "pages": pages,
        "native_ref": page_label,
    }


def build_graph(contexts: dict[tuple[str, str, str, str], list[tuple[int, str]]]) -> dict[str, Any]:
    framework_nodes = build_framework_nodes()
    framework_ids = {node["id"] for node in framework_nodes}
    standard_items: list[dict[str, Any]] = []
    concepts: list[dict[str, Any]] = []
    learning_evidence: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    concept_ids: set[str] = set()
    standard_ids_by_topic: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    topic_concepts: dict[tuple[str, str, str], str] = {}
    domain_stage_concepts: dict[tuple[str, str], str] = {}

    def add_framework_topic(stage: str, domain: str, theme: str) -> str:
        stage_slug = STAGES[stage]["slug"]
        domain_slug = DOMAINS[domain]["slug"]
        theme_slug = THEME_SLUGS.get(theme, slugify(theme))
        topic_id = f"cn-math-2022-{stage_slug}-{domain_slug}-{theme_slug}"
        if topic_id not in framework_ids:
            framework_nodes.append(
                {
                    "id": topic_id,
                    "type": "topic",
                    "curriculum_id": CURRICULUM_ID,
                    "parent_id": f"cn-math-2022-{domain_slug}",
                    "name": theme,
                    "native_code": f"{stage_slug}-{theme_slug}",
                    "grade_band": stage_grade_band(stage),
                    "order": len(framework_nodes) + 1,
                }
            )
            framework_ids.add(topic_id)
        return topic_id

    def add_concept(concept: dict[str, Any]) -> None:
        if concept["id"] in concept_ids:
            return
        concepts.append(concept)
        concept_ids.add(concept["id"])
        learning_evidence.append(
            {
                "id": f"evidence-{concept['id']}",
                "type": "learning_evidence",
                "concept_id": concept["id"],
                "statement": f"学生能够说明、完成或应用：{concept['name']}。",
                "subject": "mathematics",
                "confidence": 0.76,
            }
        )

    for key in sorted(contexts, key=lambda item: (STAGES[item[0]]["order"], DOMAINS[item[1]]["order"], item[2], item[3])):
        stage, domain, theme, section = key
        topic_node_id = add_framework_topic(stage, domain, theme)
        items = split_items(contexts[key], section)
        stage_slug = STAGES[stage]["slug"]
        domain_slug = DOMAINS[domain]["slug"]
        theme_slug = THEME_SLUGS.get(theme, slugify(theme))
        section_slug = SECTION_SLUGS[section]
        grade_band = stage_grade_band(stage)

        for index, item in enumerate(items, 1):
            standard_id = f"std-cn-math-2022-{stage_slug}-{domain_slug}-{theme_slug}-{section_slug}-{index:02d}"
            framework_path = [stage, domain, theme, SECTION_LABELS[section]]
            processes, dimensions = infer_dimensions(item["statement"], section)
            standard_items.append(
                {
                    "id": standard_id,
                    "type": section,
                    "statement_type": section,
                    "curriculum_id": CURRICULUM_ID,
                    "native_code": f"{stage_slug}/{domain_slug}/{theme_slug}/{section_slug}/{index:02d}",
                    "subject": "mathematics",
                    "stage": STAGES[stage]["stage"],
                    "domain": domain_slug,
                    "theme": theme_slug,
                    "framework_node_ids": [f"cn-math-2022-{stage_slug}", f"cn-math-2022-{domain_slug}", topic_node_id],
                    "framework_path": framework_path,
                    "grade_band": grade_band,
                    "statement": item["statement"],
                    "statement_language": "zh-CN",
                    "cognitive_process": processes,
                    "knowledge_dimension": dimensions,
                    "source": source_for_item(stage, domain, theme, section, item["pages"]),
                    "confidence": 0.82 if section == "teaching_hint" else 0.88,
                }
            )
            standard_ids_by_topic[(stage, domain, theme)].append(standard_id)

            concept_id = f"math.cn2022.{stage_slug}.{domain_slug}.{theme_slug}.{section_slug}.{index:02d}"
            add_concept(
                {
                    "id": concept_id,
                    "type": "concept",
                    "name": statement_name(item["statement"], section, stage, theme),
                    "subject": "mathematics",
                    "definition": concept_definition(item["statement"], section),
                    "grade_band": grade_band,
                    "domain": domain_slug,
                    "concept_type": section,
                    "source_standard_ids": [standard_id],
                    "confidence": 0.82 if section == "teaching_hint" else 0.86,
                    "properties": {
                        "stage_name": stage,
                        "domain_name": domain,
                        "theme_name": theme,
                        "section_type": section,
                        "framework_path": framework_path,
                        "pdf_pages": item["pages"],
                    },
                }
            )

    for (stage, domain, theme), standard_ids in sorted(standard_ids_by_topic.items()):
        if not standard_ids:
            continue
        stage_slug = STAGES[stage]["slug"]
        domain_slug = DOMAINS[domain]["slug"]
        theme_slug = THEME_SLUGS.get(theme, slugify(theme))
        grade_band = stage_grade_band(stage)
        domain_concept_id = f"math.cn2022.{stage_slug}.{domain_slug}"
        if (stage, domain) not in domain_stage_concepts:
            add_concept(
                {
                    "id": domain_concept_id,
                    "type": "concept",
                    "name": f"{stage} {domain}",
                    "subject": "mathematics",
                    "definition": f"{stage}数学课程内容中的{domain}学习领域。",
                    "grade_band": grade_band,
                    "domain": domain_slug,
                    "concept_type": "domain_group",
                    "source_standard_ids": [standard_ids[0]],
                    "confidence": 0.84,
                    "properties": {
                        "stage_name": stage,
                        "domain_name": domain,
                        "section_type": "domain_group",
                        "framework_path": [stage, domain],
                    },
                }
            )
            domain_stage_concepts[(stage, domain)] = domain_concept_id
        topic_concept_id = f"math.cn2022.{stage_slug}.{domain_slug}.{theme_slug}"
        topic_concepts[(stage, domain, theme)] = topic_concept_id
        add_concept(
            {
                "id": topic_concept_id,
                "type": "concept",
                "name": f"{stage} {theme}",
                "subject": "mathematics",
                "definition": f"{stage}{domain}中的{theme}主题，汇集内容要求、学业要求和教学提示。",
                "grade_band": grade_band,
                "domain": domain_slug,
                "concept_type": "topic_group",
                "source_standard_ids": [standard_ids[0]],
                "confidence": 0.84,
                "properties": {
                    "stage_name": stage,
                    "domain_name": domain,
                    "theme_name": theme,
                    "section_type": "topic_group",
                    "framework_path": [stage, domain, theme],
                },
            }
        )
        relations.append(
            {
                "id": f"rel-{topic_concept_id}-part-of-{domain_concept_id}",
                "type": "part_of",
                "source_id": topic_concept_id,
                "target_id": domain_concept_id,
                "rationale": "主题隶属于同学段学习领域。",
                "confidence": 0.9,
            }
        )

    for concept in concepts:
        props = concept.get("properties") if isinstance(concept.get("properties"), dict) else {}
        if props.get("section_type") in SECTION_SLUGS:
            stage = str(props.get("stage_name") or "")
            domain = str(props.get("domain_name") or "")
            theme = str(props.get("theme_name") or "")
            topic_id = topic_concepts.get((stage, domain, theme))
            if topic_id:
                relations.append(
                    {
                        "id": f"rel-{concept['id']}-part-of-{topic_id}",
                        "type": "part_of",
                        "source_id": concept["id"],
                        "target_id": topic_id,
                        "rationale": "课标条目隶属于对应学段主题。",
                        "confidence": 0.9,
                    }
                )
            for competency_id in detect_competency_refs(str(concept.get("definition") or "")):
                relations.append(
                    {
                        "id": f"rel-{concept['id']}-supports-{competency_id}",
                        "type": "supports_competency",
                        "source_id": concept["id"],
                        "target_id": competency_id,
                        "rationale": "条目显式指向对应核心素养。",
                        "confidence": 0.78,
                    }
                )

    for domain in DOMAINS:
        for left, right in zip(("第一学段", "第二学段", "第三学段"), ("第二学段", "第三学段", "第四学段")):
            source = domain_stage_concepts.get((left, domain))
            target = domain_stage_concepts.get((right, domain))
            if source and target:
                relations.append(
                    {
                        "id": f"rel-{source}-extends-{target}",
                        "type": "progresses_to",
                        "source_id": source,
                        "target_id": target,
                        "rationale": "同一学习领域按学段递进。",
                        "confidence": 0.86,
                    }
                )
    for domain_theme in sorted({(domain, theme) for _, domain, theme in topic_concepts}):
        domain, theme = domain_theme
        for left, right in zip(("第一学段", "第二学段", "第三学段"), ("第二学段", "第三学段", "第四学段")):
            source = topic_concepts.get((left, domain, theme))
            target = topic_concepts.get((right, domain, theme))
            if source and target:
                relations.append(
                    {
                        "id": f"rel-{source}-extends-{target}",
                        "type": "progresses_to",
                        "source_id": source,
                        "target_id": target,
                        "rationale": "同一主题按学段递进。",
                        "confidence": 0.86,
                    }
                )

    competencies = [
        {
            "id": f"math.competency.{slugify(name)}",
            "type": "competency",
            "name": name,
            "subject": "mathematics",
            "description": description,
            "grade_band": {"local": "1-9年级", "min_grade": 1, "max_grade": 9, "stage": "general"},
            "confidence": 0.8,
        }
        for name, description in COMPETENCIES.items()
    ]

    return {
        "schema_version": "ucs-kg-v0.1",
        "dataset_id": CURRICULUM_ID,
        "metadata": {
            "title": SOURCE_TITLE,
            "language": "zh-CN",
            "license": "public curriculum standard",
            "status": "expanded-from-local-ocr-cache",
            "created_at": str(date.today()),
            "source_pdf": "W020220420582346895190.pdf",
            "copyright_boundary": "clean-room structured graph; OCR/page caches remain in tmp/textbook-cache and are not committed",
            "builder": "skills/cathygo-knowledge-map/scripts/build_cn_math_2022.py",
        },
        "curricula": [
            {
                "id": CURRICULUM_ID,
                "type": "curriculum",
                "name": SOURCE_TITLE,
                "country": "CN",
                "jurisdiction": "national",
                "publisher": "中华人民共和国教育部",
                "subject": "mathematics",
                "language": "zh-CN",
                "version": "2022",
                "education_levels": ["primary", "middle"],
                "grade_range": [1, 9],
                "source": {"type": "pdf", "title": SOURCE_TITLE, "page_count": 189},
            }
        ],
        "framework_nodes": framework_nodes,
        "standard_items": standard_items,
        "concepts": sorted(concepts, key=lambda item: item["id"]),
        "competencies": competencies,
        "learning_evidence": sorted(learning_evidence, key=lambda item: item["id"]),
        "activities": [],
        "assessments": [],
        "relations": sorted(relations, key=lambda item: item["id"]),
        "alignments": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build CN Math 2022 UCS-KG from local OCR caches")
    parser.add_argument("--pages-dir", required=True, help="Directory containing page-*.json OCR caches")
    parser.add_argument("--out", required=True, help="Output UCS-KG JSON")
    parser.add_argument("--start-page", type=int, default=23)
    parser.add_argument("--end-page", type=int, default=130)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    entries = read_page_lines(Path(args.pages_dir), args.start_page, args.end_page)
    contexts = collect_context_lines(entries)
    graph = build_graph(contexts)
    write_json(Path(args.out), graph)
    print(
        json.dumps(
            {
                "ok": True,
                "out": args.out,
                "contexts": len(contexts),
                "standard_items": len(graph["standard_items"]),
                "concepts": len(graph["concepts"]),
                "relations": len(graph["relations"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

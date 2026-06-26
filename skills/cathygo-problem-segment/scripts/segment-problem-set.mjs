#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SECTION_PATTERN = /^[一二三四五六七八九十百千]+[、．.]\s*.+题/u;
const PROBLEM_START_PATTERN = /^\s*(\d+)\s*[.、．)]\s*/u;
const SUB_QUESTION_PATTERN = /^\s*[（(]\s*\d+\s*[）)]\s*/u;

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

export async function segmentProblemSet(layoutPaths, options = {}) {
  const pages = await loadPages(layoutPaths);
  const mode = normalizeMode(options.mode, pages.length);
  const effectiveMode = mode === "auto" ? "paper" : mode;
  const problems = buildProblems(pages, effectiveMode);
  const resolvedMode = mode === "auto" ? inferAutoMode(problems, pages.length) : mode;

  return {
    skill: "cathygo.problem_set",
    version: "0.1",
    status: "ok",
    mode: resolvedMode,
    pages: pages.map((page) => ({
      pageIndex: page.pageIndex,
      imageId: page.imageId,
      width: page.width,
      height: page.height,
      mimeType: page.mimeType,
      ...(page.sourcePath ? { sourcePath: page.sourcePath } : {})
    })),
    problems,
    diagnostics: {
      inputPageCount: pages.length,
      effectiveMode,
      problemCount: problems.length,
      crossPageProblemCount: problems.filter((problem) => problem.pageSpan.length > 1).length
    }
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }
  if (!args.pages.length) {
    throw new Error("Missing required --pages paths. Run with --help for usage.");
  }

  const output = await segmentProblemSet(args.pages, { mode: args.mode });
  const json = `${JSON.stringify(output, null, 2)}\n`;
  if (args.out) {
    const outPath = path.resolve(args.out);
    await fs.mkdir(path.dirname(outPath), { recursive: true });
    await fs.writeFile(outPath, json, "utf8");
    console.error(`Wrote ${outPath}`);
  } else {
    process.stdout.write(json);
  }

  console.error(
    [
      "Problem set segmentation complete",
      `  mode: ${output.mode}`,
      `  pages: ${output.pages.length}`,
      `  problems: ${output.problems.length}`
    ].join("\n")
  );
}

async function loadPages(layoutPaths) {
  const pages = [];
  for (const [pageIndex, layoutPath] of layoutPaths.entries()) {
    const sourcePath = path.resolve(layoutPath);
    const layout = JSON.parse(await fs.readFile(sourcePath, "utf8"));
    if (layout.skill !== "cathygo.ocr_layout") {
      throw new Error(`${layoutPath} is not a cathygo.ocr_layout document.`);
    }

    const sourceImage = layout.sourceImage ?? {};
    const imageId = sourceImage.imageId ?? `page_${pageIndex}`;
    const elements = (layout.elements ?? []).map((element) => ({
      ...element,
      pageIndex,
      globalId: `${pageIndex}:${element.id}`
    }));

    pages.push({
      pageIndex,
      imageId,
      width: positiveNumber(sourceImage.width, 1),
      height: positiveNumber(sourceImage.height, 1),
      mimeType: sourceImage.mimeType ?? "image/png",
      sourcePath,
      text: layout.text ?? { markdown: "", plain: "" },
      elements: elements.sort(readingOrderSort)
    });
  }
  return pages;
}

function buildProblems(pages, mode) {
  const flatElements = pages.flatMap((page) => page.elements);
  if (!flatElements.length) {
    return [];
  }

  if (mode === "single" || mode === "stitch") {
    return [createProblemFromElements(flatElements, pages, {
      id: "problem_1",
      number: mode === "single" ? "1" : null,
      section: null,
      type: "unknown"
    })];
  }

  const problems = [];
  let currentSection = null;
  let currentProblem = null;
  let problemCounter = 0;

  for (const element of flatElements) {
    const content = String(element.content ?? "").trim();
    if (!content && element.type !== "image") {
      continue;
    }

    if (content && isSectionHeader(content)) {
      currentSection = content;
      if (currentProblem) {
        problems.push(finalizeProblem(currentProblem, pages));
        currentProblem = null;
      }
      continue;
    }

    const problemNumber = content ? parseProblemNumber(content) : null;
    const startsNewProblem = Boolean(problemNumber) && !isSubQuestion(content);

    if (startsNewProblem) {
      if (currentProblem) {
        problems.push(finalizeProblem(currentProblem, pages));
      }
      problemCounter += 1;
      currentProblem = {
        id: `problem_${problemCounter}`,
        number: problemNumber,
        section: currentSection,
        type: inferProblemType(currentSection),
        elements: [element]
      };
      continue;
    }

    if (!currentProblem) {
      problemCounter += 1;
      currentProblem = {
        id: `problem_${problemCounter}`,
        number: null,
        section: currentSection,
        type: inferProblemType(currentSection),
        elements: []
      };
    }
    currentProblem.elements.push(element);
  }

  if (currentProblem) {
    problems.push(finalizeProblem(currentProblem, pages));
  }

  return problems.map((problem) => {
    const { _imageCount, ...cleaned } = problem;
    return cleaned;
  });
}

function createProblemFromElements(elements, pages, meta) {
  const draft = {
    id: meta.id,
    number: meta.number,
    section: meta.section,
    type: meta.type,
    elements
  };
  return finalizeProblem(draft, pages);
}

function finalizeProblem(draft, pages) {
  const pageSpan = [...new Set(draft.elements.map((element) => element.pageIndex))].sort((a, b) => a - b);
  const textParts = draft.elements
    .filter((element) => element.type !== "image")
    .map((element) => String(element.content ?? "").trim())
    .filter(Boolean);

  const screenshotCandidates = buildProblemScreenshotCandidates(draft.elements, pages);

  return {
    id: draft.id,
    number: draft.number,
    section: draft.section,
    type: draft.type,
    pageSpan,
    textMarkdown: textParts.join("\n\n"),
    textPlain: textParts.join("\n"),
    elementRefs: draft.elements.map((element) => ({
      pageIndex: element.pageIndex,
      elementId: element.id
    })),
    screenshotCandidates,
    continuedFrom: null,
    continuesTo: null
  };
}

function buildProblemScreenshotCandidates(elements, pages) {
  const candidates = [];
  const pageMap = new Map(pages.map((page) => [page.pageIndex, page]));
  const elementsByPage = new Map();

  for (const element of elements) {
    if (!elementsByPage.has(element.pageIndex)) {
      elementsByPage.set(element.pageIndex, []);
    }
    elementsByPage.get(element.pageIndex).push(element);
  }

  for (const [pageIndex, pageElements] of elementsByPage.entries()) {
    const page = pageMap.get(pageIndex);
    const union = unionBboxes(pageElements.map((element) => element.bbox));
    if (!union || !page) continue;
    candidates.push({
      id: `problem_page_${pageIndex}`,
      role: "problem_crop",
      title: `题目 P${pageIndex + 1}`,
      source: {
        imageId: page.imageId,
        pageIndex,
        bbox: union
      },
      provenance: {
        kind: "problem_page_union",
        elementIds: pageElements.map((element) => element.id)
      }
    });
  }

  const imageElements = elements.filter((element) => element.type === "image");
  imageElements.forEach((element, index) => {
    const page = pageMap.get(element.pageIndex);
    if (!page || !element.bbox) return;
    candidates.push({
      id: `diagram_${index + 1}`,
      role: "diagram_crop",
      title: `图 ${index + 1}`,
      source: {
        imageId: page.imageId,
        pageIndex: element.pageIndex,
        bbox: element.bbox
      },
      provenance: {
        kind: "image_element",
        elementId: element.id
      }
    });
  });

  return candidates;
}

function inferAutoMode(problems, pageCount) {
  if (pageCount <= 1 && problems.length <= 1) return "single";
  if (problems.length <= 1 && pageCount > 1) return "stitch";
  return "paper";
}

function normalizeMode(mode, pageCount) {
  const normalized = String(mode ?? "auto").toLowerCase();
  if (["single", "stitch", "paper", "auto"].includes(normalized)) {
    return normalized;
  }
  if (pageCount <= 1) return "single";
  return "auto";
}

function isSectionHeader(content) {
  return SECTION_PATTERN.test(content.trim());
}

function parseProblemNumber(content) {
  const match = content.trim().match(PROBLEM_START_PATTERN);
  return match ? match[1] : null;
}

function isSubQuestion(content) {
  return SUB_QUESTION_PATTERN.test(content.trim());
}

function inferProblemType(section) {
  const text = String(section ?? "");
  if (/选择/u.test(text)) return "choice";
  if (/填空/u.test(text)) return "fill";
  if (/解答|计算|证明|应用/u.test(text)) return "solve";
  return "unknown";
}

function readingOrderSort(a, b) {
  const pageDelta = (a.pageIndex ?? 0) - (b.pageIndex ?? 0);
  if (pageDelta) return pageDelta;
  const yDelta = (a.bbox?.y ?? 0) - (b.bbox?.y ?? 0);
  if (Math.abs(yDelta) > 0.035) return yDelta;
  return (a.bbox?.x ?? 0) - (b.bbox?.x ?? 0);
}

function unionBboxes(bboxes) {
  const valid = (bboxes ?? []).filter(Boolean);
  if (!valid.length) return null;
  const left = Math.min(...valid.map((bbox) => bbox.x));
  const top = Math.min(...valid.map((bbox) => bbox.y));
  const right = Math.max(...valid.map((bbox) => bbox.x + bbox.width));
  const bottom = Math.max(...valid.map((bbox) => bbox.y + bbox.height));
  return {
    x: round4(clamp(left, 0, 1)),
    y: round4(clamp(top, 0, 1)),
    width: round4(clamp(right - left, 0.0001, 1)),
    height: round4(clamp(bottom - top, 0.0001, 1)),
    unit: "normalized"
  };
}

function parseArgs(argv) {
  const args = { pages: [], mode: "auto" };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = () => {
      index += 1;
      if (index >= argv.length) throw new Error(`Missing value for ${arg}.`);
      return argv[index];
    };
    if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--pages") {
      while (index + 1 < argv.length && !argv[index + 1].startsWith("--")) {
        index += 1;
        args.pages.push(argv[index]);
      }
    } else if (arg === "--mode") args.mode = next();
    else if (arg === "--out") args.out = next();
    else throw new Error(`Unknown argument: ${arg}. Run with --help for usage.`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/segment-problem-set.mjs --pages page1.ocr-layout.json [page2.json ...] [--mode auto] [--out tmp/problem-set.json]

Modes:
  single   Force one problem from all pages
  stitch   Merge all pages into one cross-page problem
  paper    Segment by section headers and numbered questions
  auto     Run paper segmentation and infer the effective scenario (default)
`);
}

function positiveNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

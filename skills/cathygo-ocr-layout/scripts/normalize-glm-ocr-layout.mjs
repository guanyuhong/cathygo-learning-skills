#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_SOURCE_IMAGE_ID = "recognition";
const DEFAULT_MIME_TYPE = "image/png";

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }
  if (!args.input) throw new Error("Missing required --input path. Run with --help for usage.");

  const inputPath = path.resolve(args.input);
  const rawProvider = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const output = normalizeGlmOcrLayout(rawProvider, {
    sourceImageId: args.imageId ?? DEFAULT_SOURCE_IMAGE_ID,
    mimeType: args.mimeType ?? DEFAULT_MIME_TYPE,
    sourceImagePath: args.sourceImage ? path.resolve(args.sourceImage) : undefined
  });

  const json = `${JSON.stringify(output, null, 2)}\n`;
  if (args.out) {
    const outPath = path.resolve(args.out);
    await fs.mkdir(path.dirname(outPath), { recursive: true });
    await fs.writeFile(outPath, json, "utf8");
    console.error(`Wrote ${outPath}`);
  } else {
    process.stdout.write(json);
  }
  printSummary(output);
}

export function normalizeGlmOcrLayout(rawProvider, options = {}) {
  const pages = normalizePages(rawProvider);
  const page = pages[0] ?? { width: 1, height: 1, pageIndex: 0 };
  const markdown = typeof rawProvider?.md_results === "string" ? rawProvider.md_results : "";
  const layoutElements = normalizeLayoutElements(rawProvider, pages, options);
  const markdownImages = parseMarkdownImageBboxes(markdown, pages, options);
  const imageElements = mergeImageElements(layoutElements, markdownImages);
  const screenshotCandidates = buildScreenshotCandidates(layoutElements, imageElements, options);

  return {
    skill: "cathygo.ocr_layout",
    version: "0.1",
    status: "ok",
    provider: {
      name: "zhipu",
      model: String(rawProvider?.model || "glm-ocr").toLowerCase()
    },
    sourceImage: {
      imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID,
      width: page.width,
      height: page.height,
      mimeType: options.mimeType ?? DEFAULT_MIME_TYPE,
      ...(options.sourceImagePath ? { path: options.sourceImagePath } : {})
    },
    text: {
      markdown,
      plain: markdownToPlainText(markdown)
    },
    elements: layoutElements,
    screenshotCandidates,
    diagnostics: {
      providerRequestId: rawProvider?.request_id ?? "",
      providerTaskId: rawProvider?.id ?? "",
      created: rawProvider?.created ?? null,
      usage: rawProvider?.usage ?? null,
      pages: pages.map(({ pageIndex, width, height }) => ({ pageIndex, width, height })),
      markdownImageCount: markdownImages.length,
      layoutImageCount: layoutElements.filter((element) => element.type === "image").length,
      layoutVisualization: Array.isArray(rawProvider?.layout_visualization)
        ? rawProvider.layout_visualization
        : [],
      rawProvider
    }
  };
}

function normalizePages(rawProvider) {
  const rawPages = Array.isArray(rawProvider?.data_info?.pages) ? rawProvider.data_info.pages : [];
  if (!rawPages.length) {
    const firstElement = Array.isArray(rawProvider?.layout_details?.[0])
      ? rawProvider.layout_details[0].find((element) => element?.width && element?.height)
      : null;
    return [
      {
        pageIndex: 0,
        width: positiveNumber(firstElement?.width, 1),
        height: positiveNumber(firstElement?.height, 1)
      }
    ];
  }
  return rawPages.map((page, pageIndex) => ({
    pageIndex,
    width: positiveNumber(page?.width, 1),
    height: positiveNumber(page?.height, 1)
  }));
}

function normalizeLayoutElements(rawProvider, pages, options) {
  const pageGroups = Array.isArray(rawProvider?.layout_details) ? rawProvider.layout_details : [];
  const elements = [];
  for (const [pageIndex, pageElements] of pageGroups.entries()) {
    if (!Array.isArray(pageElements)) continue;
    const page = pages[pageIndex] ?? pages[0] ?? { width: 1, height: 1, pageIndex };
    for (const raw of pageElements) {
      const bbox = normalizeProviderBbox(raw?.bbox_2d, page);
      if (!bbox) continue;
      const nativeLabel = String(raw?.native_label ?? raw?.label ?? "").trim();
      const type = normalizeElementType(raw?.label, nativeLabel);
      elements.push({
        id: `layout_${pageIndex}_${raw?.index ?? elements.length}`,
        pageIndex,
        index: Number.isFinite(Number(raw?.index)) ? Number(raw.index) : elements.length,
        type,
        label: String(raw?.label ?? type),
        nativeLabel,
        content: String(raw?.content ?? ""),
        bbox,
        source: {
          provider: "zhipu",
          model: "glm-ocr",
          field: "layout_details",
          imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID
        }
      });
    }
  }
  return elements.sort(readingOrderSort);
}

function normalizeElementType(label, nativeLabel) {
  const normalizedNative = String(nativeLabel || "").toLowerCase();
  if (normalizedNative === "figure_title") return "figure_title";
  const normalized = String(label || "").toLowerCase();
  if (["text", "formula", "table", "image"].includes(normalized)) return normalized;
  return "text";
}

function parseMarkdownImageBboxes(markdown, pages, options) {
  const matches = [];
  const pattern = /!\[[^\]]*]\(page=(\d+),bbox=\[([^\]]+)]\)/g;
  let match;
  while ((match = pattern.exec(markdown)) !== null) {
    const pageIndex = Number(match[1]);
    const values = match[2].split(",").map((part) => Number(part.trim()));
    const page = pages[pageIndex] ?? pages[0] ?? { width: 1, height: 1, pageIndex };
    const bbox = normalizeProviderBbox(values, page);
    if (!bbox) continue;
    matches.push({
      id: `markdown_image_${matches.length + 1}`,
      pageIndex,
      index: matches.length,
      type: "image",
      label: "image",
      nativeLabel: "markdown_image",
      content: match[0],
      bbox,
      source: {
        provider: "zhipu",
        model: "glm-ocr",
        field: "md_results",
        imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID
      }
    });
  }
  return matches;
}

function mergeImageElements(layoutElements, markdownImages) {
  const images = layoutElements.filter((element) => element.type === "image");
  const merged = [...images];
  for (const candidate of markdownImages) {
    if (merged.some((existing) => bboxIoU(existing.bbox, candidate.bbox) >= 0.82)) continue;
    merged.push(candidate);
  }
  return merged.sort(diagramOrderSort);
}

function buildScreenshotCandidates(layoutElements, imageElements, options) {
  const candidates = [];
  const allElementBbox = unionBboxes(layoutElements.map((element) => element.bbox));
  if (allElementBbox) {
    candidates.push({
      id: "problem",
      role: "problem_crop",
      title: "题目",
      source: {
        imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID,
        bbox: allElementBbox
      },
      provenance: {
        kind: "layout_union",
        elementIds: layoutElements.map((element) => element.id)
      }
    });
  }

  const diagramBboxes = imageElements.map((element) => element.bbox);
  const diagramAll = unionBboxes(diagramBboxes);
  if (diagramAll) {
    candidates.push({
      id: "diagram_all",
      role: "diagram_crop",
      title: "配图",
      source: {
        imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID,
        bbox: diagramAll
      },
      provenance: {
        kind: "image_union",
        elementIds: imageElements.map((element) => element.id)
      }
    });
    imageElements.forEach((element, index) => {
      candidates.push({
        id: `diagram_${index + 1}`,
        role: "diagram_crop",
        title: `图 ${index + 1}`,
        source: {
          imageId: options.sourceImageId ?? DEFAULT_SOURCE_IMAGE_ID,
          bbox: element.bbox
        },
        provenance: {
          kind: "image_element",
          elementId: element.id
        }
      });
    });
  }
  return candidates;
}

function normalizeProviderBbox(value, page) {
  if (!Array.isArray(value) || value.length < 4) return null;
  const coords = value.slice(0, 4).map(Number);
  if (coords.some((coord) => !Number.isFinite(coord))) return null;
  const [rawX1, rawY1, rawX2, rawY2] = coords;
  const pixelLike = coords.some((coord) => Math.abs(coord) > 1);
  const divisorX = pixelLike ? page.width : 1;
  const divisorY = pixelLike ? page.height : 1;
  const x1 = clamp(Math.min(rawX1, rawX2) / divisorX, 0, 1);
  const y1 = clamp(Math.min(rawY1, rawY2) / divisorY, 0, 1);
  const x2 = clamp(Math.max(rawX1, rawX2) / divisorX, 0, 1);
  const y2 = clamp(Math.max(rawY1, rawY2) / divisorY, 0, 1);
  const width = clamp(x2 - x1, 0, 1);
  const height = clamp(y2 - y1, 0, 1);
  if (width <= 0 || height <= 0) return null;
  return {
    x: round4(x1),
    y: round4(y1),
    width: round4(width),
    height: round4(height),
    unit: "normalized"
  };
}

function unionBboxes(bboxes) {
  const valid = bboxes.filter(Boolean);
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

function bboxIoU(a, b) {
  const left = Math.max(a.x, b.x);
  const top = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  const intersection = Math.max(0, right - left) * Math.max(0, bottom - top);
  const areaA = a.width * a.height;
  const areaB = b.width * b.height;
  const union = areaA + areaB - intersection;
  return union > 0 ? intersection / union : 0;
}

function markdownToPlainText(markdown) {
  return String(markdown || "")
    .replace(/!\[[^\]]*]\(page=\d+,bbox=\[[^\]]+]\)/g, "")
    .replace(/<img\b[^>]*>/gi, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function readingOrderSort(a, b) {
  const pageDelta = (a.pageIndex ?? 0) - (b.pageIndex ?? 0);
  if (pageDelta) return pageDelta;
  const yDelta = a.bbox.y - b.bbox.y;
  if (Math.abs(yDelta) > 0.035) return yDelta;
  return a.bbox.x - b.bbox.x;
}

function diagramOrderSort(a, b) {
  const pageDelta = (a.pageIndex ?? 0) - (b.pageIndex ?? 0);
  if (pageDelta) return pageDelta;
  const centerYA = a.bbox.y + a.bbox.height / 2;
  const centerYB = b.bbox.y + b.bbox.height / 2;
  const sameVisualRow = Math.abs(centerYA - centerYB) <= 0.18;
  if (sameVisualRow) return a.bbox.x - b.bbox.x;
  return centerYA - centerYB || a.bbox.x - b.bbox.x;
}

function printSummary(output) {
  const counts = new Map();
  for (const element of output.elements) {
    counts.set(element.type, (counts.get(element.type) ?? 0) + 1);
  }
  const countText = [...counts.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([type, count]) => `${type}:${count}`)
    .join(", ");
  console.error(
    [
      "OCR Layout summary",
      `  source: ${output.sourceImage.width}x${output.sourceImage.height}`,
      `  markdown_chars: ${output.text.markdown.length}`,
      `  elements: ${output.elements.length}${countText ? ` (${countText})` : ""}`,
      `  screenshotCandidates: ${output.screenshotCandidates.map((item) => item.id).join(", ") || "(none)"}`
    ].join("\n")
  );
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = () => {
      index += 1;
      if (index >= argv.length) throw new Error(`Missing value for ${arg}.`);
      return argv[index];
    };
    if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--input") args.input = next();
    else if (arg === "--out") args.out = next();
    else if (arg === "--image-id") args.imageId = next();
    else if (arg === "--mime-type") args.mimeType = next();
    else if (arg === "--source-image") args.sourceImage = next();
    else throw new Error(`Unknown argument: ${arg}. Run with --help for usage.`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/normalize-glm-ocr-layout.mjs --input raw-glm-ocr.json [--out tmp/problem.ocr-layout.json]

Options:
  --input PATH        Required raw GLM-OCR layout_parsing JSON.
  --out PATH          Optional normalized OCR Layout JSON output path. Defaults to stdout.
  --image-id ID       Defaults to recognition.
  --mime-type TYPE    Defaults to image/png.
  --source-image PATH Optional local source image path for diagnostics.
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

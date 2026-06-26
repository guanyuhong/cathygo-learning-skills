#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.error("Usage: node ocr-layout-to-html.mjs --input layout.json [--out page.html] [--image path.jpg]");
    process.exit(1);
  }

  const layout = JSON.parse(await fs.readFile(path.resolve(args.input), "utf8"));
  const outPath = path.resolve(args.out ?? args.input.replace(/\.ocr-layout\.json$/, ".layout.html"));
  const imagePath = args.image ?? layout.sourceImage?.path;
  const imageSrc = imagePath ? await resolvePreviewImage(imagePath, outPath) : "";
  const html = renderLayoutOverlay(layout, imageSrc);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, html, "utf8");
  console.error(`Wrote ${outPath}`);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--input") args.input = argv[++i];
    else if (token === "--out") args.out = argv[++i];
    else if (token === "--image") args.image = argv[++i];
  }
  return args;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function isNoise(content) {
  const text = String(content ?? "").trim();
  return !text || text === "```markdown" || text === "```" || text.startsWith("```markdown");
}

async function resolvePreviewImage(imagePath, outPath) {
  const resolvedImage = path.resolve(imagePath);
  const outDir = path.dirname(outPath);
  const outBase = path.basename(outPath, path.extname(outPath));
  const ext = path.extname(resolvedImage) || ".png";
  const previewName = `${outBase}.source${ext}`;
  const previewPath = path.join(outDir, previewName);

  await fs.mkdir(outDir, { recursive: true });
  await fs.copyFile(resolvedImage, previewPath);
  return previewName;
}

function renderLayoutOverlay(layout, imageSrc) {
  const { width, height } = layout.sourceImage ?? { width: 4032, height: 3024 };
  const aspect = `${width} / ${height}`;
  const elements = [...(layout.elements ?? [])].sort((a, b) => (a.index ?? 0) - (b.index ?? 0));

  const blocks = elements
    .map((el) => renderElementBlock(el))
    .filter(Boolean)
    .join("\n");

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OCR Layout Overlay</title>
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 24px;
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      background: #f3f4f6;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 18px;
    }
    .note {
      margin: 0 0 16px;
      color: #6b7280;
      font-size: 13px;
      line-height: 1.6;
    }
    .stage {
      position: relative;
      width: min(100%, 1100px);
      margin: 0 auto;
      aspect-ratio: ${aspect};
      background: #fff;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
      overflow: hidden;
    }
    .bg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
      opacity: 0.55;
    }
    .block {
      position: absolute;
      overflow: hidden;
      padding: 2px;
      font-size: 10px;
      line-height: 1.35;
      color: #111827;
      background: rgba(255, 251, 235, 0.82);
      border: 1px solid rgba(245, 158, 11, 0.55);
      border-radius: 2px;
    }
    .block-image {
      background: rgba(219, 234, 254, 0.45);
      border: 2px dashed rgba(37, 99, 235, 0.75);
      color: #1d4ed8;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 600;
    }
    .block-figure-title {
      background: rgba(243, 244, 246, 0.88);
      border: 1px solid rgba(107, 114, 128, 0.55);
      color: #374151;
      text-align: center;
      font-size: 9px;
    }
    .block:hover,
    .block-image:hover,
    .block-figure-title:hover {
      z-index: 2;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    }
  </style>
</head>
<body>
  <h1>OCR 版面叠加预览</h1>
  <p class="note">按 <code>elements[].bbox</code> 绝对定位：黄框为文字，蓝虚框为配图区域，灰框为图注。底图为本地原图副本。仅供校对版面。</p>
  <div class="stage">
    ${imageSrc ? `<img class="bg" src="${escapeHtml(imageSrc)}" alt="原图" />` : ""}
    ${blocks}
  </div>
</body>
</html>
`;
}

function renderElementBlock(element) {
  if (!element?.bbox) return "";
  const { x, y, width: w, height: h } = element.bbox;
  const style = [
    `left:${(x * 100).toFixed(3)}%`,
    `top:${(y * 100).toFixed(3)}%`,
    `width:${(w * 100).toFixed(3)}%`,
    `height:${(h * 100).toFixed(3)}%`
  ].join(";");

  if (element.type === "image") {
    const label = element.id?.includes("markdown_image") ? "markdown 配图" : "配图";
    return `<div class="block block-image" data-id="${escapeHtml(element.id)}" style="${style}">${label}</div>`;
  }

  const content = String(element.content ?? "").trim();
  if (isNoise(content)) return "";

  const className =
    element.type === "figure_title" || element.nativeLabel === "figure_title"
      ? "block block-figure-title"
      : "block";
  const vertical = h > w * 2;
  const textStyle = vertical ? ";writing-mode:vertical-rl;text-orientation:mixed" : "";
  const htmlContent = escapeHtml(stripHtml(content)).replaceAll("\n", "<br />");
  return `<div class="${className}" data-id="${escapeHtml(element.id)}" style="${style}${textStyle}">${htmlContent}</div>`;
}

function stripHtml(value) {
  return String(value || "").replace(/<[^>]+>/g, "").trim();
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

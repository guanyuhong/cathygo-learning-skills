#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { cropScreenshotsFromLayout } from "./crop-layout-assets.mjs";

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

export async function buildReasoningContext(layout, options = {}) {
  const layoutPath = options.layoutPath ? path.resolve(options.layoutPath) : undefined;
  const scope = options.scope;
  const includePage = Boolean(options.includePage);
  const embedBase64 = Boolean(options.embedBase64);
  const textMode = options.textMode ?? "plain";
  const roles = normalizeRoles(options.roles ?? "diagrams");

  const cropResult = await cropScreenshotsFromLayout(layout, {
    layoutPath,
    image: options.image,
    outDir: options.outDir,
    scope,
    roles
  });

  const attachments = [...cropResult.crops];
  const usedAttachmentIds = new Set(attachments.map((item) => item.attachment_id));

  if (includePage) {
    const pageAttachment = await cropFullPage(layout, cropResult, usedAttachmentIds);
    if (pageAttachment) attachments.unshift(pageAttachment);
  }

  if (embedBase64) {
    for (const attachment of attachments) {
      const bytes = await fs.readFile(attachment.path);
      attachment.data_base64 = bytes.toString("base64");
    }
  }

  const text = pickLayoutText(layout, textMode);
  const parts = [
    { type: "text", text },
    ...attachments.map((attachment) => ({
      type: "image",
      attachment_id: attachment.attachment_id,
      role: attachment.role
    }))
  ];

  return {
    skill: "cathygo.reasoning_context",
    version: "0.1",
    status: "ok",
    capability: attachments.length ? "photo_question" : "chat",
    source: {
      layoutPath: layoutPath ?? null,
      imagePath: cropResult.imagePath,
      scope: cropResult.scope,
      cropOutDir: cropResult.outDir
    },
    text: {
      mode: textMode,
      plain: layout.text?.plain ?? "",
      markdown: layout.text?.markdown ?? ""
    },
    parts,
    attachments: attachments.map((attachment) => ({
      attachment_id: attachment.attachment_id,
      kind: attachment.kind,
      role: attachment.role,
      mime_type: attachment.mime_type,
      path: attachment.path,
      uri: attachment.uri,
      screenshotCandidateId: attachment.screenshotCandidateId,
      title: attachment.title,
      bbox: attachment.bbox,
      ...(attachment.data_base64 ? { data_base64: attachment.data_base64 } : {})
    })),
    diagnostics: {
      attachmentCount: attachments.length,
      attachmentIds: attachments.map((attachment) => attachment.attachment_id),
      roles,
      embedBase64
    }
  };
}

async function cropFullPage(layout, cropResult, usedAttachmentIds) {
  const imagePath = cropResult.imagePath;
  const scope = cropResult.scope;
  const outDir = cropResult.outDir;
  const attachmentId = uniqueAttachmentId(scope, "page_full", usedAttachmentIds);
  const filePath = path.join(outDir, `${attachmentId}.png`);

  const sharp = (await import("sharp")).default;
  await sharp(imagePath).png().toFile(filePath);

  return {
    attachment_id: attachmentId,
    kind: "image",
    role: "page",
    mime_type: "image/png",
    path: filePath,
    uri: pathToFileURL(filePath).href,
    screenshotCandidateId: "page_full",
    title: "整页原图",
    bbox: {
      x: 0,
      y: 0,
      width: 1,
      height: 1,
      unit: "normalized"
    },
    pixels: {
      left: 0,
      top: 0,
      width: positiveNumber(layout.sourceImage?.width, 1),
      height: positiveNumber(layout.sourceImage?.height, 1)
    }
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }
  if (!args.input) {
    throw new Error("Missing required --input layout JSON path.");
  }

  const layoutPath = path.resolve(args.input);
  const layout = JSON.parse(await fs.readFile(layoutPath, "utf8"));
  const output = await buildReasoningContext(layout, {
    layoutPath,
    image: args.image,
    outDir: args.outDir,
    scope: args.scope,
    roles: args.roles,
    includePage: args.includePage,
    embedBase64: args.embedBase64,
    textMode: args.textMode
  });

  const json = `${JSON.stringify(output, null, 2)}\n`;
  const outPath = path.resolve(args.out ?? layoutPath.replace(/\.ocr-layout\.json$/u, ".reasoning-context.json"));
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, json, "utf8");
  console.error(`Wrote ${outPath}`);
  console.error(
    [
      "Reasoning context ready",
      `  capability: ${output.capability}`,
      `  parts: ${output.parts.length}`,
      `  attachments: ${output.attachments.map((item) => item.attachment_id).join(", ")}`
    ].join("\n")
  );
}

function pickLayoutText(layout, textMode) {
  if (textMode === "markdown") return layout.text?.markdown ?? "";
  return layout.text?.plain ?? layout.text?.markdown ?? "";
}

function uniqueAttachmentId(scope, candidateId, usedAttachmentIds) {
  const base = `att_${scope}_${sanitizeToken(candidateId)}`;
  let attachmentId = base;
  let suffix = 2;
  while (usedAttachmentIds.has(attachmentId)) {
    attachmentId = `${base}_${suffix}`;
    suffix += 1;
  }
  usedAttachmentIds.add(attachmentId);
  return attachmentId;
}

function sanitizeToken(value) {
  return String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9_-]+/gu, "_")
    .replace(/^_+|_+$/gu, "")
    .slice(0, 48);
}

function normalizeRoles(value) {
  if (Array.isArray(value)) return value;
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseArgs(argv) {
  const args = { textMode: "plain" };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = () => {
      index += 1;
      if (index >= argv.length) throw new Error(`Missing value for ${arg}.`);
      return argv[index];
    };
    if (arg === "--help" || arg === "-h") args.help = true;
    else if (arg === "--input") args.input = next();
    else if (arg === "--image") args.image = next();
    else if (arg === "--out-dir") args.outDir = next();
    else if (arg === "--out") args.out = next();
    else if (arg === "--scope") args.scope = next();
    else if (arg === "--roles") args.roles = next();
    else if (arg === "--text-mode") args.textMode = next();
    else if (arg === "--include-page") args.includePage = true;
    else if (arg === "--embed-base64") args.embedBase64 = true;
    else throw new Error(`Unknown argument: ${arg}. Run with --help for usage.`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/build-reasoning-context.mjs --input tmp/page.ocr-layout.json --image /path/to/source.png --out-dir tmp/crops/page --out tmp/page.reasoning-context.json

Options:
  --roles diagrams          Default: only diagram_1, diagram_2, ...
  --include-page            Also attach the full source page as att_<scope>_page_full
  --embed-base64            Include data_base64 in attachments for direct API testing
  --text-mode plain|markdown
`);
}

function positiveNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

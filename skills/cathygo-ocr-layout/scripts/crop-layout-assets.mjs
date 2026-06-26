#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import sharp from "sharp";

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

export async function cropScreenshotsFromLayout(layout, options = {}) {
  const layoutPath = options.layoutPath ? path.resolve(options.layoutPath) : undefined;
  const imagePath = path.resolve(options.image ?? layout.sourceImage?.path ?? "");
  const outDir = path.resolve(options.outDir ?? path.join(path.dirname(layoutPath ?? "."), "crops"));
  const scope = sanitizeScope(options.scope ?? inferScope(layoutPath));
  const roles = normalizeRoles(options.roles ?? "diagrams");

  if (!imagePath) {
    throw new Error("Missing source image path. Pass --image or ensure layout.sourceImage.path is set.");
  }
  if (layout.skill !== "cathygo.ocr_layout") {
    throw new Error("Input must be a cathygo.ocr_layout document.");
  }

  const candidates = selectCandidates(layout.screenshotCandidates ?? [], roles);
  if (!candidates.length) {
    throw new Error(`No screenshot candidates matched roles=${roles.join(",")}.`);
  }

  await fs.mkdir(outDir, { recursive: true });
  const metadata = await sharp(imagePath).metadata();
  const imageWidth = positiveNumber(layout.sourceImage?.width, metadata.width);
  const imageHeight = positiveNumber(layout.sourceImage?.height, metadata.height);

  const usedAttachmentIds = new Set();
  const crops = [];

  for (const candidate of candidates) {
    const attachmentId = uniqueAttachmentId(scope, candidate.id, usedAttachmentIds);
    const bbox = candidate.source?.bbox;
    if (!bbox) continue;

    const fileName = `${attachmentId}.png`;
    const filePath = path.join(outDir, fileName);
    const pixels = bboxToPixels(bbox, imageWidth, imageHeight);

    await sharp(imagePath)
      .extract(pixels)
      .png()
      .toFile(filePath);

    crops.push({
      attachment_id: attachmentId,
      kind: "image",
      role: mapCandidateRole(candidate),
      mime_type: "image/png",
      path: filePath,
      uri: pathToFileURL(filePath).href,
      screenshotCandidateId: candidate.id,
      title: candidate.title ?? candidate.id,
      bbox,
      pixels
    });
  }

  return {
    scope,
    imagePath,
    outDir,
    layoutPath,
    crops
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
  const result = await cropScreenshotsFromLayout(layout, {
    layoutPath,
    image: args.image,
    outDir: args.outDir,
    scope: args.scope,
    roles: args.roles
  });

  const manifest = {
    skill: "cathygo.crop_manifest",
    version: "0.1",
    status: "ok",
    scope: result.scope,
    layoutPath,
    imagePath: result.imagePath,
    outDir: result.outDir,
    crops: result.crops
  };

  const json = `${JSON.stringify(manifest, null, 2)}\n`;
  if (args.manifestOut) {
    const manifestPath = path.resolve(args.manifestOut);
    await fs.mkdir(path.dirname(manifestPath), { recursive: true });
    await fs.writeFile(manifestPath, json, "utf8");
    console.error(`Wrote ${manifestPath}`);
  } else {
    process.stdout.write(json);
  }

  console.error(
    [
      "Crop complete",
      `  scope: ${result.scope}`,
      `  crops: ${result.crops.length}`,
      `  outDir: ${result.outDir}`,
      `  attachments: ${result.crops.map((crop) => crop.attachment_id).join(", ")}`
    ].join("\n")
  );
}

function selectCandidates(candidates, roles) {
  const roleSet = new Set(roles);
  return candidates.filter((candidate) => {
    const id = String(candidate.id ?? "");
    const role = String(candidate.role ?? "");
    if (roleSet.has("all")) return true;
    if (roleSet.has("diagrams")) {
      return role === "diagram_crop" && /^diagram_\d+$/u.test(id);
    }
    if (roleSet.has("problem")) {
      return role === "problem_crop" && id === "problem";
    }
    if (roleSet.has("page")) {
      return id === "page_full";
    }
    return roleSet.has(role) || roleSet.has(id);
  });
}

function mapCandidateRole(candidate) {
  const id = String(candidate.id ?? "");
  if (id === "problem") return "problem_crop";
  if (id === "page_full") return "page";
  if (String(candidate.role ?? "") === "diagram_crop") return "diagram";
  return candidate.role ?? "image";
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

function inferScope(layoutPath) {
  if (!layoutPath) return "layout";
  const base = path.basename(layoutPath, path.extname(layoutPath))
    .replace(/\.ocr-layout$/u, "")
    .replace(/[^A-Za-z0-9_-]+/gu, "_")
    .replace(/^_+|_+$/gu, "");
  return base || "layout";
}

function sanitizeScope(value) {
  return sanitizeToken(value) || "layout";
}

function sanitizeToken(value) {
  return String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9_-]+/gu, "_")
    .replace(/^_+|_+$/gu, "")
    .slice(0, 48);
}

function bboxToPixels(bbox, imageWidth, imageHeight) {
  const left = clamp(Math.floor(bbox.x * imageWidth), 0, Math.max(imageWidth - 1, 0));
  const top = clamp(Math.floor(bbox.y * imageHeight), 0, Math.max(imageHeight - 1, 0));
  const right = clamp(Math.ceil((bbox.x + bbox.width) * imageWidth), left + 1, imageWidth);
  const bottom = clamp(Math.ceil((bbox.y + bbox.height) * imageHeight), top + 1, imageHeight);
  return {
    left,
    top,
    width: Math.max(right - left, 1),
    height: Math.max(bottom - top, 1)
  };
}

function normalizeRoles(value) {
  if (Array.isArray(value)) return value;
  return String(value)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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
    else if (arg === "--image") args.image = next();
    else if (arg === "--out-dir") args.outDir = next();
    else if (arg === "--scope") args.scope = next();
    else if (arg === "--roles") args.roles = next();
    else if (arg === "--manifest-out") args.manifestOut = next();
    else throw new Error(`Unknown argument: ${arg}. Run with --help for usage.`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/crop-layout-assets.mjs --input tmp/page.ocr-layout.json --image /path/to/source.png --out-dir tmp/crops/page [--roles diagrams] [--manifest-out tmp/crops/page/manifest.json]

Roles:
  diagrams   Only diagram_1, diagram_2, ... (default)
  problem    Only the problem crop
  all        Every screenshot candidate
  page       Reserved for page_full candidate when present

Attachment ids are generated as att_<scope>_<candidateId>, with numeric suffixes only if a collision occurs.
`);
}

function positiveNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

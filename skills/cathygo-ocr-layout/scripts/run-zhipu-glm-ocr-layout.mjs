#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import { normalizeGlmOcrLayout } from "./normalize-glm-ocr-layout.mjs";

const DEFAULT_MODEL = "glm-ocr";
const DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.dirname(scriptDir);

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});

async function main() {
  await loadDotenv(path.join(skillRoot, ".env"));
  await loadDotenv(path.join(process.cwd(), ".env"));

  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }
  if (!args.image) throw new Error("Missing required --image path. Run with --help for usage.");

  const apiKey = process.env.ZHIPU_API_KEY;
  if (!apiKey) {
    throw new Error("ZHIPU_API_KEY is required. Set it in the shell or a local .env file.");
  }

  const imagePath = path.resolve(args.image);
  const mimeType = inferMimeType(imagePath);
  const imageBase64 = await fs.readFile(imagePath, "base64");
  const requestId = args.requestId ?? makeRequestId(imagePath);
  const baseUrl = args.baseUrl ?? process.env.ZHIPU_OCR_BASE_URL ?? DEFAULT_BASE_URL;
  const model = args.model ?? process.env.ZHIPU_OCR_MODEL ?? DEFAULT_MODEL;

  const body = {
    model,
    file: `data:${mimeType};base64,${imageBase64}`,
    request_id: requestId
  };
  if (args.visualize) body.need_layout_visualization = true;
  if (args.cropImagesDebug) body.return_crop_images = true;
  if (args.userId) body.user_id = args.userId;

  const startedAt = Date.now();
  const rawProvider = await callZhipuLayoutParsing({ apiKey, baseUrl, body });
  const elapsedMs = Date.now() - startedAt;

  if (args.rawOut) {
    const rawOutPath = path.resolve(args.rawOut);
    await fs.mkdir(path.dirname(rawOutPath), { recursive: true });
    await fs.writeFile(rawOutPath, `${JSON.stringify(rawProvider, null, 2)}\n`, "utf8");
    console.error(`Wrote raw provider output ${rawOutPath}`);
  }

  const output = normalizeGlmOcrLayout(rawProvider, {
    sourceImageId: args.imageId ?? "recognition",
    mimeType,
    sourceImagePath: imagePath
  });
  output.diagnostics.elapsedMs = elapsedMs;
  output.diagnostics.standardCropImagesRequested = Boolean(args.cropImagesDebug);

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
      "GLM-OCR Layout run complete",
      `  image: ${imagePath}`,
      `  model: ${model}`,
      `  request_id: ${requestId}`,
      `  elapsed_ms: ${elapsedMs}`,
      `  screenshotCandidates: ${output.screenshotCandidates.map((item) => item.id).join(", ") || "(none)"}`
    ].join("\n")
  );
}

async function callZhipuLayoutParsing({ apiKey, baseUrl, body }) {
  const response = await fetch(baseUrl, {
    method: "POST",
    headers: {
      Authorization: authHeader(apiKey),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  const text = await response.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch {
    parsed = { rawText: text };
  }
  if (!response.ok) {
    throw new Error(`Zhipu GLM-OCR request failed: ${response.status} ${JSON.stringify(parsed)}`);
  }
  return parsed;
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
    else if (arg === "--image") args.image = next();
    else if (arg === "--out") args.out = next();
    else if (arg === "--raw-out") args.rawOut = next();
    else if (arg === "--model") args.model = next();
    else if (arg === "--base-url") args.baseUrl = next();
    else if (arg === "--request-id") args.requestId = next();
    else if (arg === "--user-id") args.userId = next();
    else if (arg === "--image-id") args.imageId = next();
    else if (arg === "--visualize") args.visualize = true;
    else if (arg === "--crop-images-debug") args.cropImagesDebug = true;
    else throw new Error(`Unknown argument: ${arg}. Run with --help for usage.`);
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/run-zhipu-glm-ocr-layout.mjs --image /path/to/problem.png [--out tmp/problem.ocr-layout.json]

Options:
  --image PATH          Required local image path. Supports PNG, JPG, JPEG, and PDF.
  --out PATH            Optional normalized OCR Layout JSON output path. Defaults to stdout.
  --raw-out PATH        Optional raw provider JSON output path.
  --model NAME          Defaults to ZHIPU_OCR_MODEL or ${DEFAULT_MODEL}.
  --base-url URL        Defaults to ZHIPU_OCR_BASE_URL or ${DEFAULT_BASE_URL}.
  --request-id ID       Optional 6-64 character request id. Defaults to a generated id.
  --user-id ID          Optional end-user id for abuse monitoring.
  --image-id ID         Defaults to recognition.
  --visualize           Request provider layout visualization for diagnostics.
  --crop-images-debug   Debug only: request provider crop URLs. Not for standard CathyGO assets.
`);
}

async function loadDotenv(filePath) {
  try {
    const text = await fs.readFile(filePath, "utf8");
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const match = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
      if (!match) continue;
      const [, key, rawValue] = match;
      if (process.env[key] !== undefined) continue;
      process.env[key] = rawValue.replace(/^['"]|['"]$/g, "");
    }
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}

function inferMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".pdf") return "application/pdf";
  throw new Error(`Unsupported file type: ${ext || "(none)"}. Use PNG, JPG, JPEG, or PDF.`);
}

function makeRequestId(imagePath) {
  const base = path.basename(imagePath, path.extname(imagePath))
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 20) || "image";
  return `${base}-${randomUUID()}`.slice(0, 64);
}

function authHeader(apiKey) {
  const trimmed = apiKey.trim();
  return /^Bearer\s+/i.test(trimmed) ? trimmed : `Bearer ${trimmed}`;
}

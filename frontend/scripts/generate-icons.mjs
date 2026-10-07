// Generates the PWA icon set (any + maskable) from public/favicon.svg.
// Usage: npm run icons   (requires the "sharp" dev dependency)
import sharp from "sharp";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.resolve(here, "..", "public");
const svgPath = path.join(publicDir, "favicon.svg");
const outDir = path.join(publicDir, "icons");

await mkdir(outDir, { recursive: true });

// Maskable icons need a safe zone: content within the inner 80% circle.
const maskableSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#2563eb"/>
  <circle cx="256" cy="256" r="205" fill="#2563eb"/>
  <text x="256" y="330" font-size="240" font-family="Arial" font-weight="bold" fill="#fff" text-anchor="middle">A</text>
</svg>`;

const jobs = [
  { file: "icon-192.png", size: 192, source: svgPath },
  { file: "icon-512.png", size: 512, source: svgPath },
  { file: "icon-maskable-192.png", size: 192, source: Buffer.from(maskableSvg) },
  { file: "icon-maskable-512.png", size: 512, source: Buffer.from(maskableSvg) },
];

for (const job of jobs) {
  await sharp(job.source).resize(job.size, job.size).png().toFile(path.join(outDir, job.file));
  console.log(`created ${job.file} (${job.size}x${job.size})`);
}

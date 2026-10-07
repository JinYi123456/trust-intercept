/**
 * package-source.mjs — builds TRUST//INTERCEPT_Source_Code.zip at the project root for
 * portal upload. Cross-platform (pure Node + archiver), no shell commands.
 *
 * Excluded: .venv, node_modules, .git, .cache, build artefacts (dist, .vite,
 * __pycache__, *.pyc, .pytest_cache, *.egg-info), databases (*.db, *.sqlite*),
 * uploaded media, environment secrets (.env — the committed .env.example IS
 * included), and the archive itself.
 *
 * Run from anywhere:  npm run zip   (in frontend/)  or
 *                     node frontend/scripts/package-source.mjs
 */
import { createWriteStream } from "node:fs";
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import archiver from "archiver";

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "..", ".."); // frontend/scripts -> project root
const OUT = path.join(ROOT, "TRUST//INTERCEPT_Source_Code.zip");

const EXCLUDED_DIRS = new Set([
  ".venv", "venv", "env", "node_modules", ".git", ".cache", ".pytest_cache",
  ".mypy_cache", ".ruff_cache", "__pycache__", "dist", "build", ".vite",
  ".idea", ".vscode", "android", "ios", ".gradle", ".freebuff",
]);

const EXCLUDED_FILES = new Set([
  ".env", ".DS_Store", "Thumbs.db", "TRUST//INTERCEPT_Source_Code.zip", "package-lock.json",
]);

const EXCLUDED_SUFFIXES = [
  ".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log", ".apk", ".aab",
  ".png.tmp", ".har",
];

const EXCLUDED_PREFIXES = [".env."]; // .env.local etc. — but NOT .env.example

function isExcludedDir(name) {
  return EXCLUDED_DIRS.has(name);
}

function isExcludedFile(name) {
  const lower = name.toLowerCase();
  if (EXCLUDED_FILES.has(name)) return true;
  if (name === ".env.example") return false;
  if (EXCLUDED_PREFIXES.some((prefix) => lower.startsWith(prefix))) return true;
  return EXCLUDED_SUFFIXES.some((suffix) => lower.endsWith(suffix));
}

async function walk(dir, base = dir, files = []) {
  const { readdir } = await import("node:fs/promises");
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    const rel = path.relative(base, full);
    if (entry.isDirectory()) {
      if (!isExcludedDir(entry.name)) await walk(full, base, files);
    } else if (!isExcludedFile(entry.name)) {
      files.push({ full, rel });
    }
  }
  return files;
}

await mkdir(path.dirname(OUT), { recursive: true });

const files = await walk(ROOT);
const output = createWriteStream(OUT);
const archive = archiver("zip", { zlib: { level: 9 } });

const done = new Promise((resolve, reject) => {
  output.on("close", resolve);
  archive.on("warning", (err) => {
    if (err.code !== "ENOENT") reject(err);
  });
  archive.on("error", reject);
});

archive.pipe(output);
for (const file of files) {
  archive.append(file.full, { name: path.join("trust-intercept", file.rel) });
}
await archive.finalize();
await done;

const { size } = await stat(OUT);
const kb = (size / 1024).toFixed(1);
console.log(`✔ TRUST//INTERCEPT_Source_Code.zip created at project root`);
console.log(`  ${files.length} files · ${kb} KB`);
console.log(`  Excluded: .venv, node_modules, .git, .cache, dist/__pycache__/build artefacts, *.db, .env (secrets)`);

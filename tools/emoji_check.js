#!/usr/bin/env node
// Simple emoji enforcement: scans for emoji in source files and fails when
// disallowed emoji appear in titles or keys where policies forbid them.
// Allowed in comments/strings; configurable list below.

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();
const ALLOWED_FILES = new Set([
  'README.md',
]);

// Basic regex for emoji ranges (not exhaustive but practical)
const EMOJI_REGEX = /[\u{1F300}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;

let violations = [];

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    if (e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (['node_modules', '.next', 'dist', 'build', '.git', '__pycache__'].includes(e.name)) continue;
      walk(p);
    } else {
      checkFile(p);
    }
  }
}

function checkFile(filePath) {
  const rel = path.relative(ROOT, filePath).replace(/\\/g, '/');
  const base = path.basename(rel);
  if (ALLOWED_FILES.has(base)) return;
  const text = fs.readFileSync(filePath, 'utf8');
  // Heuristic: flag emoji in JSON keys, TS/JS export const ids/names, and Markdown headings
  const lines = text.split(/\r?\n/);
  lines.forEach((line, i) => {
    const isHeading = /^\s*#{1,6}\s+/.test(line);
    const isKeyLine = /"[^"]+"\s*:/.test(line) || /export\s+const\s+[A-Za-z0-9_]+\s*=/.test(line);
    if ((isHeading || isKeyLine) && EMOJI_REGEX.test(line)) {
      violations.push(`${rel}:${i + 1}: emoji not allowed in headings or keys`);
    }
  });
}

walk(ROOT);

if (violations.length) {
  console.error('Emoji policy violations:');
  for (const v of violations) console.error(' -', v);
  process.exit(2);
} else {
  console.log('Emoji policy check passed.');
}

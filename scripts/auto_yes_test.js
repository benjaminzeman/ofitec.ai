#!/usr/bin/env node
/**
 * Lightweight test harness for auto_yes.js detection logic.
 * Run: node scripts/auto_yes_test.js
 */
import { promptRegex, looksLikePrompt } from './auto_yes.js';

const cases = [
  { text: 'Overwrite existing file? (y/n)', expect: true },
  { text: '? Proceed with installation [Y/n]', expect: true },
  { text: 'replace current config? ', expect: true },
  { text: 'Random log line without question', expect: false },
  { text: 'confirm action:', expect: true },
  { text: 'Done. No prompts here.', expect: false },
  { text: '\n? short leading question', expect: true },
];

let passed = 0;
for (const c of cases) {
  const got = looksLikePrompt(c.text);
  const ok = got === c.expect;
  if (ok) passed++;
  console.log(`${ok ? '✔' : '✘'}  expect=${c.expect} got=${got} | ${JSON.stringify(c.text)}`);
}

console.log(`\nSummary: ${passed}/${cases.length} passed`);
if (passed !== cases.length) {
  console.error('Some tests failed');
  process.exit(1);
}

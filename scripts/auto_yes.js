#!/usr/bin/env node
/**
 * Auto-answer 'y' to prompts a spawned command prints (heuristic based).
 * Usage: node scripts/auto_yes.js -- <command> [args...]
 * Example: node scripts/auto_yes.js -- npm init
 */
import { spawn } from 'node:child_process';

// Exported for testability
export const promptRegex = /(?:(?:^|\s)\?\s.*$|\[Y\/n\]|\(y\/n\)|\b(confirm|overwrite|replace|proceed|continue)\b)/i;

export function looksLikePrompt(text) {
  return promptRegex.test(text);
}

function parseArgs(argv = process.argv) {
  const idx = process.argv.indexOf('--');
  if (idx === -1 || idx === process.argv.length - 1) {
    console.error('Usage: node scripts/auto_yes.js -- <command> [args...]');
    process.exit(1);
  }
  return { cmd: process.argv[idx + 1], args: process.argv.slice(idx + 2) };
}

function run() {
  const { cmd, args } = parseArgs();
  console.log(`[auto_yes] Spawning: ${cmd} ${args.join(' ')}`);
  const child = spawn(cmd, args, { stdio: ['pipe', 'pipe', 'pipe'], env: process.env });

  const handle = (chunk, isErr = false) => {
    const text = chunk.toString();
    (isErr ? process.stderr : process.stdout).write(text);
    if (looksLikePrompt(text)) {
      child.stdin.write('y\n');
    }
  };

  child.stdout.on('data', (c) => handle(c, false));
  child.stderr.on('data', (c) => handle(c, true));
  child.on('exit', (code, signal) => {
    console.log(`[auto_yes] Child exited code=${code} signal=${signal}`);
    process.exit(code ?? 0);
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  // Executed directly
  run();
}

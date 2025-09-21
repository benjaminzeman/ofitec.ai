// sanitize.ts - minimal utility to strip/replace disallowed emoji in UI titles
// Used where policy requires headings or keys free of emoji.

// Avoid Unicode flag to keep compatibility with older JS targets; cover common ranges
// Note: This is a heuristic and may not catch all emoji, but suffices for headings
const EMOJI_REGEX = /[\u2600-\u27BF]|[\uD83C-\uDBFF][\uDC00-\uDFFF]/;

export function stripEmoji(input: string | null | undefined): string {
  if (!input) return '';
  return input.replace(EMOJI_REGEX, '').trim();
}

export function replaceEmoji(input: string | null | undefined, placeholder = ''): string {
  if (!input) return '';
  return input.replace(EMOJI_REGEX, placeholder).trim();
}

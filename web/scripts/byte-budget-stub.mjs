#!/usr/bin/env node
// Byte-budget STUB for T-016's CI job — informational only.
//
// The enforced ≤120KB gzipped first-load-JS gate on the public route ("/")
// is T-042's task (frontend-architecture.md §8 "Byte budget (AD-1/C8)";
// milestones.md). This script only parses `next build`'s own route table
// (captured to a text file by the CI step that runs it) and prints the
// figure for "/" so it is visible in every CI run from here on. It fails
// the CI step only when the table cannot be found/parsed at all (a
// build-output-format regression worth catching early) — it does not
// assert the 120KB ceiling itself.
//
// Usage: node scripts/byte-budget-stub.mjs <path-to-captured-build-output>

import { readFileSync } from "node:fs";

const inputPath = process.argv[2];
if (!inputPath) {
  console.error("byte-budget-stub: usage: node scripts/byte-budget-stub.mjs <build-output-file>");
  process.exit(1);
}

const text = readFileSync(inputPath, "utf8");
const lines = text.split(/\r?\n/);

// Next.js prints a route table with a "First Load JS" column, e.g.:
//   ┌ ○ /                                    142 B          123 kB
// Match the root route "/" specifically (slash immediately followed by
// whitespace — "/complaints" and "/login" have a non-whitespace character
// right after the slash and are not matched).
const rootRouteLine = lines.find((line) => /(^|\s)\/(?=\s)/.test(line));

if (!rootRouteLine) {
  console.error(
    "byte-budget-stub: could not find a route-table line for '/' in the captured " +
      "build output — next build's output format may have changed. Failing so this " +
      "is caught now rather than silently losing visibility ahead of T-042's real gate."
  );
  process.exit(1);
}

// The last two whitespace-separated tokens are the First Load JS column,
// e.g. "107" + "kB".
const sizeMatch = rootRouteLine.trim().match(/(\S+)\s+(kB|KB|B|MB)\s*$/);
const firstLoadJs = sizeMatch ? `${sizeMatch[1]} ${sizeMatch[2]}` : "(unparsed)";

console.log(`byte-budget-stub: route "/" first-load JS (as reported by next build): ${firstLoadJs}`);
console.log(
  "byte-budget-stub: this is a STUB — informational only. The enforced ≤120KB " +
    "gzipped ceiling on this route is added by T-042, not this task."
);
process.exit(0);

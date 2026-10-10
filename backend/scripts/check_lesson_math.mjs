#!/usr/bin/env node
// Compile-check every LaTeX expression in a lesson with KaTeX.
//
// Catches malformed maths that renders as a red error box in the browser but
// looks fine in a diff. The Markdown renderer has no rehype-raw, so raw HTML
// would be escaped; this checks the maths that *does* get rendered.
//
// Requires the frontend dependencies to be installed once:
//   cd frontend/web && npm install
//
// Usage:
//   node backend/scripts/check_lesson_math.mjs                 # all lessons
//   node backend/scripts/check_lesson_math.mjs content/01_qubits.md
//
// Exit code 1 if any expression fails to compile.

import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');

let katex;
try {
  katex = (
    await import(join(repoRoot, 'frontend/web/node_modules/katex/dist/katex.mjs'))
  ).default;
} catch {
  console.error(
    'KaTeX not found. Install the frontend dependencies first:\n' +
      '  cd frontend/web && npm install'
  );
  process.exit(2);
}

function targetsFromArgs(args) {
  if (args.length) return args.map((a) => resolve(process.cwd(), a));
  const dir = join(repoRoot, 'content');
  return readdirSync(dir)
    .filter((f) => f.endsWith('.md'))
    .sort()
    .map((f) => join(dir, f));
}

function extract(text) {
  // Strip fenced code blocks and inline code so we check prose maths, not code.
  const stripped = text.replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
  const display = [];
  const inline = [];
  // Display maths first, so $$...$$ is not mistaken for two empty inline runs.
  const rest = stripped
    .replace(/\$\$([\s\S]+?)\$\$/g, (_m, body) => {
      display.push(body);
      return '';
    })
    .replace(/\$([^$\n]+?)\$/g, (_m, body) => {
      inline.push(body);
      return '';
    });
  // A leftover lone "$" means a delimiter is unbalanced.
  const stray = (rest.match(/\$/g) || []).length;
  return { display, inline, stray };
}

const files = targetsFromArgs(process.argv.slice(2));
let failed = 0;
let total = 0;

for (const file of files) {
  let text;
  try {
    text = readFileSync(file, 'utf8');
  } catch {
    console.error(`cannot read ${file}`);
    failed += 1;
    continue;
  }

  const { display, inline, stray } = extract(text);
  const problems = [];
  let ok = 0;

  for (const [mode, list] of [
    ['display', display],
    ['inline', inline],
  ]) {
    for (const expr of list) {
      try {
        katex.renderToString(expr, {
          displayMode: mode === 'display',
          throwOnError: true,
        });
        ok += 1;
      } catch (err) {
        problems.push(`  ${mode}: ${JSON.stringify(expr.slice(0, 90))} -> ${err.message.split('\n')[0]}`);
      }
    }
  }

  total += ok;
  const label = file.replace(repoRoot + '/', '');
  if (problems.length || stray) {
    failed += 1;
    console.log(`FAIL ${label}: ${ok} compile, ${problems.length} error(s)` +
      (stray ? `, ${stray} stray $ delimiter(s)` : ''));
    problems.slice(0, 25).forEach((p) => console.log(p));
  } else {
    console.log(`ok   ${label}: ${ok} expressions (${display.length} display / ${inline.length} inline)`);
  }
}

console.log(failed ? `\n${failed} file(s) failed` : `\nall ${files.length} file(s) ok (${total} expressions)`);
process.exit(failed ? 1 : 0);

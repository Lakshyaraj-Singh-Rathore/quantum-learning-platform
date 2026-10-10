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
//   node backend/scripts/check_lesson_math.mjs --selftest       # checker tests
//
// Exit code 1 if any expression fails to compile or any delimiter is stray.

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

// Replace a matched maths run with whitespace of the SAME length, keeping every
// newline in place. That preserves character offsets and line numbers, so the
// leftover-`$` scan below can report where the stray delimiter actually is.
function blankKeepingLayout(match) {
  return match.replace(/[^\n]/g, ' ');
}

/**
 * Pull the maths out of a lesson.
 *
 * Fenced code blocks and inline code spans are removed first: a `$` in a shell
 * prompt or an f-string is a literal, not a delimiter. An escaped `\$` in prose
 * is likewise a literal dollar sign under CommonMark.
 *
 * Returns the display and inline bodies to compile, plus the file positions of
 * any `$` that survived -- those are unbalanced delimiters.
 */
function extract(text) {
  const stripped = text.replace(/```[\s\S]*?```/g, '').replace(/`[^`\n]*`/g, '');
  const display = [];
  const inline = [];
  // Display maths first, so $$...$$ is not mistaken for two empty inline runs.
  // `afterDisplay` keeps every remaining delimiter in place: it is the true
  // per-line picture, and is what the parity check below counts.
  const afterDisplay = stripped.replace(/\$\$([\s\S]+?)\$\$/g, (m, body) => {
    display.push(body);
    return blankKeepingLayout(m);
  });
  const rest = afterDisplay.replace(/\$([^$\n]+?)\$/g, (m, body) => {
    inline.push(body);
    return blankKeepingLayout(m);
  });

  // A leftover "$" means a delimiter is unbalanced. The most common cause is
  // inline maths wrapped across two physical lines, which the renderer emits
  // as literal "$...\n...$" text instead of an equation.
  const stray = [];
  for (let i = 0; i < rest.length; i += 1) {
    if (rest[i] !== '$') continue;
    if (i > 0 && stripped[i - 1] === '\\') continue; // escaped literal dollar
    const upto = rest.slice(0, i);
    const line = upto.split('\n').length;
    const col = i - (upto.lastIndexOf('\n') + 1) + 1;
    const sourceLine = (stripped.split('\n')[line - 1] || '').trim();
    stray.push({ line, col, sourceLine });
  }

  // Per-line parity. Pairing alone is not enough: a stray "$" can pair up with
  // an unrelated "$" further along and be swallowed into a bogus "expression"
  // that then compiles happily, so nothing is reported. Counting the
  // delimiters on each physical line catches that, because an inline run that
  // opens on one line and closes on the next leaves an ODD count on both.
  //
  // Display maths is blanked out above, so its delimiters are not counted.
  // This runs on `afterDisplay`, NOT on `rest`: `rest` has already had matched
  // pairs removed, and a wrapped expression's stray half can be swallowed into
  // a bogus pair with the next delimiter, erasing the evidence.
  const oddLines = [];
  const lines = afterDisplay.split('\n');
  const sourceLines = stripped.split('\n');
  for (let n = 0; n < lines.length; n += 1) {
    let count = 0;
    for (let i = 0; i < lines[n].length; i += 1) {
      if (lines[n][i] !== '$') continue;
      // Re-check the escape against the original text: `rest` keeps offsets.
      const offset = lines.slice(0, n).reduce((a, l) => a + l.length + 1, 0) + i;
      if (offset > 0 && stripped[offset - 1] === '\\') continue;
      count += 1;
    }
    if (count % 2 !== 0) {
      oddLines.push({ line: n + 1, count, sourceLine: (sourceLines[n] || '').trim() });
    }
  }

  return { display, inline, stray, oddLines };
}

// --------------------------------------------------------------------------- #
// Self-test: fixtures covering both the valid syntax that must be accepted and
// the malformed syntax that must be caught. Run with --selftest.
// --------------------------------------------------------------------------- #
const SELFTESTS = [
  {
    name: 'inline maths on one line is accepted',
    text: 'The amplitude is $\\alpha$ and $\\beta$.\n',
    expect: { stray: 0, inline: 2 },
  },
  {
    name: 'display maths spanning lines is accepted',
    text: '$$\n\\begin{aligned}\na &= 1 \\\\\nb &= 2\n\\end{aligned}\n$$\n',
    expect: { stray: 0, display: 1 },
  },
  {
    name: 'dollars inside a code fence are ignored',
    text: '```bash\nexport PS1="$ "\necho $HOME\n```\n',
    expect: { stray: 0 },
  },
  {
    name: 'dollars inside an inline code span are ignored',
    text: 'Set `$price` before running with `$HOME` set.\n',
    expect: { stray: 0 },
  },
  {
    name: 'an escaped dollar in prose is a literal',
    text: 'The instance costs \\$5 per hour.\n',
    expect: { stray: 0 },
  },
  {
    name: 'several pairs on one line are all captured',
    text: 'Given $x$, $y$ and $z$ we compute $w = x + y + z$.\n',
    expect: { stray: 0, inline: 4 },
  },
  {
    name: 'INVALID: inline maths split across lines is caught',
    text: 'The state is $\\ket{\\psi} =\n\\alpha\\ket{0} + \\beta\\ket{1}$ here.\n',
    expect: { stray: 2 },
  },
  {
    name: 'INVALID: a single unpaired delimiter is caught',
    text: 'The value $\\alpha is left open.\n',
    expect: { stray: 1 },
  },
  {
    name: 'INVALID: an unclosed display block is caught',
    text: '$$\nE = mc^2\n',
    expect: { stray: 2 },
  },
  {
    name: 'INVALID: two wrapped expressions on consecutive lines are caught',
    text: 'Take $\\ket{\\psi} =\n\\alpha\\ket{0}$, then $\\ket{\\phi} =\n\\beta\\ket{1}$.\n',
    expect: { oddLines: 2 },
  },
  {
    name: 'INVALID: a wrapped expression in a Summary bullet is caught',
    text: '- The code distance $d = 3$ corrects any single error on the $n =\n  9$ physical qubits used by the code.\n',
    expect: { oddLines: 2 },
  },
  {
    name: 'VALID: two self-contained pairs on one line each are accepted',
    text: '- The code distance $d = 3$ corrects any single\n  error on the $n = 9$ physical qubits.\n',
    expect: { stray: 0, oddLines: 0 },
  },
  {
    name: 'stray delimiters report the offending line number',
    text: 'First line is fine $a$.\nSecond line opens $x =\nand closes $ late.\n',
    expect: { stray: 2 },
    expectLine: 2,
  },
  {
    name: 'INVALID: a loose delimiter with an odd total is still caught',
    text: 'Good $a$ and $b$, then $ loose, then $c$.\n',
    expect: { stray: 1, oddLines: 1 },
  },
  {
    name: 'KNOWN LIMITATION: an even count of delimiters can still pair wrongly',
    // Six delimiters on one line: the two loose "$" pair with each other to
    // form the bogus expression " loose, then ", and "$c$" still pairs
    // correctly. Parity is even and the bogus body compiles, so neither check
    // fires. Realistic wrapped-inline mistakes leave an odd count and ARE
    // caught by the parity check above; this fixture records the remaining
    // blind spot rather than hiding it.
    text: 'Good $a$ and $b$, then $ loose, then $ more $c$.\n',
    expect: { stray: 0, oddLines: 0 },
  },
];

function runSelftest() {
  let failures = 0;
  for (const t of SELFTESTS) {
    const { display, inline, stray, oddLines } = extract(t.text);
    const problems = [];
    if (t.expect.stray !== undefined && stray.length !== t.expect.stray) {
      problems.push(`stray ${stray.length}, expected ${t.expect.stray}`);
    }
    if (t.expect.inline !== undefined && inline.length !== t.expect.inline) {
      problems.push(`inline ${inline.length}, expected ${t.expect.inline}`);
    }
    if (t.expect.display !== undefined && display.length !== t.expect.display) {
      problems.push(`display ${display.length}, expected ${t.expect.display}`);
    }
    if (t.expect.oddLines !== undefined && oddLines.length !== t.expect.oddLines) {
      problems.push(`oddLines ${oddLines.length}, expected ${t.expect.oddLines}`);
    }
    if (t.expectLine !== undefined && !stray.some((s) => s.line === t.expectLine)) {
      problems.push(
        `no stray reported on line ${t.expectLine} (got ${stray.map((s) => s.line).join(',') || 'none'})`
      );
    }
    if (problems.length) {
      failures += 1;
      console.log(`FAIL ${t.name}: ${problems.join('; ')}`);
    } else {
      console.log(`ok   ${t.name}`);
    }
  }
  console.log(
    failures
      ? `\n${failures} of ${SELFTESTS.length} checker self-tests FAILED`
      : `\nall ${SELFTESTS.length} checker self-tests passed`
  );
  return failures ? 1 : 0;
}

// --------------------------------------------------------------------------- #

const args = process.argv.slice(2);
if (args.includes('--selftest')) {
  process.exit(runSelftest());
}

const files = targetsFromArgs(args);
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

  const { display, inline, stray, oddLines } = extract(text);
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
  if (problems.length || stray.length || oddLines.length) {
    failed += 1;
    console.log(`FAIL ${label}: ${ok} compile, ${problems.length} error(s)` +
      (stray.length ? `, ${stray.length} stray $ delimiter(s)` : '') +
      (oddLines.length ? `, ${oddLines.length} line(s) with an odd number of $ delimiters` : ''));
    problems.slice(0, 25).forEach((p) => console.log(p));
    // Report where each stray delimiter is, so a wrapped inline expression can
    // be found without hunting through the file by eye.
    for (const s of stray.slice(0, 25)) {
      console.log(`  stray $ at line ${s.line}, col ${s.col}: ${s.sourceLine.slice(0, 100)}`);
    }
    for (const s of oddLines.slice(0, 25)) {
      console.log(`  odd $ count (${s.count}) on line ${s.line}: ${s.sourceLine.slice(0, 100)}`);
    }
  } else {
    console.log(`ok   ${label}: ${ok} expressions (${display.length} display / ${inline.length} inline)`);
  }
}

console.log(failed ? `\n${failed} file(s) failed` : `\nall ${files.length} file(s) ok (${total} expressions)`);
process.exit(failed ? 1 : 0);

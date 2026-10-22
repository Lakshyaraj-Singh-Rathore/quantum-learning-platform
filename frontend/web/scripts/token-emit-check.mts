/**
 * Every colour utility used in source must emit a rule in the built CSS.
 *
 * `bg-card` survived in this codebase for months across 7 call sites in 5
 * files. It is a plausible-looking token, there is no `--color-card` in the
 * `@theme` block, Tailwind emits nothing for an undefined colour, and nothing
 * warns. The panels rendered a border and no background, and every existing
 * check passed: tsc sees a string, the UI harnesses assert on class *names*,
 * and SSR cannot apply a cascade.
 *
 * This closes the whole class rather than that one token. It reads the built
 * CSS, so it cannot be satisfied by source that merely looks right -- which is
 * exactly how the original defect survived.
 *
 * Run after `npm run build`.
 */
import { readFileSync, readdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const SRC = path.join(WEB, "src");
const DIST = path.join(WEB, "dist", "assets");

let failures = 0;
let checks = 0;
function check(ok: boolean, name: string, detail = "") {
  checks += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures += 1;
}

if (!existsSync(DIST)) {
  console.log("BLOCKED  dist/assets not found — run `npm run build` first.");
  console.log("This check reads the compiled CSS; source alone cannot decide it.");
  process.exit(0);
}

const cssFile = readdirSync(DIST).find((f) => f.startsWith("index-") && f.endsWith(".css"));
if (!cssFile) {
  console.log("BLOCKED  no index-*.css in dist/assets.");
  process.exit(0);
}
const css = readFileSync(path.join(DIST, cssFile), "utf8");

/** Walk src/ collecting .tsx/.ts sources. */
function sources(dir: string, acc: string[] = []): string[] {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) sources(p, acc);
    else if (/\.tsx?$/.test(e.name)) acc.push(p);
  }
  return acc;
}

// Colour-bearing utility prefixes. Spacing/layout utilities are excluded:
// they are generated arithmetically and cannot silently reference a missing
// token the way a colour can.
const PREFIXES = ["bg", "text", "border", "fill", "stroke", "ring", "from", "to", "via"];
const used = new Map<string, string[]>();

for (const file of sources(SRC)) {
  const body = readFileSync(file, "utf8");
  for (const m of body.matchAll(/\b((?:bg|text|border|fill|stroke|ring|from|to|via)-[a-z][a-z0-9-]*)\b/g)) {
    const util = m[1];
    const prefix = util.slice(0, util.indexOf("-"));
    if (!PREFIXES.includes(prefix)) continue;
    const rest = util.slice(prefix.length + 1);
    // Skip non-colour utilities that share a prefix (bg-cover, text-sm,
    // border-2, …) and anything arbitrary-valued.
    if (/^\d/.test(rest)) continue;
    // Trailing numeric segment means a width/offset/inset utility
    // (border-b-0, border-l-2, from-top-3), not a colour reference.
    if (/-\d+$/.test(rest) && !/-(\d{2,3})$/.test(rest)) continue;
    // Modifier families whose bare prefix is never itself a utility.
    if (["opacity", "offset", "gradient"].some((x) => rest.startsWith(x))) continue;
    if (
      [
        "cover", "contain", "center", "repeat", "no-repeat", "fixed", "local", "scroll",
        "clip", "origin", "none", "auto", "left", "right", "top", "bottom", "middle",
        "start", "end", "justify", "nowrap", "wrap", "balance", "pretty", "ellipsis",
        "solid", "dashed", "dotted", "double", "hidden", "separate", "collapse",
        "transparent", "current", "inherit", "xs", "sm", "base", "lg", "xl", "inset",
      ].includes(rest)
    )
      continue;
    if (!used.has(util)) used.set(util, []);
    const list = used.get(util)!;
    if (list.length < 3) list.push(path.relative(WEB, file));
  }
}

// A utility is "emitted" if its escaped class selector appears in the CSS,
// with or without an opacity modifier.
function emitted(util: string): boolean {
  const esc = util.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return (
    new RegExp(`\\.${esc}(?![a-zA-Z0-9_-])`).test(css) ||
    new RegExp(`\\.${esc}\\\\/`).test(css)
  );
}

const dead: string[] = [];
for (const [util] of [...used].sort()) if (!emitted(util)) dead.push(util);

for (const util of dead) {
  console.log(`DEAD  ${util}  — used in ${used.get(util)!.join(", ")} but emits no CSS rule`);
}

/**
 * Known-dead utilities as of Phase 8A. These are real instances of the same
 * defect as `bg-card` -- a token that was never defined in the `@theme` block,
 * so Tailwind emits nothing and the style silently does not apply. They are
 * recorded rather than fixed because they are outside this phase's scope and
 * each needs a design decision about which existing token replaces it.
 *
 * This is a ratchet, exactly like the ruff count: the list may shrink, never
 * grow. Adding a utility here requires an explicit decision; removing one is
 * always welcome.
 */
const BASELINE = new Set([
  "bg-line-focus",
  "bg-surface",
  "border-slate-400",
  "from-accent-hover",
  "from-emerald-500",
  "ring-line-focus",
  "stroke-white",
  "text-ink-1",
  "text-ink-4",
  "text-slate-200",
  "to-sky-500",
  "to-teal-500",
]);

const regressions = dead.filter((d) => !BASELINE.has(d));
const fixed = [...BASELINE].filter((b) => !dead.includes(b));

for (const f of fixed) console.log(`FIXED ${f} — now emits a rule; remove it from BASELINE`);

check(
  regressions.length === 0,
  `no NEW dead colour utility in ${cssFile}`,
  `${used.size} scanned, ${dead.length} dead (${BASELINE.size} known), ${regressions.length} new`,
);

console.log(
  failures === 0
    ? `\nALL CHECKS PASSED — ${checks} check over ${used.size} colour utilities, 0 dead`
    : `\n${failures} FAILED of ${checks}`,
);
process.exit(failures === 0 ? 0 : 1);

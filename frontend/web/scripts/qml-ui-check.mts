/* Static guards for the QML Lab's UI contract.
 *
 * These are the rules that break *silently* — nothing throws, the build
 * passes, and the page just renders wrong or reaches past the layer it is
 * supposed to use. Each one has a concrete precedent in this repository:
 *
 *  QL-001  An interpolated Tailwind class. Tailwind v4 scans source text for
 *          complete class names, so `bg-${tone}-500` lands in the markup and
 *          in no stylesheet. This is how the density-matrix heatmap shipped
 *          invisible.
 *  CSS     Every colour utility used must actually exist in the built CSS.
 *          `bg-card`, `text-muted` and friends are not tokens in this theme;
 *          writing one produces a class with no rule behind it.
 *  FETCH   No raw `fetch`. `src/api/client.ts` attaches the session token and
 *          normalises FastAPI's three error shapes; bypassing it yields
 *          anonymous requests and `[object Object]` error text.
 *  CHART   No chart library. None is installed and none may be added; the
 *          charts are hand-rolled SVG.
 *  POLL    No `setInterval` for polling. react-query's `refetchInterval` is
 *          torn down on unmount and on terminal states; a hand-rolled timer
 *          outlives the component that started it.
 *  FLAG    The nav entry must be flag-gated, or the whole gating story is
 *          decoration.
 *
 *   npx tsx scripts/qml-ui-check.mts
 */
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

const TARGETS = [
  "src/api/qml.ts",
  "src/api/features.ts",
  "src/hooks/useFeatures.ts",
  "src/hooks/useQmlExperiment.ts",
  "src/pages/QmlLabPage.tsx",
  "src/components/qml/charts.tsx",
  "src/components/qml/circuitIr.ts",
  "src/components/qml/QmlConfigForm.tsx",
  "src/components/qml/QmlCircuitPreview.tsx",
  "src/components/qml/QmlTrainingDashboard.tsx",
  "src/components/qml/QmlResultsPanel.tsx",
  "src/components/shell/nav.ts",
];

let failures = 0;
let checks = 0;

function check(ok: boolean, label: string, detail = "") {
  checks += 1;
  if (!ok) {
    failures += 1;
    console.log(`FAIL  ${label}${detail ? `\n        ${detail}` : ""}`);
  }
}

/* -------------------------------------------------------------------------- */
/* Load sources                                                                */
/* -------------------------------------------------------------------------- */

const sources = new Map<string, string>();
for (const rel of TARGETS) {
  const abs = join(root, rel);
  if (!existsSync(abs)) {
    failures += 1;
    checks += 1;
    console.log(`FAIL  missing expected source: ${rel}`);
    continue;
  }
  sources.set(rel, readFileSync(abs, "utf-8"));
}

/* -------------------------------------------------------------------------- */
/* QL-001 — no interpolated class names                                       */
/* -------------------------------------------------------------------------- */

/** Comment-free source: a class name mentioned in prose is documentation,
 *  not markup, and this file's own header mentions several. */
const stripped = new Map<string, string>();
for (const [rel, src] of sources) {
  stripped.set(rel, src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, ""));
}

/** An interpolation glued straight onto a Tailwind utility prefix. */
const UTILITY_PREFIX =
  /(?:^|[\s"'`])(?:bg|text|border|from|to|via|ring|fill|stroke|outline|decoration|shadow|opacity|rounded|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|w|h|min-w|min-h|max-w|max-h|gap|space-x|space-y|col-span|row-span|grid-cols|order|z|inset|top|left|right|bottom|translate-x|translate-y|scale|rotate|duration|delay)-\$\{/;

/** Looks like a Tailwind utility list rather than prose or a URL. */
const CLASSY = /\b(?:bg|text|border|from|to|via|ring|fill|stroke|flex|grid|rounded|p|px|py|m|mt|mb|gap|w|h|space)-[a-z0-9[]/;

let templatesScanned = 0;
for (const [rel, src] of stripped) {
  // Every template literal in the file, wherever it sits — className={`…`},
  // cn(`…`), a helper, a variable. Interpolating a class is the hazard; the
  // syntax that surrounds it is not.
  const offenders: string[] = [];
  for (const m of src.matchAll(/`([^`]*)`/g)) {
    const body = m[1];
    if (!body.includes("${")) continue;
    templatesScanned += 1;
    // A template whose *static* text contains utility-looking tokens is
    // building a class name. `${pct}%` in a style value is not.
    if (CLASSY.test(body.replace(/\$\{[^}]*\}/g, " "))) offenders.push(m[0].slice(0, 90));
    // An interpolation glued directly onto a *Tailwind* prefix is the
    // classic form and fails on its own. The prefix list is explicit: a DOM
    // id like `qml-feature-${i}` is not a class name and must not trip this.
    if (UTILITY_PREFIX.test(body)) offenders.push(m[0].slice(0, 90));
  }
  check(offenders.length === 0, `QL-001 ${rel}: no interpolated Tailwind class`, offenders.join(" | "));
}

/* -------------------------------------------------------------------------- */
/* CSS — every colour utility used exists in the built stylesheet             */
/* -------------------------------------------------------------------------- */

const assetsDir = join(root, "dist", "assets");
const cssFile = existsSync(assetsDir)
  ? readdirSync(assetsDir).find((f) => /^index-.*\.css$/.test(f))
  : undefined;

if (!cssFile) {
  console.log(
    "BLOCKED  dist/assets/index-*.css not found — run `npm run build` first; " +
      "this check verifies the utilities survive the bundle, which cannot be " +
      "decided from source alone.",
  );
  process.exit(1);
}

const css = readFileSync(join(assetsDir, cssFile), "utf-8");

/** Tailwind escapes `/` and `.` in generated selectors. */
const escapeClass = (c: string) => c.replace(/[/.]/g, (ch) => `\\${ch}`);

// Only colour-ish utilities: those are the ones that silently vanish. Layout
// utilities failing would be visible instantly.
const COLOUR_PREFIX = /\b(bg|text|border|from|to|via|ring|fill|stroke)-([a-z0-9][a-z0-9-]*(?:\/\d{1,3})?)\b/g;
const IGNORE_SUFFIX = new Set([
  "transparent", "current", "inherit", "white", "black", "none", "auto",
  // text-* sizing and weight utilities share the prefix
  "xs", "sm", "base", "lg", "xl", "2xl", "3xl", "left", "right", "center", "wrap",
  "nowrap", "balance", "pretty", "ellipsis", "clip", "start", "end", "justify",
  // border-* sizing / style
  "solid", "dashed", "dotted", "double", "hidden", "collapse", "separate",
  // bg-* positioning
  "cover", "contain", "fixed", "local", "scroll", "repeat", "bottom", "top",
]);

const missing: string[] = [];
const seen = new Set<string>();
for (const [rel, src] of stripped) {
  // Every string literal in the comment-free source. Classes reach the DOM
  // through className="…", cn("…", …), a ternary branch and a lookup table,
  // and a check that only understood the first of those would pass while the
  // other three shipped broken.
  for (const attr of src.matchAll(/"([^"\n]*)"|'([^'\n]*)'|`([^`]*)`/g)) {
    const value = attr[1] ?? attr[2] ?? attr[3] ?? "";
    for (const m of value.matchAll(COLOUR_PREFIX)) {
      const cls = `${m[1]}-${m[2]}`;
      const bare = m[2].split("/")[0];
      if (IGNORE_SUFFIX.has(bare) || /^\d+$/.test(bare)) continue;
      if (seen.has(cls)) continue;
      seen.add(cls);
      const full = `.${escapeClass(cls)}`;
      const base = `.${escapeClass(cls.split("/")[0])}`;
      if (!css.includes(full) && !css.includes(base)) missing.push(`${cls} (${rel})`);
    }
  }
}
check(
  missing.length === 0,
  `CSS: all ${seen.size} colour utilities used by the QML Lab exist in ${cssFile}`,
  missing.join(", "),
);

/* -------------------------------------------------------------------------- */
/* Token names passed to style={{ … var(--color-*) }} resolve                 */
/* -------------------------------------------------------------------------- */

const globals = readFileSync(join(root, "src", "globals.css"), "utf-8");
const themeTokens = new Set(
  [...globals.matchAll(/--color-([a-z0-9-]+)\s*:/g)].map((m) => m[1]),
);
const badTokens: string[] = [];
for (const [rel, src] of sources) {
  for (const m of src.matchAll(/var\(--color-([a-z0-9-]+)\)/g)) {
    if (!themeTokens.has(m[1])) badTokens.push(`--color-${m[1]} (${rel})`);
  }
}
check(
  badTokens.length === 0,
  `tokens: every var(--color-*) resolves against the ${themeTokens.size} @theme tokens`,
  badTokens.join(", "),
);

/* -------------------------------------------------------------------------- */
/* Layer discipline                                                            */
/* -------------------------------------------------------------------------- */

for (const [rel, src] of stripped) {
  check(!/\bfetch\s*\(/.test(src), `FETCH ${rel}: goes through src/api/client.ts`);
  check(
    !/\bsetInterval\s*\(/.test(src),
    `POLL ${rel}: no hand-rolled timer (use react-query refetchInterval)`,
  );
  check(
    !/from\s+["'](recharts|chart\.js|react-chartjs-2|d3|victory|@nivo\/|plotly|apexcharts|echarts)/.test(
      src,
    ),
    `CHART ${rel}: no chart library`,
  );
}

/* -------------------------------------------------------------------------- */
/* Flag gating                                                                 */
/* -------------------------------------------------------------------------- */

const nav = sources.get("src/components/shell/nav.ts") ?? "";
const qmlEntry = /\{[^}]*to:\s*"\/qml-lab"[^}]*\}/s.exec(nav)?.[0] ?? "";
check(qmlEntry !== "", "FLAG nav.ts: a /qml-lab entry exists");
check(
  /flag:\s*"qml_enabled"/.test(qmlEntry),
  "FLAG nav.ts: the /qml-lab entry is gated on qml_enabled",
  qmlEntry.replace(/\s+/g, " ").slice(0, 120),
);
check(
  /export function useNavItems/.test(nav) && /item\.flag === undefined \|\| features\[item\.flag\]/.test(nav),
  "FLAG nav.ts: useNavItems filters gated entries",
);

for (const consumer of ["src/components/shell/Sidebar.tsx", "src/components/shell/CommandPalette.tsx"]) {
  const src = readFileSync(join(root, consumer), "utf-8");
  check(
    /useNavItems\(\)/.test(src) && !/\bNAV_ITEMS\b/.test(src),
    `FLAG ${consumer}: lists navItems from useNavItems(), not the raw NAV_ITEMS`,
  );
}

const page = sources.get("src/pages/QmlLabPage.tsx") ?? "";
check(
  /useQmlEnabled\(\)/.test(page) && /if \(!enabled\)/.test(page),
  "FLAG QmlLabPage: the route gates itself, not just the nav entry",
);
check(
  /if \(!resolved\)/.test(page) && page.indexOf("if (!resolved)") < page.indexOf("if (!enabled)"),
  "FLAG QmlLabPage: unresolved is handled before disabled (no 404 flash on refresh)",
);

const features = sources.get("src/hooks/useFeatures.ts") ?? "";
check(
  /query\.data \?\? FEATURES_CLOSED/.test(features),
  "FLAG useFeatures: fails closed when the flag query errors",
);

console.log(
  failures === 0
    ? `ALL CHECKS PASSED — ${checks} UI contract guards over ${sources.size} QML sources ` +
      `(${seen.size} colour utilities, ${templatesScanned} interpolated templates scanned)`
    : `${failures} of ${checks} GUARDS FAILED`,
);
process.exit(failures === 0 ? 0 : 1);

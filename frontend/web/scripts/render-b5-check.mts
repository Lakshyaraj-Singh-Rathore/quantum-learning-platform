import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { Markdown } from "../src/components/Markdown";
import { readFileSync, readdirSync, existsSync } from "node:fs";

const root = "/home/user/quantum-learning-platform/content";
const files = readdirSync(root).filter(f => /\.md$/.test(f)).sort();

let fail = 0, mdLinkFiles = 0, mdLinks = 0;
const perBucket: Record<string, {files:number, links:number}> = {pre:0,b5:0} as any;

for (const f of files) {
  const n = parseInt(f.split("_")[0], 10);
  const bucket = n >= 49 && n <= 70 ? "b5" : "pre";
  const raw = readFileSync(`${root}/${f}`, "utf8").replace(/<!--\s*track:.*?-->/s, "");
  const html = renderToString(createElement(Markdown, { children: raw }));

  const problems: string[] = [];
  if (/\$\$/.test(html)) problems.push("raw $$ leaked");
  // a table is optional: 7 pre-existing lessons legitimately have none
  if (!html.includes("katex")) problems.push("no katex");

  // every emitted .md href must point at a file that exists
  const hrefs = [...html.matchAll(/href="([^"]+\.md)"/g)].map(m => m[1]);
  const missing = hrefs.filter(h => !existsSync(`${root}/${h}`));
  if (missing.length) problems.push(`broken target: ${missing.join(",")}`);
  if (hrefs.length) { mdLinkFiles++; mdLinks += hrefs.length; (perBucket as any)[bucket] = ((perBucket as any)[bucket]||0) + hrefs.length; }

  if (problems.length) { fail++; console.log(`FAIL ${f}: ${problems.join("; ")}`); }
}
console.log(`\n  lessons rendered          : ${files.length}`);
console.log(`  render failures           : ${fail}`);
console.log(`  files emitting .md links  : ${mdLinkFiles}`);
console.log(`  total .md links emitted   : ${mdLinks}`);
console.log(`  ... of which pre-existing (01-48): ${(perBucket as any).pre||0}`);
console.log(`  ... of which batch-5      (49-70): ${(perBucket as any).b5||0}`);
console.log(`  any broken link targets   : ${fail ? "YES" : "no — every .md href resolves to a real file"}`);

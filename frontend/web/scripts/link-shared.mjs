/* Gives the shared grid source a place to resolve its imports from.
 *
 * The drag-and-drop grid lives outside this app (frontend/circuit_composer,
 * see the @composer alias), so when TypeScript and Node resolve `react` from
 * ITS directory they find nothing — this app's node_modules does not apply
 * there. The tempting fix is `npm install` inside the component, but that
 * produces a SECOND copy of React, and a bundle with two Reacts fails at
 * runtime with "invalid hook call" rather than at build time.
 *
 * So: create frontend/node_modules and point react / react-dom / @types at
 * this app's copies. One React, resolved identically by tsc, Vite, Node and
 * the Docker build. Directories are linked as junctions, which works on
 * Windows without elevated privileges.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, "..");
const shared = path.resolve(web, "..", "node_modules");
const own = path.join(web, "node_modules");

const LINKS = ["react", "react-dom", "@types", "streamlit-component-lib"];

if (!fs.existsSync(own)) {
  console.error("[link-shared] run `npm install` in frontend/web first");
  process.exit(1);
}

fs.mkdirSync(shared, { recursive: true });

for (const name of LINKS) {
  const target = path.join(own, name);
  const link = path.join(shared, name);
  if (!fs.existsSync(target)) {
    console.warn(`[link-shared] skipped ${name}: not installed in frontend/web`);
    continue;
  }
  // Re-point on every run: the link must follow this app's copy, not whatever
  // it happened to point at before (e.g. a component-local install).
  if (fs.lstatSync(link, { throwIfNoEntry: false })) {
    fs.rmSync(link, { recursive: true, force: true });
  }
  fs.symlinkSync(target, link, "junction");
  console.log(`[link-shared] ${name} -> ${path.relative(shared, target)}`);
}

// `npm install` inside the component (to rebuild the Streamlit bundle by hand)
// creates a second React there. Vite's dedupe keeps the app correct, but plain
// Node resolves it first, which breaks the headless render checks.
const componentReact = path.join(web, "..", "circuit_composer", "frontend", "node_modules", "react");
if (fs.existsSync(componentReact)) {
  console.warn(
    "[link-shared] warning: circuit_composer/frontend/node_modules/react exists.\n" +
      "              The app is fine (Vite dedupes), but `npm run render:check`\n" +
      "              would see two Reacts. Remove that folder to run the checks.",
  );
}

/* Renders the REAL Games page against REAL data.
 *
 *   npx tsx scripts/render-games.mts
 *   npm run render:games
 *
 * Two fixtures, both generated rather than written by hand:
 *
 * - test-fixtures/games.json — the catalogue from a live GET /games
 *   (regenerate with scripts/game-fixtures.py): 4 games, 10 levels.
 * - test-fixtures/games-results.json — grader output produced by the
 *   platform's OWN game_graders.py running on real Aer counts: a 4/4 truth
 *   table and a subsampled convergence curve. Regenerate with
 *   scripts/game-results.py. Nothing here is invented.
 *
 * Honest limit, as with the other harnesses: renderToString cannot click, so
 * "Run & score" and the polling it starts are browser-only. The result panels
 * are checked by rendering LevelResult directly with the real grader output.
 */

import { readFileSync } from "node:fs";

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-games-token",
      user: { id: 1, email: "a@b.dev", role: "student", display_name: "Render Games", is_active: true },
    },
    version: 0,
  }),
);
const storage = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
  key: () => null,
  length: 0,
};
(globalThis as { localStorage?: unknown }).localStorage = storage;
(globalThis as { window?: unknown }).window = {
  localStorage: storage,
  location: { hostname: "localhost", href: "http://localhost/", origin: "http://localhost" },
};

const { renderToString } = await import("react-dom/server");
const { createElement } = await import("react");
const { MemoryRouter } = await import("react-router-dom");
const { QueryClient, QueryClientProvider } = await import("@tanstack/react-query");
const { Catalogue, LevelPlay, LevelResult } = await import("../src/pages/GamesPage.tsx");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

const ENTITIES: Record<string, string> = { "&#x27;": "'", "&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">", "&#39;": "'" };
function text(html: string): string {
  return html
    .replace(/<!-- -->/g, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&quot;|&amp;|&lt;|&gt;|&#39;/g, (m) => ENTITIES[m] ?? m)
    .replace(/\s+/g, " ");
}

type Level = {
  slug: string;
  title: string;
  prompt: string;
  level: number;
  grader: string | null;
  allowed_gates: string[];
  constraints: Record<string, unknown>;
  starter_ir: Record<string, unknown> | null;
  epsilon: number | null;
  max_edits: number | null;
  n_controls: number | null;
  best_score: number;
  passed: boolean;
  attempts: number;
};

const catalogue = JSON.parse(
  readFileSync(new URL("../test-fixtures/games.json", import.meta.url), "utf8"),
) as { games: ({ game_id: string; title: string; blurb: string; icon: string; completed: number; total: number } & { levels: Level[] })[] };

const results = JSON.parse(
  readFileSync(new URL("../test-fixtures/games-results.json", import.meta.url), "utf8"),
) as {
  truth_table: { score: number; note: string; details: Record<string, unknown> };
  shot_detective: { counts: Record<string, number>; curve: { shots: number; tvd: number }[]; ideal: Record<string, number> };
};

const LEVELS = catalogue.games.flatMap((game) => game.levels);
check("the catalogue is real data", catalogue.games.length === 4 && LEVELS.length === 10, `${catalogue.games.length} games, ${LEVELS.length} levels`);

function render(node: React.ReactElement): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  client.setQueryData(["games"], catalogue);
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/games"] }, node),
    ),
  );
}

/* ---------- the catalogue ---------- */

const listHtml = render(createElement(Catalogue, { games: catalogue.games, onPlay: () => {} }));
const listText = text(listHtml);

check("the catalogue renders", listHtml.length > 3000, `${listHtml.length} chars`);
check(
  "every game is shown with its blurb",
  catalogue.games.every((game) => listText.includes(game.title) && listText.includes(game.blurb)),
);
check(
  "every level is shown with its number",
  LEVELS.every((level) => listText.includes(`Level ${level.level}`)),
);
check("progress is shown per game", catalogue.games.every((game) => listText.includes(`${game.completed}/${game.total}`)));
check("each level has a play control", (listHtml.match(/Play/g) ?? []).length >= LEVELS.length, `${LEVELS.length} levels`);

/* ---------- playing a level ---------- */

const vault = LEVELS.find((level) => level.grader === "truth_table");
const shots = LEVELS.find((level) => level.grader === "shot_detective");
const bug = LEVELS.find((level) => level.grader === "find_bug");
const bellLevel = LEVELS.find((level) => level.grader === null);
check("the fixture covers every grader", Boolean(vault && shots && bug && bellLevel));

if (vault) {
  const html = render(createElement(LevelPlay, { level: vault, onBack: () => {} }));
  const body = text(html);
  check("the objective is shown", body.includes("🎯 Objective") && body.includes(vault.prompt.slice(0, 40)));
  check("the allowed gates are listed as rules", vault.allowed_gates.every((gate) => body.includes(gate.toUpperCase())));
  check(
    "the input coverage is stated",
    body.includes(`Checked over all ${2 ** ((vault.n_controls ?? 0) + 1)} basis inputs`),
    `${2 ** ((vault.n_controls ?? 0) + 1)} inputs`,
  );
  check("the editor guidance is kept", body.includes("Drag a gate from the palette"));
  check("run, clear and back are all offered", body.includes("Run & score") && body.includes("Clear circuit") && body.includes("All games"));
  check("no result is claimed before running", !body.includes("Level complete") && !body.includes("Truth table"));
}

if (shots) {
  const body = text(render(createElement(LevelPlay, { level: shots, onBack: () => {} })));
  check(
    "Shot Detective carries the tolerance note verbatim",
    body.includes("Shots — fewer scores higher, but you must stay within tolerance"),
  );
  check("its tolerance is shown in the rules", body.includes(`Tolerance: ${shots.epsilon}`));
}

if (bug) {
  const body = text(render(createElement(LevelPlay, { level: bug, onBack: () => {} })));
  check("Find the Bug offers the broken circuit back", body.includes("Reset to broken"));
  check("its edit budget is shown", body.includes(`Edit budget: ${bug.max_edits}`));
  check("it has a starter circuit to repair", bug.starter_ir !== null);
}

/* ---------- the result panels, against real grader output ---------- */

const truthTable = {
  attempt_id: 1,
  job_id: 1,
  status: "graded",
  passed: true,
  score: results.truth_table.score,
  feedback: results.truth_table.note,
  details: { game: results.truth_table.details },
};
const truthHtml = render(createElement(LevelResult, { outcome: truthTable }));
const truthText = text(truthHtml);
const table = results.truth_table.details as unknown as {
  testcases_total: number;
  testcases_passed: number;
  rows: { input: string; output: string; expected_target: number; got_target: number; controls_intact: boolean; certainty: number; passed: boolean }[];
};
const rows = (results.truth_table.details as unknown as { table: { input: string; expected_target: number; got_target: number; controls_intact: boolean; certainty: number; passed: boolean }[] }).table;

check("a pass is announced with its score", truthText.includes("Level complete") && truthText.includes(results.truth_table.score.toFixed(2)));
check(
  "the test-case tally is shown",
  truthText.includes(`Test cases passed ${table.testcases_passed}/${table.testcases_total}`),
);
check(
  "every checked input is in the truth table",
  rows.every((row) => truthText.includes(row.input)),
  rows.map((row) => row.input).join(" "),
);
check("the column headings are kept", truthText.includes("Input |c…t⟩") && truthText.includes("Controls preserved"));
check("the reading rule is kept", truthText.includes("Controls are the left characters"));
check("certainty is shown as a percentage", rows.every((row) => truthText.includes(`${Math.round(row.certainty * 100)}%`)));

const curveAttempt = {
  attempt_id: 2,
  job_id: 2,
  status: "graded",
  passed: false,
  score: 0,
  feedback: "Distribution error exceeds the tolerance. Use more shots.",
  details: {
    game: { curve: results.shot_detective.curve },
    counts: results.shot_detective.counts,
  },
};
const curveText = text(render(createElement(LevelResult, { outcome: curveAttempt })));
check("the convergence curve is drawn", curveText.includes("How the error shrinks with more shots"));
check(
  "every curve point is tabulated",
  results.shot_detective.curve.every((point) => curveText.includes(String(point.shots)) && curveText.includes(point.tvd.toFixed(4))),
  results.shot_detective.curve.map((p) => `${p.shots}:${p.tvd.toFixed(4)}`).join(" "),
);
check("the subsampling caveat is kept", curveText.includes("costs a single simulation"));
check("the measured counts are shown", curveText.includes("Measurement outcomes"));
check(
  "a fail is announced as not-yet, not as a pass",
  curveText.includes("Not yet") && !curveText.includes("Level complete"),
);

const editsAttempt = {
  attempt_id: 3,
  job_id: 3,
  status: "graded",
  passed: true,
  score: 1,
  feedback: "Fixed with 1 edit (budget 1).",
  details: { game: { edits: { total: 1, modified: 1, added: 0, removed: 0 }, max_edits: 1 } },
};
const editsText = text(render(createElement(LevelResult, { outcome: editsAttempt })));
check(
  "the edit budget is reported",
  editsText.includes("Edits used") && editsText.includes("budget 1") && editsText.includes("Modified"),
);

if (bellLevel) {
  const fidelityAttempt = {
    attempt_id: 4,
    job_id: 4,
    status: "graded",
    passed: true,
    score: 1,
    feedback: "State matches.",
    details: {
      behaviour_note: "graded on fidelity 0.999",
      counts: results.shot_detective.counts,
    },
  };
  const fidelityText = text(render(createElement(LevelResult, { outcome: fidelityAttempt })));
  check("a fidelity-graded level says so", fidelityText.includes("Graded on state fidelity"));
  check(
    "and explains why the histogram is not enough",
    fidelityText.includes("Two different states can produce this same histogram"),
  );
}

console.log(
  failures === 0 ? "\nAll Games render checks passed." : `\n${failures} Games check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);

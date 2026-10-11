/* Renders the REAL Learn page against REAL curriculum data.
 *
 * The lesson bodies come from test-fixtures/lessons.json, captured from a live
 * GET /lessons and GET /lessons/{slug} (regenerate with
 * scripts/lesson-fixtures.py). That matters: the lessons are LaTeX-heavy, and
 * a reader that silently drops the maths would still render *a* page.
 *
 *   npx tsx scripts/render-learn.mts
 *   npm run render:learn
 *
 * Because the selected lesson is derived rather than stored in an effect (see
 * LearnPage), the page renders its first lesson on the very first pass, so
 * SSR can actually see the body. What it still cannot reach is anything behind
 * a click: switching lesson, switching track, and sending a question.
 */

import { readFileSync } from "node:fs";

const store = new Map<string, string>();
store.set(
  "ql-session",
  JSON.stringify({
    state: {
      token: "render-learn-token",
      user: {
        id: 1,
        email: "a@b.dev",
        role: "student",
        display_name: "Render Learn",
        is_active: true,
      },
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
const { LearnPage } = await import("../src/pages/LearnPage.tsx");

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

const ENTITIES: Record<string, string> = {
  "&#x27;": "'",
  "&quot;": '"',
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&#39;": "'",
};

function text(html: string): string {
  return html
    .replace(/<!-- -->/g, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&quot;|&amp;|&lt;|&gt;|&#39;/g, (m) => ENTITIES[m] ?? m)
    .replace(/\s+/g, " ");
}

const fixture = JSON.parse(
  readFileSync(new URL("../test-fixtures/lessons.json", import.meta.url), "utf8"),
) as {
  lessons: { slug: string; title: string; tags: string[]; order_index: number; track: string }[];
  bodies: Record<string, { slug: string; title: string; tags: string[]; content: string }>;
};

const LESSONS = fixture.lessons;
const BODIES = fixture.bodies;
const FIRST = LESSONS[0];

check("the fixture is real curriculum data", LESSONS.length === 13, `${LESSONS.length} lessons`);
check(
  "the fixture carries both tracks",
  LESSONS.some((l) => l.track === "circuit") && LESSONS.some((l) => l.track === "theory"),
);

/** Opens a chosen lesson first, by reordering the list the page is given. */
function renderOpening(slug: string): string {
  const wanted = LESSONS.find((l) => l.slug === slug);
  if (!wanted) throw new Error(`no such lesson: ${slug}`);
  return render({ lessons: [wanted, ...LESSONS.filter((l) => l.slug !== slug)] });
}

function render(seed: Record<string, unknown> = {}): string {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  client.setQueryData(["lessons"], seed.lessons ?? LESSONS);
  // `bodies` lets a check substitute lesson content without editing the
  // fixture, which is captured from a live API and should stay honest.
  const bodies = (seed.bodies as Record<string, unknown>) ?? BODIES;
  for (const [slug, body] of Object.entries(bodies)) {
    client.setQueryData(["lesson", slug], body);
  }
  return renderToString(
    createElement(
      QueryClientProvider,
      { client },
      createElement(MemoryRouter, { initialEntries: ["/learn"] }, createElement(LearnPage)),
    ),
  );
}

/* ---------- the reader ---------- */

const html = render();
const body = text(html);

check("the page renders", html.length > 3000, `${html.length} chars`);
check("it is no longer the P4 placeholder", !body.includes("Not built yet"));
// Compared against decoded text: React escapes the apostrophe in
// "Grover's Search Algorithm" to &#x27;.
check(
  "the table of contents lists every lesson",
  LESSONS.every((l) => body.includes(l.title)),
  LESSONS.filter((l) => !body.includes(l.title)).map((l) => l.slug).join(", ") || "all 13",
);
check("each lesson is tagged with its track", body.includes("C") && html.includes(">T<"));
check(
  "the first lesson is opened by default",
  body.includes(FIRST.title) && body.includes("Track:"),
);
check(
  "the track filter offers Theory, Circuit and All",
  body.includes("Theory") && body.includes("Circuit") && body.includes("All"),
);
check(
  "the tracks are explained, as in Streamlit",
  body.includes("Theory explains the concepts") || body.includes("explains the concepts"),
);

/* ---------- the lesson body is really rendered ---------- */

const qubits = BODIES["01_qubits"];
check("the lesson body is on the page", body.includes("Qubits and Superposition"));
check(
  "prose from the lesson survives",
  body.includes("classical bit") && body.includes("Bloch sphere"),
);
check("headings become real headings", html.includes("<h2") || html.includes("<h1"));
check("the lesson's concept tags are shown", qubits.tags.every((t) => body.includes(t)));

/* ---------- LaTeX and tables: the part a naive renderer loses ---------- */

check("display maths is typeset, not left as $$", html.includes("katex"));
check("no raw $$ markers leak into the page", !body.includes("$$"));
check("inline maths is typeset too", (html.match(/class="katex"/g) ?? []).length > 1, `${(html.match(/class="katex"/g) ?? []).length} maths spans`);
// 01_qubits has no table, so open the lesson that does rather than assert on
// a page that cannot show one.
const withTable = renderOpening("02_gates");
check(
  "GFM tables are rendered as tables",
  withTable.includes("<table>") && withTable.includes("<th>") && withTable.includes("<td>"),
  "02_gates",
);

/* ---------- the tutor ---------- */

check("the AI tutor is offered", body.includes("Ask the AI tutor"));
check(
  "the input is scoped to the open lesson",
  html.includes(`Ask about ${FIRST.title}`),
);
check(
  "the tutor says where its answers come from",
  body.includes("cites the lessons it used") || body.includes("curriculum"),
);

/* ---------- the circuit-lesson banner ---------- */

check(
  "a theory lesson does not claim to be hands-on",
  !body.includes("Hands-on lesson."),
  `${FIRST.slug} is ${FIRST.track}`,
);

/* ---------- the interactive demos are really mounted ---------- */

// 01_qubits carries four demos in Streamlit; the same four must be here.
const demos = text(render());
const FOUR = [
  "A bit versus a qubit",
  "Amplitude is not probability",
  "Explore the Bloch sphere",
  "Build a circuit here",
];
  check(
    "the lesson's demos are offered as tabs",
    FOUR.every((title) => demos.includes(title)),
    FOUR.filter((t) => !demos.includes(t)).join(", ") || "all 4 for 01_qubits",
  );
  // Regression guard. The active style used to be keyed on `demoKey`, which
  // starts as null while the panel falls back to showing the first demo, so
  // the tab that was actually open rendered unselected until you clicked a
  // different one and came back. Counting the marker catches it either way:
  // zero means "nothing looks selected", two means "the wrong one is".
  const activeDemoTabs = (html.match(/border-accent bg-accent\/15/g) ?? []).length;
  check(
    "exactly one demo tab is marked active on first render",
    activeDemoTabs === 1,
    `${activeDemoTabs} marked active`,
  );
check(
  "the first demo is open and really rendered",
  demos.includes("Measure the qubit") && demos.includes("Reset qubit"),
);
check(
  "it opens in the superposition state, with the honest wording",
  demos.includes("It has no value yet"),
);
check(
  "the measurement controls are disabled until it is collapsed",
  html.includes("disabled"),
);
check(
  "the demos are introduced as live",
  demos.includes("every control computes a real quantum state"),
);
// A lesson with no demos registered must not show an empty section.
const noDemos = renderOpening("07_vqe_qaoa");
check(
  "a lesson with no demos gets no demo section",
  !text(noDemos).includes("Try it yourself"),
  "07_vqe_qaoa has none",
);

/* ---------- cross-lesson links actually go somewhere ---------- */

// Lessons reference each other by bare filename ("see 02_gates.md"). There are
// 344 of these and no .md route exists, so rendered literally they are dead
// ends. They must be rewritten to the ?lesson=<slug> deep link the page
// already reads. The fixture carries none, so the body is substituted here.
const linked = render({
  bodies: {
    [FIRST.slug]: {
      ...BODIES[FIRST.slug],
      content: [
        "See [single-qubit gates](02_gates.md) first.",
        "",
        "Then the [Qiskit docs](https://example.com/qiskit).",
      ].join("\n"),
    },
  },
});
check(
  "a cross-lesson .md link becomes an in-app ?lesson= link",
  linked.includes("?lesson=02_gates"),
  "344 of these across /content",
);
check(
  "it no longer points at a .md file that has no route",
  !linked.includes('href="02_gates.md"'),
);
check(
  "the link text survives the rewrite",
  text(linked).includes("single-qubit gates"),
);
check(
  "an external link opens in a new tab, safely",
  /href="https:\/\/example\.com\/qiskit"/.test(linked) &&
    linked.includes('target="_blank"') &&
    linked.includes('rel="noopener noreferrer"'),
);

/* ---------- the empty state ---------- */

const empty = render({ lessons: [] });
const emptyText = text(empty);
check(
  "no lessons is explained, not blank",
  emptyText.includes("No lessons are loaded yet") && emptyText.includes("/content/*.md"),
);
check("the empty state does not invent a lesson list", !emptyText.includes("Ask about"));

console.log(
  failures === 0 ? "\nAll Learn render checks passed." : `\n${failures} Learn check(s) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);

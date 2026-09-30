/* End-to-end smoke for the P0 shell's data layer, run against a REAL
 * FastAPI instance (no mocks, no fixtures — the same "nothing fake" rule the
 * backend suite follows). It drives the actual modules the browser uses:
 * src/api/client.ts, src/api/auth.ts, src/api/backends.ts.
 *
 *   npm run build && VITE_API_BASE=http://127.0.0.1:8123 node --experimental-strip-types scripts/smoke-auth.mts
 */
import { api, ApiError } from "../src/api/client.ts";
import { login, me, register } from "../src/api/auth.ts";
import { backends } from "../src/api/backends.ts";
import { useSession } from "../src/state/session.ts";

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

// The app calls relative /api/* and lets the proxy (nginx / vite) route it.
// Under plain Node there is no proxy, so the harness rewrites those URLs onto
// the live server named by API_TARGET. This is the ONLY bit of indirection in
// the script — every module under test is the real one the browser loads.
const target = process.env.API_TARGET ?? "http://127.0.0.1:8123";
const routedFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  return routedFetch(url.startsWith("/api/") ? `${target}${url.slice(4)}` : url, init);
}) as typeof fetch;

const email = `p0-${Date.now()}@test.dev`;
const password = "quant123";

// 1. register stores a token in the session store, exactly like the form does
const created = await register({ email, password, display_name: "P0 Smoke" });
useSession.getState().setFromToken(created);
check("register returns a bearer token", created.token_type === "bearer", created.email);
check("session store holds the token", !!useSession.getState().token);
check("new accounts are students, not whatever the client asked for", created.role === "student", created.role);

// 2. a protected call through the real client, bearer header attached
const identity = await me();
check("GET /auth/me with the stored token", identity.email === email, identity.role);

// 3. login path (same account), and /auth/me still works after the swap
const relogged = await login({ email, password });
useSession.getState().setFromToken(relogged);
check("login returns a token", !!relogged.access_token);
check("GET /auth/me after re-login", (await me()).id === identity.id);

// 4. the engine catalogue the sidebar/topbar badge renders
const catalogue = await backends();
check("GET /backends lists 6 engines", catalogue.backends.length === 6, `${catalogue.backends.length}`);
const cudaq = catalogue.backends.find((b) => b.id === "cudaq");
check("CUDA-Q entry is present with the GPU label", !!cudaq && /GPU/.test(cudaq.label), cudaq?.label);
check(
  "every engine reports availability honestly (bool + reason string)",
  catalogue.backends.every((b) => typeof b.available === "boolean" && typeof b.reason === "string"),
);
console.log("      engines:", catalogue.backends.map((b) => `${b.id}=${b.available ? "up" : "down"}`).join(" "));

// 5. a wrong password must surface FastAPI's own message, not a JSON dump
try {
  await login({ email, password: "nope" });
  check("bad password raises", false);
} catch (exc) {
  check(
    "bad password surfaces the API's message",
    exc instanceof ApiError && exc.status === 401 && exc.message === "Invalid email or password",
    exc instanceof ApiError ? `${exc.status} ${exc.message}` : String(exc),
  );
}

// 6. duplicate registration must surface FastAPI's own message
try {
  await register({ email, password });
  check("duplicate email raises", false);
} catch (exc) {
  check(
    "duplicate email surfaces the API's message",
    exc instanceof ApiError && exc.status === 400 && exc.message === "Email is already registered",
    exc instanceof ApiError ? `${exc.status} ${exc.message}` : String(exc),
  );
}

// 7. with no token, a protected call must fail loudly (not silently 200)
useSession.getState().clear();
try {
  await me();
  check("unauthenticated /auth/me raises", false);
} catch (exc) {
  check(
    "unauthenticated /auth/me raises 401/403",
    exc instanceof ApiError && (exc.status === 401 || exc.status === 403),
    exc instanceof ApiError ? String(exc.status) : String(exc),
  );
}

// 8. a dead API (`make up` not running) must read as status 0 with a message
//    that tells the learner what to do. Simulated by stubbing fetch — the
//    network itself is real in checks 1-7.
useSession.setState({ token: "some-token" });
const currentFetch = globalThis.fetch;
globalThis.fetch = (() => {
  throw new TypeError("fetch failed");
}) as unknown as typeof fetch;
try {
  await me();
  check("dead API raises", false);
} catch (exc) {
  check(
    "dead API is reported as status 0 with actionable text",
    exc instanceof ApiError && exc.status === 0 && /make up/.test(exc.message),
    exc instanceof ApiError ? exc.message : String(exc),
  );
} finally {
  globalThis.fetch = currentFetch;
}

console.log(failures === 0 ? "\nALL CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);

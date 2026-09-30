import { useSession } from "../state/session";

/** One thin fetch wrapper for the whole app. The token is read from the
 * session store (not from React), so every hook — queries, mutations,
 * background refetches — authenticates identically, and a 401 always means
 * the same thing: drop the session, let RequireAuth bounce to /login. */

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/** FastAPI puts the learner-facing message in `detail`; validation errors
 *  arrive as a list — surface the first one, never a JSON dump. */
function readableError(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return humanizeValidation(first.msg);
  }
  return status === 0 ? "Cannot reach the API" : `Request failed (${status})`;
}

function humanizeValidation(msg: string): string {
  if (msg.startsWith("Value error, ")) return msg.slice(13);
  if (msg.includes("field required")) return "Please fill in every required field.";
  return msg.replaceAll("Value error, ", "");
}

/** Reads Vite's env without assuming it exists, so this module also runs
 *  under plain Node/vitest (the parity and contract tests from P1 on). */
const envBase = (import.meta as { env?: Record<string, string | undefined> }).env
  ?.VITE_API_BASE;

export const API_BASE = envBase ?? "/api";

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = auth ? useSession.getState().token : null;
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the API. Is `make up` running?", 0, null);
  }

  if (response.status === 401 && auth) {
    // Expired or forged token: same treatment the Streamlit client gives it.
    useSession.getState().clear();
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = (payload as { detail?: unknown })?.detail ?? payload;
    throw new ApiError(readableError(response.status, detail), response.status, detail);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, opts?: { auth?: boolean }) =>
    request<T>(path, { method: "POST", body, ...opts }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

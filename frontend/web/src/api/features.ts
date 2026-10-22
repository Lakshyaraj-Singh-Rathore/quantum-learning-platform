import { api } from "./client";

/** Map of optional features this deployment has switched on.
 *
 *  Served by the always-mounted `GET /features`, which answers in both flag
 *  states. That matters: a 404 cannot distinguish "the server says off" from
 *  "the request never arrived", so visibility must never be decided by one.
 */
export interface Features {
  qml_enabled: boolean;
}

export function getFeatures(): Promise<Features> {
  return api.get<Features>("/features");
}

/** What to assume when the flag query has not resolved, or failed.
 *
 *  Fail closed: an unreachable backend hides optional features rather than
 *  advertising them. For everyone without the flag this is the normal state,
 *  so it is never surfaced as an error.
 */
export const FEATURES_CLOSED: Features = { qml_enabled: false };

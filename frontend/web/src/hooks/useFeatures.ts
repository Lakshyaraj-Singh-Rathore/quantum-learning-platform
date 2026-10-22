import { useQuery } from "@tanstack/react-query";
import { FEATURES_CLOSED, getFeatures, type Features } from "../api/features";

export const FEATURES_QUERY_KEY = ["features"] as const;

/** Deployment feature flags, fetched once per session.
 *
 *  `staleTime: Infinity` because a flag is a deployment property, not
 *  session state: it cannot change while the tab is open, so re-fetching it
 *  on every mount would be pure noise. One request serves every consumer —
 *  the nav, the command palette and the route guard all read this cache.
 *
 *  Three behaviours this deliberately encodes:
 *
 *  - **No flash.** `enabled` is false until the server says otherwise, so a
 *    gated entry is hidden and then revealed. The opposite order — render,
 *    then retract — makes the UI visibly flicker and, worse, lets someone
 *    click through to a feature that is off.
 *  - **Fail closed, silently.** A failed flag query yields "off". For every
 *    deployment without the feature that is the *normal* state, so it is
 *    never surfaced as an error.
 *  - **`resolved` is exposed separately** so a route guard can distinguish
 *    "still asking" (show nothing) from "answered: off" (show NotFound).
 *    Without it the guard would 404 a legitimate user for a few hundred
 *    milliseconds on every hard refresh.
 */
export function useFeatures(): {
  features: Features;
  resolved: boolean;
  isError: boolean;
} {
  const query = useQuery({
    queryKey: FEATURES_QUERY_KEY,
    queryFn: getFeatures,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });

  return {
    features: query.data ?? FEATURES_CLOSED,
    // An error is a resolved answer: it resolves to "off".
    resolved: !query.isPending,
    isError: query.isError,
  };
}

/** Convenience for the common single-flag read. */
export function useQmlEnabled(): { enabled: boolean; resolved: boolean } {
  const { features, resolved } = useFeatures();
  return { enabled: features.qml_enabled, resolved };
}

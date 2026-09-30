import { api } from "./client";
import type { BackendsResponse } from "./types";

export function backends(): Promise<BackendsResponse> {
  return api.get<BackendsResponse>("/backends");
}

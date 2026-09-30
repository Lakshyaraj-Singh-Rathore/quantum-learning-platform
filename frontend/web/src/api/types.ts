/** Response shapes, mirroring the backend schemas by hand so the SPA has no
 *  codegen build step (the schemas are small and change rarely; FastAPI docs
 *  remain the authority). */

export interface TokenOut {
  access_token: string;
  token_type: string;
  role: string;
  user_id: number;
  email: string;
}

export interface MeOut {
  id: number;
  email: string;
  role: string;
  display_name: string;
  is_active: boolean;
}

export interface RegisterIn {
  email: string;
  password: string;
  display_name?: string;
}

export interface LoginIn {
  email: string;
  password: string;
}

export interface BackendInfo {
  id: string;
  label: string;
  supports: string[];
  available: boolean;
  reason: string;
}

export interface BackendsResponse {
  backends: BackendInfo[];
  limits: Record<string, number>;
}

import { api } from "./client";
import type { LoginIn, MeOut, RegisterIn, TokenOut } from "./types";

export async function login(payload: LoginIn): Promise<TokenOut> {
  return api.post<TokenOut>("/auth/login", payload, { auth: false });
}

export async function register(payload: RegisterIn): Promise<TokenOut> {
  return api.post<TokenOut>("/auth/register", payload, { auth: false });
}

export function me(): Promise<MeOut> {
  return api.get<MeOut>("/auth/me");
}

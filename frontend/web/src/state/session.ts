import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MeOut, TokenOut } from "../api/types";

interface SessionState {
  token: string | null;
  user: MeOut | null;
  setFromToken: (t: TokenOut) => void;
  setUser: (u: MeOut) => void;
  clear: () => void;
}

/** The JWT lives in localStorage exactly as long as it lived in the
 * Streamlit session — no new threat model, no cookies. The bootstrap admin
 * note (docs) still applies: default creds are a dev convenience. */
export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setFromToken: (t) =>
        set({
          token: t.access_token,
          // The login response knows these but not the display name; the
          // shell refreshes from /auth/me right after.
          user: {
            id: t.user_id,
            email: t.email,
            role: t.role,
            display_name: t.email.split("@")[0],
            is_active: true,
          },
        }),
      setUser: (user) => set({ user }),
      clear: () => set({ token: null, user: null }),
    }),
    { name: "ql-session" },
  ),
);

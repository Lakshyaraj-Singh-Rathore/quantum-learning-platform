import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "dark" | "light";

interface ThemeState {
  theme: Theme;
  toggle: () => void;
}

function apply(theme: Theme) {
  // Guarded so the store is importable outside a browser (scripts, tests);
  // index.html already paints the stored theme before first paint, so this
  // is only ever about keeping the DOM in sync with React state.
  if (typeof document === "undefined") return;
  document.documentElement.classList.toggle("dark", theme !== "light");
  document.documentElement.classList.toggle("light", theme === "light");
}

/** Default dark; index.html applies the stored value before first paint,
 * this store keeps the DOM class in sync with React state from then on. */
export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      toggle: () => {
        const next: Theme = get().theme === "dark" ? "light" : "dark";
        apply(next);
        set({ theme: next });
      },
    }),
    {
      name: "ql-theme",
      onRehydrateStorage: () => (state) => {
        if (state) apply(state.theme);
      },
    },
  ),
);

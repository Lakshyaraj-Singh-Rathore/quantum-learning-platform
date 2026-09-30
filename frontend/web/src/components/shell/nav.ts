import {
  Blocks,
  BookOpen,
  Code2,
  FlaskConical,
  Gamepad2,
  LayoutDashboard,
  Trophy,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Which redesign phase takes this page from placeholder to rebuilt —
   * kept in the UI so the parity progress is visible to anyone, not just
   * in docs. */
  phase: string;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/learn", label: "Learn", icon: BookOpen, phase: "P4" },
  { to: "/composer", label: "Composer", icon: Blocks, phase: "P1–P2" },
  { to: "/challenges", label: "Challenges", icon: Trophy, phase: "P5" },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, phase: "P5" },
  { to: "/codelab", label: "Code Lab", icon: Code2, phase: "P3" },
  { to: "/games", label: "Games", icon: Gamepad2, phase: "P6" },
  { to: "/playground", label: "Playground", icon: FlaskConical, phase: "P6" },
];

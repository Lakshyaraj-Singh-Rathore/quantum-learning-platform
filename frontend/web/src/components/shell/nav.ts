import {
  Blocks,
  BookOpen,
  Code2,
  FlaskConical,
  Gamepad2,
  Layers,
  LayoutDashboard,
  Route as RouteIcon,
  Trophy,
  type LucideIcon,
} from "lucide-react";

export type NavSection = "study" | "build" | "practice" | "insights";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  section: NavSection;
}

export const NAV_ITEMS: NavItem[] = [
  // Study
  { to: "/learn", label: "Learn", icon: BookOpen, section: "study" },
  { to: "/curriculum", label: "Curriculum", icon: RouteIcon, section: "study" },
  { to: "/playground", label: "Playground", icon: FlaskConical, section: "study" },

  // Build & Simulate
  { to: "/composer", label: "Composer", icon: Blocks, section: "build" },
  { to: "/qudit-lab", label: "Qudit Lab (Beta)", icon: Layers, section: "build" },
  { to: "/codelab", label: "Code Lab", icon: Code2, section: "build" },

  // Practice
  { to: "/challenges", label: "Challenges", icon: Trophy, section: "practice" },
  { to: "/games", label: "Games", icon: Gamepad2, section: "practice" },

  // Insights
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, section: "insights" },
];

export const NAV_SECTIONS: { id: NavSection; label: string }[] = [
  { id: "study", label: "Study" },
  { id: "build", label: "Build & Simulate" },
  { id: "practice", label: "Practice" },
  { id: "insights", label: "Insights" },
];

import { useMemo } from "react";
import type { Features } from "../../api/features";
import { useFeatures } from "../../hooks/useFeatures";
import {
  Blocks,
  BookOpen,
  BrainCircuit,
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
  /** When set, this entry is only navigable if the named deployment flag is
   *  on. Items without a flag are always present, which is every existing
   *  entry — the shape is additive and changes nothing about them. */
  flag?: keyof Features;
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
  {
    to: "/qml-lab",
    label: "Quantum ML Lab",
    icon: BrainCircuit,
    section: "build",
    flag: "qml_enabled",
  },

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

/** The nav entries this user may actually navigate to.
 *
 *  Flag-gated entries are filtered out until the server has confirmed they
 *  are on. Until then `useFeatures` reports every flag as false, so a gated
 *  item is hidden first and revealed second — never rendered and then taken
 *  away, which would both flicker and briefly offer a dead link.
 *
 *  `NAV_ITEMS` itself is left exported and unfiltered: `TopBar` reads it only
 *  to title the current route, and resolving a title is not the same thing as
 *  advertising a destination.
 */
export function useNavItems(): NavItem[] {
  const { features } = useFeatures();
  return useMemo(
    () => NAV_ITEMS.filter((item) => item.flag === undefined || features[item.flag]),
    [features],
  );
}

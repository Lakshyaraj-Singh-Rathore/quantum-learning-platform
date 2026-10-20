import React from "react";
import { Radio, Activity, Waves, ArrowDownRight, RotateCcw } from "lucide-react";
import { type QuditNoiseConfig } from "../../api/quditLab";
import { Badge, Button } from "../ui";

interface QuditNoisePanelProps {
  dimension: number;
  config: QuditNoiseConfig;
  onChange: (updated: QuditNoiseConfig) => void;
}

export const QuditNoisePanel: React.FC<QuditNoisePanelProps> = ({
  dimension,
  config,
  onChange,
}) => {
  const handleToggleDepol = (enabled: boolean) => {
    onChange({
      ...config,
      depolarizing: { ...config.depolarizing, enabled },
    });
  };

  const handleDepolProb = (p: number) => {
    onChange({
      ...config,
      depolarizing: { ...config.depolarizing, p },
    });
  };

  const handleToggleDephase = (enabled: boolean) => {
    onChange({
      ...config,
      dephasing: { ...config.dephasing, enabled },
    });
  };

  const handleDephaseGamma = (gamma: number) => {
    onChange({
      ...config,
      dephasing: { ...config.dephasing, gamma },
    });
  };

  const handleToggleRelax = (enabled: boolean) => {
    onChange({
      ...config,
      relaxation: { ...config.relaxation, enabled },
    });
  };

  const handleRelaxGamma = (gamma: number) => {
    onChange({
      ...config,
      relaxation: { ...config.relaxation, gamma },
    });
  };

  const handleResetNoise = () => {
    onChange({
      depolarizing: { enabled: false, p: 0.1 },
      dephasing: { enabled: false, gamma: 0.1 },
      relaxation: { enabled: false, gamma: 0.1 },
    });
  };

  const isAnyActive =
    config.depolarizing.enabled || config.dephasing.enabled || config.relaxation.enabled;

  return (
    <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-4 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold tracking-wide text-ink">Generalized Qudit Noise</h2>
          <Badge tone={isAnyActive ? "accent" : "neutral"}>
            {isAnyActive ? "Noise Active" : "Ideal Circuit"}
          </Badge>
        </div>

        {isAnyActive && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetNoise}
            className="text-xs text-ink-3 hover:text-ink"
            aria-label="Disable all noise"
          >
            <RotateCcw className="h-3 w-3 mr-1" />
            Clear Noise
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Depolarizing Channel */}
        <div
          className={`p-3 rounded-lg border transition-all ${
            config.depolarizing.enabled
              ? "border-accent/40 bg-accent/5"
              : "border-line/60 bg-subtle/30 opacity-70"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Radio className="h-3.5 w-3.5 text-accent" />
              <span className="text-xs font-semibold text-ink">Depolarizing</span>
            </div>
            <input
              type="checkbox"
              checked={config.depolarizing.enabled}
              onChange={(e) => handleToggleDepol(e.target.checked)}
              className="accent-accent cursor-pointer"
              aria-label="Toggle depolarizing noise"
            />
          </div>

          <p className="text-[11px] text-ink-3 leading-relaxed mb-3">
            Isotropically contracts state toward maximally mixed state: E(ρ) = (1-p)ρ + (p/{dimension})I.
          </p>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-ink-2">
              <span>Error prob (p):</span>
              <input
                type="number"
                min={0.0}
                max={1.0}
                step={0.01}
                value={config.depolarizing.p}
                disabled={!config.depolarizing.enabled}
                onChange={(e) => handleDepolProb(Math.min(1.0, Math.max(0.0, Number(e.target.value))))}
                className="w-16 px-1.5 py-0.5 rounded bg-subtle border border-line text-right font-mono font-bold text-accent disabled:opacity-40 text-xs"
                aria-label="Depolarizing error probability value"
              />
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.01}
              value={config.depolarizing.p}
              disabled={!config.depolarizing.enabled}
              onChange={(e) => handleDepolProb(Number(e.target.value))}
              className="w-full accent-accent cursor-pointer disabled:opacity-40"
              aria-label="Depolarizing error probability"
            />
          </div>
        </div>

        {/* Dephasing Channel */}
        <div
          className={`p-3 rounded-lg border transition-all ${
            config.dephasing.enabled
              ? "border-accent/40 bg-accent/5"
              : "border-line/60 bg-subtle/30 opacity-70"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Waves className="h-3.5 w-3.5 text-indigo-400" />
              <span className="text-xs font-semibold text-ink">Pure Dephasing</span>
            </div>
            <input
              type="checkbox"
              checked={config.dephasing.enabled}
              onChange={(e) => handleToggleDephase(e.target.checked)}
              className="accent-accent cursor-pointer"
              aria-label="Toggle dephasing noise"
            />
          </div>

          <p className="text-[11px] text-ink-3 leading-relaxed mb-3">
            Damps off-diagonal coherences ρ_jk → (1-γ)ρ_jk while preserving diagonal populations.
          </p>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-ink-2">
              <span>Damping (γ):</span>
              <input
                type="number"
                min={0.0}
                max={1.0}
                step={0.01}
                value={config.dephasing.gamma}
                disabled={!config.dephasing.enabled}
                onChange={(e) => handleDephaseGamma(Math.min(1.0, Math.max(0.0, Number(e.target.value))))}
                className="w-16 px-1.5 py-0.5 rounded bg-subtle border border-line text-right font-mono font-bold text-indigo-400 disabled:opacity-40 text-xs"
                aria-label="Dephasing damping gamma value"
              />
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.01}
              value={config.dephasing.gamma}
              disabled={!config.dephasing.enabled}
              onChange={(e) => handleDephaseGamma(Number(e.target.value))}
              className="w-full accent-indigo-400 cursor-pointer disabled:opacity-40"
              aria-label="Dephasing damping gamma"
            />
          </div>
        </div>

        {/* Multi-level Relaxation */}
        <div
          className={`p-3 rounded-lg border transition-all ${
            config.relaxation.enabled
              ? "border-accent/40 bg-accent/5"
              : "border-line/60 bg-subtle/30 opacity-70"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <ArrowDownRight className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs font-semibold text-ink">Cascade Relaxation</span>
            </div>
            <input
              type="checkbox"
              checked={config.relaxation.enabled}
              onChange={(e) => handleToggleRelax(e.target.checked)}
              className="accent-accent cursor-pointer"
              aria-label="Toggle relaxation noise"
            />
          </div>

          <p className="text-[11px] text-ink-3 leading-relaxed mb-3">
            Models downward energy dissipation |j⟩ → |j-1⟩ with transition rate γ·j/({dimension}-1).
          </p>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono text-ink-2">
              <span>Decay rate (γ):</span>
              <input
                type="number"
                min={0.0}
                max={1.0}
                step={0.01}
                value={config.relaxation.gamma}
                disabled={!config.relaxation.enabled}
                onChange={(e) => handleRelaxGamma(Math.min(1.0, Math.max(0.0, Number(e.target.value))))}
                className="w-16 px-1.5 py-0.5 rounded bg-subtle border border-line text-right font-mono font-bold text-amber-400 disabled:opacity-40 text-xs"
                aria-label="Relaxation decay rate gamma value"
              />
            </div>
            <input
              type="range"
              min={0.0}
              max={1.0}
              step={0.01}
              value={config.relaxation.gamma}
              disabled={!config.relaxation.enabled}
              onChange={(e) => handleRelaxGamma(Number(e.target.value))}
              className="w-full accent-amber-400 cursor-pointer disabled:opacity-40"
              aria-label="Relaxation decay rate gamma"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

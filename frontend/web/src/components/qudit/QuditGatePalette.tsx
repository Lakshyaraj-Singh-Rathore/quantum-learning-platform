import React from "react";
import { Sparkles, Plus } from "lucide-react";
import { type QuditGateCatalogueItem } from "../../api/quditLab";
import { Badge, Tooltip } from "../ui";

interface QuditGatePaletteProps {
  dimension: number;
  catalogue: QuditGateCatalogueItem[];
  onAddGate: (gateId: string) => void;
  disabled?: boolean;
}

export const QuditGatePalette: React.FC<QuditGatePaletteProps> = ({
  dimension,
  catalogue,
  onAddGate,
  disabled = false,
}) => {
  return (
    <div className="rounded-xl border border-line bg-card/60 backdrop-blur-md p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold tracking-wide text-ink">Gate Palette</h2>
          <Badge tone="accent">
            d = {dimension}
          </Badge>
        </div>
        <span className="text-xs text-ink-3">Click gate to append to circuit</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
        {catalogue.map((gate) => {
          const isTwoQudit = gate.is_two_qudit;
          const displaySymbol = gate.symbol.replace("_d", `_${dimension}`);

          return (
            <Tooltip
              key={gate.id}
              content={
                <div className="max-w-xs space-y-1.5 p-1 text-left">
                  <div className="font-semibold text-accent">{gate.name}</div>
                  <div className="text-xs text-ink-2 font-mono bg-bg/80 p-1.5 rounded border border-line">
                    {gate.latex}
                  </div>
                  <div className="text-xs text-ink-3">{gate.description}</div>
                  {isTwoQudit && (
                    <div className="text-[10px] text-amber-400 font-medium">
                      Requires 2 qudits (control + target)
                    </div>
                  )}
                </div>
              }
            >
              <button
                type="button"
                onClick={() => onAddGate(gate.id)}
                disabled={disabled}
                className="group relative flex flex-col items-center justify-center p-3 rounded-xl border border-line/80 bg-subtle/50 hover:bg-accent/10 hover:border-accent/40 active:scale-95 transition-all duration-150 disabled:opacity-40 disabled:pointer-events-none"
                aria-label={`Add ${gate.name} gate`}
              >
                <div className="text-base font-bold font-mono text-ink group-hover:text-accent tracking-wider">
                  {displaySymbol}
                </div>
                {/* The full name is what distinguishes these tiles. Truncating
                    to one 85px line rendered four of the seven gates as the
                    identical string "Generalized …", so the subtitle told the
                    student nothing. Wrap to two lines instead. */}
                <div className="mt-0.5 w-full px-0.5 text-center text-[11px] leading-tight text-ink-3 group-hover:text-ink-2">
                  {gate.name.split("(")[0].trim()}
                </div>

                <div className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Plus className="h-3 w-3 text-accent" />
                </div>
              </button>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
};

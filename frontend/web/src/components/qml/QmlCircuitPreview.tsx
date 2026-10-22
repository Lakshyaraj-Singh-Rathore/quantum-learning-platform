/* View B — Circuit.
 *
 * Reuses `components/results/CircuitDiagram.tsx` rather than drawing a second
 * circuit renderer: the lab's circuits must look like every other circuit in
 * the product, and a parallel renderer would drift. All this component does
 * is turn a config into the IR that diagram already consumes.
 */
import { useMemo } from "react";
import { CircuitDiagram } from "../results/CircuitDiagram";
import { Badge, Card } from "../ui";
import type { CircuitConfig } from "../../api/qml";
import { buildQmlCircuitIr, entanglerPairs, parameterCount } from "./circuitIr";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-subtle/50 px-3 py-2">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-ink-3">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{value}</dd>
    </div>
  );
}

export function QmlCircuitPreview({
  circuit,
  nFeatures,
  /** The server's own structural summary, when a run has produced one.
   *  Shown beside the derived figures so a drift between this preview and
   *  the backend ansatz is visible rather than silent. */
  serverParameters,
}: {
  circuit: CircuitConfig;
  nFeatures: number;
  serverParameters?: number;
}) {
  const ir = useMemo(
    () => buildQmlCircuitIr(circuit, nFeatures),
    [circuit, nFeatures],
  );

  const entanglers = entanglerPairs(circuit.n_qubits, circuit.entanglement).length;
  const nParams = parameterCount(circuit.n_qubits, circuit.n_layers);
  const drift = serverParameters !== undefined && serverParameters !== nParams;
  const idle = Math.max(0, circuit.n_qubits - nFeatures);

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-ink">Ansatz</h3>
          <div className="flex items-center gap-2">
            <Badge tone="neutral">{circuit.entanglement}</Badge>
            <Badge tone="accent">{`R${circuit.rotation} encoding`}</Badge>
          </div>
        </header>

        <div className="overflow-x-auto rounded-xl border border-line bg-bg/40 p-3">
          <CircuitDiagram ir={ir} />
        </div>

        <p className="text-[11px] leading-relaxed text-ink-3">
          Structure only — the rotation angles shown are not the trained weights.
          {circuit.rotation === "Z" && " The Hadamards precede RZ encoding so the feature is not lost to a global phase."}
          {idle > 0 &&
            ` ${idle} wire${idle === 1 ? "" : "s"} beyond the ${nFeatures} features start in |0⟩ and act as ancillas the entangler mixes in.`}
        </p>
      </Card>

      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Qubits" value={circuit.n_qubits} />
        <Stat label="Layers" value={circuit.n_layers} />
        <Stat label="Entanglers / layer" value={entanglers} />
        <Stat label="Parameters" value={nParams} />
      </dl>

      {drift && (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-2.5 text-xs font-medium text-danger">
          This preview derives {nParams} parameters but the server reported{" "}
          {serverParameters}. The drawing no longer matches the circuit that ran —
          trust the server figure.
        </p>
      )}
    </div>
  );
}

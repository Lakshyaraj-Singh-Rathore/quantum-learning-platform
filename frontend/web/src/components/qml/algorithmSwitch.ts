/* What happens to a config when the user changes algorithm.
 *
 * Extracted from the form as a pure function for one reason: it is the part
 * most likely to be wrong and the part hardest to see. Radix renders Select
 * items in a portal, so an SSR harness cannot observe which options a form
 * offers — asserting on the markup would be asserting on nothing. A pure
 * function can be called directly with all 16 algorithm/dataset combinations.
 *
 * The rule it enforces: there are 4 algorithms x 3 datasets = 12 valid pairs,
 * and a user who picks `sine` and then switches back to the VQC has built one
 * of the 4 invalid ones. The server answers that with a 422 the user cannot
 * act on, so the client resets the selection instead.
 */
import type { AlgorithmInfo, DatasetName, QmlConfig } from "../../api/qml";

function clamp(value: number, bound?: { min: number; max: number }): number {
  if (!bound) return value;
  return Math.min(Math.max(value, bound.min), bound.max);
}

/** The config the form should hold after switching to `next`.
 *
 * - An incompatible dataset is replaced by the new algorithm's first one.
 * - A compatible dataset is kept, so switching VQC → kernel on `moons` does
 *   not silently move the user off the data they chose.
 * - Numeric fields are clamped into the **new** algorithm's ceilings, which
 *   differ per algorithm (§2C.3): the kernel's sample cap is lower, so a
 *   config built for the VQC would otherwise submit over it.
 * - `n_hidden` is added only when the new algorithm supports it and removed
 *   when it does not — the server config model is `extra="forbid"`, so a
 *   stray `n_hidden` is a 422 in itself.
 */
export function nextConfigForAlgorithm(config: QmlConfig, next: AlgorithmInfo): QmlConfig {
  const keepDataset = next.datasets.some((d) => d.name === config.dataset.name);
  const datasetName = (keepDataset ? config.dataset.name : next.datasets[0]?.name) as
    | DatasetName
    | undefined;
  const chosen = next.datasets.find((d) => d.name === datasetName);

  const circuit = { ...config.circuit };
  if (next.supports.n_hidden) {
    circuit.n_hidden = circuit.n_hidden ?? next.limits.n_hidden?.default ?? 4;
  } else {
    delete circuit.n_hidden;
  }
  circuit.n_qubits = clamp(circuit.n_qubits, next.limits.n_qubits);
  circuit.n_layers = clamp(circuit.n_layers, next.limits.n_layers);

  // Angle encoding needs one wire per feature, and the regression sets have
  // fewer features than the classification ones. Raising (never lowering)
  // keeps a switch from producing a config the encoder rejects.
  if (chosen && chosen.n_features > circuit.n_qubits) {
    circuit.n_qubits = clamp(chosen.n_features, next.limits.n_qubits);
  }

  const training = { ...config.training };
  training.epochs = clamp(training.epochs, next.limits.epochs);
  training.batch_size = clamp(training.batch_size, next.limits.batch_size);

  // The per-algorithm sample ceiling wins over both the dataset's own cap
  // and whatever the user had typed.
  const sampleCap = Math.min(
    next.limits.n_samples?.max ?? Number.POSITIVE_INFINITY,
    chosen?.max_samples ?? Number.POSITIVE_INFINITY,
  );
  const sampleFloor = next.limits.n_samples?.min ?? 0;

  return {
    ...config,
    algorithm: next.name,
    dataset: {
      ...config.dataset,
      name: datasetName ?? config.dataset.name,
      n_samples: Math.max(sampleFloor, Math.min(config.dataset.n_samples, sampleCap)),
    },
    circuit,
    training,
  };
}

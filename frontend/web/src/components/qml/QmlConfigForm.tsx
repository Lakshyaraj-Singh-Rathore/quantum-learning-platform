/* View A — Configuration.
 *
 * Every bound comes from `GET /qml/describe`, never from a constant in this
 * file. Duplicating the limits here would create a second source of truth
 * that silently rots the moment Phase 4 tunes one from measured data; worse,
 * a client-side bound that is *looser* than the server's turns a clear 422
 * into a confusing one. The server re-validates regardless — this is a
 * convenience, not a gate.
 */
import { useMemo } from "react";
import {
  Button,
  Card,
  ErrorNote,
  Input,
  Label,
  Select,
  SelectItem,
  Spinner,
} from "../ui";
import {
  type AlgorithmInfo,
  type AlgorithmName,
  type DatasetName,
  type DiffMethod,
  type Entanglement,
  type QmlConfig,
  type QmlDescribe,
  type Rotation,
} from "../../api/qml";
import { parameterCount } from "./circuitIr";
import { nextConfigForAlgorithm } from "./algorithmSwitch";

/** One numeric field, bounded by the server's own range. */
function NumberField({
  id,
  label,
  hint,
  value,
  range,
  step = 1,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  hint?: string;
  value: number;
  range?: { min: number; max: number };
  step?: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const out = range !== undefined && (value < range.min || value > range.max);
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="number"
        value={String(value)}
        min={range?.min}
        max={range?.max}
        step={step}
        disabled={disabled}
        aria-invalid={out || undefined}
        aria-describedby={`${id}-hint`}
        onChange={(e) => {
          const next = Number(e.target.value);
          if (Number.isFinite(next)) onChange(next);
        }}
      />
      <p
        id={`${id}-hint`}
        className={out ? "text-[11px] text-danger" : "text-[11px] text-ink-3"}
      >
        {/* `/qml/describe` publishes bounds for the circuit and training
            sizes but not for learning rate, noise, test fraction or seed.
            Those say so rather than showing a blank line, because the
            absence of a number should not read as "anything goes" — the
            server still rejects an out-of-range value. */}
        {range ? `${range.min}–${range.max}` : "validated on submit"}
        {hint ? " · " : ""}
        {hint}
      </p>
    </div>
  );
}

export function QmlConfigForm({
  config,
  onChange,
  describe,
  describeError,
  onSubmit,
  submitting,
  submitError,
  disabled,
}: {
  config: QmlConfig;
  onChange: (c: QmlConfig) => void;
  describe: QmlDescribe | undefined;
  describeError: Error | null;
  onSubmit: () => void;
  submitting: boolean;
  submitError: Error | null;
  disabled: boolean;
}) {
  // The selected algorithm's own table, not the flat one. §2C.3 gives the
  // kernel a lower sample cap, and it has to appear the moment the kernel is
  // picked -- a form bounded by the global maximum would let a user build a
  // config the server then rejects.
  const algorithm: AlgorithmInfo | undefined = useMemo(
    () => describe?.algorithms.find((a) => a.name === config.algorithm),
    [describe, config.algorithm],
  );
  const limits = algorithm?.limits ?? describe?.limits;
  const range = (key: string) =>
    limits?.[key] ? { min: limits[key].min, max: limits[key].max } : undefined;

  // Datasets are the selected algorithm's, so a classification set is never
  // offered for a regressor (and vice versa). The 12 valid pairs are the
  // server's; the client just renders them.
  const datasetOptions = algorithm?.datasets ?? describe?.datasets ?? [];

  const dataset = useMemo(
    () => datasetOptions.find((d) => d.name === config.dataset.name),
    [datasetOptions, config.dataset.name],
  );

  const supports = algorithm?.supports;

  // The one cross-field rule the schema cannot express as a bound: angle
  // encoding needs a wire per feature (`encoder.py:21-28`). Catching it here
  // turns a 422 after submit into a warning before it.
  const tooFewQubits =
    dataset !== undefined && dataset.n_features > config.circuit.n_qubits;

  const nParams = parameterCount(config.circuit.n_qubits, config.circuit.n_layers);

  const set = <K extends keyof QmlConfig>(key: K, value: QmlConfig[K]) =>
    onChange({ ...config, [key]: value });

  /** Switching algorithm can strand the form on a dataset the new algorithm
   *  cannot accept. The rule lives in `algorithmSwitch.ts` as a pure
   *  function so it can be tested against all 16 combinations directly --
   *  Radix renders Select items in a portal, so an SSR harness cannot see
   *  which options this form offers. */
  const selectAlgorithm = (name: AlgorithmName) => {
    const next = describe?.algorithms.find((a) => a.name === name);
    if (next) onChange(nextConfigForAlgorithm(config, next));
  };

  if (describeError) {
    return (
      <ErrorNote>
        Could not load the experiment limits: {describeError.message}. The form stays
        disabled rather than guessing bounds the server would reject.
      </ErrorNote>
    );
  }

  if (!describe) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-ink-3">
        <Spinner /> Loading limits…
      </div>
    );
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <Card className="space-y-4">
        <header className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Algorithm</h3>
          {algorithm && (
            <span className="text-[11px] uppercase tracking-wider text-ink-3">
              {algorithm.task}
            </span>
          )}
        </header>

        <div className="space-y-1">
          <Label htmlFor="qml-algorithm">Model</Label>
          <Select
            value={config.algorithm}
            onValueChange={(v) => selectAlgorithm(v as AlgorithmName)}
            disabled={disabled}
          >
            {describe.algorithms.map((a) => (
              <SelectItem key={a.name} value={a.name}>
                {a.label}
              </SelectItem>
            ))}
          </Select>
          <p className="text-[11px] leading-relaxed text-ink-3">
            {algorithm?.summary ?? "Select a model."}
          </p>
        </div>
      </Card>

      <Card className="space-y-4">
        <header className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Dataset</h3>
          <span className="text-[11px] text-ink-3">
            {dataset ? `${dataset.n_features} features` : ""}
          </span>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor="qml-dataset">Source</Label>
            <Select
              value={config.dataset.name}
              onValueChange={(v) =>
                set("dataset", { ...config.dataset, name: v as DatasetName })
              }
              disabled={disabled}
            >
              {datasetOptions.map((d) => (
                <SelectItem key={d.name} value={d.name}>
                  {d.name}
                </SelectItem>
              ))}
            </Select>
            <p className="text-[11px] text-ink-3">
              {dataset?.required_angle_frequency != null
                ? `Needs angle frequency ${dataset.required_angle_frequency}; re-uploading supplies it.`
                : "Generated locally, seeded."}
            </p>
          </div>

          <NumberField
            id="qml-n-samples"
            label="Samples"
            value={config.dataset.n_samples}
            range={range("n_samples")}
            step={50}
            disabled={disabled}
            hint={dataset ? `max ${dataset.max_samples} for this set` : undefined}
            onChange={(v) => set("dataset", { ...config.dataset, n_samples: v })}
          />

          <NumberField
            id="qml-noise"
            label="Noise"
            value={config.dataset.noise}
            range={range("noise")}
            step={0.05}
            disabled={disabled}
            hint="label overlap"
            onChange={(v) => set("dataset", { ...config.dataset, noise: v })}
          />

          <NumberField
            id="qml-test-fraction"
            label="Test fraction"
            value={config.dataset.test_fraction}
            range={range("test_fraction")}
            step={0.05}
            disabled={disabled}
            hint="held out before scaling"
            onChange={(v) => set("dataset", { ...config.dataset, test_fraction: v })}
          />
        </div>
      </Card>

      <Card className="space-y-4">
        <header className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Circuit</h3>
          <span className="text-[11px] tabular-nums text-ink-3">
            {nParams} parameters
          </span>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            id="qml-n-qubits"
            label="Qubits"
            value={config.circuit.n_qubits}
            range={range("n_qubits")}
            disabled={disabled}
            onChange={(v) => set("circuit", { ...config.circuit, n_qubits: v })}
          />

          <NumberField
            id="qml-n-layers"
            label="Layers"
            value={config.circuit.n_layers}
            range={range("n_layers")}
            disabled={disabled}
            hint="RY+RZ then entangler"
            onChange={(v) => set("circuit", { ...config.circuit, n_layers: v })}
          />

          <div className="space-y-1">
            <Label htmlFor="qml-rotation">Encoding axis</Label>
            <Select
              value={config.circuit.rotation}
              onValueChange={(v) =>
                set("circuit", { ...config.circuit, rotation: v as Rotation })
              }
              disabled={disabled}
            >
              {describe.rotations.map((r) => (
                <SelectItem key={r} value={r}>
                  {`R${r}`}
                </SelectItem>
              ))}
            </Select>
            <p className="text-[11px] text-ink-3">
              {config.circuit.rotation === "Z"
                ? "Hadamard first, or RZ on |0⟩ is a global phase"
                : "one rotation per feature"}
            </p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="qml-entanglement">Entanglement</Label>
            <Select
              value={config.circuit.entanglement}
              onValueChange={(v) =>
                set("circuit", { ...config.circuit, entanglement: v as Entanglement })
              }
              disabled={disabled}
            >
              {describe.entanglements.map((e) => (
                <SelectItem key={e} value={e}>
                  {e}
                </SelectItem>
              ))}
            </Select>
            <p className="text-[11px] text-ink-3">CNOT topology per layer</p>
          </div>
        </div>

        {supports?.n_hidden && (
          <NumberField
            id="qml-n-hidden"
            label="Hidden units"
            value={config.circuit.n_hidden ?? limits?.n_hidden?.default ?? 4}
            range={range("n_hidden")}
            disabled={disabled}
            hint="classical layer before the circuit"
            onChange={(v) => set("circuit", { ...config.circuit, n_hidden: v })}
          />
        )}

        {tooFewQubits && (
          <ErrorNote>
            Angle encoding needs one wire per feature: {dataset?.name} has{" "}
            {dataset?.n_features} features but the circuit has {config.circuit.n_qubits}{" "}
            qubits. Raise the qubit count to at least {dataset?.n_features}.
          </ErrorNote>
        )}
      </Card>

      <Card className="space-y-4">
        <h3 className="text-sm font-semibold text-ink">Training</h3>

        {/* `supports.epochs`, never a name check. An algorithm with no
            training loop gets no epoch, batch-size or learning-rate control,
            because none of them would do anything -- showing a disabled
            slider would still imply the knob is meaningful here. */}
        {supports?.epochs === false && (
          <p className="text-[11px] leading-relaxed text-ink-3">
            This algorithm has no training loop. It builds the kernel matrix and solves one linear
            system, so there are no epochs, no batches and no learning rate to set. Sample count
            dominates its cost: the matrix grows as n².
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {supports?.epochs !== false && (
            <>
              <NumberField
                id="qml-epochs"
                label="Epochs"
                value={config.training.epochs}
                range={range("epochs")}
                disabled={disabled}
                onChange={(v) => set("training", { ...config.training, epochs: v })}
              />

              <NumberField
                id="qml-batch-size"
                label="Batch size"
                value={config.training.batch_size}
                range={range("batch_size")}
                disabled={disabled}
                hint="cancellation is checked per batch"
                onChange={(v) => set("training", { ...config.training, batch_size: v })}
              />

              <NumberField
                id="qml-learning-rate"
                label="Learning rate"
                value={config.training.learning_rate}
                range={range("learning_rate")}
                step={0.01}
                disabled={disabled}
                onChange={(v) => set("training", { ...config.training, learning_rate: v })}
              />
            </>
          )}

          {supports?.diff_method !== false && (
            <div className="space-y-1">
              <Label htmlFor="qml-diff-method">Gradient</Label>
              <Select
                value={config.training.diff_method}
                onValueChange={(v) =>
                  set("training", { ...config.training, diff_method: v as DiffMethod })
                }
                disabled={disabled}
              >
                {describe.diff_methods.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </Select>
              <p className="text-[11px] text-ink-3">
                {config.training.diff_method === "backprop"
                  ? "fast; simulator only"
                  : "hardware-compatible, 2 evaluations per parameter"}
              </p>
            </div>
          )}

          <NumberField
            id="qml-seed"
            label="Seed"
            value={config.seed}
            range={range("seed")}
            disabled={disabled}
            hint="same seed ⇒ same run"
            onChange={(v) => set("seed", v)}
          />
        </div>

        {supports?.data_reuploading && (
          <p className="text-[11px] leading-relaxed text-ink-3">
            Data re-uploading is on: the input is re-encoded before every layer, which raises the
            reachable Fourier frequency. Without it a single encoding caps the model at frequency
            1 and these targets are unreachable.
          </p>
        )}
      </Card>

      {submitError && (
        <ErrorNote>The server rejected this configuration: {submitError.message}</ErrorNote>
      )}

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={disabled || submitting || tooFewQubits}>
          {submitting ? "Submitting…" : "Train model"}
        </Button>
        <p className="text-[11px] text-ink-3">
          {describe.max_concurrent_experiments === 1
            ? "One experiment runs at a time."
            : `Up to ${describe.max_concurrent_experiments} run at a time.`}{" "}
          Device: {describe.device}.
        </p>
      </div>
    </form>
  );
}

# Quantum Gates

Quantum gates are **unitary** matrices: they are reversible and they preserve total
probability. Unitarity ($U^\dagger U = I$) is why every gate in the palette (except
measure and reset) has an inverse.

## Single-qubit gates

| Gate | Effect | Matrix intuition |
|------|--------|------------------|
| **X** | Bit flip, the quantum NOT | swaps $|0\rangle \leftrightarrow |1\rangle$ |
| **Y** | Bit + phase flip | $X$ and $Z$ combined, with an $i$ |
| **Z** | Phase flip | leaves $|0\rangle$, sends $|1\rangle \to -|1\rangle$ |
| **H** | Hadamard | creates superposition; maps Z-basis to X-basis |
| **S**, **Sdg** | Quarter turn | phase of $\pm i$ on $|1\rangle$ |
| **T**, **Tdg** | Eighth turn | phase of $e^{\pm i\pi/4}$ on $|1\rangle$ |
| **SX** | Square root of X | half a bit flip |
| **I** | Identity | does nothing (useful as a placeholder/delay) |

The Hadamard is the workhorse:

$$H|0\rangle = \frac{|0\rangle + |1\rangle}{\sqrt2}, \qquad H|1\rangle = \frac{|0\rangle - |1\rangle}{\sqrt2}$$

Note that $H|1\rangle$ carries a **minus sign**. Applying $H$ twice returns the original
state ($H^2 = I$) precisely because of that sign - the two paths interfere.

## Rotation and phase gates

**RX($\theta$)**, **RY($\theta$)** and **RZ($\theta$)** rotate the Bloch vector by
$\theta$ radians about the X, Y and Z axes. **P($\lambda$)** applies a relative phase
$e^{i\lambda}$ to $|1\rangle$ only.

Useful special cases: $Z = P(\pi)$, $S = P(\pi/2)$, $T = P(\pi/4)$.

### Parameter entry in this platform

Parameters accept numeric radians or symbolic expressions built **only** from `pi`,
numbers and `+ - * / ( )`. Examples: `pi/2`, `3*pi/4`, `-0.5*pi`, `1.234`.
Free variables such as `theta` are rejected, because every circuit must be numerically
executable the moment you press Run.

## Multi-qubit gates

- **CNOT / CX**: flips the target iff the control is $|1\rangle$. This is the standard
  entangling gate.
- **CZ**: applies a phase of $-1$ only to $|11\rangle$. Symmetric in its two qubits.
- **SWAP**: exchanges two qubits.
- **Toffoli / CCX**: flips the target iff *both* controls are $|1\rangle$. Universal for
  classical reversible computation.
- **MCX**: the general multi-controlled X with any number of controls.

### How controls work in the composer

Drop the gate on its **target** qubit, then click the qubits in the same column that
should act as **controls**. The editor draws the control dots and the vertical connector.
Internally every controlled gate is stored as a base gate plus a list of control qubits,
so `cx`, `ccx` and a 5-controlled X are all the same structure.

Multi-controlled gates are convenient but expensive: after transpilation to a hardware
basis, an MCX with many controls becomes a long sequence of two-qubit gates.

## Universality and transpilation

A small set of gates - for example $\{H, T, \text{CNOT}\}$ - is **universal**: it can
approximate any unitary to arbitrary accuracy. Real hardware exposes only its own native
set, so a compiler must rewrite your circuit.

This platform transpiles every static circuit to the portable basis
**`rx, ry, rz, cx`** before handing it to Cirq, PennyLane or qBraid. That guarantees all
backends execute the *same* normalized program, which is why their histograms agree.

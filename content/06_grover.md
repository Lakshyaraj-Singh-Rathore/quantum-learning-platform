# Grover's Search Algorithm

Grover's algorithm finds a marked item in an unstructured database of $N$ items
using $O(\sqrt{N})$ queries, versus $O(N)$ classically. It is a **quadratic**
speed-up, and it is provably optimal for unstructured search. It is also the
second place where phase kickback — which you met in
**[Deutsch-Jozsa](05_deutsch_jozsa.md)** — does the real work.

## Learning objectives

By the end of this lesson you should be able to:

- **State** Grover's query complexity and its classical counterpart.
- **Describe** the oracle and the diffuser, and explain what each one does to the
  amplitudes.
- **Explain** why the two reflections compose into a rotation.
- **Compute** the optimal iteration count and predict what over-rotation does.
- **Construct** a working two-qubit Grover circuit and verify its output.

## Setup

With $n$ qubits we have $N = 2^n$ basis states. We want the marked state
$|w\rangle$.

**Step 0.** Apply H to every qubit to build the uniform superposition

$$|s\rangle = \frac{1}{\sqrt N}\sum_{x=0}^{N-1}|x\rangle$$

Every item currently has amplitude $1/\sqrt{N}$. Note what this means: at this
point measuring gives you the answer with probability $1/N$, no better than
guessing. Superposition alone has bought you nothing — exactly as in
Deutsch-Jozsa.

## The Grover iteration

Each iteration has two parts.

**1. The oracle $U_w$** flips the *phase* of the marked state:

$$U_w|x\rangle = \begin{cases} -|x\rangle & x = w \\ |x\rangle & \text{otherwise}\end{cases}$$

For $n=2$ marking $|11\rangle$, the oracle is simply a **CZ** gate.

The oracle is a **reflection about the hyperplane perpendicular to** $|w\rangle$.
Flipping the sign of one component while leaving every other component alone is
exactly that geometric operation.

**2. The diffuser** reflects all amplitudes about their mean:

$$U_s = 2|s\rangle\langle s| - I$$

In gates: H on all qubits, X on all qubits, a multi-controlled Z, X on all, H on
all.

The marked amplitude was pushed below the mean by the oracle, so reflecting about
the mean pushes it *up*. This is **amplitude amplification**.

## Geometry

Two reflections compose into a **rotation**. Applied in sequence, $U_s U_w$
rotates the state by angle

$$\theta = 2\arcsin\!\left(\frac{1}{\sqrt N}\right)$$

toward $|w\rangle$, in the plane spanned by $|w\rangle$ and the uniform
superposition of the non-solutions. Every iteration advances the same amount.

The optimal number of iterations is

$$k \approx \frac{\pi}{4}\sqrt{N}$$

which is where the rotation lands as close to $|w\rangle$ as it ever gets.

## Do not over-rotate

Because it is a rotation, **more iterations is not better**. Run past the optimum
and you rotate away from the answer and the success probability falls again.
Grover's algorithm is periodic, and this surprises people the first time they see
it.

Verified for $N = 4$ over 2048 shots, seed 1234:

| Iterations | Result |
|------------|--------|
| 1 (optimal) | `{'11': 2048}` — **100% success** |
| 2 (over-rotated) | `{'00': 530, '01': 501, '10': 517, '11': 500}` — back to uniform |

Two iterations undid everything. This is not noise; it is the rotation
continuing past the target.

## The two-qubit case

For $N = 4$ with one marked item, $\theta = 2\arcsin(1/2) = 60°$, and a *single*
iteration rotates the state exactly onto $|w\rangle$. You find the answer with
**probability 1** in one query.

Circuit for marking $|11\rangle$:

1. H q0, H q1
2. Oracle: CZ q0, q1
3. Diffuser: H q0, H q1 → X q0, X q1 → CZ q0, q1 → X q0, X q1 → H q0, H q1
4. Measure both

Verified result: `{'11': 2048}` — the marked state, every time.

### Building CZ from the palette

If you only have CX, note that $CZ = (I \otimes H)\,CX\,(I \otimes H)$: put an H
on the target before and after the CX. Verified: the two constructions give
identical matrices.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0, `seed_simulator=1234`:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Operator

sim = AerSimulator()

def run(qc, shots=2048):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

def grover(n_qubits, marked, iterations):
    """`marked` is a bitstring in Qiskit display order: qubit 0 is RIGHTMOST."""
    zeros = [n_qubits - 1 - i for i, bit in enumerate(marked) if bit == "0"]
    qc = QuantumCircuit(n_qubits, n_qubits)
    qc.h(range(n_qubits))              # uniform superposition
    for _ in range(iterations):
        # oracle: phase-flip the marked state with a multi-controlled Z
        if zeros:
            qc.x(zeros)                # surround with X to mark |0> bits too
        qc.h(n_qubits - 1)
        qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
        if zeros:
            qc.x(zeros)
        # diffuser: H, X, MCZ, X, H
        qc.h(range(n_qubits))
        qc.x(range(n_qubits))
        qc.h(n_qubits - 1)
        qc.mcx(list(range(n_qubits - 1)), n_qubits - 1)
        qc.h(n_qubits - 1)
        qc.x(range(n_qubits))
        qc.h(range(n_qubits))
    qc.measure(range(n_qubits), range(n_qubits))
    return run(qc)

print("N=4, mark |11>, 1 iteration :", grover(2, "11", 1))   # {'11': 2048}
print("N=4, mark |11>, 2 iterations:", grover(2, "11", 2))   # ~uniform
print("N=4, mark |01>, 1 iteration :", grover(2, "01", 1))   # {'01': 2048}
print("theta = 2 arcsin(1/2) =", np.degrees(2 * np.arcsin(1 / 2)), "deg")

# CZ == (I x H) CX (I x H)
a = QuantumCircuit(2); a.cz(0, 1)
b = QuantumCircuit(2); b.h(1); b.cx(0, 1); b.h(1)
print("CZ == (I x H) CX (I x H):", np.allclose(Operator(a).data, Operator(b).data))
```

**Try it.** In the Composer: **H** on q0 and q1, then **CZ** (or H–CNOT–H) as
the oracle, then the diffuser, then measure all. With the marked state $|11\rangle$
you should see only `11`. Add a second full iteration and watch the advantage
disappear.

## Common misconceptions

- **"Grover searches by trying all $N$ items at once."** Superposition alone
  gives probability $1/N$, which is guessing. The amplification is what does the
  work, and it requires $O(\sqrt{N})$ iterations.
- **"More iterations keeps helping."** It is a rotation. Two iterations on $N=4$
  returns you to uniform — verified above.
- **"The quadratic speed-up breaks cryptography."** It halves the effective key
  length (AES-256 → 2^128 Grover steps), which doubling the key fixes. Shor's
  exponential speed-up is the one that breaks public-key crypto.
- **"The oracle is a database lookup."** It is a reversible phase-flip; it does
  not scan anything.

## Exercises

**1.** What is the optimal iteration count for $N = 1024$?

**2.** For $N = 4$, what is $\theta$ in degrees, and why does one iteration give
certainty?

**3.** Explain in one sentence why two reflections make a rotation.

**4.** You run Grover with $N = 16$ and 5 iterations and get poor results. What
is the likely cause?

**5.** How would you mark $|01\rangle$ rather than $|11\rangle$ in the two-qubit
circuit?

### Answers

**1.** $k \approx \tfrac{\pi}{4}\sqrt{1024} = \tfrac{\pi}{4}\cdot 32 \approx 25.1$,
so **25 iterations**.

**2.** $\theta = 2\arcsin(1/2) = 60°$. Starting from the uniform state, the
initial angle to $|w\rangle$ is $90° - \theta/2 = 60°$, so a single $60°$
rotation lands exactly on $|w\rangle$ — giving probability 1 in one query.

**3.** In the plane spanned by the two reflections' axes, reflecting about one
line and then another is a rotation by twice the angle between them.

**4.** You over-rotated. The optimum is $\tfrac{\pi}{4}\sqrt{16} \approx 3.14$,
so 3 iterations is right; 5 has rotated past the target.

**5.** Surround the CZ with X gates on the qubits whose marked bit is 0 — here
X on q0 before the CZ, and X on q0 after it. This maps $|01\rangle$ to $|11\rangle$,
applies the CZ, and maps back. Verified: `grover(2, "01", 1)` returns
`{'01': 2048}`.

## Summary

- Grover finds a marked item in $O(\sqrt{N})$ queries versus $O(N)$
  classically, and is provably optimal for unstructured search.
- The oracle phase-flips the marked state; the diffuser reflects amplitudes about
  their mean.
- Together they rotate by $\theta = 2\arcsin(1/\sqrt{N})$ per iteration.
- Optimal iterations $k \approx \tfrac{\pi}{4}\sqrt{N}$; over-rotating undoes the
  advantage.
- For $N = 4$, one iteration succeeds with probability 1.
- $CZ = (I \otimes H)\,CX\,(I \otimes H)$.

Next, **[Variational Algorithms](07_vqe_qaoa.md)** turns to the noisy,
shallow-circuit regime.

## References

- Grover, L. K. "A fast quantum mechanical algorithm for database search", in
  *Proceedings of the 28th Annual ACM Symposium on Theory of Computing* (1996)
  212.
- Bennett, C. H., Bernstein, E., Brassard, G. & Vazirani, U. "Strengths and
  weaknesses of quantum computing", *SIAM Journal on Computing* 26 (1997) 1510 —
  the optimality proof.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §6.1–6.2.
- Qiskit documentation, "Grover's algorithm": https://docs.quantum.ibm.com/

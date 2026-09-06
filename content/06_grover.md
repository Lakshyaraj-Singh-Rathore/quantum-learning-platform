# Grover's Search Algorithm

Grover's algorithm finds a marked item in an unstructured database of $N$ items using
$O(\sqrt{N})$ queries, versus $O(N)$ classically. It is a **quadratic** speed-up, and it
is provably optimal for unstructured search.

## Setup

With $n$ qubits we have $N = 2^n$ basis states. We want the marked state $|w\rangle$.

**Step 0.** Apply H to every qubit to build the uniform superposition
$$|s\rangle = \frac{1}{\sqrt N}\sum_{x=0}^{N-1}|x\rangle$$
Every item currently has amplitude $1/\sqrt{N}$.

## The Grover iteration

Each iteration has two parts.

**1. The oracle $U_w$** flips the *phase* of the marked state:
$$U_w|x\rangle = \begin{cases} -|x\rangle & x = w \\ |x\rangle & \text{otherwise}\end{cases}$$
For $n=2$ marking $|11\rangle$, the oracle is simply a **CZ** gate.

**2. The diffuser** reflects all amplitudes about their mean:
$$U_s = 2|s\rangle\langle s| - I$$
In gates: H on all qubits, X on all qubits, a multi-controlled Z, X on all, H on all.

The marked amplitude was pushed below the mean by the oracle, so reflecting about the mean
pushes it *up*. This is **amplitude amplification**.

## Geometry

The two reflections compose into a **rotation** by angle
$\theta = 2\arcsin(1/\sqrt N)$ toward $|w\rangle$ in the plane spanned by $|w\rangle$ and
the uniform superposition of the non-solutions.

The optimal number of iterations is
$$k \approx \frac{\pi}{4}\sqrt{N}$$

## Do not over-rotate

Because it is a rotation, **more iterations is not better**. Run past the optimum and you
rotate away from the answer and the success probability falls again. Grover's algorithm is
periodic, and this surprises people the first time they see it.

## The two-qubit case

For $N = 4$ with one marked item, $\theta = 2\arcsin(1/2) = 60°$, and a *single*
iteration rotates the state exactly onto $|w\rangle$. You find the answer with
**probability 1** in one query.

Circuit for marking $|11\rangle$:

1. H q0, H q1
2. Oracle: CZ q0, q1
3. Diffuser: H q0, H q1 → X q0, X q1 → CZ q0, q1 → X q0, X q1 → H q0, H q1
4. Measure both

Result: `11` with essentially 100% probability.

### Building CZ from the palette

If you only have CX, note that $CZ = (I \otimes H)\,CX\,(I \otimes H)$: put an H on the
target before and after the CX.

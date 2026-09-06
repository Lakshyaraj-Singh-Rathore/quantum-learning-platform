# Deutsch-Jozsa and Quantum Parallelism

The Deutsch-Jozsa algorithm is the classic first demonstration that a quantum computer can
beat a classical one *with certainty*, not just on average.

## The problem

You are given a black-box function $f:\{0,1\}^n \to \{0,1\}$ with a promise: it is either
**constant** (same output for every input) or **balanced** (0 for exactly half the inputs,
1 for the other half). Decide which.

Classically, in the worst case you must query $2^{n-1}+1$ inputs. Quantum mechanically,
**one** query suffices.

## The phase kickback trick

The oracle is implemented reversibly as

$$U_f: |x\rangle|y\rangle \mapsto |x\rangle|y \oplus f(x)\rangle$$

Prepare the target qubit in $|-\rangle = (|0\rangle - |1\rangle)/\sqrt2$. Then

$$U_f|x\rangle|-\rangle = (-1)^{f(x)}|x\rangle|-\rangle$$

The target is unchanged, but a **phase** $(-1)^{f(x)}$ has been "kicked back" onto the
control register. Phase kickback appears again in Grover, in phase estimation and in Shor.

## The algorithm

1. Start with $n$ query qubits in $|0\rangle$ and one target in $|1\rangle$.
2. Apply H to all of them (target becomes $|-\rangle$).
3. Apply the oracle once.
4. Apply H to the query qubits.
5. Measure the query register.

If you measure **all zeros**, $f$ is constant. **Any other outcome** means balanced.

## Why it works

After step 3 the query register is $\frac{1}{\sqrt{2^n}}\sum_x (-1)^{f(x)}|x\rangle$.
The final Hadamards make the amplitude of $|0\cdots0\rangle$ equal to
$\frac{1}{2^n}\sum_x (-1)^{f(x)}$.

- Constant $f$: every term has the same sign, the sum is $\pm1$, so $|0\cdots0\rangle$ has
  probability 1 - **constructive interference**.
- Balanced $f$: half the terms are $+1$ and half are $-1$, they cancel exactly, so the
  probability of $|0\cdots0\rangle$ is 0 - **destructive interference**.

The lesson: the speed-up is not "trying all inputs at once". Superposition alone gives you
nothing, because measurement returns a single random branch. The power comes from
engineering interference so that the answer you want survives and the rest cancels.

## Build it

A 2-qubit balanced example: H on q0 and q1, a CNOT from q0 to q1 as the oracle
(this computes $f(x)=x_0$), then H on q0, then measure q0. You should get `1` every time.

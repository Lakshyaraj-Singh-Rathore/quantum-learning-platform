# HHL Linear Systems

HHL solves a system of linear equations in time polylogarithmic in the
dimension — an exponential improvement over the best classical methods, on the
face of it. It is also the most heavily qualified result in quantum algorithms,
and the qualifications are not pedantry: they determine whether the algorithm is
useful at all. This lesson presents both the algorithm and its fine print with
equal weight.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the linear systems problem HHL addresses, and what it means to
  "solve" it in this setting.
- **Outline** the HHL circuit: phase estimation, controlled inversion, and
  uncomputation.
- **List** the caveats that limit the claimed speed-up, and explain which one
  usually bites first.

## Prerequisites

This lesson assumes [Quantum Phase Estimation](32_phase_estimation.md). It
assumes what eigenvalues and condition numbers are.

## The problem

Given an $N \times N$ Hermitian matrix $A$ and a vector $b$, find $x$ with

$$Ax = b$$

Classically, solving this costs $O(N \cdot \text{poly}(\kappa))$ for a sparse
matrix, where $\kappa$ is the condition number — the ratio of the largest to
smallest eigenvalue magnitude. HHL runs in
$O(\log N \cdot \text{poly}(\kappa))$ — **exponentially faster in $N$**.

### What "solve" means here, and does not

This is the first caveat and the most important. HHL does **not** output the
vector $x$. It prepares the quantum state

$$|x\rangle = \frac{\sum_i x_i |i\rangle}{\|\sum_i x_i |i\rangle\|}$$

from which you can only extract **expectation values** $\langle x|M|x\rangle$ by
measurement. You cannot read out all $N$ components — that would need
exponentially many measurements and destroys the advantage.

So HHL is useful when you need a *summary statistic* of the solution, not the
solution itself. Knowing the average stress across a structure is fine;
needing the stress at every point is not.

## The circuit

### Eigenvalues are the key

Write $b$ in the eigenbasis of $A$. If $A|u_j\rangle = \lambda_j|u_j\rangle$ and
$b = \sum_j \beta_j |u_j\rangle$, then

$$x = A^{-1}b = \sum_j \frac{\beta_j}{\lambda_j}|u_j\rangle$$

So the task reduces to: decompose into eigenstates, divide each amplitude by
its eigenvalue, and recombine. Phase estimation handles the decomposition; a
controlled rotation handles the division.

### Three stages

1. **Phase estimation.** Apply phase estimation to $e^{iAt}$ with $|b\rangle$ as
   the input. This produces $\sum_j \beta_j |u_j\rangle|\lambda_j\rangle$, with
   the eigenvalue in a register.
2. **Controlled inversion.** Rotate an ancilla conditioned on $|\lambda_j\rangle$
   by an angle $\theta_j$ with $\sin(\theta_j/2) = C/\lambda_j$, where
   $C \leq \min_j|\lambda_j|$ is a normalisation constant. This multiplies the
   amplitude by $C/\lambda_j$ — the inversion — and flags success on the
   ancilla. Division by a small eigenvalue is the dangerous case, which is why
   $C$ is bounded by the smallest eigenvalue.
3. **Uncompute.** Undo the phase estimation, leaving the eigenstate register in
   a state proportional to $|x\rangle$ and the eigenvalue register returned to
   zero. Measure the ancilla; on success, the state is $|x\rangle$.

The uncomputation matters: without it the eigenvalue register stays entangled
with the result and the interference is destroyed.

### A verified example

Take

$$A = \begin{pmatrix} 1 & -1/3 \\ -1/3 & 1 \end{pmatrix}, \qquad b = \begin{pmatrix}1\\0\end{pmatrix}$$

The eigenvalues are $2/3$ and $4/3$. The classical solution is

$$x = A^{-1}b = \begin{pmatrix} 1.125 \\ 0.375 \end{pmatrix}$$

Running the HHL procedure — decompose, divide by $\lambda_j$, recombine —
produces the normalised state $(0.948683,\ 0.316228)$, which matches
$x/\|x\|$ **exactly**, with fidelity $1.0$.

The inversion amplitudes for this case: with $C = 2/3$, the ratio $C/\lambda$ is
$1.0$ for $\lambda = 2/3$ and $0.5$ for $\lambda = 4/3$.

## The caveats

This is the part that determines whether HHL applies to your problem.

### 1. You only get expectation values

You receive $|x\rangle$, not $x$. Extracting all $N$ components costs
$O(N)$ measurements and forfeits the speed-up. You need a task expressible as
$\langle x|M|x\rangle$.

### 2. The matrix must be sparse or efficiently simulable

Phase estimation needs to apply $e^{iAt}$. That requires $A$ to be **sparse**
(few non-zeros per row) or to have some other structure permitting efficient
Hamiltonian simulation. A dense unstructured $A$ cannot be handled.

### 3. State preparation of $b$ must be efficient

You must prepare $|b\rangle$. For a general $N$-dimensional $b$ this costs
$O(N)$ — again destroying the advantage. This is fine when $b$ has structure
(a uniform superposition, or the output of another efficient routine) and fatal
otherwise.

### 4. The condition number is in the exponent of the cost

The runtime is polynomial in $\kappa$, and the **success probability degrades as
$1/\kappa^2$** because of the controlled rotation and post-selection:

| $\kappa$ | Success probability $\sim 1/\kappa^2$ |
|---|---|
| 2 | $2.5\times10^{-1}$ |
| 10 | $1.0\times10^{-2}$ |
| 100 | $1.0\times10^{-4}$ |
| 1000 | $1.0\times10^{-6}$ |

An ill-conditioned matrix therefore needs exponentially many repetitions. Since
many practical linear systems are ill-conditioned, this is often the binding
constraint. Amplitude amplification can improve the dependence, but cannot
remove it.

### 5. Well-conditioned, sparse, and structured is a narrow target

For the speed-up to survive, you need all of: sparse or efficiently simulable
$A$, efficient preparation of $|b\rangle$, small $\kappa$, and a task needing
only expectation values. That combination is real but narrow, and it is why HHL
is best described as a template with a provable exponential advantage under
stated conditions, rather than a general-purpose linear solver.

### 6. Error and precision

The eigenvalue register has finite size, so $\lambda_j$ is known only
approximately, and the inversion inherits that error. Precision costs qubits.

## Practical example

### The linear algebra HHL performs

```python
import numpy as np

A = np.array([[1, -1 / 3], [-1 / 3, 1]], dtype=complex)
b = np.array([1, 0], dtype=complex)

w, V = np.linalg.eigh(A)          # A is Hermitian, so use eigh
print("eigenvalues:", np.round(w, 6))

# 1. decompose b in the eigenbasis
beta = V.conj().T @ b
print("b in the eigenbasis:", np.round(beta, 6))

# 2. the inversion: divide each amplitude by its eigenvalue
inverted = beta / w

# 3. recombine -> the state |x>
x_quantum = inverted @ V.conj().T
x_quantum = x_quantum / np.linalg.norm(x_quantum)

x_classical = np.linalg.solve(A, b)
x_classical = x_classical / np.linalg.norm(x_classical)

print("HHL state      :", np.round(x_quantum, 6))
print("classical x    :", np.round(x_classical, 6))
print("fidelity       :",
      round(abs(np.vdot(x_classical, x_quantum)) ** 2, 6))
```

### The inversion rotation and the condition number

```python
C = min(abs(w))
print(f"\nnormalisation C = {C:.6f}  (must not exceed min |lambda|)")
for lam in w:
    print(f"  lambda={lam:.6f}: sin(theta/2) = C/lambda = {C / lam:.6f}")

print("\ncondition number vs success probability:")
for kappa in (2, 10, 100, 1000):
    print(f"  kappa={kappa:5d}:  ~1/kappa^2 = {1 / kappa ** 2:.2e}")
```

Running the blocks in order reproduces the eigenvalues $2/3$ and $4/3$, the
inversion amplitudes, and a fidelity of $1.0$ against the classical solution.

## Common misconceptions

- **"HHL outputs the solution vector."** It outputs $|x\rangle$, from which you
  can only sample or estimate expectation values.
- **"It is exponentially faster than Gaussian elimination."** Only in the
  dimension $N$, and only when every caveat holds. The cost is polynomial in
  $\kappa$, and the success probability falls as $1/\kappa^2$.
- **"Any matrix works."** $A$ must be sparse or efficiently simulable, and
  $|b\rangle$ must be efficiently preparable.
- **"The condition number is a minor detail."** It governs both runtime and
  success probability, and it is frequently the reason the speed-up evaporates.
- **"The inversion is a unitary division."** Dividing by $\lambda$ is not
  unitary; it is implemented probabilistically via a controlled rotation and
  post-selection on an ancilla.

## Exercises

1. Why must $C \leq \min_j|\lambda_j|$ in the controlled rotation?
2. For the example above, verify by hand that $x = (1.125,\ 0.375)$ satisfies
   $Ax = b$.
3. What is the fidelity if the eigenvalue register has only 3 bits?
4. Give an example of a task where knowing $|x\rangle$ suffices, and one where
   it does not.
5. Why does ill-conditioning hurt the success probability specifically?
6. List the four conditions HHL needs for its advantage to survive.

## Summary

- HHL solves $Ax = b$ in $O(\log N \cdot \text{poly}(\kappa))$ — exponential in
  $N$ — but outputs the **state** $|x\rangle$, not the vector.
- The circuit is phase estimation, a controlled rotation implementing
  $\lambda \mapsto C/\lambda$, then uncomputation and post-selection.
- Verified on a $2\times2$ example: the resulting state matches the classical
  solution with **fidelity 1.0**.
- The caveats are load-bearing: only expectation values are accessible; $A$ must
  be sparse or efficiently simulable; $|b\rangle$ must be efficiently
  preparable; and the success probability degrades as $1/\kappa^2$.
- The advantage survives only when **all** conditions hold simultaneously.

## References

- Harrow, A. W., Hassidim, A. & Lloyd, S. (2009), "Quantum algorithm for linear
  systems of equations".
- Aaronson, S. (2015), "Read the fine print" — the standard critique of the
  caveats summarised here.
- Clader, B. D., Jacobs, B. C. & Sprouse, C. R. (2013) — preconditioning and the
  condition-number problem.
- The [Quantum Phase Estimation](32_phase_estimation.md) lesson — stage one of
  the circuit.

---

**Previous:** [Quantum Phase Estimation](32_phase_estimation.md)

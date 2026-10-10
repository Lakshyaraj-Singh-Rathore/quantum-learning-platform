# U3, iSWAP and fSim

Textbooks write circuits in CNOTs and single-qubit rotations. Real processors
do not run those either — they run *their own* native gates, and the compiler
translates. This lesson introduces the three parameterised gates that show up
again and again in hardware documentation: **U3**, the general single-qubit
gate; **iSWAP**, the native two-qubit gate on several superconducting
platforms; and **fSim**, the two-parameter family Google used on Sycamore.
Knowing what they are, what they cost, and why hardware prefers them is what
lets you read a hardware spec sheet and predict what your circuit will cost.

## Learning objectives

By the end of this lesson you should be able to:

- **Write** the matrix form of U3, iSWAP and fSim.
- **Relate** each gate to the portable rotation-and-CNOT basis, and count the
  CNOTs it costs.
- **Explain** why hardware exposes these gates natively rather than CNOT.
- **Express** iSWAP as the exponential of a two-term generator, and connect the
  number of generator terms to the CNOT cost.
- **Identify** which of these gates are equivalent to each other at special
  parameter values.

## U3: the general single-qubit gate

### Definition

**U3** with parameters $(\theta, \phi, \lambda)$ is

$$U3(\theta,\phi,\lambda) = \begin{pmatrix} \cos\frac{\theta}{2} & -e^{i\lambda}\sin\frac{\theta}{2} \\ e^{i\phi}\sin\frac{\theta}{2} & e^{i(\phi+\lambda)}\cos\frac{\theta}{2} \end{pmatrix}$$

Three real parameters is exactly the right number: a single-qubit unitary has
four real degrees of freedom, and one of them is an unobservable global phase,
so three parameters plus a phase convention covers everything. **U3 is
universal for single-qubit operations** — every single-qubit gate can be
written as one U3.

### Special cases

The familiar gates are particular settings, which is how you sanity-check the
formula:

| Gate | U3 parameters | Verified |
|---|---|---|
| $X$ | $U3(\pi, 0, \pi)$ | yes |
| $H$ | $U3(\tfrac{\pi}{2}, 0, \pi)$ | yes |
| $R_z(\lambda)$ | $U3(0, 0, \lambda)$, up to phase $e^{i\lambda/2}$ | yes |

The $R_z$ case comes with the caveat that matters everywhere in quantum
computing: it matches **up to a global phase** $e^{i\lambda/2}$, which is
physically unobservable, so the two are interchangeable in practice.

U3 is the gate a compiler emits when it has fused a long chain of single-qubit
operations. Rather than storing $R_z\,R_y\,R_z$ as three gates, it collapses
them into one U3 — fewer gates, shorter circuit, less decoherence.

## iSWAP

### Definition

**iSWAP** exchanges the two amplitudes of $|01\rangle$ and $|10\rangle$, and
picks up a phase of $i$ while doing so:

$$\text{iSWAP} = \begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & 0 & i & 0 \\ 0 & i & 0 & 0 \\ 0 & 0 & 0 & 1 \end{pmatrix}$$

So $|01\rangle \mapsto i|10\rangle$ and $|10\rangle \mapsto i|01\rangle$, while
$|00\rangle$ and $|11\rangle$ are untouched. Plain SWAP does the same exchange
without the $i$.

### The generator form

The compact and revealing way to write it is as an exponential:

$$\text{iSWAP} = \exp\!\left[i\frac{\pi}{4}\big(XX + YY\big)\right]$$

This was verified to hold exactly, with no residual phase. The two Pauli terms
in the generator, $XX$ and $YY$, are the *interaction*: the part of the gate
that cannot be undone by single-qubit operations alone.

### Decomposition into CNOTs

iSWAP belongs to the **two-CNOT class**. An explicit decomposition, verified to
reproduce iSWAP exactly with global phase 1:

$$\text{iSWAP} = (H \otimes S)\; \text{CX}_{0\to1}\; (H \otimes H)\; \text{CX}_{0\to1}\; (H \otimes S)$$

Two CNOTs and five single-qubit gates. That is the price of admitting iSWAP
into a CNOT-based circuit.

## fSim

### Definition

**fSim** — "fermionic simulation" — is a two-parameter family:

$$\text{fSim}(\theta,\phi) = \begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & \cos\theta & -i\sin\theta & 0 \\ 0 & -i\sin\theta & \cos\theta & 0 \\ 0 & 0 & 0 & e^{-i\phi} \end{pmatrix}$$

It does two things at once. The $\theta$ parameter continuously interpolates
the swap: it exchanges $|01\rangle$ and $|10\rangle$ with amplitude
$-i\sin\theta$. The $\phi$ parameter applies a phase to $|11\rangle$ only,
which is a controlled-phase.

### Special cases

| Parameters | Gate | Verified |
|---|---|---|
| $\text{fSim}(0, 0)$ | identity | yes |
| $\text{fSim}(-\tfrac{\pi}{2}, 0)$ | iSWAP | yes |
| $\text{fSim}(-\tfrac{\pi}{4}, 0)$ | $\sqrt{\text{iSWAP}}$ | yes |

Watch the sign on the swap angle: it is $\text{fSim}(-\pi/2, 0)$ that equals
iSWAP, **not** $+\pi/2$. With $+\pi/2$ the middle block carries $-i$ where
iSWAP carries $+i$, and the two differ in a way that no global phase can fix.
This sign is a genuine trap.

The generality is the point. One calibrated hardware pulse realises an entire
family of gates, and the compiler picks $\theta$ and $\phi$ per use.

## Why hardware exposes these gates

### Gates come from physics, not from a gate library

A superconducting processor does not have a "CNOT button". Two qubits are
coupled by a fixed physical interaction — typically an exchange coupling whose
Hamiltonian looks like

$$H_{\text{int}} \propto XX + YY$$

Switch it on for a time $t$ and the unitary
$\exp[-iH_{\text{int}}t]$ is generated. That unitary **is** an fSim gate, with
$\theta$ set by the interaction time and $\phi$ by the accumulated controlled
phase. iSWAP is what you get at full swap time.

So the honest statement is not "hardware approximates CNOT" but the reverse:
the hardware natively produces the XY family, and CNOT is *synthesised* from
it — costing two of them, as we saw above.

### The cost hierarchy

The number of Pauli terms in the interaction generator predicts the CNOT cost:

| Gate | Interaction generator | Terms | CNOTs |
|---|---|---|---|
| CZ | $\exp[i\tfrac{\pi}{4}ZZ]$ (up to local gates) | 1 | 1 |
| iSWAP | $\exp[i\tfrac{\pi}{4}(XX+YY)]$ | 2 | 2 |
| SWAP | $\exp[i\tfrac{\pi}{4}(XX+YY+ZZ)]$ (up to phase) | 3 | 3 |

CZ being locally equivalent to a single $ZZ$ interaction was verified directly
from $\text{CZ} = \exp[i\frac{\pi}{4}(I-Z_1)(I-Z_2)]$. SWAP's three-term
generator holds up to a global phase of $e^{-i\pi/4}$, also verified.

Reading the table: a processor whose native gate is iSWAP pays two native
two-qubit gates per CNOT your circuit asks for. If your circuit has 100 CNOTs,
that is 200 hardware two-qubit gates, each with its own error. Choosing an
algorithm whose communication pattern suits the native gate is worth more than
most other optimisations combined.

### Practical consequences

- **Prefer gates close to the native one.** On an iSWAP machine, circuits built
  from iSWAP-like interactions transpile with fewer gates than CNOT-heavy ones.
- **Expect the compiler to rewrite.** Your CNOTs will not survive to the
  hardware; they become native gates plus single-qubit corrections.
- **Check the calibration report.** $\theta$ and $\phi$ are measured per qubit
  pair and drift, so the "same" fSim is slightly different across the chip.

## Practical example

### U3 and its special cases

```python
import numpy as np
from scipy.linalg import expm

X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def U3(theta, phi, lam):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -np.exp(1j * lam) * s],
                     [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
                    dtype=complex)


print("U3(pi,0,pi)  == X:", np.allclose(U3(np.pi, 0, np.pi), X))
print("U3(pi/2,0,pi)== H:", np.allclose(U3(np.pi / 2, 0, np.pi), H))


def rz(lam):
    return np.array([[np.exp(-1j * lam / 2), 0], [0, np.exp(1j * lam / 2)]],
                    dtype=complex)


# Rz appears with a global phase, which is unobservable
for lam in (0.4, 1.3):
    ratio = U3(0, 0, lam)[0, 0] / rz(lam)[0, 0]
    print(f"U3(0,0,{lam}) == e^(i*lam/2) Rz({lam}):",
          np.allclose(U3(0, 0, lam), ratio * rz(lam)),
          " phase:", np.round(ratio, 6))
```

### iSWAP, fSim and the generator forms

```python
XX, YY, ZZ = np.kron(X, X), np.kron(Y, Y), np.kron(Z, Z)
S = np.array([[1, 0], [0, 1j]], dtype=complex)
CN = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
              dtype=complex)          # CNOT, control 0, target 1


def iswap():
    return np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
                    dtype=complex)


def fsim(theta, phi):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1, 0, 0, 0], [0, c, -1j * s, 0],
                     [0, -1j * s, c, 0], [0, 0, 0, np.exp(-1j * phi)]],
                    dtype=complex)


IS = iswap()
print("iSWAP == exp(i*pi/4 (XX+YY)):",
      np.allclose(IS, expm(1j * (np.pi / 4) * (XX + YY))))
print("fSim(-pi/2,0) == iSWAP:", np.allclose(fsim(-np.pi / 2, 0), IS))
print("fSim(+pi/2,0) == iSWAP:", np.allclose(fsim(np.pi / 2, 0), IS))
print("fSim(-pi/4,0) == sqrt(iSWAP):",
      np.allclose(fsim(-np.pi / 4, 0), expm(1j * (np.pi / 8) * (XX + YY))))

# exact two-CNOT decomposition of iSWAP
built = np.kron(H, S) @ CN @ np.kron(H, H) @ CN @ np.kron(H, S)
print("iSWAP == (H⊗S) CNOT (H⊗H) CNOT (H⊗S):", np.allclose(built, IS))
```

### The cost hierarchy

```python
CZ = np.diag([1, 1, 1, -1]).astype(complex)
SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
                dtype=complex)

print("CZ == exp(i*pi/4 (I-Z1)(I-Z2)):",
      np.allclose(CZ, expm(1j * (np.pi / 4) * np.kron(np.eye(2) - Z,
                                                      np.eye(2) - Z))))


def up_to_phase(A, B):
    """True if A = (phase) * B."""
    nz = [(i, j) for i in range(4) for j in range(4) if abs(B[i, j]) > 1e-9]
    r = A[nz[0]] / B[nz[0]]
    return np.allclose(A, r * B), r


local = (np.kron(expm(-1j * (np.pi / 4) * Z), expm(-1j * (np.pi / 4) * Z))
         * np.exp(1j * np.pi / 4))
print("CZ == [local] * exp(i*pi/4 ZZ):",
      up_to_phase(CZ, local @ expm(1j * (np.pi / 4) * ZZ))[0])
print("SWAP == exp(i*pi/4 (XX+YY+ZZ)) up to phase:",
      up_to_phase(SWAP, expm(1j * (np.pi / 4) * (XX + YY + ZZ)))[0])
```

Running the blocks in order confirms $U3(\pi,0,\pi)=X$ and $U3(\pi/2,0,\pi)=H$,
the $R_z$ global-phase relation, iSWAP's generator form, that
$\text{fSim}(-\pi/2,0)$ is iSWAP while $+\pi/2$ is **not**, the exact two-CNOT
decomposition, and the CZ and SWAP generator relations.

## Common misconceptions

- **"fSim$(\pi/2, 0)$ is iSWAP."** It is $-\pi/2$. The wrong sign gives $-i$
  where iSWAP has $+i$, and no global phase repairs it.
- **"U3$(0,0,\lambda)$ equals $R_z(\lambda)$."** It equals $e^{i\lambda/2}$
  times it. The difference is a global phase and is unobservable, but if you
  compare matrices entry by entry you will see the mismatch.
- **"Hardware runs CNOT."** Superconducting hardware natively produces the XY
  family; CNOT is synthesised, at the cost of two native gates.
- **"SWAP is free."** It costs three CNOTs, and on real hardware it is usually
  replaced by routing and gate cancellation instead.
- **"All two-qubit gates cost the same."** The interaction generator determines
  the cost: one Pauli term costs one CNOT, two cost two, three cost three.

## Exercises

1. Write the U3 matrix and show it is unitary for arbitrary
   $\theta, \phi, \lambda$.
2. Find U3 parameters for $Y$ and for $S$, and verify numerically.
3. Verify that $\text{fSim}(-\pi/2, 0)$ is iSWAP but $\text{fSim}(\pi/2, 0)$ is
   not, and explain the difference in terms of the middle block.
4. Using the two-CNOT decomposition, how many native gates does an iSWAP
   machine need for a circuit containing 50 CNOTs?
5. Explain why $\exp[i\frac{\pi}{4}(XX+YY)]$ has two interaction terms while
   CZ has one, and what that implies for cost.
6. Give U3 parameters for $\sqrt{\text{iSWAP}}$'s role as $\text{fSim}(-\pi/4,0)$
   is not applicable — instead, verify that $\text{fSim}(-\pi/4,0)$ squared is
   iSWAP.

## Summary

- **U3$(\theta,\phi,\lambda)$** is the universal single-qubit gate; $X$ and $H$
  are special cases, and $R_z(\lambda)$ is one up to a global phase.
- **iSWAP** is $\exp[i\frac{\pi}{4}(XX+YY)]$ and costs **2 CNOTs**, via the
  exact decomposition $(H\otimes S)\,\text{CX}\,(H\otimes H)\,\text{CX}\,(H\otimes S)$.
- **fSim$(\theta,\phi)$** interpolates the swap with $\theta$ and applies a
  controlled phase with $\phi$; $\text{fSim}(-\pi/2,0)$ is iSWAP.
- The number of Pauli terms in the interaction generator sets the CNOT cost:
  **CZ 1, iSWAP 2, SWAP 3**.
- Hardware exposes these gates because they are what the physical coupling
  Hamiltonian generates — CNOT is the synthesised one, not the native one.

## References

- Qiskit documentation, *U3Gate* — the parameter convention used here.
- Cirq documentation, *ISWAP and fSim gates* — the XY-family conventions and
  the sign of the swap angle.
- Arute, F. et al. (2019), "Quantum supremacy using a programmable
  superconducting processor" — fSim as the Sycamore native gate.
- The [Toffoli and Multi-Controlled Gates](38_multi_controlled.md) lesson —
  decomposition cost in the other direction.

---

**Previous:** [Toffoli, Multi-Controlled Gates and Controlled Rotations](38_multi_controlled.md)

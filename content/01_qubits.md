# Qubits and Superposition

A **classical bit** is either 0 or 1. A **qubit** can be in any *superposition* of the
two computational basis states $|0\rangle$ and $|1\rangle$:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle, \qquad |\alpha|^2 + |\beta|^2 = 1$$

The complex numbers $\alpha$ and $\beta$ are **amplitudes**. They are not probabilities:
probabilities are obtained by squaring their magnitudes. This is the Born rule, and it is
why $|\alpha|^2 + |\beta|^2$ must equal 1 - the qubit has to be found *somewhere*.

## Why amplitudes matter more than probabilities

Because amplitudes are complex, they can be **negative or imaginary**, and therefore they
can *cancel*. Two paths leading to the same outcome with amplitudes $+\tfrac{1}{\sqrt2}$
and $-\tfrac{1}{\sqrt2}$ sum to zero: that outcome never happens. This cancellation is
called **destructive interference**, and every quantum speed-up relies on arranging for
wrong answers to interfere destructively while right answers interfere constructively.

## The Bloch sphere

A single-qubit pure state can be written with two angles:

$$|\psi\rangle = \cos\frac{\theta}{2}|0\rangle + e^{i\varphi}\sin\frac{\theta}{2}|1\rangle$$

- $\theta$ is the polar angle: the north pole is $|0\rangle$, the south pole is $|1\rangle$.
- $\varphi$ is the **relative phase**, the rotation around the equator.

Points on the equator are equal superpositions that differ only by phase, e.g.
$|+\rangle = (|0\rangle+|1\rangle)/\sqrt2$ and $|-\rangle = (|0\rangle-|1\rangle)/\sqrt2$.
They give *identical* measurement statistics in the computational basis, yet they behave
completely differently once another gate is applied. Phase is real, physical information.

A **global** phase, however, is unobservable: $|\psi\rangle$ and $e^{i\gamma}|\psi\rangle$
are the same physical state. Only *relative* phases between basis states matter.

## Multiple qubits

An $n$-qubit register lives in a $2^n$-dimensional space and needs $2^n$ complex
amplitudes to describe it. Three qubits need 8 numbers; fifty qubits need more numbers
than there are atoms in a small planet. That exponential growth is the reason classical
simulation of quantum systems is hard - and the reason this platform caps simulations at
a modest number of qubits.

## Bit ordering convention

This platform follows the **Qiskit convention**: in a bitstring like `011`, qubit 0 is the
**rightmost** character. So `001` means qubit 0 is excited and qubits 1 and 2 are in
$|0\rangle$. Every backend in the platform (Aer, Cirq, PennyLane, qBraid) normalizes its
output to this convention so histograms are directly comparable.

## Try it

In the Composer, place a single **H** gate on q0 and press **Measure All (Append)**.
Run it with 1024 shots: you should see roughly 512 counts of `0` and 512 of `1`. Then look
at the phase disk - the amplitudes are equal in magnitude and both real and positive.

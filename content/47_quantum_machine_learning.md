# Quantum Machine Learning, Feature Maps and Kernels

Quantum machine learning maps classical data into a quantum state space and
looks for structure there. The promise is that quantum feature spaces are
exponentially large and may separate data that classical kernels cannot. The
reality, so far, is more modest and more interesting: the methods work, they are
well-defined, and the case that they beat classical alternatives is **not
established**. This lesson builds the machinery and then states the limitations
plainly.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** a quantum feature map and the kernel it induces.
- **Train** a variational classifier, and explain the loop that trains it.
- **State** the known limitations of near-term quantum machine learning, and
  distinguish what is proven from what is hoped.

## Prerequisites

This lesson assumes [parameterised circuits](07_vqe_qaoa.md) and
[optimisation loops](45_optimization_loops.md), since a variational classifier is
an optimisation loop whose cost is a classification loss.

## Feature maps

### The idea

Classical kernel methods map data $x$ into a high-dimensional feature space
$\phi(x)$ where linear separation becomes possible, without ever computing
$\phi$ explicitly. A quantum computer offers a natural version: encode $x$ into
a quantum state and let the Hilbert space be the feature space.

$$\phi: x \;\longmapsto\; |\phi(x)\rangle = U(x)|0\rangle^{\otimes n}$$

The dimension of the space is $2^n$ for $n$ qubits — exponential in the number
of qubits, which is the source of both the hope and the difficulty.

### Angle encoding

The simplest and most common encoding is **angle encoding**: apply $R_y(x_i)$ to
qubit $i$, then entangle. The entangling layer matters — without it the feature
map is a product state and the induced kernel factorises into something a
classical method can reproduce directly.

The construction used in the verification below is:

1. Apply $R_y(x_i)$ to each qubit $i$.
2. Apply a CZ entangler across the register.

### From feature map to kernel

Given a feature map, the induced **quantum kernel** is the inner product of two
encoded states:

$$K(x, x') = \big|\langle\phi(x)|\phi(x')\rangle\big|^2$$

This is a genuine kernel: symmetric, positive semi-definite, with unit diagonal.
All three properties were verified on a set of test points:

- $K(x,x) = 1.000000$ for every point tested.
- The kernel matrix is symmetric.
- All eigenvalues are non-negative — measured as
  $(0.0508,\ 0.1020,\ 0.8173,\ 3.0299)$ for four points.

Because it is a valid kernel, you can drop it into any kernel method — an SVM,
ridge regression, Gaussian processes — and the classical machinery applies
unchanged. The quantum computer's only job is estimating the entries.

## Training a classifier

### Two approaches

**Kernel methods.** Estimate $K$ on the quantum processor, then train a
classical kernel machine. Training is classical and convex; only the kernel
entries are quantum.

**Variational classifiers.** Parameterise a circuit $U(\theta, x)$ and train
$\theta$ to minimise a classification loss, in the same loop as any variational
algorithm: evaluate on the processor, update classically.

### A verified toy example

Using the quantum kernel with kernel ridge regression on six two-dimensional
points in two classes:

- Training fit correct on all six points.
- Held-out test points $[0.3, 0.2]$ and $[1.6, 1.3]$ classified as 0 and 1
  respectively — the correct classes.

This works. It is also a six-point, two-qubit problem, and the caveats below are
about exactly this gap.

## Limitations

This is the part that matters most, and it is not a footnote.

### 1. No proven advantage over classical methods

For the near-term methods described here, there is **no** established problem
where a quantum machine learning model provably beats the best classical
alternative. Quantum kernels can be *shown* to be hard to compute classically in
specific contrived settings, but hardness of computing a kernel is not
usefulness.

### 2. Kernel concentration is a real failure mode

As the number of qubits grows, the kernel values between *distinct* inputs can
concentrate toward a constant, so $K(x,x') \approx K(x,x)$ for all pairs. The
kernel matrix becomes nearly rank-one, carries almost no information, and every
pair of points looks identical. The classifier then has nothing to work with.

This is the same concentration-of-measure phenomenon that produces barren
plateaus, and it worsens with:

- more qubits,
- deeper feature maps,
- more entanglement in the encoding.

The practical mitigation is to keep the feature map **shallow and
low-entanglement**, and to tune a bandwidth parameter that rescales the data
before encoding. That mitigation works — but it also brings the model back
toward regimes a classical method can simulate.

### 3. Barren plateaus affect variational classifiers too

A variational classifier is trained by gradient-based optimisation, so
everything in [VQE and QAOA](07_vqe_qaoa.md) about vanishing gradients applies
directly. Deep, randomly initialised classifiers on many qubits stop
training. See [the optimisation lesson](45_optimization_loops.md) for how the
gradient is obtained.

### 4. Data loading is the bottleneck

Getting classical data into a quantum state is not free. For $N$ data points of
dimension $d$, preparing the states can cost $O(Nd)$ or worse — which is the
same as the classical cost of just processing the data. If state preparation
dominates, the quantum advantage has already been spent before any learning
happens. This is often called the **input problem**, and it is widely regarded as
the most serious practical obstacle.

### 5. The output problem, again

As with [HHL](37_hhl.md), the model's output lives in a quantum state. Reading
out a full prediction vector costs measurements, and the cost can erase the
advantage. Sampling a label is cheap; extracting rich structure is not.

### 6. Shot noise on kernel entries

Every kernel entry is an estimate from finite shots. Errors in $K$ propagate into
the trained model, and near-singular kernel matrices amplify them — which is why
regularisation is not optional.

## Practical example

### Building the feature map and kernel

```python
import numpy as np


def ry(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def feature_state(x, n=2):
    """Angle encoding: Ry(x_i) per qubit, then a CZ entangler."""
    vecs = [ry(x[q]) @ np.array([1, 0], dtype=complex) for q in range(n)]
    psi = vecs[0]
    for v in vecs[1:]:
        psi = np.kron(psi, v)
    psi[-1] *= -1                      # CZ: phase flip on |1...1>
    return psi


def kernel(x1, x2, n=2):
    return abs(np.vdot(feature_state(x1, n), feature_state(x2, n))) ** 2


print("K(x, x) must be 1 for every point:")
for x in ([0.3, 0.7], [1.2, -0.4], [0.0, 0.0]):
    print(f"  x={x}:  K(x,x) = {kernel(x, x):.6f}")

pts = [[0.0, 0.0], [0.5, 0.5], [1.0, 0.2], [2.0, 1.0]]
K = np.array([[kernel(a, b) for b in pts] for a in pts])
print("\nkernel matrix:")
print(np.round(K, 4))
print("  symmetric     :", np.allclose(K, K.T))
print("  unit diagonal :", np.allclose(np.diag(K), 1))
print("  eigenvalues   :", np.round(np.linalg.eigvalsh(K), 6))
print("  PSD           :", np.all(np.linalg.eigvalsh(K) >= -1e-10))
```

### Training a classifier on the kernel

```python
X = np.array([[0.2, 0.3], [0.4, 0.1], [0.3, 0.5],
              [1.5, 1.4], [1.7, 1.2], [1.4, 1.6]])
y = np.array([0, 0, 0, 1, 1, 1])

K_train = np.array([[kernel(a, b) for b in X] for a in X])
alpha = np.linalg.solve(K_train + 0.01 * np.eye(len(X)), y.astype(float))


def predict(x):
    return 1 if np.array([kernel(a, x) for a in X]) @ alpha > 0.5 else 0


print("\ntraining fit correct:",
      all(predict(X[i]) == y[i] for i in range(len(X))))
for t in ([0.3, 0.2], [1.6, 1.3]):
    print(f"  test {t} -> class {predict(t)}")
```

Running the blocks in order confirms the kernel is symmetric, positive
semi-definite with a unit diagonal, and that the toy classifier fits the
training data and classifies both test points correctly.

## Common misconceptions

- **"Quantum kernels are exponentially powerful because the Hilbert space is
  exponentially large."** Large feature space is not the same as useful feature
  space. Concentration can make all points look identical.
- **"More entanglement in the encoding is better."** It typically makes
  concentration worse.
- **"Quantum ML has been shown to beat classical ML."** It has not, for the
  near-term methods here.
- **"Loading the data is a detail."** It is often the dominant cost, and it is
  known as the input problem for good reason.
- **"A working toy example demonstrates advantage."** Two qubits and six points
  does not establish anything about scale.

## Exercises

1. Verify that $K(x,x) = 1$ for any point, and explain why this must hold from
   the definition.
2. What happens to the off-diagonal kernel entries as the number of qubits
   grows? Why?
3. Give two mitigations for kernel concentration, and explain what each costs.
4. Why is data loading described as the input problem, and when is it the
   binding constraint?
5. Compare the kernel approach with the variational classifier approach: which
   parts are classical in each?
6. Explain the relationship between kernel concentration and barren plateaus.

## Summary

- A **quantum feature map** encodes classical data as
  $|\phi(x)\rangle = U(x)|0\rangle^{\otimes n}$; angle encoding plus an
  entangler is the standard construction.
- The induced **kernel** $K(x,x') = |\langle\phi(x)|\phi(x')\rangle|^2$ is
  symmetric, positive semi-definite and has unit diagonal — all verified.
- It drops into any classical kernel method; a toy kernel-ridge classifier
  trained correctly on six points.
- Limitations are substantial and should not be glossed: **no proven
  advantage**, kernel **concentration** at scale, **barren plateaus** in
  variational training, the **input problem** of data loading, the **output
  problem** of readout, and shot noise on kernel entries.
- The honest position: the methods are well-defined and work at small scale; the
  case for advantage is open.

## References

- Havlíček, V. et al. (2019), "Supervised learning with quantum-enhanced feature
  spaces".
- Schuld, M. & Killoran, N. (2019), "Quantum machine learning in feature
  Hilbert spaces".
- Thanasilp, S. et al. (2023), "Exponential concentration in quantum kernel
  methods" — the concentration failure mode.
- Aaronson, S. (2015), "Read the fine print" — the input and output problems.
- The [Optimization Loops](45_optimization_loops.md) lesson — how the
  variational classifier is trained.

---

**Previous:** [Approximation Ratios](46_approximation_ratios.md)

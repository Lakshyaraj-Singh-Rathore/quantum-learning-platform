# Complex Numbers and Euler's Formula

Every amplitude in quantum mechanics is a complex number. That is not a
mathematical convenience bolted on afterwards: if amplitudes were ordinary real
numbers, interference could not happen, and without interference there is no
quantum speed-up at all. This lesson builds the complex numbers from the one
new idea they introduce — a number whose square is $-1$ — and ends at Euler's
formula, which is the single identity used most often in this course. It is the
first lesson of the mathematical foundations section and everything in it is
assumed by the linear algebra, eigenvalue and statistics lessons that follow.

## Learning objectives

By the end of this lesson you should be able to:

- **Convert** a complex number between rectangular form $a + bi$ and polar
  form $r e^{i\theta}$ in both directions.
- **Derive** Euler's formula $e^{i\theta} = \cos\theta + i\sin\theta$ from the
  Taylor series of the exponential, cosine and sine.
- **Compute** the magnitude and phase of a complex amplitude, and use the
  conjugate to find $|z|^2 = z^* z$.
- **Explain** why a global phase $e^{i\phi}$ has no effect on measurement
  probabilities while a relative phase does.
- **Implement** complex amplitude arithmetic in Python and verify the results
  numerically.

## Why quantum mechanics needs complex numbers

Real numbers can add and cancel: $3 + (-3) = 0$. Complex numbers can do
something richer, because they carry **two** independent pieces of information
in one object — a magnitude and an angle. Two complex numbers of the same
magnitude can still cancel exactly if their angles differ by $\pi$, and the
*angle* is what lets amplitudes interfere constructively or destructively
depending on the path taken.

In quantum mechanics the magnitude squared of an amplitude gives a probability,
and the angle is what drives interference. A real-valued theory would have
amplitudes with only two possible angles ($0$ or $\pi$), which is too poor a
structure to produce the interference patterns quantum mechanics predicts and
experiments confirm.

## The imaginary unit

### Intuition

The equation $x^2 = -1$ has no solution among the real numbers, because a real
number squared is never negative. Rather than declare the equation defective,
we **extend** the number system by adjoining a new symbol $i$ defined by the
property we want.

### Formal definition

The **imaginary unit** $i$ is defined by

$$i^2 = -1$$

A **complex number** is a number of the form

$$z = a + bi, \qquad a, b \in \mathbb{R}$$

where $a$ is the **real part**, $\operatorname{Re}(z) = a$, and $b$ is the
**imaginary part**, $\operatorname{Im}(z) = b$. Note that the imaginary part is
the real number $b$, not $bi$.

### Arithmetic

Addition and multiplication follow from ordinary algebra together with
$i^2 = -1$:

$$(a + bi) + (c + di) = (a + c) + (b + d)i$$

$$(a + bi)(c + di) = (ac - bd) + (ad + bc)i$$

Division uses the **complex conjugate** $\bar{z} = z^* = a - bi$. Multiplying
numerator and denominator by the conjugate of the denominator clears the
imaginary part from the denominator:

$$\frac{a + bi}{c + di} = \frac{(a + bi)(c - di)}{(c + di)(c - di)} = \frac{(ac + bd) + (bc - ad)i}{c^2 + d^2}$$

### Worked example: multiplication and division

Take $z_1 = 1 + 2i$ and $z_2 = 3 - i$.

Multiplication, using the formula above with $a=1, b=2, c=3, d=-1$:

$$z_1 z_2 = (1\cdot 3 - 2 \cdot (-1)) + (1 \cdot (-1) + 2 \cdot 3)i = 5 + 5i$$

Division:

$$\frac{z_1}{z_2} = \frac{(1 + 2i)(3 + i)}{3^2 + (-1)^2} = \frac{(3 - 2) + (1 + 6)i}{10} = \frac{1 + 7i}{10} = 0.1 + 0.7i$$

## Magnitude, phase and the polar form

### The complex plane

A complex number can be drawn as a point in the **complex plane** (also called
an Argand diagram), with the real part on the horizontal axis and the imaginary
part on the vertical axis. This picture is what makes the polar form natural.

### Mathematics

The **magnitude** (or modulus, or absolute value) is the distance from the
origin:

$$|z| = \sqrt{a^2 + b^2}$$

The **phase** (or argument) is the angle from the positive real axis:

$$\theta = \arg(z) = \operatorname{atan2}(b, a)$$

The relationship $|z|^2 = z^* z$ is the one you will use constantly, because it
converts a complex amplitude into a real probability:

$$z^* z = (a - bi)(a + bi) = a^2 + b^2 = |z|^2$$

Every complex number can be written in **polar form** using $a = r\cos\theta$
and $b = r\sin\theta$:

$$z = r(\cos\theta + i\sin\theta), \qquad r = |z|$$

### Worked example: converting to polar form

Convert $z = 1 + i$.

$$r = \sqrt{1^2 + 1^2} = \sqrt{2} \approx 1.4142$$

$$\theta = \operatorname{atan2}(1, 1) = \frac{\pi}{4} \text{ rad} = 45^\circ$$

So $z = \sqrt{2}\, e^{i\pi/4}$. Going the other way, $r = 2$, $\theta = \pi/3$
gives

$$2e^{i\pi/3} = 2\left(\cos\frac{\pi}{3} + i\sin\frac{\pi}{3}\right) = 2(0.5 + 0.8660i) = 1 + 1.7321i$$

where $1.7321 \approx \sqrt{3}$.

## Euler's formula

### Derivation from Taylor series

The three series involved, valid for all real $\theta$, are

$$e^{x} = \sum_{n=0}^{\infty} \frac{x^n}{n!}, \qquad \cos\theta = \sum_{n=0}^{\infty} \frac{(-1)^n \theta^{2n}}{(2n)!}, \qquad \sin\theta = \sum_{n=0}^{\infty} \frac{(-1)^n \theta^{2n+1}}{(2n+1)!}$$

Substitute $x = i\theta$ into the exponential series and use
$i^2 = -1$, $i^3 = -i$, $i^4 = 1$, which then repeats with period 4:

$$e^{i\theta} = 1 + i\theta + \frac{(i\theta)^2}{2!} + \frac{(i\theta)^3}{3!} + \frac{(i\theta)^4}{4!} + \cdots = \left(1 - \frac{\theta^2}{2!} + \frac{\theta^4}{4!} - \cdots\right) + i\left(\theta - \frac{\theta^3}{3!} + \frac{\theta^5}{5!} - \cdots\right)$$

The bracketed real part is exactly the series for $\cos\theta$ and the
bracketed imaginary part is exactly the series for $\sin\theta$. Therefore

$$e^{i\theta} = \cos\theta + i\sin\theta$$

This is **Euler's formula**. Setting $\theta = \pi$ gives the celebrated
identity $e^{i\pi} + 1 = 0$.

### The compact polar form

Combining Euler's formula with the polar form gives the most useful
representation of a complex number in quantum mechanics:

$$z = r e^{i\theta}, \qquad r = |z|, \quad \theta = \arg(z)$$

Two immediate consequences matter throughout the course. First,
$|e^{i\theta}| = 1$ for every real $\theta$ — multiplying by $e^{i\theta}$
rotates without stretching. Second, multiplying two complex numbers multiplies
their magnitudes and *adds* their phases:

$$r_1 e^{i\theta_1} \cdot r_2 e^{i\theta_2} = r_1 r_2 \, e^{i(\theta_1 + \theta_2)}$$

### Worked example: the quarter phases

Because $\cos$ and $\sin$ are known exactly at multiples of $\pi/2$, four phases
come up repeatedly:

| $\theta$ | $e^{i\theta}$ | Value |
|---|---|---|
| $0$ | $\cos 0 + i\sin 0$ | $1$ |
| $\pi/2$ | $\cos\frac{\pi}{2} + i\sin\frac{\pi}{2}$ | $i$ |
| $\pi$ | $\cos\pi + i\sin\pi$ | $-1$ |
| $3\pi/2$ | $\cos\frac{3\pi}{2} + i\sin\frac{3\pi}{2}$ | $-i$ |

So $i$ itself is a rotation by a quarter turn: $i = e^{i\pi/2}$.

## Global versus relative phase

A **global phase** multiplies an entire state by $e^{i\phi}$. It is physically
invisible, because measurement probabilities use $|z|^2$ and

$$|e^{i\phi} z|^2 = (e^{i\phi} z)^* (e^{i\phi} z) = e^{-i\phi} e^{i\phi} z^* z = |z|^2$$

A **relative phase** multiplies only *part* of a state. It is physically
observable, because it changes the interference between the parts. Given
$\alpha$ and $\beta$,

$$|\alpha + \beta|^2 \neq |\alpha + e^{i\phi}\beta|^2 \quad \text{in general}$$

Concretely, with $\alpha = \beta = 1/\sqrt{2}$:

- $\phi = 0$: $|1/\sqrt{2} + 1/\sqrt{2}|^2 = |\sqrt{2}|^2 = 2$ (after
  renormalising, probability $1$)
- $\phi = \pi$: $|1/\sqrt{2} - 1/\sqrt{2}|^2 = 0$ — complete destructive
  interference

This distinction — invisible globally, decisive relatively — is the reason
phase appears everywhere in quantum algorithms, and it is revisited in detail
in the superposition lesson.

## Practical example

The following script verifies every identity introduced above numerically.
`1e-15` tolerances are used because floating-point arithmetic cannot represent
$\pi$ or $\sqrt{2}$ exactly.

```python
import cmath
import math

# --- rectangular arithmetic -------------------------------------------------
z1, z2 = 1 + 2j, 3 - 1j
print("z1 * z2      =", z1 * z2)          # (5+5j)
print("z1 / z2      =", z1 / z2)          # (0.1+0.7j)

# --- magnitude via the conjugate -------------------------------------------
z = 3 + 4j
print("|z|^2        =", (z.conjugate() * z).real)   # 25.0
print("abs(z)       =", abs(z))                     # 5.0

# --- polar conversion -------------------------------------------------------
w = 1 + 1j
r, theta = abs(w), cmath.phase(w)
print("|1+i|        =", r)                 # 1.4142135623730951
print("arg(1+i) deg =", math.degrees(theta))  # 45.0
print("round trip   =", cmath.rect(r, theta))  # (1.0000000000000002+1j)

# --- Euler's formula --------------------------------------------------------
for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
    lhs = cmath.exp(1j * angle)
    rhs = complex(math.cos(angle), math.sin(angle))
    print(f"theta={angle:5.2f}  e^(i.theta)={lhs.real:+.4f}{lhs.imag:+.4f}i"
          f"   matches cos+isin: {abs(lhs - rhs) < 1e-15}")

# --- global phase leaves |z|^2 untouched ------------------------------------
amp = 0.3 + 0.4j
for phi in (0, math.pi / 3, math.pi):
    rotated = cmath.exp(1j * phi) * amp
    print(f"phi={phi:5.2f}  |z|^2 = {abs(rotated) ** 2:.6f}")

# --- relative phase does change interference -------------------------------
a = b = 1 / math.sqrt(2)
for phi in (0, math.pi / 2, math.pi):
    print(f"phi={phi:5.2f}  |a + e^(i.phi) b|^2 = {abs(a + cmath.exp(1j * phi) * b) ** 2:.6f}")
```

Running it prints `5.0` for `abs(3+4j)`, `45.0` for `arg(1+i)` in degrees,
`True` for all four Euler checks, and `0.250000` for every global-phase row.
That last number is the point: $|0.3 + 0.4i|^2 = 0.09 + 0.16 = 0.25$, and the
probability stays exactly there no matter what $\phi$ is applied, because a
global phase cannot be detected.

The relative-phase rows are different: `2.000000` at $\phi = 0$, `1.000000`
at $\phi = \pi/2$, and `0.000000` at $\phi = \pi$. That last row is complete
destructive interference, and it is produced entirely by a phase.

## Common misconceptions

- **"The imaginary part of $a + bi$ is $bi$."** No: the imaginary part is the
  real number $b$. The number $bi$ is the imaginary *component*. This matters
  when reading `z.imag` in Python, which returns $b$, not $bi$.
- **"$\sqrt{2}$ and $\pi$ come out exact in code."** They do not. Floating
  point gives `1.4142135623730951`, not $\sqrt{2}$. Always compare with a
  tolerance such as `abs(a - b) < 1e-9` rather than `==`.
- **"Multiplying by $e^{i\phi}$ changes the state."** Multiplying a *whole*
  state by a phase does not change any measurement probability. Multiplying
  *one component* of a superposition does. The word "global" versus
  "relative" is doing real work here.
- **"$|z|^2$ means squaring the complex number."** It means $z^* z$, which is
  always a non-negative real number. The ordinary square $z^2$ is generally
  complex and is a different object entirely.
- **"Euler's formula only holds for small angles."** The Taylor series
  derivation shows it holds for every real $\theta$, with no approximation.

## Exercises

1. Write $z = -1 + i$ in polar form $r e^{i\theta}$, giving $\theta$ in radians
   in the interval $(-\pi, \pi]$.
2. Compute $(2 + 3i)(2 - 3i)$ and confirm that the answer equals $|2 + 3i|^2$.
   Explain why this always happens for a number times its conjugate.
3. Using Euler's formula, show that $\cos\theta = \frac{e^{i\theta} + e^{-i\theta}}{2}$
   and $\sin\theta = \frac{e^{i\theta} - e^{-i\theta}}{2i}$.
4. Let $\alpha = 1/\sqrt{2}$ and $\beta = e^{i\phi}/\sqrt{2}$. For which
   $\phi$ is $|\alpha + \beta|^2$ maximal, and for which is it minimal?
5. A qubit amplitude is $z = \frac{1}{2} + \frac{i}{2}$. What is the
   probability of the corresponding outcome? Is $z = \frac{1}{2} + i$ a valid
   amplitude on its own? Explain.
6. In Python, `(1 + 2j) / (3 - 1j)` returned `0.1+0.7j`. Verify this by hand
   using the conjugate method, and confirm `abs(z1 / z2) == abs(z1) / abs(z2)`.

## Summary

- The imaginary unit satisfies $i^2 = -1$; a complex number is $z = a + bi$
  with real part $a$ and imaginary part $b$.
- The conjugate is $z^* = a - bi$, and the magnitude satisfies the key identity
  $|z|^2 = z^* z$ — the bridge from complex amplitude to real probability.
- Polar form is $z = r e^{i\theta}$ with $r = |z|$ and $\theta = \arg(z)$;
  multiplication multiplies magnitudes and adds phases.
- Euler's formula $e^{i\theta} = \cos\theta + i\sin\theta$ follows directly
  from comparing Taylor series and holds for all real $\theta$.
- A global phase $e^{i\phi}$ is unobservable; a relative phase changes
  interference and is the mechanism behind quantum speed-ups.

## References

- Euler's formula and the Taylor series derivation — standard results in any
  introductory complex analysis text.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §1.2 — the quantum-mechanical motivation for complex
  amplitudes.
- Python documentation, `cmath` module — `cmath.phase`, `cmath.rect` and the
  numerical conventions used above.

---

**Next:** [Vectors, Matrices and Linear Algebra](15_linear_algebra.md), which
uses these amplitudes as the entries of the vectors and matrices that describe
quantum states and gates.

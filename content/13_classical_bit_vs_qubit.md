<!-- track: theory -->
# A Classical Switch vs a Qubit

The most common way to misunderstand quantum computing is to picture a qubit as
a coin that is "secretly heads or tails". This lesson kills that idea with an
experiment you can run in five minutes.

## The classical switch

A light switch is a bit. It is up (1) or down (0). If you flip it twice, it
returns to where it started. If you cover your eyes, it still has a definite
position — you just do not happen to know it.

Two facts define classical bits:

1. The state is always definite, whether or not you look.
2. Looking does not change it.

Both fail for qubits.

## The qubit

A qubit can be in a **superposition**:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle, \qquad |\alpha|^2 + |\beta|^2 = 1$$

$\alpha$ and $\beta$ are complex **amplitudes**, not probabilities. You get
probabilities by squaring their magnitudes — which means amplitudes can be
negative or complex and can therefore **cancel**. Probabilities never cancel.
That single fact is where all quantum advantage comes from.

## The decisive experiment

Here is the experiment that separates the two pictures. Run both in the
Composer.

### The "hidden coin" hypothesis

Suppose H just randomises the qubit to a secret 0 or 1 with 50/50 odds.

**Circuit A.** `H` on q0, then measure.
**Result:** about 512 / 512 out of 1024. Consistent with the hypothesis so far.

**Circuit B.** `H`, then `H` again, then measure.

If the hypothesis were right, the first H picks a secret value, and the second H
randomises again — so you should *still* see 50/50.

**Actual result: `0`, 100% of the time.**

The hypothesis is dead. There was no secret value between the two gates. The
first H produced a genuine superposition, and the second H made the two paths
**interfere**: the amplitudes for reaching $|1\rangle$ cancelled exactly, while
those for $|0\rangle$ reinforced.

### Making the cancellation explicit

Track the amplitude for landing in $|1\rangle$ after `H`,`H`:

- Path 1: $|0\rangle \to |0\rangle \to |1\rangle$, amplitude
  $\tfrac{1}{\sqrt2}\cdot\tfrac{1}{\sqrt2} = +\tfrac12$
- Path 2: $|0\rangle \to |1\rangle \to |1\rangle$, amplitude
  $\tfrac{1}{\sqrt2}\cdot\left(-\tfrac{1}{\sqrt2}\right) = -\tfrac12$

Total: $+\tfrac12 - \tfrac12 = 0$. Zero probability.

A classical coin has no minus signs available. This is the whole game.

### Now break the interference

**Circuit C.** `H`, **measure**, `H`, measure again.

Now you *do* get 50/50. The intermediate measurement destroyed the superposition
and forced a definite value — so the second H really did act on a definite bit.

Three circuits, three different answers:

| Circuit | Result | Interpretation |
|---|---|---|
| `H` | 50/50 | superposition, collapsed at readout |
| `H`,`H` | 100% `0` | interference — no hidden value existed |
| `H`, measure, `H` | 50/50 | measurement forced a classical value |

Circuit B and Circuit C differ **only** by a measurement in the middle. If the
qubit had always held a hidden definite value, they would give the same answer.

## Visualising it: the Bloch sphere

A single qubit's state is a point on the surface of a sphere.

- North pole: $|0\rangle$
- South pole: $|1\rangle$
- Equator: equal superpositions, differing by phase

A classical bit only has access to the two poles. A qubit has the entire
surface. Open the **Bloch** tab after `H` and you will see the arrow lying on
the equator pointing along $+X$ — neither up nor down.

Then apply `Z` and look again: the arrow **rotates around the equator** to
$-X$. The poles-only classical picture has no room for that motion at all, which
is precisely why `Z` is invisible to a measurement but visible to interference.

## Where the analogy really ends: entanglement

One qubit is a point on a sphere. Two qubits are **not** two points.

Build a Bell pair and open the **Bloch** tab: both arrows have zero length. Each
qubit individually is maximally uncertain, yet the pair is perfectly correlated
— measure one and you instantly know the other.

Two classical switches always have a definite joint setting, and each switch has
its own definite state. Entangled qubits have a definite **joint** state and no
individual states at all. There is no classical picture of this. Use the
**Q-sphere** tab, which shows the register as a whole rather than qubit by
qubit.

## Summary

| | Classical bit | Qubit |
|---|---|---|
| States | 0 or 1 | any $\alpha|0\rangle + \beta|1\rangle$ |
| Definite when unobserved? | yes | no |
| Reading it | harmless | collapses the state |
| Can states cancel? | no | yes — negative and complex amplitudes |
| Two of them | two independent bits | can be entangled, with no individual state |
| Geometry | two points | surface of a sphere |

## Exercise

1. Run all three circuits above and record the counts.
2. Explain in one sentence why B and C differ.
3. Run `H`,`Z`,`H` and predict the answer before you look. (It is `1` — the `Z`
   flipped the sign so the interference now cancels $|0\rangle$ instead.)

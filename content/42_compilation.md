# Native Gates, Connectivity and Routing

You write a circuit as if any qubit could interact with any other. Hardware
does not work that way. A superconducting chip has qubits laid out in a graph,
and a two-qubit gate can only run between neighbours in that graph. Everything
else has to be *routed* — physically moved into adjacency with SWAPs. This
lesson explains the constraint, how routing resolves it, and how to estimate
what routing costs you.

## Learning objectives

By the end of this lesson you should be able to:

- **Explain** how the coupling graph constrains which two-qubit gates can run.
- **Describe** how routing inserts SWAPs to satisfy connectivity, and verify a
  routed circuit against the original.
- **Estimate** the depth cost of routing on a simple topology, and compute the
  SWAP count for a given circuit and graph.
- **Compare** a line with a ring, and explain why the topology change matters
  more than it looks.

## The connectivity constraint

### Coupling graphs

A processor exposes a **coupling graph**: vertices are physical qubits, edges
are pairs that can run a native two-qubit gate. Three common shapes:

- **Line** — qubit $i$ connects to $i\pm1$. Simplest to fabricate and wire.
- **Ring** — a line with the ends joined. One extra edge changes the cost
  dramatically.
- **Heavy-hex / grid** — what IBM and Google actually ship: sparse, with a
  few degree-3 junctions among mostly degree-2 qubits.

The graph is fixed by the fabrication. You cannot change it; you can only route
around it.

### What counts as a legal gate

A two-qubit gate between logical qubits $a$ and $b$ can execute directly only
if their physical positions are adjacent in the graph. Everything else needs
routing. Single-qubit gates are unaffected — they act on one qubit and need no
interaction.

This is why connectivity is a *two-qubit* problem exclusively.

## Routing

### The idea

Routing maintains a map from logical qubits to physical positions. When a gate
needs two logical qubits that are not adjacent, the router inserts SWAP gates
along a shortest path in the graph until they are. Each SWAP exchanges the
contents of two neighbouring physical qubits.

Bringing two qubits separated by graph distance $d$ into adjacency costs
$d - 1$ SWAPs. Since a SWAP is three CNOTs:

$$\text{CNOT cost} = 3(d-1) + 1$$

where the final $+1$ is the gate you actually wanted.

### A concrete example

On a **line of five qubits**, a CNOT between logical qubits 0 and 4 sits at
graph distance 4. Routing it:

$$\text{SWAP}(0,1),\; \text{SWAP}(1,2),\; \text{SWAP}(2,3),\; \text{CNOT}(3,4)$$

Three SWAPs, so $3 \times 3 + 1 = 10$ CNOTs to perform one logical CNOT.

This was verified by building the full $32\times32$ matrix of the routed
circuit, undoing the final permutation, and confirming it equals the ideal
$\text{CNOT}(0,4)$ exactly.

### The same gate on a ring

Add one edge — join qubit 4 back to qubit 0 — and qubits 0 and 4 become
**neighbours**. Distance drops from 4 to 1, so the cost is $3(1-1)+1 = 1$
CNOT. The same logical operation goes from **10 CNOTs to 1**.

That is a 10$\times$ difference from a single extra connection, and it is why
topology choice dominates compilation cost.

## Estimating routing cost

### Distance on a line versus a ring

For five qubits, the graph distance between each pair, and the CNOT cost of
routing a gate between them on a line:

| Pair | Line distance | Ring distance | SWAPs (line) | CNOTs (line) |
|---|---|---|---|---|
| (0,1) | 1 | 1 | 0 | 1 |
| (0,2) | 2 | 2 | 1 | 4 |
| (0,3) | 3 | 2 | 2 | 7 |
| (0,4) | 4 | 1 | 3 | 10 |
| (1,4) | 3 | 2 | 2 | 7 |

The ring never does worse, and for the longest-range pairs it does far better,
because it can route the short way around.

### The cost of an all-pairs circuit

Algorithms like the QFT need gates between essentially **every pair** of
qubits. Summing $d-1$ over all pairs gives the total SWAP count:

| Qubits $n$ | Pairs | Native CNOTs | Line SWAPs | Line CNOTs | Ring SWAPs | Ring CNOTs |
|---|---|---|---|---|---|---|
| 4 | 6 | 6 | 4 | 18 | 2 | 12 |
| 5 | 10 | 10 | 10 | 40 | 5 | 25 |
| 6 | 15 | 15 | 20 | 75 | 12 | 51 |
| 8 | 28 | 28 | 56 | 196 | 36 | 136 |
| 10 | 45 | 45 | 120 | 405 | 80 | 285 |

At ten qubits, an all-pairs circuit that needs 45 native CNOTs costs **405**
on a line. That is a ninefold overhead, and every one of those extra gates
adds error.

### The scaling

Dividing the line SWAP count by $n^3$:

| $n$ | SWAPs | SWAPs$/n^3$ |
|---|---|---|
| 5 | 10 | 0.080 |
| 10 | 120 | 0.120 |
| 20 | 1140 | 0.143 |
| 40 | 9880 | 0.154 |
| 80 | 82160 | 0.160 |

The ratio converges to $1/6$, so the total routing cost for an all-pairs
circuit on a line is

$$\text{SWAPs} \;\sim\; \frac{n^3}{6} \quad=\quad \Theta(n^3)$$

Cubic. Doubling the problem size makes routing about eight times more
expensive. This is the practical reason that algorithms with long-range gates
are considered a poor fit for near-term hardware, and why QFT-based algorithms
like Shor's are discussed in terms of qubit *connectivity*, not just qubit
*count*.

## What compilers do about it

Routing is not the only tool, and modern transpilers combine several:

- **Qubit placement** — choosing the initial logical-to-physical mapping well
  removes most SWAPs before routing starts. This is a large part of why
  transpiler output varies between runs.
- **Gate cancellation and rewriting** — fewer gates before routing means fewer
  SWAPs after.
- **Commuting gates past each other** — reordering can expose cheaper routes.
- **Accepting a permutation** — if the qubits end up permuted and nothing
  later depends on their identity, the trailing SWAPs can be dropped.

The last point matters. In the worked example above, three of the SWAPs
happened *before* the gate. If the circuit ends there, the compiler can leave
the qubits permuted and simply relabel the measurement results, saving the
return journey.

## Practical example

### Graph distances on a line and a ring

```python
from collections import deque


def build_line(n):
    g = {i: set() for i in range(n)}
    for i in range(n - 1):
        g[i].add(i + 1)
        g[i + 1].add(i)
    return g


def build_ring(n):
    g = build_line(n)
    g[0].add(n - 1)
    g[n - 1].add(0)
    return g


def distance(g, a, b):
    prev, q = {a: 0}, deque([a])
    while q:
        u = q.popleft()
        if u == b:
            return prev[u]
        for v in g[u]:
            if v not in prev:
                prev[v] = prev[u] + 1
                q.append(v)
    return float("inf")


n = 5
line, ring = build_line(n), build_ring(n)
print("pair     line  ring   SWAPs  CNOTs(line)")
for a, b in ((0, 1), (0, 2), (0, 3), (0, 4), (1, 4)):
    d = distance(line, a, b)
    print(f"({a},{b})      {d}     {distance(ring, a, b)}      "
          f"{d - 1}      {3 * (d - 1) + 1}")
```

### Routing one long-range CNOT, and checking it

```python
import numpy as np


def cnot_mat(c, t, n):
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        M[col ^ (1 << (n - 1 - t)) if (col >> (n - 1 - c)) & 1 else col, col] = 1
    return M


def swap_mat(a, b, n):
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        ba, bb = (col >> (n - 1 - a)) & 1, (col >> (n - 1 - b)) & 1
        r = (col & ~(1 << (n - 1 - a))) | (bb << (n - 1 - a))
        r = (r & ~(1 << (n - 1 - b))) | (ba << (n - 1 - b))
        M[r, col] = 1
    return M


# route logical CNOT(0,4) across a 5-qubit line
ops = [("swap", 0, 1), ("swap", 1, 2), ("swap", 2, 3), ("cnot", 3, 4)]
M = np.eye(1 << n, dtype=complex)
for kind, a, b in ops:
    M = (swap_mat(a, b, n) if kind == "swap" else cnot_mat(a, b, n)) @ M

# undo the final permutation: move physical 3 back to position 0
back = np.eye(1 << n, dtype=complex)
for a, b in ((3, 2), (2, 1), (1, 0)):
    back = swap_mat(a, b, n) @ back

print("\nrouted ops:", ops)
print("routed + unpermuted == ideal CNOT(0,4):",
      np.allclose(back @ M, cnot_mat(0, 4, n)))
```

### Cost of an all-pairs circuit

```python
print("\n n  pairs  native  lineSWAPs  lineCNOTs  ringSWAPs  ringCNOTs")
for nq in (4, 5, 6, 8, 10):
    ln, rg = build_line(nq), build_ring(nq)
    pairs = [(i, j) for i in range(nq) for j in range(i + 1, nq)]
    ls = sum(distance(ln, a, b) - 1 for a, b in pairs)
    rs = sum(distance(rg, a, b) - 1 for a, b in pairs)
    print(f"{nq:2d}  {len(pairs):5d}  {len(pairs):6d}  {ls:9d}  "
          f"{3 * ls + len(pairs):9d}  {rs:9d}  {3 * rs + len(pairs):9d}")

# the cubic scaling
print("\n n   SWAPs   SWAPs/n^3")
for nq in (5, 10, 20, 40, 80):
    t = sum(abs(a - b) - 1 for a in range(nq) for b in range(a + 1, nq))
    print(f"{nq:2d}  {t:6d}   {t / nq ** 3:.4f}")
```

Running the blocks in order prints the distance table, confirms the routed
circuit equals the ideal CNOT once the permutation is undone, gives the
all-pairs cost table (405 CNOTs at $n=10$ against 45 native), and shows
SWAPs$/n^3$ converging toward $1/6$.

## Common misconceptions

- **"My circuit has 100 CNOTs, so it runs 100 gates."** Only if every CNOT
  happens to be between connected qubits. Routing can multiply that several
  times over.
- **"SWAP is a cheap primitive."** It is three CNOTs, and CNOTs are the
  noisiest gates you have.
- **"Adding one connection barely helps."** Closing a line into a ring took
  the example gate from 10 CNOTs to 1.
- **"Routing cost grows with qubit count."** It grows with qubit count *and*
  interaction range — a local circuit on a line routes cheaply, an all-pairs
  circuit routes at $\Theta(n^3)$.
- **"The compiler always puts the qubits back."** It often leaves them
  permuted and relabels the results, which is cheaper.

## Exercises

1. On a 6-qubit line, how many SWAPs does a CNOT between qubits 0 and 5 need?
   What is the CNOT cost?
2. Answer the same question for a 6-qubit ring, and explain the difference.
3. A circuit on 5 qubits needs gates between pairs (0,1), (2,3) and (0,4).
   Compute the total SWAP count on a line.
4. Explain why the routing cost of an all-pairs circuit scales as
   $\Theta(n^3)$ on a line, using the average distance between pairs.
5. Why might a compiler prefer a worse route that leaves qubits permuted?
6. Give an algorithm whose communication pattern suits a line, and one that
   does not.

## Summary

- The **coupling graph** fixes which qubit pairs can interact; only two-qubit
  gates are affected.
- Routing inserts SWAPs along a shortest path. Cost: $3(d-1) + 1$ CNOTs for
  graph distance $d$.
- On a 5-qubit line, CNOT(0,4) costs **10 CNOTs**; on a ring, **1**. One extra
  edge, tenfold difference.
- For an all-pairs circuit, routing on a line costs $\Theta(n^3)$ SWAPs —
  about $n^3/6$. At $n=10$, 45 native gates become 405.
- Compilers mitigate this with good initial placement, gate cancellation,
  commutation, and leaving qubits permuted.

## References

- Qiskit documentation, *transpiler and routing (SabreSwap)* — the placement
  and routing passes used in practice.
- Li, G., Ding, Y. & Xie, Y. (2019), "Tackling the qubit mapping problem for
  NISQ-era quantum devices" — the SWAP-based routing model described here.
- The [Circuit Identities and Simplification](40_circuit_identities.md)
  lesson — SWAP as three CNOTs, and the rewrites that reduce routing cost.
- The [Quantum Fourier Transform](31_qft.md) lesson — an algorithm whose
  all-pairs pattern makes routing expensive.

---

**Previous:** [GHZ versus W States](41_multipartite_entanglement.md)

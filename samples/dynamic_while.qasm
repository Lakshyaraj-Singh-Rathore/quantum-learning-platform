// Dynamic circuit: mid-circuit measurement + if/else + a while loop capped at 32.
// Routed automatically to the Qiskit dynamic engine.
//
// q0 is put into superposition and measured. The if/else entangles the outcome into
// q1's preparation. The while loop then flips and re-measures q0 until c[0] == 0,
// so every shot ends with c[0] = 0.
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
bit[2] c;

h q[0];
c[0] = measure q[0];

if (c[0] == 1) {
  x q[1];
} else {
  id q[1];
}

while (c[0] == 1) {
  x q[0];
  c[0] = measure q[0];
}

c[1] = measure q[1];

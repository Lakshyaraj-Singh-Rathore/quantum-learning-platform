// Grover search on 2 qubits, marked state |11>.
// One iteration is optimal for N=4, so this finds |11> with ~100% probability.
// CZ is built as H-CX-H on the target because CZ is not in the base palette.
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
bit[2] c;

// 1. uniform superposition
h q[0];
h q[1];

// 2. oracle: phase-flip |11>  (CZ)
h q[1];
cx q[0], q[1];
h q[1];

// 3. diffuser: reflect about the mean
h q[0];
h q[1];
x q[0];
x q[1];
h q[1];
cx q[0], q[1];
h q[1];
x q[0];
x q[1];
h q[0];
h q[1];

c[0] = measure q[0];
c[1] = measure q[1];

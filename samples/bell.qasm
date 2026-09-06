// Bell state |Phi+> = (|00> + |11>)/sqrt(2)
// Static circuit: runs on Qiskit Aer, Cirq, PennyLane and qBraid.
// Expected counts: ~50% "00" and ~50% "11", nothing else.
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];

c[0] = measure q[0];
c[1] = measure q[1];

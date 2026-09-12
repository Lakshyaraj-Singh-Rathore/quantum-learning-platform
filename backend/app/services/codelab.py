"""Execute learner-written circuit code and hand the result to a backend.

The learner writes a small program in Qiskit, Cirq or PennyLane that *builds*
a circuit and assigns it to a variable named ``circuit``. This module runs that
program in a separate, restricted process, converts whatever it produced into
the platform IR (via OpenQASM 3), and returns the IR. Execution then goes
through the normal backend path, so the code lab produces exactly the same
result payload -- histogram, metrics, timeline -- as the drag-and-drop composer.

Security posture
----------------
User code is untrusted. It runs in a **subprocess** so that:

  * a hard wall-clock timeout can kill runaway loops (the in-process
    alternative cannot reliably interrupt a tight C-level loop),
  * a crash or ``sys.exit`` cannot take the API worker down,
  * memory can be capped with RLIMIT_AS on POSIX.

The child also drops obvious escape hatches (``open``, ``__import__`` of
non-allowlisted modules, ``subprocess``, ``socket``). This is a teaching
sandbox, not a hostile-code jail: it stops accidents and casual mischief, not a
determined attacker. Deployments exposing this to the public internet should
add OS-level isolation (a container per run, seccomp, or gVisor).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from typing import Any

from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import from_qasm3

#: Wall-clock limit for the learner's program. Building a circuit is fast;
#: anything slower is a bug or a loop, and the user needs to hear about it.
BUILD_TIMEOUT_SECONDS = 12

#: Address-space cap for the child process (POSIX only).
MEMORY_LIMIT_MB = 1024

MAX_CODE_CHARS = 20_000

FRAMEWORKS = ("qiskit", "cirq", "pennylane", "qasm3")

#: Modules the learner's program may import. Everything needed to build a
#: circuit, nothing that reaches the filesystem, network or other processes.
ALLOWED_MODULES = {
    "qiskit",
    "cirq",
    "pennylane",
    "numpy",
    "math",
    "cmath",
    "random",
    "itertools",
    "functools",
    "collections",
    "fractions",
    "decimal",
    "statistics",
    "typing",
    "dataclasses",
    "enum",
    "abc",
    "copy",
    "operator",
    "string",
    "re",
    "json",
    "warnings",
    "sympy",
    "scipy",
    # Quantum ecosystem packages a learner will reasonably reach for. These
    # were missing, so ordinary textbook code (e.g. importing AerSimulator to
    # run a circuit before returning it) failed with a confusing ImportError.
    "qiskit_aer",
    "qiskit_algorithms",
    "qiskit_ibm_runtime",
    "pennylane_lightning",
    "openqasm3",
    "matplotlib",
    "pylatexenc",
    "networkx",
    "pandas",
    # Pure-computation stdlib modules with no filesystem, network or process
    # reach. Blocking these bought no safety and only broke normal programs.
    "heapq",
    "bisect",
    "array",
    "struct",
    "textwrap",
    "pprint",
    "time",
    "datetime",
    "unicodedata",
    "types",
    "numbers",
    "contextlib",
    "hashlib",
    "base64",
    "binascii",
    "uuid",
    "secrets",
    "queue",
    "graphlib",
    "difflib",
    "keyword",
    "reprlib",
    "traceback",
    "inspect",
    "logging",
}


class CodeLabError(Exception):
    """The learner's program could not be turned into a runnable circuit."""


# --------------------------------------------------------------------------- #
# Child program
# --------------------------------------------------------------------------- #
# Runs inside the subprocess. Sets limits, executes the user's code, finds the
# circuit, converts it to QASM3 and prints a JSON envelope on stdout.
_CHILD = r'''
import builtins, json, sys, io, contextlib

LIMIT_MB = {limit_mb}
ALLOWED = set(json.loads({allowed!r}))
FRAMEWORK = {framework!r}
USER_CODE = json.loads(sys.stdin.read())["code"]

try:
    import resource
    nbytes = LIMIT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (nbytes, nbytes))
    # NB: do not set RLIMIT_NPROC to 0. numpy's OpenBLAS spawns worker
    # threads at import time; blocking that makes numpy fail with a
    # misleading "importing from source directory" error. The parent's
    # wall-clock timeout is what actually contains runaway work.
except Exception:
    pass  # non-POSIX: rely on the parent's timeout

_real_import = builtins.__import__


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Allowlist imports, but only those written by the learner.

    Trusted libraries pull in plenty of private modules (``_io``, ``ctypes``,
    ...) as a side effect of being imported. Blocking those breaks qiskit and
    cirq outright, so the check applies only when the import statement is in
    the user's own file -- identified by the filename given to compile().
    """
    # SECURITY: the ``globals`` argument is only populated by the ``import``
    # statement. A direct call -- __builtins__['__import__']('os'), or the
    # same thing from eval() -- passes None, which used to skip the allowlist
    # entirely and hand the learner arbitrary code execution. Trust the actual
    # calling frame instead, exactly as _guarded_open does.
    try:
        caller = sys._getframe(1).f_globals.get("__name__")
    except Exception:
        caller = (globals or {{}}).get("__name__")
    if caller == "__codelab__":
        root = name.split(".")[0]
        if root not in ALLOWED:
            raise ImportError(
                "import of '%s' is not allowed in the code lab. Allowed: %s"
                % (root, ", ".join(sorted(ALLOWED)))
            )
    return _real_import(name, globals, locals, fromlist, level)


_real_open = builtins.open


def _guarded_open(*a, **k):
    """Deny file access to the learner, allow it to trusted libraries."""
    frame = sys._getframe(1)
    if frame.f_globals.get("__name__") == "__codelab__":
        raise PermissionError("file access is disabled in the code lab")
    return _real_open(*a, **k)


def _blocked_input(*a, **k):
    raise PermissionError("input() is not available in the code lab")


builtins.__import__ = _guarded_import
builtins.open = _guarded_open
builtins.input = _blocked_input

# SECURITY: the import hook only sees *new* imports. Dangerous modules that a
# trusted library already pulled in stay reachable as plain attributes --
# numpy.ctypeslib.ctypes.CDLL('libc.so.6').system(...) was a working escape
# that never triggered __import__ at all. Neutralise the dangerous modules in
# the child's module table before the learner's code runs; qiskit, cirq and
# pennylane have all finished importing by this point.
class _Denied:
    def __init__(self, name):
        object.__setattr__(self, "_name", name)

    def _fail(self, *a, **k):
        raise PermissionError(
            "'%s' is not available in the code lab"
            % object.__getattribute__(self, "_name")
        )

    __getattr__ = _fail
    __call__ = _fail


# Only modules the trusted libraries do not need at *call* time can be
# revoked. os/shutil are used internally by qiskit and numpy long after
# import, so replacing them breaks legitimate programs; ctypes is the one that
# grants raw syscalls, and nothing in the science stack calls it on these
# paths. The import hook still blocks every one of them by name.
#
# Swapping sys.modules['ctypes'] is not enough on its own: numpy has not been
# imported yet here, so its own later ``import ctypes`` (made from trusted
# code, which the hook allows) would pull a pristine copy back in. But qiskit
# and numpy genuinely call CDLL while loading, so the module cannot be
# disarmed yet either. _seal_ctypes() is therefore called later, after the
# framework has finished importing and immediately before the learner's code
# runs.
_CTYPES_SAVED = {{}}


def _unseal_ctypes():
    """Restore ctypes for trusted post-processing (QASM conversion)."""
    try:
        import ctypes as _ctypes
    except Exception:
        return
    for _k, _v in _CTYPES_SAVED.items():
        try:
            setattr(_ctypes, _k, _v)
        except Exception:
            pass


_OS_SAVED = {{}}


def _unseal_os():
    """Restore os for trusted post-processing (QASM conversion)."""
    try:
        import os as _os
    except Exception:
        return
    for _k, _v in _OS_SAVED.items():
        try:
            setattr(_os, _k, _v)
        except Exception:
            pass


def _seal_os():
    """Disarm the process/filesystem entry points on the real os module.

    Blocking ``import os`` does not help when a permitted library already
    holds a reference: ``logging.os`` and ``matplotlib.os`` are the same
    module object, and ``logging.os.system(...)`` was a working escape. The
    module cannot simply be replaced -- qiskit, numpy and matplotlib call
    os.path, os.environ and os.fspath constantly -- so only the dangerous
    callables are revoked, leaving path handling intact.
    """
    try:
        import os as _os
    except Exception:
        return

    def _no_os(*a, **k):
        raise PermissionError("this os function is not available in the code lab")

    for _attr in (
        "system", "popen", "execv", "execve", "execvp", "execvpe", "execl",
        "execle", "execlp", "execlpe", "spawnv", "spawnve", "spawnl", "spawnle",
        "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg",
        "remove", "unlink", "rmdir", "removedirs", "rename", "renames",
        "replace", "truncate", "chmod", "chown", "link", "symlink", "mkdir",
        "makedirs", "open", "fdopen", "pipe", "dup", "dup2", "setuid", "setgid",
    ):
        if hasattr(_os, _attr):
            try:
                _OS_SAVED.setdefault(_attr, getattr(_os, _attr))
                setattr(_os, _attr, _no_os)
            except Exception:
                pass


def _seal_subprocess():
    """Disarm subprocess.Popen.

    Blocking ``import subprocess`` is not sufficient: the class is reachable
    without any import at all by walking the type hierarchy --
    ``[c for c in ().__class__.__base__.__subclasses__()
       if 'Popen' in c.__name__][0](['touch', '/tmp/x'])``
    was a working escape. Patching __init__ on the class object itself covers
    every route to it.
    """
    try:
        import subprocess as _sp
    except Exception:
        return

    def _no_popen(*a, **k):
        raise PermissionError("subprocess is not available in the code lab")

    try:
        _sp.Popen.__init__ = _no_popen
    except Exception:
        pass
    for _fn in ("run", "call", "check_call", "check_output", "getoutput"):
        if hasattr(_sp, _fn):
            try:
                setattr(_sp, _fn, _no_popen)
            except Exception:
                pass


def _seal_ctypes():
    try:
        import ctypes as _ctypes
    except Exception:
        return

    def _no_ctypes(*a, **k):
        raise PermissionError("ctypes is not available in the code lab")

    for _attr in (
        "CDLL", "PyDLL", "OleDLL", "WinDLL",
        "cdll", "pydll", "windll", "oledll",
        "LibraryLoader", "dlopen", "memmove", "memset", "string_at", "cast",
    ):
        if hasattr(_ctypes, _attr):
            try:
                _CTYPES_SAVED.setdefault(_attr, getattr(_ctypes, _attr))
                setattr(_ctypes, _attr, _no_ctypes)
            except Exception:
                pass


def emit(payload):
    sys.stdout.write("<<<CODELAB>>>" + json.dumps(payload))
    sys.stdout.flush()


def _qasm2_to_qasm3(text):
    """Parse framework-emitted QASM 2 and re-emit it as QASM 3.

    Cirq and PennyLane both emit gates from qelib1.inc -- swap, sx, u3 and
    friends. Qiskit's strict qasm2.loads does not define those, so a plain
    SWAP failed with "'swap' is not defined in this scope". The legacy
    instruction set is exactly the qelib1 compatibility layer these emitters
    assume.
    """
    from qiskit import qasm2, qasm3 as q3

    try:
        qc = qasm2.loads(text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    except Exception:
        qc = qasm2.loads(text)

    out = q3.dumps(qc)
    # q3.dumps happily emits gates the platform's own importer does not know
    # (u3 from a Cirq PhasedXZGate, for one), so a successful dump is not
    # enough. Confirm the result actually imports, and decompose to the IR's
    # basis if it does not.
    try:
        from_qasm3(out, name="probe")
        return out
    except Exception:
        from qiskit import transpile

        basis = [
            "rx", "ry", "rz", "h", "x", "y", "z", "s", "sdg", "t", "tdg",
            "sx", "cx", "swap", "measure", "reset", "barrier",
        ]
        return q3.dumps(transpile(qc, basis_gates=basis, optimization_level=0))


def to_qasm3(obj, framework):
    """Convert a framework circuit object into OpenQASM 3."""
    if framework == "qiskit":
        from qiskit import qasm3 as q3
        try:
            return q3.dumps(obj)
        except Exception:
            # initialize(), unitary() and other opaque instructions are not
            # directly expressible in QASM3. Decomposing into a standard basis
            # keeps these perfectly ordinary programs working instead of
            # failing with a raw exporter error.
            from qiskit import transpile
            basis = ["rx", "ry", "rz", "h", "x", "y", "z", "s", "t", "cx", "measure", "reset", "barrier"]
            return q3.dumps(transpile(obj, basis_gates=basis, optimization_level=0))

    if framework == "cirq":
        import cirq
        # Cirq exports QASM 2; round-trip through Qiskit to get QASM 3 so the
        # platform has a single import path.
        return _qasm2_to_qasm3(cirq.qasm(obj))

    if framework == "pennylane":
        import pennylane as qml
        # qml.to_openqasm works on a QNode directly and returns QASM 2;
        # round-trip through Qiskit so the platform has one import path.
        if isinstance(obj, qml.QNode):
            try:
                text = qml.to_openqasm(obj)()
            except TypeError as exc:
                if "required positional argument" in str(exc):
                    raise TypeError(
                        "your QNode takes arguments, so the platform does not "
                        "know what values to draw the circuit with. Call it "
                        "once with concrete values and assign the result, e.g. "
                        "'circuit(0.5)', or give the parameters defaults like "
                        "'def circuit(theta=0.5):'."
                    ) from exc
                raise
        elif isinstance(obj, qml.tape.QuantumScript):
            text = qml.to_openqasm(obj)
        else:
            raise TypeError(
                "expected a QNode or QuantumScript, got %s" % type(obj).__name__
            )
        return _qasm2_to_qasm3(text)

    raise ValueError("unknown framework " + framework)


env = {{"__name__": "__codelab__"}}
stdout = io.StringIO()

# Warm the framework up while ctypes still works (qiskit/numpy call CDLL on
# the import path), then revoke it before any learner code executes.
try:
    if FRAMEWORK == "qiskit":
        import qiskit  # noqa: F401
    elif FRAMEWORK == "cirq":
        import cirq  # noqa: F401
    elif FRAMEWORK == "pennylane":
        import pennylane  # noqa: F401
    import numpy  # noqa: F401
except Exception:
    pass
_seal_ctypes()
_seal_subprocess()
_seal_os()

try:
    with contextlib.redirect_stdout(stdout):
        exec(compile(USER_CODE, "<your code>", "exec"), env)
except BaseException as exc:
    emit({{"ok": False, "error": "%s: %s" % (type(exc).__name__, exc),
          "stdout": stdout.getvalue()}})
    sys.exit(0)

obj = env.get("circuit")
if obj is None:
    emit({{"ok": False, "stdout": stdout.getvalue(),
          "error": "Your program finished but never defined `circuit`. "
                   "Assign your circuit to a variable named `circuit`."}})
    sys.exit(0)

try:
    # The learner's code has finished; conversion is our own trusted code and
    # cirq/pennylane touch ctypes on this path.
    _unseal_ctypes()
    _unseal_os()
    qasm = to_qasm3(obj, FRAMEWORK)
except BaseException as exc:
    emit({{"ok": False, "stdout": stdout.getvalue(),
          "error": "Could not convert your circuit to OpenQASM 3 (%s: %s)"
                   % (type(exc).__name__, exc)}})
    sys.exit(0)

emit({{"ok": True, "qasm3": qasm, "stdout": stdout.getvalue()}})
'''


def build_circuit(code: str, framework: str) -> dict[str, Any]:
    """Run the learner's program and return ``{ir, qasm3, stdout}``.

    Raises :class:`CodeLabError` with a message written for a learner, not a
    stack trace, whenever the program cannot yield a circuit.
    """
    if framework not in FRAMEWORKS:
        raise CodeLabError(f"framework must be one of {', '.join(FRAMEWORKS)}")
    if not code.strip():
        raise CodeLabError("Write some code first.")
    if len(code) > MAX_CODE_CHARS:
        raise CodeLabError(
            f"Program is too long ({len(code)} chars, limit {MAX_CODE_CHARS})."
        )

    # OpenQASM 3 is the platform's own format: it is data, not a program, so
    # it is parsed directly and never reaches the code sandbox.
    if framework == "qasm3":
        try:
            ir = from_qasm3(code, name="code-lab")
        except Exception as exc:  # noqa: BLE001
            raise CodeLabError(f"Could not parse your OpenQASM 3: {exc}") from exc
        return {"ir": ir, "qasm3": code, "stdout": ""}

    child = _CHILD.format(
        limit_mb=MEMORY_LIMIT_MB,
        allowed=json.dumps(sorted(ALLOWED_MODULES)),
        framework=framework,
    )

    # Run from an empty directory: the child would otherwise put the API's
    # own source tree on sys.path and shadow real packages.
    try:
        with tempfile.TemporaryDirectory() as workdir:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", textwrap.dedent(child)],
                input=json.dumps({"code": code}),
                capture_output=True,
                text=True,
                timeout=BUILD_TIMEOUT_SECONDS,
                cwd=workdir,
            )
    except subprocess.TimeoutExpired as exc:
        raise CodeLabError(
            f"Your program did not finish within {BUILD_TIMEOUT_SECONDS}s. "
            "Check for an infinite loop, or build a smaller circuit."
        ) from exc

    marker = "<<<CODELAB>>>"
    if marker not in proc.stdout:
        detail = (proc.stderr or proc.stdout or "").strip()[-800:]
        if not detail:
            detail = "the process produced no output (it may have run out of memory)"
        raise CodeLabError(f"Your program crashed: {detail}")

    payload = json.loads(proc.stdout.split(marker, 1)[1])
    if not payload.get("ok"):
        raise CodeLabError(payload.get("error") or "Unknown error.")

    qasm3 = payload["qasm3"]
    try:
        ir = from_qasm3(qasm3, name="code-lab")
    except Exception as exc:  # noqa: BLE001
        # An unbound Parameter reaches here as a symbolic name the platform's
        # numeric-only parameter grammar rejects. Say so plainly rather than
        # surfacing "parameter may only contain pi, numbers...", which gives
        # no hint that the real problem is a free variable.
        if "may only contain" in str(exc):
            raise CodeLabError(
                "Your circuit still has an unbound Parameter. The platform "
                "stores concrete angles, so bind it before returning the "
                "circuit, e.g. "
                "circuit = qc.assign_parameters({theta: 3.14159 / 2})."
            ) from exc
        raise CodeLabError(
            "Your circuit was built but the platform could not import it "
            f"({exc}). Gates outside the supported set can cause this."
        ) from exc

    return {"ir": ir, "qasm3": qasm3, "stdout": payload.get("stdout", "")}


STARTERS: dict[str, str] = {
    "qiskit": textwrap.dedent(
        '''\
        # Build a Bell pair with Qiskit.
        # Assign your finished circuit to a variable named `circuit`.
        from qiskit import QuantumCircuit

        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        '''
    ),
    "cirq": textwrap.dedent(
        '''\
        # Build a Bell pair with Cirq.
        # Assign your finished circuit to a variable named `circuit`.
        import cirq

        q = cirq.LineQubit.range(2)
        circuit = cirq.Circuit(
            cirq.H(q[0]),
            cirq.CNOT(q[0], q[1]),
            cirq.measure(q[0], q[1], key="m"),
        )
        '''
    ),
    "qasm3": textwrap.dedent(
        '''\
        // Write OpenQASM 3 directly -- this is the platform's native format,
        // so it is parsed as-is with no Python involved.
        OPENQASM 3.0;
        include "stdgates.inc";

        qubit[2] q;
        bit[2] c;

        h q[0];
        cx q[0], q[1];
        c[0] = measure q[0];
        c[1] = measure q[1];
        '''
    ),
    "pennylane": textwrap.dedent(
        '''\
        # Build a Bell pair with PennyLane.
        # Assign the QNode to a variable named `circuit`.
        import pennylane as qml

        dev = qml.device("default.qubit", wires=2)

        @qml.qnode(dev)
        def circuit():
            qml.Hadamard(wires=0)
            qml.CNOT(wires=[0, 1])
            return qml.probs(wires=[0, 1])
        '''
    ),
}


__all__ = ["build_circuit", "CodeLabError", "STARTERS", "FRAMEWORKS"]
